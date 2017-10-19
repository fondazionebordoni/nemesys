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

import Queue
import logging
import random
import socket
import threading
import time
from datetime import datetime

from common import httpclient
from common import iptools
from common import nem_exceptions
from common import ntptime
from common.fakefile import Fakefile
from common.netstat import Netstat
from common.proof import Proof

MEASURE_TIME = 10
RAMPUP_SECS = 2
# Long timeout since needed in some cases
TEST_TIMEOUT = 18
# 1 Gbps for 15 seconds
MAX_TRANSFERED_BYTES = 1000 * 1000000 * 15 / 8
BUFSIZE = 8192

logger = logging.getLogger(__name__)


def noop(*args, **kwargs):
    pass


class Result(object):
    def __init__(self, n_bytes=0, response=None, error=None):
        self.n_bytes = n_bytes
        self.response = response
        self.error = error


def test_from_server_response(response):
    """
    Server response is a comma separated string containing:
    <total_bytes received 10th second>, <total_bytes received 9th second>, ...
    """
    logger.debug('Ricevuto risposta dal server: %s', response)
    try:
        results = [int(num) for num in response.strip(']').strip('[').split(', ')]
    except Exception:
        raise nem_exceptions.MeasurementException('Ricevuto risposta errata dal server',
                                                  nem_exceptions.SERVER_ERROR)
    testtime = len(results) * 1000
    partial_bytes = [float(x) for x in results]
    bytes_received = int(sum(partial_bytes))
    return testtime, bytes_received


class ChunkGenerator(object):
    def __init__(self, fakefile, stop_event):
        self.fakefile = fakefile
        self.stop_event = stop_event

    def gen_chunk(self):
        while not self.stop_event.isSet():
            yield self.fakefile.read(BUFSIZE)


class Uploader(threading.Thread):
    def __init__(self, url, stop_event, result_queue, measurement_id, tcp_window_size):
        threading.Thread.__init__(self)
        self.url = url
        self.stop_event = stop_event
        self.result_queue = result_queue
        self.measurement_id = measurement_id
        self.tcp_window_size = tcp_window_size

    def run(self):
        fakefile = Fakefile(MAX_TRANSFERED_BYTES)
        chunk_generator = ChunkGenerator(fakefile, self.stop_event)
        response = None
        httpc = httpclient.HttpClient()
        try:
            headers = {'X-measurement-id': self.measurement_id}
            response = httpc.post(self.url,
                                  data_source=chunk_generator.gen_chunk(),
                                  headers=headers,
                                  tcp_window_size=self.tcp_window_size,
                                  timeout=TEST_TIMEOUT)
            if response is None:
                self.result_queue.put(Result(error={'message': 'Nessuna risposta dal server',
                                                    'code': nem_exceptions.BROKEN_CONNECTION}))
            elif response.status_code != 200:
                self.result_queue.put(Result(error={'message': 'Errore: {}'.format(response.status),
                                                    'code': nem_exceptions.CONNECTION_FAILED}))
            else:
                self.result_queue.put(Result(n_bytes=fakefile.get_bytes_read(),
                                             response=response.content))
        except Exception as e:
            self.result_queue.put(Result(error={'message': 'Errore di connessione: {}'.format(e),
                                                'code': nem_exceptions.CONNECTION_FAILED}))
        finally:
            self.stop_event.set()
            if response:
                response.close()


class Producer(threading.Thread):
    def __init__(self, url, stop_event, result_queue, num_sessions, tcp_window_size):
        super(Producer, self).__init__()
        self.url = url
        self.stop_event = stop_event
        self.result_queue = result_queue
        self.num_sessions = num_sessions
        self.tcp_window_size = tcp_window_size

    def run(self):
        measurement_id = 'sess-%d' % random.randint(0, 100000)
        for _ in range(0, self.num_sessions):
            thread = Uploader(self.url, self.stop_event, self.result_queue, measurement_id, self.tcp_window_size)
            thread.start()


