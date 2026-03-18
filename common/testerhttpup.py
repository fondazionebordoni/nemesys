# testerhttpup.py
# -*- coding: utf-8 -*-

# Copyright (c) 2015-2017 Fondazione Ugo Bordoni.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import queue
import logging
import random
import socket
import threading
import time
from datetime import datetime
import requests
import re
import json

from common import iptools
from common import nem_exceptions
from common import ntptime
from common.netstat import Netstat
from common.proof import Proof


MEASURE_TIME = 10
RAMPUP_SECS = 2
# Wait another secs in case end of file has not arrived
TIMEOUT_DELAY = 5
# 10 Gbps for measuring time seconds
MAX_TRANSFERED_BYTES = 10 * 1000000 * 1000 * (MEASURE_TIME + RAMPUP_SECS + TIMEOUT_DELAY) / 8
HTTP_TIMEOUT = 8
END_STRING = b"_ThisIsTheEnd_"

logger = logging.getLogger(__name__)
logger_csv = logging.getLogger("csv")


def noop(*args, **kwargs):
    pass


class Result(object):
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error


class ChunkGenerator(queue.Queue):
    def __init__(self, maxsize, stop_event):
        super().__init__(maxsize)
        self.stop_event = stop_event
    
    def write(self, data):
        # An empty string would be interpreted as EOF by the receiving server
        if data:
            self.put(data)

    def __iter__(self):
        """
        Custom iterator that respects stop_event.
        When stop_event is set, immediately sends END_STRING and stops,
        without draining the entire queue.
        """
        while True:
            # CRITICAL: Check stop_event BEFORE reading from queue
            # This prevents consuming hundreds of queued chunks after stop
            if self.stop_event.isSet():
                logger.debug("ChunkGenerator: stop_event detected, sending END_STRING immediately")
                yield END_STRING
                break
            
            try:
                # Use very short timeout (10ms) to check stop_event frequently
                # This ensures we react within 10-20ms when stop_event is set
                chunk = self.get(timeout=0.01)
                
                if chunk is None:
                    # Normal termination (Writer sent None)
                    break
                    
                yield chunk
                
            except queue.Empty:
                # No chunk available, loop back to check stop_event (10ms later)
                continue

    def close(self):
        self.put(END_STRING)
        self.put(None)


class Writer(threading.Thread):
    def __init__(self, stop_event, chunk_generator, live_queue):
        threading.Thread.__init__(self)
        self.stop_event = stop_event
        self.chunk_generator = chunk_generator
        self.live_queue = live_queue

    def run(self):
        while not self.stop_event.isSet():
            data = b"A" * self.chunk_generator.maxsize
            try:
                # Use timeout to avoid blocking indefinitely if queue is full
                self.chunk_generator.put(data, timeout=0.5)
                self.live_queue.put(len(data))
            except queue.Full:
                # Queue is full, slow down and retry
                time.sleep(0.05)
                continue
            time.sleep(0.1)

        # When stop_event is set, ChunkGenerator.__iter__ will automatically
        # send END_STRING and stop. We don't need to close manually.
        # Just drain any remaining items from live_queue to avoid blocking Observer
        try:
            while not self.live_queue.empty():
                self.live_queue.get_nowait()
        except queue.Empty:
            pass
        
        logger.debug("Writer thread stopped")


class Uploader(threading.Thread):
    def __init__(self, stop_event, url, measurement_id, result_queue, tcp_window_size, chunk_generator):
        threading.Thread.__init__(self)
        self.stop_event = stop_event
        self.url = url
        self.measurement_id = measurement_id
        self.result_queue = result_queue
        self.tcp_window_size = tcp_window_size
        self.chunk_generator = chunk_generator

    def run(self):
        response = None
        try:
            headers = {"X-measurement-id": self.measurement_id}
            response = requests.post(self.url, data=self.chunk_generator, headers=headers, timeout=HTTP_TIMEOUT, stream=True)

            logger.debug("Upload completed! Sending stop signal")
            self.stop_event.set()

            if response is None:
                self.result_queue.put(
                    Result(error={"message": "Nessuna risposta dal server", "code": nem_exceptions.BROKEN_CONNECTION})
                )

            elif response.status_code != 200:
                self.result_queue.put(
                    Result(
                        error={
                            "message": f"Errore: [{response.status_code}] {response.status}",
                            "code": nem_exceptions.CONNECTION_FAILED,
                        }
                    )
                )

            else:
                content = response.content.decode("utf-8")
                logger.debug("Risposta dal server: %s", content)
                self.result_queue.put(Result(response=content))

        except Exception as e:
            self.result_queue.put(Result(error={"message": f"Errore: {e}", "code": nem_exceptions.CONNECTION_FAILED}))
        finally:
            if response:
                response.close()

        logger.debug("Uploader thread stopped")


