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
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

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
# 10 seconds timeout on open and read operations
HTTP_TIMEOUT = 2.0
END_STRING = b"_ThisIsTheEnd_"

logger = logging.getLogger(__name__)
logger_csv = logging.getLogger("csv")


def noop(*args, **kwargs):
    pass


class Result(object):
    def __init__(self, n_bytes=0, received_end=False, error=None):
        self.n_bytes = n_bytes
        self.received_end = received_end
        self.error = error


class Downloader(threading.Thread):
    """
    Downloader is a subclass of threading.Thread that downloads a file from a given URL over HTTP.
    """

    def __init__(self, url, stop_event, result_queue, measurement_id, buffer_size):
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

        self.url = url
        self.result_queue = result_queue
        self.measurement_id = measurement_id
        self.stop_event = stop_event
        self.buffer_size = buffer_size

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

        try:
            headers = {
                "X-requested-file-size": str(MAX_TRANSFERED_BYTES),
                "X-requested-measurement-time": str(MEASURE_TIME + RAMPUP_SECS),
                "X-measurement-id": self.measurement_id,
            }
            request = urllib.request.Request(self.url, headers=headers)
            response = urllib.request.urlopen(request, None, HTTP_TIMEOUT)
        except Exception as e:
            error = {
                "message": "Impossibile creare connessione: {}".format(e),
                "code": nem_exceptions.CONNECTION_FAILED,
            }
            self.result_queue.put(Result(error=error))
            return

        response_code = response.getcode()
        if response_code != 200:
            error = {
                "message": "Connessione HTTP fallita, codice di errore ricevuto: {}".format(response_code),
                "code": nem_exceptions.CONNECTION_FAILED,
            }
            self.result_queue.put(Result(error=error))
            return

        filebytes = 0
        my_buffer = bytearray(self.buffer_size)
        # Read from socket until the stop event is set
        while not self.stop_event.isSet():
            try:
                filebytes += response.readinto(my_buffer)

                if filebytes <= 0:
                    error = {
                        "message": "Non ricevuti dati sufficienti per completare la misura",
                        "code": nem_exceptions.SERVER_ERROR,
                    }
                    self.result_queue.put(Result(n_bytes=filebytes, error=error))
                    return

                if END_STRING in my_buffer:
                    # Put the result in the queue and send the stop event for all other threads
                    self.stop_event.set()
                    self.result_queue.put(Result(n_bytes=filebytes, received_end=True))
                    return

            except socket.timeout:
                # Exit the loop if the timeout is reached
                error = {
                    "message": "Non ricevuti dati sufficienti per completare la misura",
                    "code": nem_exceptions.SERVER_ERROR,
                }
                self.result_queue.put(Result(n_bytes=filebytes, error=error))
                return

        # If a stop event was fired, put the result in the queue and exit
        self.result_queue.put(Result(n_bytes=filebytes))
        return


class Producer(threading.Thread):
    """
    Producer is a subclass of threading.Thread that creates a set of Downloader
    threads (based on the number of sessions requested), and then starts them.
    """

    def __init__(self, url, stop_event, result_queue, num_sessions, buffer_size):
        """
        Initializes a Producer object.

        Args:
            url (str): The URL to be used.
            stop_event (threading.Event): The event used to stop the producer.
            result_queue (Queue): The queue to store results.
            num_sessions (int): The number of sessions to be created.
            buffer_size (int): The size of the buffer for each session.

        Returns:
            None
        """
        threading.Thread.__init__(self)

        self.url = url
        self.stop_event = stop_event
        self.result_queue = result_queue
        self.num_sessions = num_sessions
        self.buffer_size = buffer_size
        self.measurement_id = "sess-{}".format(random.randint(0, 100000))

    def run(self):
        """
        Runs a set of Downloader threads based on the number of sessions requested.

        This method initializes a Downloader thread for each session and starts it.
        The Downloader threads are responsible for downloading a file from a given URL over HTTP.
        """
        for i in range(0, self.num_sessions):
            thread = Downloader(
                self.url,
                self.stop_event,
                self.result_queue,
                self.measurement_id,
                self.buffer_size,
            )
            thread.start()


class Consumer(threading.Thread):
    """
    Consumer attende i risultati dai vari thread di Downloader avviati da Producer e analizza i risultati ottenuti da ciascuno
    """

    def __init__(self, stop_event, result_queue, num_sessions):
        threading.Thread.__init__(self)

        self.stop_event = stop_event
        self.result_queue = result_queue
        self.num_sessions = num_sessions
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

        finished = 0
        has_received_end = False

        while finished < self.num_sessions:
            # Wait for a result to be available
            result = self.result_queue.get(True)

            if result.error:
                self.errors.append(result.error)

            else:
                self.total_read_bytes += result.n_bytes
                has_received_end = has_received_end or result.received_end

            finished += 1

        if not has_received_end and len(self.errors) == 0:
            self.errors.append(
                {
                    "message": "Connessione interrotta prima del segnale di fine di misura",
                    "code": nem_exceptions.BROKEN_CONNECTION,
                }
            )

        self.stop_event.set()


