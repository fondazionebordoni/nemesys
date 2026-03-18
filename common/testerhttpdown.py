# httptesterdown.py
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
import urllib3
import io
import uuid
from datetime import datetime

from common import iptools
from common import nem_exceptions
from common import ntptime
from common.netstat import Netstat
from common.proof import Proof
from common.profile import BW_5M, BW_50M, BW_100M, BW_200M, BW_500M, BW_1000M, BW_2000M

MEASURE_TIME = 10
RAMPUP_SECS = 2
# Wait another secs in case end of file has not arrived
TIMEOUT_DELAY = 5
# 100 Mbps for measuring time seconds
MAX_TRANSFERED_BYTES = 100 * 1000000 * (MEASURE_TIME + RAMPUP_SECS + TIMEOUT_DELAY) / 8
# 10 seconds timeout on open and read operations for HTTP requests
HTTP_TIMEOUT = 2.0
# Consumer queue timeout - longer to avoid false positives on slow lines
CONSUMER_QUEUE_TIMEOUT = 5.0
END_STRING = b"_ThisIsTheEnd_"

MAX_CONNECTIONS = 16

logger = logging.getLogger(__name__)
logger_csv = logging.getLogger("csv")


def noop(*args, **kwargs):
    pass


def get_threads_for_rate(rate):
    rate = rate * 1000

    if rate < BW_5M:
        return 1

    if rate < BW_50M:
        return 2

    if rate < BW_100M:
        return 3

    if rate < BW_200M:
        return 4

    if rate < BW_500M:
        return 6

    if rate < BW_1000M:
        return 8

    if rate < BW_2000M:
        return 12

    return MAX_CONNECTIONS


class Result(object):
    def __init__(self, n_bytes=0, received_end=False, error=None):
        self.n_bytes = n_bytes
        self.received_end = received_end
        self.error = error


class Downloader(threading.Thread):
    """
    Downloader is a subclass of threading.Thread that downloads a file from a given URL over HTTP.
    """

    def __init__(self, uuid, pool, url, stop_event, result_queue, measurement_id, buffer_size):
        """
        Initializes a Downloader object.

        Args:
            url (str): The URL to download the file from.
            stop_event (threading.Event): The event used to stop the download.
            result_queue (Queue): The queue to store the download results.
            measurement_id (str): The ID of the measurement.
            buffer_size (int): The size of the buffer used for reading the file.
        """
        threading.Thread.__init__(self)

        self.id = uuid
        self.pool = pool
        self.url = url
        self.result_queue = result_queue
        self.measurement_id = measurement_id
        self.stop_event = stop_event
        self.buffer_size = buffer_size

        self.headers = {
            "X-requested-file-size": int(MAX_TRANSFERED_BYTES),
            "X-requested-measurement-time": int(MEASURE_TIME + RAMPUP_SECS),
            "X-measurement-id": self.measurement_id,
        }

    def run(self):
        """
        Runs the Downloader thread.

        This method attempts to establish a connection to the specified URL with the given headers.
        If the connection fails, it adds an error message to the result queue and stops the event.
        If the connection is successful but the response code is not 200, it adds another error message to the result queue and stops the event.
        Otherwise, it reads data from the response until it encounters the end of file marker or the stop event is set.
        It keeps track of the number of bytes received and whether the end of file marker was received.
        Finally, it puts the result containing the number of bytes received and whether the end of file marker was received into the result queue and stops the event.
        """

        while not self.stop_event.isSet():
            filebytes = 0

            try:
                logger.debug(f"[{self.id}] Downloading from {self.url} with headers {self.headers}")
                response = self.pool.request("GET", self.url, headers=self.headers, timeout=HTTP_TIMEOUT, preload_content=False)
            except Exception as e:
                error = {
                    "message": "Impossibile creare connessione: {}".format(e),
                    "code": nem_exceptions.CONNECTION_FAILED,
                }
                self.result_queue.put(Result(error=error))
                return

            if response.status != 200:
                error = {
                    "message": f"Connessione HTTP fallita, codice di errore ricevuto: {response.status}",
                    "code": nem_exceptions.CONNECTION_FAILED,
                }
                self.result_queue.put(Result(error=error))
                return

            reader = io.BufferedReader(response, self.buffer_size)
            my_buffer = b""

            # Read from socket until an error occurs or the end of file marker is reached
            while END_STRING not in my_buffer and not self.stop_event.isSet():
                try:
                    my_buffer = reader.read(self.buffer_size)
                    
                    if len(my_buffer) == 0:
                        error = {
                            "message": "Non ricevuti dati sufficienti per completare la misura",
                            "code": nem_exceptions.SERVER_ERROR,
                        }
                        self.result_queue.put(Result(n_bytes=filebytes, error=error))
                        break
                    
                    filebytes += len(my_buffer)

                except socket.timeout:
                    # Exit the loop if the timeout is reached
                    error = {
                        "message": "Non ricevuti dati sufficienti per completare la misura",
                        "code": nem_exceptions.SERVER_ERROR,
                    }
                    self.result_queue.put(Result(n_bytes=filebytes, error=error))
                    break

                except Exception as e:
                    error = {
                        "message": "Errore durante la ricezione dei dati: {}".format(e),
                        "code": nem_exceptions.SERVER_ERROR,
                    }
                    self.result_queue.put(Result(n_bytes=filebytes, error=error))
                    break

            response.release_conn()
            received_end = END_STRING in my_buffer
            logging.debug(f"[{self.id}] Download finished, bytes received: {filebytes}, received_end: {received_end}")
            self.result_queue.put(Result(n_bytes=filebytes, received_end=received_end))

        return