class Producer(threading.Thread):
    def __init__(self, url, stop_event, live_queue, result_queue, num_sessions, tcp_window_size, buffer_size=8192):
        super(Producer, self).__init__()
        self.url = url
        self.stop_event = stop_event
        self.live_queue = live_queue
        self.result_queue = result_queue
        self.num_sessions = num_sessions
        self.tcp_window_size = tcp_window_size
        self.buffer_size = buffer_size

    def run(self):
        measurement_id = "sess-%d" % random.randint(0, 100000)
        for _ in range(0, self.num_sessions):
            chunk_generator = ChunkGenerator(self.buffer_size, self.stop_event)
            writer = Writer(self.stop_event, chunk_generator, self.live_queue)
            uploader = Uploader(
                self.stop_event, self.url, measurement_id, self.result_queue, self.tcp_window_size, chunk_generator
            )

            writer.start()
            uploader.start()

            time.sleep(0.05)


class Observer(threading.Thread):
    def __init__(self, stop_event, live_queue, callback=noop):
        super(Observer, self).__init__()
        self.stop_event = stop_event
        self.live_queue = live_queue
        if callback:
            self.callback = callback
        else:
            self.callback = noop
        self.total_bytes = 0
        self.rampup_complete = threading.Event()  # Signal when rampup phase ends
        self.rampup_timer = None
        self.measure_timer = None

    def run(self):
        start_measure_time = time.time()
        last_measured_time = time.time()
        measure_count = 0

        # Set timer for rampup completion (precise timing)
        self.rampup_timer = threading.Timer(RAMPUP_SECS, self._complete_rampup)
        self.rampup_timer.start()

        while not self.stop_event.isSet():
            time.sleep(1.0)
            current_time = time.time()
            elapsed = current_time - last_measured_time
            measure_count += 1

            tx_bytes = 0
            while not self.live_queue.empty():
                tx_bytes += self.live_queue.get()

            self.total_bytes += tx_bytes

            rate_tot = float(tx_bytes * 8) / float(elapsed * 1000)
            last_measured_time = current_time

            logger.debug(f"[HTTP] Sending... Count = {measure_count}; Speed = {int(rate_tot):,} kbps")
            logger_csv.debug(";%d" % int(rate_tot))

            self.callback(second=measure_count, speed=rate_tot)

        logger.debug("Observer thread stopped")
        
        # Cancel timers if still active
        if self.rampup_timer:
            self.rampup_timer.cancel()
        if self.measure_timer:
            self.measure_timer.cancel()
    
    def _complete_rampup(self):
        """Called by rampup timer after RAMPUP_SECS"""
        self.rampup_complete.set()
        logger.info(f"========== UPLOAD RAMPUP COMPLETE (after {RAMPUP_SECS}s) ==========")
        
        # Start the measurement timer slightly early (9.8s instead of 10s)
        # This gives Uploaders ~200ms to send END_STRING and complete POST cleanly
        # before server times out
        measure_duration = MEASURE_TIME - 0.2
        self.measure_timer = threading.Timer(measure_duration, lambda: self.stop_event.set())
        self.measure_timer.start()
        logger.info(f"========== UPLOAD MEASUREMENT PHASE STARTED (will run for {measure_duration:.1f}s) ==========")


def parse_response(response):
    pattern = r"\[(\s*(\d+)\s*,?)+\]"
    match = re.match(pattern, response)
    if match:
        # Gestisci le risposte del server Python del tipo [<>, <>, <>]
        pattern = r"(?P<bytes>\d+)"

        matches = re.finditer(pattern, response)
        bytes_array = [int(match.group("bytes")) for match in matches]
        bytes_transferred = sum(bytes_array)
        duration = len(bytes_array) * 1000
        logger.debug("Risultato ottenuto: %d bytes in %d ms", bytes_transferred, duration)
        return duration, bytes_transferred, False

    # Gestisci le risposte JSON del tipo {"received": <>, "responseTime": <>, "speed": <>}
    result = json.loads(response)
    logger.debug("Risultato ottenuto: %s", result)
    return result["responseTime"], result["received"], True


class Consumer(threading.Thread):
    def __init__(self, stop_event, result_queue, num_sessions):
        super(Consumer, self).__init__()

        self.stop_event = stop_event
        self.result_queue = result_queue
        self.num_sessions = num_sessions
        self.errors = []

        # Data from server response at the end of the measurement
        self.duration = 0
        self.bytes_transferred = 0

    def run(self):
        for _ in range(self.num_sessions):
            result = self.result_queue.get()

            if result.error:
                self.errors.append(result.error)
            elif result.response:
                try:
                    duration, bytes_transferred, incremental = parse_response(result.response)

                    if duration and bytes_transferred:
                        self.duration = max(self.duration, duration)
                        if incremental:
                            self.bytes_transferred += bytes_transferred
                        else:
                            self.bytes_transferred = max(self.bytes_transferred, bytes_transferred)

                except nem_exceptions.MeasurementException as e:
                    self.errors.append({"message": e.message, "code": e.errorcode})
                except Exception as exception:
                    error_code = nem_exceptions.errorcode_from_exception(exception)
                    self.errors.append({"message": exception.message, "code": error_code})

            else:
                self.errors.append({"message": "No response from server", "code": nem_exceptions.BROKEN_CONNECTION})

        if self.errors:
            logger.error("Consumer thread stopped with errors: %s" % self.errors)

        logger.debug("Consumer thread stopped")


