# netran.py
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
from logger import logging
from threading import Thread, Condition, Event

import contabyte
import random
import sniffer
import sys
import time


logger = logging.getLogger()

buffer_shared = deque([], maxlen = 20000)
condition = Condition()

analyzer_memory = Event()
analyzer_flag = Event()
switch_flag = Event()



class Device:

  def __init__(self): None

  def getdev(self, req = None):
    device = sniffer.getdev(req)
    return device


class Sniffer(Thread):

  def __init__(self, dev, buff = 22 * 1024000, snaplen = 8192, timeout = 1, promisc = 1):
    Thread.__init__(self)
    self._run_sniffer = 1
    self._stop_pkt = 0
    sniffer.debugmode(0)
    self._init = sniffer.initialize(dev, buff, snaplen, timeout, promisc)
    if (self._init['err_flag'] != 0):
      self._run_sniffer = 0
      logger.error('Errore inizializzazione dello Sniffer')

  def run(self):
    global buffer_shared
    global condition
    global switch_flag
    sniffer_data = {'err_flag':0, 'err_str':None, 'datalink':0, 'py_pcap_hdr':None, 'py_pcap_data':None}
    sniff_mode = 0
    loop = 0
    while (self._run_sniffer == 1):
      self.switch()
      if (switch_flag.isSet()):
        sniff_mode = 1
        stat = sniffer.getstat()
        loop = stat['pkt_pcap_tot'] - stat['pkt_pcap_proc']
        if (loop <= 0):
          loop = 1
        if (len(buffer_shared) < 20000):
          while (loop > 0):
            try:
              sniffer_data = sniffer.start(sniff_mode)
              sniffer.clear()
              if (sniffer_data['err_flag'] < 0):
                logger.error(sniffer_data['err_str'])
                raise Exception (sniffer_data['err_str'])
              if (sniffer_data['py_pcap_hdr'] != None):
                condition.acquire()
                buffer_shared.append(sniffer_data)
                condition.notify()
                condition.release()
            except:
              logger.error("Errore nello Sniffer: %s" % str(sys.exc_info()[0]))
            loop -= 1
        else:
          condition.acquire()
          condition.wait(2.0)
          condition.release()
      else:
        sniff_mode = 0
        sniffer.start(sniff_mode)

  def switch(self):
    global analyzer_memory
    global analyzer_flag
    global switch_flag
    if (analyzer_memory.isSet() or analyzer_flag.isSet()):
      if(analyzer_flag.isSet()):
        analyzer_memory.set()
        switch_flag.set()
      else:
        stat = sniffer.getstat()
        if (self._stop_pkt == 0):
          stat = sniffer.getstat()
          self._stop_pkt = stat['pkt_pcap_tot']
        if (stat['pkt_pcap_proc'] >= self._stop_pkt):
          analyzer_memory.clear()
          switch_flag.clear()
          self._stop_pkt = 0
    else:
      analyzer_memory.clear()
      switch_flag.clear()

  def stop(self):
    self._run_sniffer = 0
    while (self.isAlive()):
      None
    sniffer_stop = sniffer.stop()
    return sniffer_stop

  def getstat(self):
    sniffer_stat = sniffer.getstat()
    return sniffer_stat

  def join(self, timeout = None):
    Thread.join(self, timeout)


class Contabyte(Thread):

  def __init__(self, dev, nem):
    Thread.__init__(self)
    self._run_contabyte = 1
    self._stat = {}
    self._dev = dev
    self._nem = nem

  def run(self):
    global buffer_shared
    global condition
    global analyzer_flag
    contabyte.reset()
    self._stat.clear()
    buffer_shared.clear()
    analyzer_flag.set()
    while (self._run_contabyte == 1):
      contabyte_data = {'err_flag':0, 'err_str':None, 'datalink':0, 'py_pcap_hdr':None, 'py_pcap_data':None}
      if (len(buffer_shared) > 0):
        try:
          condition.acquire()
          contabyte_data = buffer_shared.popleft()
          condition.notify()
          condition.release()
          if (contabyte_data['py_pcap_hdr'] != None):
            self._stat = contabyte.analyze(self._dev, self._nem, contabyte_data['py_pcap_hdr'], contabyte_data['py_pcap_data'])
        except:
          logger.error("Errore nel Contabyte: %s" % str(sys.exc_info()[0]))
          raise
      elif (analyzer_flag.isSet()):
        condition.acquire()
        condition.wait(2.0)
        condition.release()

  def stop(self):
    global buffer_shared
    global analyzer_flag
    analyzer_flag.clear()
    while (switch_flag.isSet()):
      time.sleep(0.2)
    while (len(buffer_shared) > 0):
      None
    self._run_contabyte = 0
    while (self.isAlive()):
      None

  def getstat(self):
    contabyte_stat = self._stat
    return contabyte_stat

  def join(self, timeout = None):
    Thread.join(self, timeout)

if __name__ == '__main__':

  mydev = '192.168.208.53'
  mynem = '194.244.5.206'

  print "\nDevices:"

  mydevice = Device()

  print "\nFirst Request: All Devices"

  device = mydevice.getdev()

  if (device != None):
    print
    keys = device.keys()
    keys.sort()
    for key in keys:
      print "%s \t %s" % (key, device[key])
  else:
    print "No Devices"

  print "\nSecond Request: Device by IP not assigned to the machine"

  device = mydevice.getdev('194.244.5.206')

  if (device != None):
    print
    keys = device.keys()
    keys.sort()
    for key in keys:
      print "%s \t %s" % (key, device[key])
  else:
    print "No Devices"

  print "\nThird Request: Device by IP assigned to the machine"

  device = mydevice.getdev(mydev)

  if (device != None):
    print
    keys = device.keys()
    keys.sort()
    for key in keys:
      print "%s \t %s" % (key, device[key])
  else:
    print "No Devices"


  print "\nInitialize Sniffer And Contabyte...."

  mysniffer = Sniffer(mydev, 22 * 1024000, 150, 1, 1)
  mycontabyte = Contabyte(mydev, mynem)

  print "Start Sniffer And Contabyte...."

  mysniffer.start()
  mycontabyte.start()

  print "Sniffing And Analyzing...."

  raw_input("Enter When Finished!!")

  mycontabyte.stop()

  sniffer_stop = mysniffer.stop()
  if (sniffer_stop['err_flag'] == 0):
    print "Success Sniffer"
  else:
    print "Fail:", sniffer_stop['err_flag']
    print "Error:", sniffer_stop['err_str']

  print "Sniffer And Contabyte Statistics:\n"

  contabyte_stat = mycontabyte.getstat()
  if (contabyte_stat != None):
    keys = contabyte_stat.keys()
    keys.sort()
    for key in keys:
      print "Key: %s \t Value: %s" % (key, contabyte_stat[key])
  else:
    print "No Statistics"

  print

  sniffer_stat = mysniffer.getstat()
  if (sniffer_stat != None):
    keys = sniffer_stat.keys()
    keys.sort()
    for key in keys:
      print "Key: %s \t Value: %s" % (key, sniffer_stat[key])
  else:
    print "No Statistics"

  print "\nSniffer And Contabyte Join...."

  mycontabyte.join()
  print "Success Contabyte"
  mysniffer.join()
  print "Success Sniffer"



