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

buffer_shared = deque([],maxlen=20000)
analyzer_flag = Event()
condition = Condition()


class Device:

  def __init__(self): None

  def getdev(self, req=None):
    device = sniffer.getdev(req)
    return device


class Sniffer(Thread):

  def __init__(self, dev, buff=22 * 1024000, snaplen=8192, timeout=1, promisc=1):
    Thread.__init__(self)
    self._run_sniffer = 1
    self._sniffer_data = {}
    sniffer.debugmode(0)
    self._init = sniffer.initialize(dev, buff, snaplen, timeout, promisc)
    if (self._init['err_flag'] != 0):
      self._run_sniffer = 0
    else:
      logger.error('Errore inizializzazione dello Sniffer')

  def run(self):
    global buffer_shared
    global analyzer_flag
    global condition
    sniff_mode = 0
    loop = 0
    while (self._run_sniffer == 1):
      if (analyzer_flag.isSet()):
        sniff_mode = 1
        stat = sniffer.getstat()
        if (('pkt_pcap_tot' in stat) and ('pkt_pcap_proc' in stat)):
          loop = stat['pkt_pcap_tot'] - stat['pkt_pcap_proc']
        if (loop <= 0):
          loop=1         
        if (len(buffer_shared) < 20000):  
          while (loop > 0):
            self._sniffer_data = sniffer.start(sniff_mode)          
            if ('err_flag' in self._sniffer_data):
              if (self._sniffer_data['err_flag'] < 0):
                logger.error(self._sniffer_data['err_str'])
                raise Exception (self._sniffer_data['err_str'])      
            if ('py_pcap_hdr' in self._sniffer_data):
              if (self._sniffer_data['py_pcap_hdr'] != None):
                condition.acquire()      
                buffer_shared.append(self._sniffer_data)
                condition.notify()
                condition.release()
            loop -= 1
        else:
          condition.acquire()
          logger.debug("WAIT: Buffer Pieno!!")
          condition.wait(2.0)
          condition.release()    
      else:
        sniff_mode = 0
        sniffer.start(sniff_mode)
        
  def stop(self):
    self._run_sniffer = 0
    while (self.isAlive()):
      None
    sniffer_stop = sniffer.stop()
    return sniffer_stop

  def getstat(self):
    sniffer_stat = sniffer.getstat()
    return sniffer_stat

  def join(self, timeout=None):
    Thread.join(self, timeout)


class Contabyte(Thread):

  def __init__(self, dev, nem):
    Thread.__init__(self)
    self._run_contabyte = 1
    self._contabyte_data = {}
    self._stat = {}
    self._dev = dev
    self._nem = nem

  def run(self):
    global buffer_shared
    global analyzer_flag
    global condition
    contabyte.reset()
    buffer_shared.clear()
    analyzer_flag.set()
    while (self._run_contabyte == 1):
      condition.acquire()
      if (len(buffer_shared) > 0):
        try:
          self._contabyte_data = buffer_shared.popleft()
          if ('py_pcap_hdr' in self._contabyte_data):
            if (self._contabyte_data['py_pcap_hdr'] != None):            
              self._stat = contabyte.analyze(self._dev, self._nem, self._contabyte_data['py_pcap_hdr'], self._contabyte_data['py_pcap_data'])
              condition.notify()
        except:
          logger.error("Errore nel Contabyte: %s" % str(sys.exc_info()[0]))
          raise
      elif (analyzer_flag.isSet()):
        condition.wait(2.0)
      condition.release()
  
#    if (self._stat != None):
#      keys = self._stat.keys()
#      keys.sort()
#      for key in keys:
#        print "Key: %s \t Value: %s" % (key, self._stat[key])
#    else:
#      print "No Statistics"

  def stop(self):
    global buffer_shared
    global analyzer_flag
    time.sleep(0.8)
    analyzer_flag.clear()
    while (len(buffer_shared) != 0):
      None
    self._run_contabyte = 0
    while (self.isAlive()):
      None

  def getstat(self):
    contabyte_stat = self._stat
    return contabyte_stat

  def join(self, timeout=None):
    Thread.join(self, timeout)




if __name__ == '__main__':

  mydev = '192.168.88.8'
  mynem = '194.244.5.206'
  debug = 1

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

  mysniffer = Sniffer(mydev, 32 * 1024000, 150, 1, 1, debug)
  mycontabyte = Contabyte(mydev, mynem)

  print "Start Sniffer And Contabyte...."

  mysniffer.start()
  mycontabyte.start()

  print "Sniffing And Analyzing...."

  raw_input("Enter When Finished!!")
  #time.sleep(30)

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

  #print("Sniffer Flag:"+str(sniffer_flag)+" Analyzer Flag:"+str(analyzer_flag))

  mycontabyte.join()
  print "Success Contabyte"
  mysniffer.join()
  print "Success Sniffer"



