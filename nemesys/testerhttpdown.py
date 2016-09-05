# httptester.py
# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 Fondazione Ugo Bordoni.
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

import Queue
from datetime import datetime
import logging
import random
import socket
import threading
import time
import urllib2

from nem_exceptions import MeasurementException
import nem_exceptions
import netstat
from proof import Proof
import timeNtp


TOTAL_MEASURE_TIME = 10
# Wait another 15 secs in case end of file has not arrived
DOWNLOAD_TIMEOUT_DELAY = 15
# 100 Mbps for 11 seconds
MAX_TRANSFERED_BYTES = 100 * 1000000 * 11 / 8
# 10 seconds timeout on open and read operations
HTTP_TIMEOUT = 10.0

logger = logging.getLogger(__name__)


class HttpTesterDown:
    '''
    NOTE: not thread-safe, make sure to only call
    one measurement at a time!
    '''

    def __init__(self, dev, bufsize=8 * 1024, rampup_secs=2):
        self._num_bytes = bufsize
        self._rampup_secs = rampup_secs
        self._netstat = netstat.Netstat(dev)

    def _init_counters(self):
        self._time_to_stop = False
        self._last_rx_bytes = self._netstat.get_rx_bytes()
        self._bytes_total = 0
        self._measures_tot = []
        self._measure_count = 0
        self._read_measure_threads = []
        self._last_measured_time = time.time()

    def test_down(self,
                  url,
                  total_test_time_secs=TOTAL_MEASURE_TIME,
                  callback_update_speed=None,
                  num_sessions=7):
        start_timestamp = datetime.fromtimestamp(timeNtp.timestampNtp())
        self._timeout = False
        self._received_end = False
        self.callback_update_speed = callback_update_speed
        self._total_measure_time = total_test_time_secs + self._rampup_secs
        file_size = (MAX_TRANSFERED_BYTES *
                     self._total_measure_time /
                     TOTAL_MEASURE_TIME)
        download_threads = []
        result_queue = Queue.Queue()
        error_queue = Queue.Queue()
        measurement_id = "sess-%d" % random.randint(0, 100000)

        logger.debug("Starting download test...")
        self._init_counters()
        read_thread = threading.Timer(1.0, self._read_down_measure)
        read_thread.start()
        self._read_measure_threads.append(read_thread)
        starttotalbytes = self._netstat.get_rx_bytes()

        for _ in range(0, num_sessions):
            download_thread = threading.Thread(target=self._do_one_download,
                                               args=(url,
                                                     self._total_measure_time,
                                                     file_size,
                                                     result_queue,
                                                     error_queue,
                                                     measurement_id))
            download_thread.start()
            download_threads.append(download_thread)
        for download_thread in download_threads:
            download_thread.join()
        logger.debug("Download threads done, stopping...")
        self._time_to_stop = True
        filebytes = 0
        missing_results = False
        for _ in download_threads:
            try:
                filebytes += int(result_queue.get(block=False))
            except Queue.Empty:
                missing_results = True
                break
        total_bytes = self._netstat.get_rx_bytes() - starttotalbytes
        for read_thread in self._read_measure_threads:
            read_thread.join()
        if not error_queue.empty():
            raise MeasurementException(error_queue.get())
        if missing_results:
            raise MeasurementException("Risultati mancanti da uno o piu' "
                                       "sessioni, impossibile "
                                       "calcolare la banda.",
                                       nem_exceptions.MISSING_SESSION)
        if not self._received_end:
            raise MeasurementException("Connessione interrotta",
                                       nem_exceptions.BROKEN_CONNECTION)
        if (total_bytes < 0):
            raise MeasurementException("Ottenuto banda negativa, "
                                       "possibile azzeramento dei contatori.",
                                       nem_exceptions.COUNTER_RESET)
        if (total_bytes == 0) or (filebytes == 0):
            raise MeasurementException("Ottenuto banda zero",
                                       nem_exceptions.ZERO_SPEED)
        spurio = float(total_bytes - filebytes) / float(total_bytes)
        logger.info("Traffico spurio: %f" % spurio)
        test_time = (self._endtime - self._starttime) * 1000.0
        bytes_nem = int(round(self._bytes_total * (1 - spurio)))
        return Proof(test_type='download_http',
                     start_time=start_timestamp,
                     duration=test_time,
                     bytes_nem=bytes_nem,
                     bytes_tot=self._bytes_total,
                     spurious=spurio)

    def _do_one_download(self, url, total_measure_time, file_size,
                         result_queue, error_queue, measurement_id):
        filebytes = 0

        try:
            headers = ({"X-requested-file-size": file_size,
                        "X-requested-measurement-time": total_measure_time,
                        "X-measurement-id": measurement_id})
            request = urllib2.Request(url, headers=headers)
            response = urllib2.urlopen(request, None, HTTP_TIMEOUT)
        except Exception as e:
            logger.error("Impossibile creare connessione: %s" % str(e))
            self._time_to_stop = True
            self._timeout = True
            error_queue.put("Impossibile aprire la connessione HTTP: %s"
                            % str(e))
            return
        if response.getcode() != 200:
            self._time_to_stop = True
            error_queue.put("Impossibile aprire la connessione HTTP, "
                            "codice di errore ricevuto: %d"
                            % response.getcode())
            return
        else:
            while (((not self._time_to_stop) or
                    (not self._received_end)) and
                    (not self._timeout)):
                try:
                    my_buffer = response.read(self._num_bytes)
                    if my_buffer is not None:
                        filebytes += len(my_buffer)
                        if "_ThisIsTheEnd_" in my_buffer:
                            self._received_end = True
                    else:
                        self._time_to_stop = True
                        error_queue.put("Non ricevuti dati sufficienti per "
                                        "completare la misura")
                        return
                except socket.timeout:
                    pass
        result_queue.put(filebytes)

    def _read_down_measure(self):
        measuring_time = time.time()
        if self._time_to_stop:
            logger.debug("Time to stop, checking for timeout")
            if not self._received_end and not self._timeout:
                total_time = measuring_time - self._starttime
                timeout = self._total_measure_time + DOWNLOAD_TIMEOUT_DELAY
                if total_time > timeout:
                    logger.info("Timeout, total_time is %.2f" % total_time)
                    self._timeout = True
                else:
                    # Continue until received end or timeout set
                    logger.debug("Not timeout yet, total_time is %.2f"
                                 % total_time)
                    read_thread = threading.Timer(1.0, self._read_down_measure)
                    self._read_measure_threads.append(read_thread)
                    read_thread.start()
            return
        self._measure_count += 1
        elapsed = (measuring_time - self._last_measured_time)*1000.0
        self._last_measured_time = measuring_time
        new_rx_bytes = self._netstat.get_rx_bytes()
        rx_diff = new_rx_bytes - self._last_rx_bytes
        rate_tot = float(rx_diff * 8)/float(elapsed)
        if self._measure_count > self._rampup_secs:
            self._bytes_total += rx_diff
            self._measures_tot.append(rate_tot)
            if self._measure_count == (self._total_measure_time):
                self._endtime = measuring_time
                self._time_to_stop = True
        elif self._measure_count == self._rampup_secs:
            self._starttime = measuring_time
        if self.callback_update_speed:
            self.callback_update_speed(second=self._measure_count,
                                       speed=rate_tot)
        logger.debug("[HTTP] Reading... count = %d, speed = %d"
                     % (self._measure_count, int(rate_tot)))
        if True:
            # not self._time_to_stop and not self._received_end:
            self._last_rx_bytes = new_rx_bytes
            read_thread = threading.Timer(1.0, self._read_down_measure)
            self._read_measure_threads.append(read_thread)
            read_thread.start()


if __name__ == '__main__':
    import log_conf
    log_conf.init_log()
    socket.setdefaulttimeout(10)
#    host = "10.80.1.1"
#    host = "193.104.137.133"
#    host = "regopptest6.fub.it"
#     host = "eagle2.fub.it"
    host = "eagle2.fub.it"
#     host = "regoppwebtest.fub.it"
#    host = "rocky.fub.it"
#    host = "billia.fub.it"
    import iptools
    dev = iptools.get_dev()
    http_tester = HttpTesterDown(dev)
    print "\n------ DOWNLOAD -------\n"
    for _ in range(0, 1):
        res = http_tester.test_down("http://%s:80" % host, num_sessions=7)
        print res