class Observer(threading.Thread):
    def __init__(self, stop_event, netstat, callback=noop):
        threading.Thread.__init__(self)

        self.stop_event = stop_event
        self.netstat = netstat
        if callback:
            self.callback = callback
        else:
            self.callback = noop
        self.starttime = None
        self.endtime = None
        self.measured_bytes = 0

    def run(self):
        last_measured_time = time.time()
        measure_count = 0
        start_rx_bytes = self.netstat.get_rx_bytes()
        last_rx_bytes = start_rx_bytes
        status = "Waiting"

        while not self.stop_event.isSet():
            time.sleep(1.0)
            measure_count += 1
            measuring_time = time.time()
            elapsed = (measuring_time - last_measured_time) * 1000.0
            last_measured_time = measuring_time
            new_rx_bytes = self.netstat.get_rx_bytes()
            rx_diff = new_rx_bytes - last_rx_bytes
            rate_tot = float(rx_diff * 8) / float(elapsed)
            last_rx_bytes = new_rx_bytes

            if MEASURE_TIME + RAMPUP_SECS >= measure_count > RAMPUP_SECS:
                status = "Measuring."
                self.measured_bytes += rx_diff
                if measure_count == MEASURE_TIME + RAMPUP_SECS:
                    self.endtime = measuring_time

            elif measure_count <= RAMPUP_SECS:
                status = "Waiting..."
                self.starttime = measuring_time

            self.callback(second=measure_count, speed=rate_tot)
            logger.debug(f"[HTTP] {status} Count = {measure_count:>2}; Speed = {int(rate_tot):,}.0 kbps")
            logger_csv.debug(";%d" % int(rate_tot))

        self.total_observed_bytes = self.netstat.get_rx_bytes() - start_rx_bytes


class HttpTesterDown(object):
    def __init__(self, dev):
        self.dev = dev

    def test(self, url, callback_update_speed=noop, num_sessions=7, buffer_size=8192):
        
        # Prepare the measurement
        stop_event = threading.Event()
        result_queue = queue.Queue()
        producer = Producer(url, stop_event, result_queue, num_sessions, buffer_size)
        consumer = Consumer(stop_event, result_queue, num_sessions)
        observer = Observer(stop_event, Netstat(self.dev), callback_update_speed)

        # Prepare an alarm to stop the measurement if it takes too long
        timeout = threading.Timer(
            MEASURE_TIME + RAMPUP_SECS + TIMEOUT_DELAY,
            lambda: stop_event.set(),
        )

        # Start the timers and counters for overall measurement
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
            timeout.cancel()

        if consumer.errors:
            logger.debug("Errori: %s", consumer.errors)
            first_error = consumer.errors[0]
            raise nem_exceptions.MeasurementException(first_error.get("message"), first_error.get("code"))

        if observer.starttime is None or observer.endtime is None:
            raise nem_exceptions.MeasurementException("Misura non completata", nem_exceptions.BROKEN_CONNECTION)

        if observer.total_observed_bytes < 0:
            raise nem_exceptions.MeasurementException(
                "Ottenuto banda negativa, possibile azzeramento dei contatori",
                nem_exceptions.COUNTER_RESET,
            )
        if (observer.total_observed_bytes == 0) or (consumer.total_read_bytes == 0):
            raise nem_exceptions.MeasurementException("Ottenuto banda zero", nem_exceptions.ZERO_SPEED)

        duration = (observer.endtime - observer.starttime) * 1000.0
        overhead = float(observer.total_observed_bytes - consumer.total_read_bytes) / float(observer.total_observed_bytes)
        bytes_nem = observer.measured_bytes
        bytes_tot = int(bytes_nem * (1 + overhead))

        logger.debug(f"Observer: dati totali letti sulla scheda di rete: {observer.total_observed_bytes:,} bytes")
        logger.debug(f"Consumer: dati totali ricevuti dal server di misura: {consumer.total_read_bytes:,} bytes")
        logger.debug(f"Traffico spurio: {overhead*100:.2f}%")

        logger.debug(f"Observer: dati misurati (al netto della rampa): {observer.measured_bytes:,} bytes")
        logger.debug(f"Observer: tempo di misura: {duration:,.2f} ms")

        logger.debug(f"Dati di misura: {bytes_nem:,} bytes")
        logger.debug(f"Dati totali (misura + overhead): {bytes_tot:,} bytes")
        
        logger_csv.debug(f";{observer.total_observed_bytes};{observer.measured_bytes};{consumer.total_read_bytes};{overhead};{bytes_tot};{bytes_nem}")
        
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
