# httptester.py
# -*- coding: utf8 -*-

# Copyright (c) 2015 Fondazione Ugo Bordoni.
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

import errorcode
import random
import requests
import socket
import threading
import time
import urllib2
import Queue

from datetime import datetime
from fakefile import Fakefile
from logger import logging
import netstat
from measurementexception import MeasurementException
from proof import Proof
from statistics import Statistics
from timeNtp import timestampNtp


TOTAL_MEASURE_TIME = 10
DOWNLOAD_TIMEOUT_DELAY = 5 #Wait another 5 secs in case end of file has not arrived  
MAX_TRANSFERED_BYTES = 100 * 1000000 * 11 / 8 # 100 Mbps for 11 seconds
BUF_SIZE = 8*1024
HTTP_TIMEOUT = 10.0 # 10 seconds timeout on open and read operations
logger = logging.getLogger()

'''
NOTE: not thread-safe, make sure to only call 
one measurement at a time!
'''

class HttpTester:

    def __init__(self, dev, bufsize = 8 * 1024, rampup_secs = 2):
        self._num_bytes = bufsize
        self._rampup_secs = rampup_secs
        self._netstat = netstat.get_netstat(dev)
        self._fakefile = None
    
    def _init_counters(self):
        self._time_to_stop = False
        self._last_rx_bytes = self._netstat.get_rx_bytes()
        self._last_tx_bytes = self._netstat.get_tx_bytes()
        self._bytes_total = 0
        self._measures_tot = []
        self._measure_count = 0
        self._read_measure_threads = []
        self._last_measured_time = time.time()


    def test_down(self, url, total_test_time_secs = TOTAL_MEASURE_TIME, callback_update_speed = None, num_sessions = 1):
        start_timestamp = datetime.fromtimestamp(timestampNtp())
        self._timeout = False
        self._received_end = False
        self.callback_update_speed = callback_update_speed
        self._total_measure_time = total_test_time_secs + self._rampup_secs
        file_size = MAX_TRANSFERED_BYTES * self._total_measure_time / TOTAL_MEASURE_TIME
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
            download_thread = threading.Thread(target= self.do_one_download, 
                                               args = (url, self._total_measure_time, file_size, result_queue, error_queue, measurement_id))
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
                filebytes += int(result_queue.get(block = False))
            except Queue.Empty:
                missing_results = True
                break
            
        total_bytes = self._netstat.get_rx_bytes() - starttotalbytes
        
        for read_thread in self._read_measure_threads:
            read_thread.join()
            
        if not error_queue.empty():
            raise MeasurementException(error_queue.get(), errorcode.CONNECTION_FAILED)
        if missing_results:
            raise MeasurementException("Risultati mancanti da uno o piu' sessioni, impossibile calcolare la banda.", errorcode.MISSING_SESSION)
        if not self._received_end:
            raise MeasurementException("Connessione interrotta", errorcode.BROKEN_CONNECTION)
        if (total_bytes < 0):
            raise MeasurementException("Ottenuto banda negativa, possibile azzeramento dei contatori.", errorcode.COUNTER_RESET)
        if (total_bytes == 0) or (filebytes == 0):
            raise MeasurementException("Ottenuto banda zero", errorcode.ZERO_SPEED)
        spurio = float(total_bytes - filebytes) / float(total_bytes)
        logger.debug("Traffico spurio: %f" % spurio)

        # "Trucco" per calcolare i bytes corretti da inviare al backend basato sul traffico spurio
        test_time = (self._endtime - self._starttime) * 1000.0
        test_bytes = int(round(self._bytes_total * (1 - spurio)))

        counter_stats = Statistics(byte_down_nem = test_bytes, byte_down_all = self._bytes_total)
        return Proof('download_http', start_timestamp, test_time, test_bytes, counter_stats)

        
    def do_one_download(self, url, total_measure_time, file_size, result_queue, error_queue, measurement_id):
        filebytes = 0

        try:
            request = urllib2.Request(url, headers = {"X-requested-file-size" : file_size, 
                                                      "X-requested-measurement-time" : total_measure_time,
                                                      "X-measurement-id" : measurement_id})
            response = urllib2.urlopen(request, None, HTTP_TIMEOUT)
        except Exception as e:
            logger.error("Impossibile creare connessione: %s" % str(e))
            self._time_to_stop = True
            error_queue.put("Impossibile aprire la connessione HTTP: %s" % str(e))
            return
        if response.getcode() != 200:
            self._time_to_stop = True
            error_queue.put("Impossibile aprire la connessione HTTP, codice di errore ricevuto: %d" % response.getcode())
            return
        