class Consumer(threading.Thread):
    def __init__(self, stop_event, result_queue, num_sessions):
        super(Consumer, self).__init__()
        self.stop_event = stop_event
        self.result_queue = result_queue
        self.num_sessions = num_sessions
        self.total_read_bytes = 0
        self.errors = []
        self.duration = None
        self.bytes_received = None

    def run(self):
        finished = 0
        response_data = None
        while finished < self.num_sessions:
            res = self.result_queue.get(True)
            if res.error:
                self.errors.append(res.error)
            else:
                if res.response:
                    response_data = res.response
                self.total_read_bytes += res.n_bytes
            finished += 1
        if not response_data and len(self.errors) == 0:
            self.errors.append({'message': 'Nessuna risposta dal server', 'code': nem_exceptions.BROKEN_CONNECTION})
        else:
            try:
                (self.duration, self.bytes_received) = test_from_server_response(response_data)
            except nem_exceptions.MeasurementException as e:
                self.errors.append({'message': e.message, 'code': e.errorcode})
            except Exception as e:
                self.errors.append({'message': e.message, 'code': nem_exceptions.errorcode_from_exception(e)})


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
        last_tx_bytes = self.netstat.get_tx_bytes()
        while not self.stop_event.isSet():
            time.sleep(1.0)
            measure_count += 1
            measuring_time = time.time()
            elapsed = (measuring_time - last_measured_time) * 1000.0
            new_tx_bytes = self.netstat.get_tx_bytes()
            tx_diff = new_tx_bytes - last_tx_bytes
            if MEASURE_TIME + RAMPUP_SECS >= measure_count > RAMPUP_SECS:
                self.measured_bytes += tx_diff
            rate_tot = float(tx_diff * 8) / float(elapsed)
            last_tx_bytes = new_tx_bytes
            last_measured_time = measuring_time
            logger.debug('[HTTP] secondo = %d, velocita\' = %d', measure_count, int(rate_tot))
            self.callback(second=measure_count, speed=rate_tot)


class HttpTesterUp(object):
    def __init__(self, dev):
        self.dev = dev

    def test(self, url, callback_update_speed=noop, num_sessions=1, tcp_window_size=-1):
        start_timestamp = datetime.fromtimestamp(ntptime.timestamp())
        stop_event = threading.Event()
        result_queue = Queue.Queue()
        netstat = Netstat(self.dev)
        producer = Producer(url, stop_event, result_queue, num_sessions, tcp_window_size)
        consumer = Consumer(stop_event, result_queue, num_sessions)
        observer = Observer(stop_event, netstat, callback_update_speed)
        timeout = threading.Timer(TEST_TIMEOUT, lambda: stop_event.set())
        starttotalbytes = netstat.get_tx_bytes()
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
            logger.debug('Errori: %s', consumer.errors)
            first_error = consumer.errors[0]
            raise nem_exceptions.MeasurementException(first_error.get('message'), first_error.get('code'))
        total_sent_bytes = netstat.get_tx_bytes() - starttotalbytes
        if consumer.duration < (MEASURE_TIME * 1000) - 1:
            raise nem_exceptions.MeasurementException('Test non risucito - tempo ritornato dal server non '
                                                      'corrisponde al tempo richiesto.',
                                                      nem_exceptions.SERVER_ERROR)
        if total_sent_bytes < 0:
            raise nem_exceptions.MeasurementException('Ottenuto banda negativa, possibile '
                                                      'azzeramento dei contatori.',
                                                      nem_exceptions.COUNTER_RESET)
        if (consumer.total_read_bytes == 0) or (total_sent_bytes == 0):
            raise nem_exceptions.MeasurementException('Ottenuto banda zero',
                                                      nem_exceptions.ZERO_SPEED)
        if total_sent_bytes > consumer.total_read_bytes:
            overhead = (float(total_sent_bytes - consumer.total_read_bytes) / float(total_sent_bytes))
        else:
            logger.warn('Byte di payload > tx_diff, uso calcolo alternativo di spurious traffic')
            # for thread in self._read_measure_threads:
            #     thread.join()
            overhead = (float(observer.measured_bytes - consumer.bytes_received) /
                        float(observer.measured_bytes))
        if (total_sent_bytes == 0) or (consumer.total_read_bytes == 0):
            raise nem_exceptions.MeasurementException('Ottenuto banda zero',
                                                      nem_exceptions.ZERO_SPEED)
        #   = (observer.endtime - observer.starttime) * 1000.0
        # int(round(consumer.bytes_received * (1 - overhead)))
        bytes_tot = int(consumer.bytes_received * (1 + overhead))
        return Proof(test_type='upload_http',
                     start_time=start_timestamp,
                     duration=consumer.duration,
                     bytes_nem=consumer.bytes_received,
                     bytes_tot=bytes_tot,
                     spurious=overhead)


def main():
    socket.setdefaulttimeout(10)
    dev = iptools.get_dev()
    print HttpTesterUp(dev).test('http://{}:8080'.format('eagle2.fub.it'))


if __name__ == '__main__':
    main()
