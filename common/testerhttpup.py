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
    def write(self, data):
        # An empty string would be interpreted as EOF by the receiving server
        if data:
            self.put(data)

    def __iter__(self):
        return iter(self.get, None)

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
            self.chunk_generator.write(data)
            self.live_queue.put(len(data))
            time.sleep(0.1)

        self.chunk_generator.close()


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
            chunk_generator = ChunkGenerator(self.buffer_size)
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

    def run(self):
        start_measure_time = time.time()
        last_measured_time = time.time()
        measure_count = 0

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

            if current_time - start_measure_time >= MEASURE_TIME + RAMPUP_SECS:
                self.stop_event.set()

        logger.debug("Observer thread stopped")


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

        # Start the timers and counters for overall measurement
        start_bytes = self.netstat.get_tx_bytes()
        start_timestamp = datetime.fromtimestamp(ntptime.timestamp())

        # Start the measurement
        producer.start()
        consumer.start()
        observer.start()

        # Activate the alarm
        timeout.start()

        # Wait for the measurement to finish
        producer.join()
        consumer.join()
        observer.join()

        # Deactivate the alarm for stopping the measurement (at this point the measuremente has finished)
        if timeout.is_alive():
            logger.debug("Timeout terminato")
            timeout.cancel()

        if consumer.errors:
            logger.debug("Errori: %s", consumer.errors)
            # first_error = consumer.errors[0]
            # raise nem_exceptions.MeasurementException(first_error.get("message"), first_error.get("code"))

        if consumer.duration < (MEASURE_TIME * 1000) - 1:
            raise nem_exceptions.MeasurementException("Durata del test insufficiente", nem_exceptions.SERVER_ERROR)

        if consumer.bytes_transferred <= 0:
            raise nem_exceptions.MeasurementException("Ottenuto banda zero", nem_exceptions.ZERO_SPEED)

        total_bytes = self.netstat.get_tx_bytes() - start_bytes
        produced_bytes = observer.total_bytes
        overhead = max(float(total_bytes - produced_bytes) / float(total_bytes), 0)

        bytes_nem = consumer.bytes_transferred
        bytes_tot = int(bytes_nem * (1 + overhead))

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