class HttpTesterUp(object):
    def __init__(self, dev):
        self.dev = dev
        self.netstat = Netstat(self.dev)

    def test(self, url, callback_update_speed=noop, num_sessions=1, tcp_window_size=-1, buffer_size=8192):
        # Prepare the measurement
        stop_event = threading.Event()
        result_queue = queue.Queue()
        live_queue = queue.Queue()

        producer = Producer(url, stop_event, live_queue, result_queue, num_sessions, tcp_window_size, buffer_size)
        consumer = Consumer(stop_event, result_queue, num_sessions)
        observer = Observer(stop_event, live_queue, callback_update_speed)

        # Prepare an alarm to stop the measurement if it takes too long
        timeout = threading.Timer(
            MEASURE_TIME + RAMPUP_SECS + TIMEOUT_DELAY,
            lambda: stop_event.set(),
        )

        # Start the timestamp for the overall measurement
        start_timestamp = datetime.fromtimestamp(ntptime.timestamp())

        # Start threads
        producer.start()
        consumer.start()
        observer.start()

        # Activate the alarm
        timeout.start()

        # CRITICAL: Wait for rampup to complete before measuring start_bytes
        # This ensures bytes_tot and bytes_nem are synchronized (both measure same time window)
        logger.info("Waiting for upload rampup to complete...")
        observer.rampup_complete.wait()
        
        # NOW read start_bytes AFTER rampup, so bytes_tot only includes measurement phase
        start_bytes = self.netstat.get_tx_bytes()
        logger.info(f"Upload rampup complete, measurement phase starts now. start_bytes={start_bytes:,}")

        # Wait for the measurement to finish
        producer.join()
        consumer.join()
        observer.join()

        # Deactivate the alarm for stopping the measurement (at this point the measuremente has finished)
        if timeout.is_alive():
            logger.debug("Timeout terminato")
            timeout.cancel()

        if consumer.errors:
            logger.error("Errori durante la misura: %s", consumer.errors)
            first_error = consumer.errors[0]
            raise nem_exceptions.MeasurementException(first_error.get("message"), first_error.get("code"))

        if consumer.duration < (MEASURE_TIME * 1000) - 1:
            raise nem_exceptions.MeasurementException("Durata del test insufficiente", nem_exceptions.SERVER_ERROR)

        if consumer.bytes_transferred <= 0:
            raise nem_exceptions.MeasurementException("Ottenuto banda zero", nem_exceptions.ZERO_SPEED)

        total_bytes = self.netstat.get_tx_bytes() - start_bytes
        produced_bytes = observer.total_bytes
        
        bytes_nem = consumer.bytes_transferred
        bytes_tot = total_bytes

        if bytes_tot > 0:
            overhead = float(bytes_tot - bytes_nem) / float(bytes_tot)
        else:
            overhead = 0
        
        logger.info(f"DEBUG - Upload results: bytes_tot={bytes_tot:,}, bytes_nem={bytes_nem:,}, overhead={overhead*100:.2f}%")
        logger.debug(f"Netstat: dati letti sulla scheda di rete: {total_bytes:,} bytes")
        logger.debug(f"Observer: dati prodotti dal generatore: {observer.total_bytes:,} bytes")
        logger.debug(f"Consumer: dati ricevuti dal server di misura: {consumer.bytes_transferred:,} bytes")
        logger.debug(f"Consumer: tempo di misura: {consumer.duration:,} s")
        logger.debug(f"Dati di misura: {bytes_nem:,} bytes")
        logger.debug(f"Traffico spurio: {overhead*100:.2f}%")
        logger.debug(f"Dati totali (misura + overhead): {bytes_tot:,} bytes")

        logger_csv.debug(
            f";;{total_bytes};{observer.total_bytes};{consumer.bytes_transferred};{overhead};{bytes_tot};{bytes_nem}"
        )

        if overhead < 0:
            raise nem_exceptions.MeasurementException("Traffico spurio negativo", nem_exceptions.NEGATIVE_SPEED)

        if bytes_nem < 0:
            raise nem_exceptions.MeasurementException("Byte di misura trasferiti negativi", nem_exceptions.NEGATIVE_SPEED)

        if bytes_tot < 0:
            raise nem_exceptions.MeasurementException("Byte totali trasferiti negativi", nem_exceptions.NEGATIVE_SPEED)

        return Proof(
            test_type="upload_http",
            start_time=start_timestamp,
            duration=consumer.duration,
            bytes_nem=bytes_nem,
            bytes_tot=bytes_tot,
            spurious=overhead,
        )


def main():
    socket.setdefaulttimeout(10)
    dev = iptools.get_dev()
    print(HttpTesterUp(dev).test("http://{}:8080".format("193.104.137.133")))


if __name__ == "__main__":
    main()