#         # In some cases urlopen blocks until all data has been received
#         if self._time_to_stop:
#             logger.warn("Suspected blocked urlopen")
#             # Try to handle anyway!
#             while True:
#                 my_buffer = response.read(self._num_bytes)
#                 if my_buffer: 
#                     filebytes += len(my_buffer)
#                 else: 
#                     break
#                 
        else:
            while ((not self._time_to_stop) or (not self._received_end)) and not self._timeout:
                try:
                    my_buffer = response.read(self._num_bytes)
                    if my_buffer != None: 
                        filebytes += len(my_buffer)
                        if "_ThisIsTheEnd_" in my_buffer:
                            self._received_end = True
                    else: 
                        self._time_to_stop = True
                        error_queue.put("Non ricevuti dati sufficienti per completare la misura")
                        return
                except socket.timeout:
                    logger.debug("socket timeout")
                    pass
                
            logger.debug("Download done")
        result_queue.put(filebytes)
                
    
    def _get_max_rate(self):
        try:
            return max(self._measures_tot)
        except Exception:
            return 0


    def _read_down_measure(self):

        measuring_time = time.time()

        if self._time_to_stop:
            logger.debug("Time to stop, checking for timeout")
            if not self._received_end and not self._timeout:
                total_time = measuring_time - self._starttime 
                if total_time > (self._total_measure_time + DOWNLOAD_TIMEOUT_DELAY):
                    logger.debug("Timeout, total_time is %.2f" % total_time)
                    self._timeout = True
                else:
                    # Continue until received end or timeout set
                    logger.debug("Not timeout yet, total_time is %.2f" % total_time)
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
            self.callback_update_speed(second=self._measure_count, speed=rate_tot)
        logger.debug("[HTTP] Reading... count = %d, speed = %d" 
                     % (self._measure_count, int(rate_tot)))
        
        if True:#not self._time_to_stop and not self._received_end:
            self._last_rx_bytes = new_rx_bytes
            read_thread = threading.Timer(1.0, self._read_down_measure)
            self._read_measure_threads.append(read_thread)
            read_thread.start()
            
           
    def _read_up_measure(self):

        if not self._time_to_stop:
            self._measure_count += 1
            measuring_time = time.time()
            elapsed = (measuring_time - self._last_measured_time)*1000.0
            
            new_tx_bytes = self._netstat.get_tx_bytes()
            tx_diff = new_tx_bytes - self._last_tx_bytes
            rate_tot = float(tx_diff * 8)/float(elapsed) 
            logger.debug("[HTTP] Reading... count = %d, speed = %d" 
                  % (self._measure_count, int(rate_tot)))
            if self.callback_update_speed:
                self.callback_update_speed(second=self._measure_count, speed=rate_tot)
        
            self._last_tx_bytes = new_tx_bytes
            self._last_measured_time = measuring_time
            read_thread = threading.Timer(1.0, self._read_up_measure)
            self._read_measure_threads.append(read_thread)
            read_thread.start()


    def _stop_up_measurement(self):
        self._time_to_stop = True
        for t in self._read_measure_threads:
            t.join()

   
    '''
    Upload test is done server side. We just measure
    the average speed payload/net in order to 
    verify spurious traffic.
    '''
    def test_up(self, url, callback_update_speed = None, total_test_time_secs = TOTAL_MEASURE_TIME, file_size = MAX_TRANSFERED_BYTES, recv_bufsize = 8 * 1024, is_first_try = True, num_sessions = 1):
        start_timestamp = datetime.fromtimestamp(timestampNtp())
        measurement_id = "sess-%d" % random.randint(0, 100000)
        self.callback_update_speed = callback_update_speed
        upload_threads = []
        if is_first_try:
            self._upload_sending_time_secs = total_test_time_secs + self._rampup_secs + 1
        else:
            self._upload_sending_time_secs = total_test_time_secs * 2 + self._rampup_secs + 1
        file_size = MAX_TRANSFERED_BYTES * self._upload_sending_time_secs / TOTAL_MEASURE_TIME
        self._init_counters()
        # Read progress each second, just for display
        read_thread = threading.Timer(1.0, self._read_up_measure)
        read_thread.start()
        self._read_measure_threads.append(read_thread)
        self._starttime = time.time()
        start_tx_bytes = self._netstat.get_tx_bytes()
        for _ in range(0, num_sessions):
            fakefile = Fakefile(file_size)
            upload_thread = UploadThread(httptester=self, fakefile=fakefile, url=url, upload_sending_time_secs=self._upload_sending_time_secs, measurement_id=measurement_id, recv_bufsize=recv_bufsize, num_bytes=self._num_bytes)#threading.Thread(target = self._do_one_upload, args = (fakefile, url, self._upload_sending_time_secs))
            upload_thread.start()
            upload_threads.append(upload_thread)
        for upload_thread in upload_threads:
            upload_thread.join()
            thread_error = upload_thread.get_error()
            thread_response = upload_thread.get_response()
            if thread_response != None:
                response_content = thread_response.content
                thread_response.close()
        self._time_to_stop = True
        if thread_error:
            raise MeasurementException(thread_error, errorcode.CONNECTION_FAILED)
        test = _test_from_server_response(response_content)
        
        if test['time'] < (total_test_time_secs * 1000) - 1:
            # Probably slow creation of connection, needs more time
            # Double the sending time
            if is_first_try:
                self._stop_up_measurement()
                logger.warn("Test non sufficientemente lungo, aumento del tempo di misura.")
                return self.test_up(url, callback_update_speed, total_test_time_secs, file_size, recv_bufsize, is_first_try = False)
            else:
                raise MeasurementException("Test non risucito - tempo ritornato dal server non corrisponde al tempo richiesto.", errorcode.SERVER_ERROR)
        bytes_read = 0
        for upload_thread in upload_threads:
            bytes_read += upload_thread.get_bytes_read()
        tx_diff = self._netstat.get_tx_bytes() - start_tx_bytes
        if (tx_diff < 0):
            raise MeasurementException("Ottenuto banda negativa, possibile azzeramento dei contatori.", errorcode.COUNTER_RESET)
        spurious = (float(tx_diff - bytes_read)/float(tx_diff))
        logger.info("Traffico spurio: %0.4f" % spurious)
        test['bytes_total'] = int(test['bytes'] * (1 + spurious))
        test['rate_tot_secs'] = [x * (1 + spurious) for x in test['rate_secs']]
        test['spurious'] = spurious
        
        counter_stats = Statistics(byte_up_nem = test['bytes'], byte_up_all = test['bytes_total'])
        return Proof('upload_http', start_timestamp, test['time'], test['bytes'], counter_stats)
    

