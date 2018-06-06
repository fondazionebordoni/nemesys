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

import Queue
import logging
import random
import socket
import threading
import time
import urllib2
from datetime import datetime

from common import iptools
from common import nem_exceptions
from common import ntptime
from common.netstat import Netstat
from common.proof import Proof

MEASURE_TIME = 10
RAMPUP_SECS = 2
# Wait another 15 secs in case end of file has not arrived
DOWNLOAD_TIMEOUT_DELAY = 15
# 1000 Mbps for 12 seconds
MAX_TRANSFERED_BYTES = 1000 * 1000000 * 12 / 8
# 10 seconds timeout on open and read operations
HTTP_TIMEOUT = 10.0

logger = logging.getLogger(__name__)


def noop(*args, **kwargs):
    pass


class Result(object):
    def __init__(self, n_bytes=0, received_end=False, error=None):
        self.n_bytes = n_bytes
        self.received_end = received_end
        self.error = error


class Downloader(threading.Thread):
    def __init__(self, url, stop_event, result_queue, measurement_id, buffer_size):
        super(Downloader, self).__init__()
        self.url = url
        self.result_queue = result_queue
        self.measurement_id = measurement_id
        self.stop_event = stop_event
        self.buffer_size = buffer_size

    def run(self):
        try:
            headers = ({'X-requested-file-size': MAX_TRANSFERED_BYTES,
                        'X-requested-measurement-time': MEASURE_TIME + RAMPUP_SECS,
                        'X-measurement-id': self.measurement_id})
            request = urllib2.Request(self.url, headers=headers)
            response = urllib2.urlopen(request, None, HTTP_TIMEOUT)
        except Exception as e:
            error = {'message': 'Impossibile creare connessione: {}'.format(e),
                     'code': nem_exceptions.CONNECTION_FAILED}
            self.result_queue.put(Result(error=error))
            self.stop_event.set()
            return
        response_code = response.getcode()
        if response_code != 200:
            error = {'message': 'Connessione HTTP fallita, codice di errore ricevuto: {}'.format(response_code),
                     'code': nem_exceptions.CONNECTION_FAILED}
            self.result_queue.put(Result(error=error))
            self.stop_event.set()
            return
        filebytes = 0
        received_end = False
        while not self.stop_event.isSet():
            try:
                my_buffer = response.read(self.buffer_size)
                if my_buffer is None:
                    error = {'message': 'Non ricevuti dati sufficienti per completare la misura',
                             'code': nem_exceptions.SERVER_ERROR}
                    self.result_queue.put(Result(error=error))
                    self.stop_event.set()
                    return
                filebytes += len(my_buffer)
                if '_ThisIsTheEnd_' in my_buffer:
                    received_end = True
                    break
            except socket.timeout:
                pass
        self.result_queue.put(Result(n_bytes=filebytes, received_end=received_end))
        self.stop_event.set()


class Producer(threading.Thread):
    def __init__(self, url, stop_event, result_queue, num_sessions, buffer_size):
        super(Producer, self).__init__()
        self.url = url
        self.stop_event = stop_event
        self.result_queue = result_queue
        self.num_sessions = num_sessions
        self.buffer_size = buffer_size
        self.measurement_id = 'sess-{}'.format(random.randint(0, 100000))

    def run(self):
        for i in range(0, self.num_sessions):
            thread = Downloader(self.url, self.stop_event, self.result_queue, self.measurement_id, self.buffer_size)
            thread.start()


class Consumer(threading.Thread):
    def __init__(self, stop_event, result_queue, num_sessions):
        super(Consumer, self).__init__()
        self.stop_event = stop_event
        self.result_queue = result_queue
        self.num_sessions = num_sessions
        self.total_read_bytes = 0
        self.errors = []

    def run(self):
        finished = 0
        has_received_end = False
        while finished < self.num_sessions:
            res = self.result_queue.get(True)
            if res.error:
                self.errors.append(res.error)
            else:
                self.total_read_bytes += res.n_bytes
                if res.received_end:
                    has_received_end = True
            finished += 1
        if not has_received_end and len(self.errors) == 0:
            self.errors.append({'message': 'Connessione interrotta', 'code': nem_exceptions.BROKEN_CONNECTION})


class Observer(threading.Thread):
    def __init__(self, stop_event, netstat, callback=noop):
        super(Observer, self).__init__()
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
        last_rx_bytes = self.netstat.get_rx_bytes()
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
                self.measured_bytes += rx_diff
                if measure_count == MEASURE_TIME + RAMPUP_SECS:
                    self.endtime = measuring_time
            elif measure_count == RAMPUP_SECS:
                self.starttime = measuring_time
            self.callback(second=measure_count, speed=rate_tot)
            logger.debug('[HTTP] Reading... count = %d, speed = %d', measure_count, int(rate_tot))


class HttpTesterDown(object):
    def __init__(self, dev):
        self.dev = dev

    def test(self, url, callback_update_speed=noop, num_sessions=7, buffer_size=8192):
        start_timestamp = datetime.fromtimestamp(ntptime.timestamp())
        stop_event = threading.Event()
        result_queue = Queue.Queue()
        netstat = Netstat(self.dev)
        producer = Producer(url, stop_event, result_queue, num_sessions, buffer_size)
        consumer = Consumer(stop_event, result_queue, num_sessions)
        observer = Observer(stop_event, netstat, callback_update_speed)
        timeout = threading.Timer(MEASURE_TIME + RAMPUP_SECS + DOWNLOAD_TIMEOUT_DELAY, lambda: stop_event.set())
        starttotalbytes = netstat.get_rx_bytes()
        producer.start()
        consumer.start()
        observer.start()
        timeout.start()
        producer.join()
        consumer.join()
        observer.join()
        if timeout.isAlive():
            timeout.cancel()
        if consumer.errors:
            logger.debug('Errors: {}'.format(consumer.errors))
            first_error = consumer.errors[0]
            raise nem_exceptions.MeasurementException(first_error.get('message'), first_error.get('code'))
        total_sent_bytes = netstat.get_rx_bytes() - starttotalbytes
        if total_sent_bytes < 0:
            raise nem_exceptions.MeasurementException('Ottenuto banda negativa, possibile azzeramento dei contatori.',
                                                      nem_exceptions.COUNTER_RESET)
        if (total_sent_bytes == 0) or (consumer.total_read_bytes == 0):
            raise nem_exceptions.MeasurementException('Ottenuto banda zero',
                                                      nem_exceptions.ZERO_SPEED)
        overhead = float(total_sent_bytes - consumer.total_read_bytes) / float(total_sent_bytes)
        logger.debug('Traffico spurio: %f', overhead)
        duration = (observer.endtime - observer.starttime) * 1000.0
        bytes_nem = int(round(observer.measured_bytes * (1 - overhead)))
        return Proof(test_type='download_http',
                     start_time=start_timestamp,
                     duration=duration,
                     bytes_nem=bytes_nem,
                     bytes_tot=observer.measured_bytes,
                     spurious=overhead)


def main():
    socket.setdefaulttimeout(10)
    dev = iptools.get_dev()
    res = HttpTesterDown(dev).test('http://{}:80'.format('eagle2.fub.it'))
    print(res)


if __name__ == '__main__':
    main()