class Consumer(threading.Thread):
    """
    Consumer attende i risultati dai vari thread di Downloader avviati da Producer e analizza i risultati ottenuti da ciascuno
    """

    def __init__(self, stop_event, result_queue):
        threading.Thread.__init__(self)

        self.stop_event = stop_event
        self.result_queue = result_queue
        self.total_read_bytes = 0
        self.errors = []

    def run(self):
        """
        Runs the function to process results from multiple sessions:
        - Loops through the number of sessions specified
        - Await for a result being created in the result queue and processes it
        - Appends errors if encountered
        - Updates total read bytes and end reception status
        - Appends an error message if the communication was interrupted before the end signal
        """

        has_received_end = False
        
        # Wait for stop_event, then collect all results
        self.stop_event.wait()
        
        # Now collect results from threads with a reasonable timeout
        # Give threads some time to finish and post their results
        collection_deadline = time.time() + 3.0  # 3 seconds to collect all results
        
        while time.time() < collection_deadline:
            try:
                result = self.result_queue.get(True, 0.5)  # Short timeout for polling

                if result.error:
                    self.errors.append(result.error)

                self.total_read_bytes += result.n_bytes
                has_received_end = has_received_end or result.received_end

            except queue.Empty:
                # No result yet, but keep trying until deadline
                pass
        
        # Check if there are any remaining results (non-blocking)
        while True:
            try:
                result = self.result_queue.get_nowait()
                if result.error:
                    self.errors.append(result.error)
                self.total_read_bytes += result.n_bytes
                has_received_end = has_received_end or result.received_end
            except queue.Empty:
                break

        # if not has_received_end and len(self.errors) == 0:
        #     message = "Connessione interrotta prima del segnale di fine di misura"
        #     self.errors.append({"message": message, "code": nem_exceptions.BROKEN_CONNECTION})
        #     self.errors.append({"message": message, "code": nem_exceptions.BROKEN_CONNECTION})
        
        # Note: Non generiamo errore se END_STRING non è ricevuto, perché quando stop_event
        # è settato (fine misura normale dopo 10s), i thread vengono terminati forzatamente
        # prima di ricevere END_STRING. Questo è comportamento atteso, non un errore.
        # Gli errori reali sono già stati raccolti dai thread Downloader.