def _init_test(testtype):
    test = {}
    test['type'] = testtype
    test['time'] = 0
    test['bytes'] = 0
    test['bytes_total'] = 0
    test['errorcode'] = 0
    return test
        
def _test_from_server_response(response):
    '''
    Server response is a comma separated string containing:
    <total_bytes received 10th second>, <total_bytes received 9th second>, ... 
    '''
    logger.info("Ricevuto risposta dal server: %s" % str(response))
    test = {}
    test['type'] = 'upload_http'
    if not response or len(response) == 0:
        logger.error("Got empty response from server")
        test['rate_medium'] = -1
        test['rate_max'] = -1
        test['rate_secs'] = -1
        test['errorcode'] = 1
    else:
        test['errorcode'] = 0
        results = str(response).split(',')
        test['time'] = len(results) * 1000
        partial_bytes = [float(x) for x in results] 
        test['rate_secs'] = []
        if partial_bytes:
            bytes_max = max(partial_bytes)
            test['rate_max'] = bytes_max * 8 / 1000 # Bytes in one second
            if test['time'] > 0:
                test['rate_secs'] = [ b * 8 / 1000 for b in partial_bytes ]
        else:
            test['rate_max'] = 0
        test['bytes'] = sum(partial_bytes)
    return test

class UploadThread(threading.Thread):
    
    def __init__(self, httptester, fakefile, url, upload_sending_time_secs, measurement_id, recv_bufsize, num_bytes):
        threading.Thread.__init__(self)
        self._httptester = httptester
        self._fakefile = fakefile
        self._url = url
        self._upload_sending_time_secs = upload_sending_time_secs
        self._measurement_id = measurement_id
        self._recv_bufsize = recv_bufsize
        self._num_bytes = num_bytes
        self._error = None
        self._response = None

    def run(self):
        chunk_generator = ChunkGenerator(self._fakefile, self._upload_sending_time_secs, self._recv_bufsize, self._num_bytes)
        response = None
        try:
            logger.info("Connecting to server, sending time is %d" % self._upload_sending_time_secs)
            headers = {"X-measurement-id" : self._measurement_id}
            response = requests.post(self._url, data=chunk_generator.gen_chunk(), headers = headers)#, hooks = dict(response = self._response_received))
            self._httptester._stop_up_measurement()
        except Exception as e:
            self._httptester._stop_up_measurement()
            chunk_generator.stop()
            self._error = "Errore di connessione: %s" % str(e)
        if response == None:
            self._httptester._stop_up_measurement()
            chunk_generator.stop()
            if not self._error:
                self._error = "Nessuna risposta dal server" 
        elif response.status_code != 200:
            self._httptester._stop_up_measurement()
            chunk_generator.stop()
            if not self._error:
                self._error = "Ricevuto risposta %d dal server" % self._response.status_code
        self._response = response

    def get_bytes_read(self):
        return self._fakefile.get_bytes_read()
    
    def get_error(self):
        return self._error
    
    def get_response(self):
        return self._response


