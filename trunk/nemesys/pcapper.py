# pcapper.py
# -*- coding: utf8 -*-

# Copyright (c) 2010 Fondazione Ugo Bordoni.
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

from collections import deque
from executer import OptionParser
from random import randint
from statistics import Statistics
from threading import Semaphore, Thread, Event
import contabyte
import logging
import sniffer
import sys
import time

MAX_BUFFER_LENGTH = 500
buffer = deque(maxlen = MAX_BUFFER_LENGTH)
prelevato = Semaphore(MAX_BUFFER_LENGTH)
depositato = Semaphore(0)
sniff = Event()
eat = Event()

TEST = False

SNIFF = '_sniff'
COUNT = '_count'
EAT = '_eat'
LOOP = '_loop'

_switch_status = { \
  SNIFF: COUNT, \
  COUNT: EAT, \
  EAT: LOOP, \
  LOOP: SNIFF, \
}

logger = logging.getLogger()

class Sniffer(Thread):


  def __init__(self, dev, buff = 22 * 1024000, snaplen = 8192, timeout = 1, promisc = 1):
    Thread.__init__(self)
    buffer.clear()
    sniff.clear()
    eat.clear()

    sniffer.debugmode(0)
    r = sniffer.initialize(dev, buff, snaplen, timeout, promisc)
    if (r['err_flag'] != 0):
      logger.error('Errore inizializzazione dello Sniffer: %s' % str(r['err_str']))
      raise Exception('Errore inizializzazione dello Sniffer')

    self._status = LOOP
    self._running = True
    self._tot = 0
    self._remaining = 0

  def run(self):
    while self._running:
      self._produce()
    logger.debug('Exit sniffer!')
    sniffer.stop()

  def stop(self):
    self._running = False

  def _get_data_test(self, mode):
    data = randint(0, 100)
    if mode > 0:
      print('\t%3d' % data)
    return data

  def _get_remaining(self):
    stats = sniffer.getstat()
    return stats['pkt_pcap_tot'] - stats['pkt_pcap_proc']

  def _get_data(self, mode):
    try:
      if mode != 0:
        data = sniffer.start(mode)
        sniffer.clear()
        if (data != None):
          if (data['err_flag'] < 0):
            logger.error(data['err_str'])
            raise Exception(data['err_str'])
          if (data['py_pcap_hdr'] != None):
            return data
      else:
        remaining = self._get_remaining()
        while remaining > 0:
          data = sniffer.start(mode)
          sniffer.clear()
          remaining -= 1
        return None
    except:
      logger.error("Errore nello Sniffer: %s" % str(sys.exc_info()[0]))

  def _cook(self, mode):
    if TEST:
      return self._get_data_test(mode)
    else:
      data = self._get_data(mode)
    if (data != None):
      prelevato.acquire()
      buffer.append(data)
      self._tot += 1
      depositato.release()

  def _loop(self):
    if not sniff.is_set():
      self._cook(0)
    else:
      self._status = _switch_status[LOOP]

  def _sniff(self):
    if sniff.is_set():
      self._cook(1)
    else:
      self._status = _switch_status[SNIFF]
      logger.debug('Stopped sniffing.')

  def _count(self):
    self._status = _switch_status[COUNT]
    self._remaining = self._get_remaining()

  def _eat(self):
    if self._remaining > 0:
      self._cook(1)
      self._remaining -= 1
    else:
      self._status = _switch_status[EAT]
      eat.clear()
      logger.debug('Stop eating! [tot: %d]' % self._tot)
      self._tot = 0

  def _produce(self):
    try:
        method = getattr(self, self._status)
    except AttributeError:
        print self._status, "not found"
    else:
        method()

class Contabyte(Thread):

  def __init__(self, dev, nem):
    global prelevato
    global depositato
    Thread.__init__(self)
    self._stat = Statistics()
    self._dev = dev
    self._nem = nem
    self._tot = 0
    prelevato = Semaphore(MAX_BUFFER_LENGTH)
    depositato = Semaphore(0)

  def run(self):
    contabyte.reset()
    buffer.clear()

    sniff.set()
    eat.set()
    self._running = True
    while self._running:
      self._consume()
    logger.debug('Exit (run) contabyte! [tot: %d]' % self._tot)

  def stop(self):
    logger.debug('Stop sniffing!')
    sniff.clear()

  def _eat_test(self, data):
    print('%s' % data)

  def _eat(self, data):
    if TEST:
      return self._eat_test(data)
    try:
      if (data != None and data['py_pcap_hdr'] != None):
        self._stat = contabyte.analyze(self._dev, self._nem, data['py_pcap_hdr'], data['py_pcap_data'])
    except:
      logger.error("Errore nel Contabyte: %s" % str(sys.exc_info()[0]))

  def _consume(self):
    if depositato.acquire(False):
      data = buffer.popleft()
      self._eat(data)
      self._tot += 1
      prelevato.release()
    else:
      self._running = sniff.is_set() or eat.is_set() or (len(buffer) > 0)

  def getstat(self):
    logger.debug('Recupero delle statistiche')
    return self._stat

if __name__ == '__main__':

  parser = OptionParser()
  parser.add_option("-i", "--ip", dest = "ip")
  parser.add_option("-t", "--tot", dest = "tot", default = 5, type = 'int', help = "Numero di cicli di test da effettuare")
  parser.add_option("-n", "--nap", dest = "nap", default = '193.104.137.133')
  (options, args) = parser.parse_args()

  ip = options.ip
  nap = options.nap
  tot = options.tot
  parser.check_required('--ip')

  if ip != None:

    p = Sniffer(ip)
    p.start()

    if TEST:
      tot = 1
    for i in range(1, tot + 1):
      c = Contabyte(ip, nap)

      print("Start! [%d/%d]" % (i, tot))

      c.start()
      time.sleep(2)
      c.stop()
      c.join()
      print c.getstat()

      print("Stop! [%d/%d]" % (i, tot))

    p.stop()
    p.join()
