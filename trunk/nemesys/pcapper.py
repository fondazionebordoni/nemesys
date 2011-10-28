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

from contabyte import Contabyte
from random import randint
from statistics import Statistics
from threading import Thread, Event
import logging
import sniffer
import socket
import sys
import time

MAX_BUFFER_LENGTH = 500

TEST = False

LOOP = '_loop'
SNIFF = '_sniff'
COUNT = '_count'
EAT = '_eat'

_switch_status = { \
  LOOP: SNIFF, \
  SNIFF: COUNT, \
  COUNT: EAT, \
  EAT: LOOP, \
}

logger = logging.getLogger()

class Pcapper(Thread):

  def __init__(self, dev, buff = 22 * 1024000, snaplen = 8192, timeout = 1, promisc = 1):
    Thread.__init__(self)
    self._dev = dev

    sniffer.debugmode(0)
    r = sniffer.initialize(self._dev, buff, snaplen, timeout, promisc)
    if (r['err_flag'] != 0):
      logger.error('Errore inizializzazione dello Sniffer: %s' % str(r['err_str']))
      raise Exception('Errore inizializzazione dello Sniffer')

    self._status = LOOP
    self._running = True
    self._tot = 0
    self._remaining = 0
    self._stop_eating = Event()

  def run(self):
    while self._running:
      self._produce()
    logger.debug('Exit sniffer. Stats: %s' % sniffer.getstat())
    sniffer.stop()

  def sniff(self, analyzer):
    self._analyzer = analyzer
    self._status = _switch_status[LOOP]

  def stop_sniff(self):
    self._status = _switch_status[SNIFF]

  def get_stats(self):
    if (self._analyzer != None):
      self._stop_eating.wait()
      self._stop_eating.clear()
      stats = self._analyzer.statistics
      self._analyzer.reset()
      return stats
    else:
      logger.warning("Nessun analizzatore da cui ricavare le statistiche!")
      return Statistics()

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

  def _produce(self):
    try:
        method = getattr(self, self._status)
    except AttributeError:
        print self._status, "not found"
    else:
        method()

  def _loop(self):
    self._cook(0)

  def _sniff(self):
    self._cook(1)

  def _count(self):
    self._status = _switch_status[COUNT]
    self._remaining = self._get_remaining()

  def _eat(self):
    if self._remaining > 0:
      self._cook(1)
      self._remaining -= 1
    else:
      logger.debug('Stop eating! [tot: %d]' % self._tot)
      self._stop_eating.set()
      self._status = _switch_status[EAT]

  def _cook(self, mode):
    if TEST:
      return self._get_data_test(mode)
    else:
      data = self._get_data(mode)

    if (data != None and self._analyzer != None):
      self._analyzer.analyze(data['py_pcap_hdr'], data['py_pcap_data'])
      self._tot += 1

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

if __name__ == '__main__':

  s = socket.socket(socket.AF_INET)
  s.connect(('www.fub.it', 80))
  ip = s.getsockname()[0]
  s.close()
  nap = '193.104.137.133'
  tot = 50

  if ip != None:

    if TEST:
      tot = 1
    for i in range(1, tot + 1):

      p = Pcapper(ip)
      p.start()

      print("Start! [%d/%d]" % (i, tot))
      p.sniff(Contabyte(ip, nap))
      time.sleep(2)
      p.stop_sniff()
      print p.get_stats()

      print("Stop! [%d/%d]" % (i, tot))

      p.stop()
      p.join()