END_STRING = '_ThisIsTheEnd_'

class ChunkGenerator:

    def __init__(self, fakefile, upload_sending_time_secs, recv_bufsize, num_bytes):
        self._fakefile = fakefile
        self._upload_sending_time_secs = upload_sending_time_secs
        self._time_to_stop = False
        self._recv_bufsize = recv_bufsize
        self._num_bytes = num_bytes
        self._starttime = time.time()
    
    def stop(self):
        self._time_to_stop = True
    
    def gen_chunk(self):
        has_sent_end_string = False
        while not self._time_to_stop:
            elapsed = time.time() - self._starttime
            file_data = self._fakefile.read(self._num_bytes)
            if file_data and not self._time_to_stop and (elapsed < self._upload_sending_time_secs):# and (self._fakefile.get_bytes_read() < MAX_TRANSFERED_BYTES):
                yield file_data
            elif not has_sent_end_string:
                has_sent_end_string = True
                yield END_STRING * (self._recv_bufsize / len(END_STRING) + 1)
            else:
                self._time_to_stop = True
                yield ""


        
if __name__ == '__main__':
    socket.setdefaulttimeout(10)
#    host = "10.80.1.1"
#    host = "193.104.137.133"
#    host = "regopptest6.fub.it"
    host = "eagle2.fub.it"
#     host = "regoppwebtest.fub.it"
#    host = "rocky.fub.it"
#    host = "billia.fub.it"
    import sysmonitor
    dev = sysmonitor.getDev()
    http_tester = HttpTester(dev)
    print "\n------ DOWNLOAD -------\n"
    for _ in range(0, 1):
        res = http_tester.test_down("http://%s:80" % host, num_sessions=7)
        print res
#     print "\n------ UPLOAD ---------\n"
#     res = http_tester.test_up("http://%s:80/file.rnd" % host, num_sessions=1)
#     print res