class Orchestrator(threading.Thread):
    def __init__(
        self,
        url,
        netstat,
        stop_event,
        result_queue,
        buffer_size,
        min_threads=1,
        max_threads=32,
        min_rate_diff=1000,
        frequency=1,
        callback=noop,
    ):
        threading.Thread.__init__(self)
        logger.debug(f"Orchestrator thread started with URL: {url} and buffer size: {buffer_size}")

        self.url = url
        self.netstat = netstat
        self.stop_event = stop_event
        self.result_queue = result_queue
        self.buffer_size = buffer_size
        self.min_threads = min_threads
        self.max_threads = max_threads
        self.min_rate_diff = min_rate_diff
        self.frequency = frequency

        if callback:
            self.callback = callback
        else:
            self.callback = noop

        self.pool = urllib3.PoolManager(num_pools=MAX_CONNECTIONS, maxsize=MAX_CONNECTIONS, block=True)
        self.measurement_id = "sess-{}".format(random.randint(0, 100000))
        self.lock = threading.Lock()
        self.measuring_event = threading.Event()
        self.threads = []

        self.status = "Waiting..."
        self.rate = 0
        self.clock = time.time()
        self.start_time = self.clock
        self.measure_start_time = None  # Will be set after rampup
        self.end_time = self.start_time
        self.rx_bytes = self.netstat.get_rx_bytes()
        self.initial_rx_bytes = 0  # It will be set after the waiting time
        self.total_rx_bytes = 0

    def get_rate(self):
        clock = time.time()
        
        rx_bytes = self.netstat.get_rx_bytes()
        
        with self.lock:
            clock_diff = (clock - self.clock) * 1000.0
            rx_diff = rx_bytes - self.rx_bytes
            
            rate = float(rx_diff * 8) / float(clock_diff)
            
            self.clock = clock
            self.rx_bytes = rx_bytes
            if self.initial_rx_bytes > 0:
                self.total_rx_bytes = rx_bytes - self.initial_rx_bytes
        
        return rate

    def run(self):
        """
        Controlla la velocità in download:
        * Dedice quando inizia la misura, dopo l'assestamento di massimo N secondo
        * Controlla la velocità istantanea e decide quanti thread di download dovrebbero essere attivi
        * Decide quando la misura finisce, ovvero M secondi dopo l'inizio della misura
        * Calcola la velocità media
        """

        # Bootstrap: scelgo di usare 2 threads come compromesso (ideale da calcolo sarebbe 4)
        # (abbastanza per scalare velocemente, non troppo per linee lente)
        self.adjust_threads(2)

        # Set and alarm for stop_event after MEASURE_TIME seconds
        measuring_event_timer = threading.Timer(RAMPUP_SECS, lambda: self.measuring_event.set())
        measuring_event_timer.start()

        # Aspetta un po' prima del primo campionamento per dare tempo alle connessioni 
        # HTTP di attivarsi ed evitare il primo campione a zero
        time.sleep(0.3)

        rampup_elapsed = 0.3  # Inizializza con il tempo già trascorso
        while not self.measuring_event.isSet():
            rate = self.get_rate()
            required_threads = get_threads_for_rate(rate)
            
            # Bootstrap dinamico: nei primi 0.5 secondi, mantieni un minimo per aiutare la scalata
            # Dopo, lascia che l'algoritmo si adatti liberamente anche verso il basso
            if rampup_elapsed < 0.5:
                required_threads = max(2, required_threads)
            
            self.adjust_threads(required_threads)
            self.callback(second=time.time() - self.start_time, speed=rate)

            logger.debug(f"[HTTP] {self.status} Time = {time.time() - self.start_time:.2f}; Speed = {int(rate):,}.0 kbps; Threads = {len(self.threads)}")
            logger_csv.debug(";%d" % int(rate))

            time.sleep(self.frequency)
            rampup_elapsed += self.frequency

        self.status = "Measuring"

        measuring_event_timer.cancel()

        # CRITICAL: Restart all threads to ensure filebytes counters start fresh
        # If we don't restart, threads that started downloading during rampup will
        # deposit Result with filebytes that include rampup bytes, causing negative overhead
        current_thread_count = len(self.threads)
        logger.info(f"========== THREAD RESTART START ==========")
        logger.info(f"Threads BEFORE restart (count={current_thread_count}):")
        for idx, (thread, stop_event) in enumerate(self.threads):
            logger.info(f"  [{idx}] Thread ID: {thread.id}, alive: {thread.is_alive()}, stop_event.isSet: {stop_event.isSet()}")
        
        logger.debug(f"Terminating {current_thread_count} threads from rampup...")
        self.adjust_threads(0)  # Terminate all (they will deposit their rampup Results)
        
        logger.info(f"Threads AFTER termination (count={len(self.threads)}):")
        for idx, (thread, stop_event) in enumerate(self.threads):
            logger.info(f"  [{idx}] Thread ID: {thread.id}, alive: {thread.is_alive()}")
        
        # CRITICAL: Clear queue AFTER terminating threads to discard rampup Results
        # The terminated threads deposited Results before exiting, we must discard them
        discarded_count = 0
        discarded_bytes = 0
        while not self.result_queue.empty():
            try:
                result = self.result_queue.get_nowait()
                discarded_bytes += result.n_bytes
                discarded_count += 1
            except queue.Empty:
                break
        logger.info(f"Discarded {discarded_count} rampup results from queue (total bytes: {discarded_bytes:,})")
        
        logger.debug(f"Restarting {current_thread_count} fresh threads...")
        self.adjust_threads(current_thread_count)  # Restart same number with fresh counters
        
        logger.info(f"Threads AFTER restart (count={len(self.threads)}):")
        for idx, (thread, stop_event) in enumerate(self.threads):
            logger.info(f"  [{idx}] Thread ID: {thread.id}, alive: {thread.is_alive()}, stop_event.isSet: {stop_event.isSet()}")
        logger.info(f"========== THREAD RESTART COMPLETE ==========")
        
        # Now queue is empty and threads have filebytes=0, perfect synchronization!

        # Set and alarm for stop_event after MEASURE_TIME seconds
        stop_event_timer = threading.Timer(MEASURE_TIME, lambda: self.stop_event.set())
        stop_event_timer.start()

        self.initial_rx_bytes = self.netstat.get_rx_bytes()
        self.measure_start_time = time.time()  # Start of actual measurement (after rampup)

        while not self.stop_event.isSet():
            rate = self.get_rate()
            self.adjust_threads(get_threads_for_rate(rate))
            self.callback(second=time.time() - self.start_time, speed=rate)

            logger.debug(f"[HTTP] {self.status} Time = {time.time() - self.start_time:.2f}; Speed = {int(rate):,}.0 kbps")
            logger_csv.debug(";%d" % int(rate))

            time.sleep(self.frequency)

        logger.debug("Stop event reached")
        
        # Register timestamp before thread termination (correct duration)
        self.end_time = time.time()
        
        stop_event_timer.cancel()

        # CRITICAL: Terminate threads BEFORE final Netstat reading
        # This ensures bytes_tot includes ALL bytes that threads will report
        # Threads may continue downloading for ~0.5s after stop_event before depositing results
        self.adjust_threads(0)
        
        # Final Netstat reading AFTER threads are terminated
        # Now total_rx_bytes will match what Consumer collected from threads
        final_rate = self.get_rate()
        logger.debug(f"[HTTP] Final Netstat reading after thread termination: {self.total_rx_bytes:,} bytes")

    def adjust_threads(self, required_threads):
        with self.lock:
            # Calculate the difference between required and current threads
            diff = required_threads - len(self.threads)
            logger.debug("Required threads: %s. Current threads: %s. Diff: %s", required_threads, len(self.threads), diff)

            # Create more threads if needed
            if diff > 0:
                for _ in range(diff):
                    stop_thread = threading.Event()
                    thread = Downloader(
                        uuid.uuid4(),
                        self.pool,
                        self.url,
                        stop_thread,
                        self.result_queue,
                        self.measurement_id,
                        self.buffer_size,
                    )
                    self.threads.append((thread, stop_thread))
                    thread.start()
                    # Wait some time before starting other threads
                    time.sleep(0.2)

            # Kill excess threads if needed
            elif diff < 0:
                for _ in range(abs(diff)):
                    thread, stop_thread = self.threads.pop(0)
                    stop_thread.set()
                    thread.join()


class HttpTesterDown(object):
    def __init__(self, dev):
        self.dev = dev

    def test(self, url, callback_update_speed=noop, buffer_size=8192):
        # Prepare the measurement
        stop_event = threading.Event()
        result_queue = queue.Queue()
        consumer = Consumer(stop_event, result_queue)
        orchestrator = Orchestrator(
            url=url,
            netstat=Netstat(self.dev),
            stop_event=stop_event,
            result_queue=result_queue,
            buffer_size=buffer_size,
            callback=callback_update_speed,
        )

        # Prepare an alarm to stop the measurement if it takes too long
        timeout = threading.Timer(
            MEASURE_TIME + RAMPUP_SECS + TIMEOUT_DELAY,
            lambda: stop_event.set(),
        )

        # Start the timers and counters for overall measurement
        start_timestamp = datetime.fromtimestamp(ntptime.timestamp())

        # Start the measurement
        consumer.start()
        orchestrator.start()

        # Activate the alarm
        timeout.start()

        # Wait for the measurement to finish
        consumer.join()
        orchestrator.join()

        # Deactivate the alarm for stopping the measurement (at this point the measuremente has finished)
        timeout.cancel()

        if consumer.errors:
            logger.error("Errori durante la misura: %s", consumer.errors)
            first_error = consumer.errors[0]
            raise nem_exceptions.MeasurementException(first_error.get("message"), first_error.get("code"))

        if not orchestrator.measure_start_time or not orchestrator.end_time:
            raise nem_exceptions.MeasurementException("Misura non completata", nem_exceptions.BROKEN_CONNECTION)

        if consumer.total_read_bytes <= 0:
            raise nem_exceptions.MeasurementException("Ottenuto banda zero", nem_exceptions.ZERO_SPEED)

        duration = (orchestrator.end_time - orchestrator.measure_start_time) * 1000.0

        bytes_nem = consumer.total_read_bytes
        with orchestrator.lock:
            bytes_tot = orchestrator.total_rx_bytes

        if bytes_tot > 0:
            overhead = float(bytes_tot - bytes_nem) / float(bytes_tot)
        else:
            overhead = 0
        
        logger.info(f"DEBUG - Orchestrator: measure_start_time={orchestrator.measure_start_time:.2f}, end_time={orchestrator.end_time:.2f}, duration={duration:.2f} ms")
        logger.info(f"DEBUG - Dati: bytes_tot={bytes_tot:,}, bytes_nem={bytes_nem:,}, overhead={overhead*100:.2f}%")
        logger.debug(f"Orchestrator: dati totali letti sulla scheda di rete: {bytes_tot:,} bytes")
        logger.debug(f"Consumer: dati totali ricevuti dal server di misura: {consumer.total_read_bytes:,} bytes")
        logger.debug(f"Traffico spurio: {overhead * 100:.2f}%")
        logger.debug(f"Orchestrator: tempo di misura: {duration:,.2f} ms")
        logger.debug(f"Dati di misura: {bytes_nem:,} bytes")
        logger.debug(f"Dati totali (misura + overhead): {bytes_tot:,} bytes")

        logger_csv.debug(f";{orchestrator.total_rx_bytes};{consumer.total_read_bytes};{overhead};{bytes_tot};{bytes_nem}")

        if overhead < 0:
            raise nem_exceptions.MeasurementException("Traffico spurio negativo", nem_exceptions.NEGATIVE_SPEED)

        if bytes_nem < 0:
            raise nem_exceptions.MeasurementException("Byte di misura trasferiti negativi", nem_exceptions.NEGATIVE_SPEED)

        if bytes_tot < 0:
            raise nem_exceptions.MeasurementException("Byte totali trasferiti negativi", nem_exceptions.NEGATIVE_SPEED)

        return Proof(
            test_type="download_http",
            start_time=start_timestamp,
            duration=duration,
            bytes_nem=bytes_nem,
            bytes_tot=bytes_tot,
            spurious=overhead,
        )


def main():
    socket.setdefaulttimeout(10)
    dev = iptools.get_dev()
    result = HttpTesterDown(dev).test("http://{}:80".format("193.104.137.133"))
    print(result)


if __name__ == "__main__":
    main()
