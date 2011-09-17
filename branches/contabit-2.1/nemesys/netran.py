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

from logger import logging
from threading import Thread, Condition, Event
from collections import deque

import time
import random
import sys
import sniffer
import contabyte

logger = logging.getLogger()

debug_mode = 1

sniffer_init = {}
contabyte_init = 0

shared_buffer = deque([],maxlen=10000)
condition = Condition()
analyzer_flag = Event()

class Device:

  def __init__(self): None

  def getdev(self, req=None):
    device = sniffer.getdev(req)
    return device


class Sniffer(Thread):

  def __init__(self, dev, buff=32 * 1024000, snaplen=8192, timeout=1, promisc=1, debug=0):
    Thread.__init__(self)
    global debug_mode
    global sniffer_init
    self._run_sniffer = 0
    self._sniffer_data = {}
    debug_mode = sniffer.debugmode(debug)
    sniffer_init = sniffer.initialize(dev, buff, snaplen, timeout, promisc)
    if (sniffer_init['err_flag'] == 0):
      self._run_sniffer = 1
    else: 
      logger.error('Errore inizializzazione dello Sniffer')

  def run(self, sniffer_mode=0):
    global analyzer_flag
    global shared_buffer
    global condition
    while (self._run_sniffer == 1):
      if (analyzer_flag.isSet()):
        condition.acquire()
        while (len(shared_buffer) >= 10000):
          logger.debug("WAIT: Buffer Pieno!!")
          condition.wait(1)
          
        try:  
          self._sniffer_data = sniffer.start(sniffer_mode)
          shared_buffer.append(self._sniffer_data)
          condition.notify()
        except:
          logger.error("Errore nello Sniffer: %s" % str(sys.exc_info()[0]))
          raise
          
        condition.release()
        
      else:
        sniffer.start(sniffer_mode)       #black hole

  def stop(self):
    global shared_buffer
    self._run_sniffer = 0
    while (self.isAlive()):
      None
    sniffer_stop = sniffer.stop()
    return sniffer_stop


  def getstat(self):
    sniffer_stat = sniffer.getstat()
    return sniffer_stat


  def join(self, timeout=None):
    #logger.debug('ALIVE SNIFFER: %s' % str(self.isAlive()))
    Thread.join(self, timeout)


class Contabyte(Thread):

  def __init__(self, dev, nem, debug=0):
    Thread.__init__(self)
    global debug_mode
    global contabyte_init
    self._run_contabyte = 0
    debug_mode = contabyte.debugmode(debug)
    contabyte_init = contabyte.initialize(dev, nem)
    if (contabyte_init == 0):
      self._run_contabyte = 1
    else: 
      logger.error('Errore inizializzazione del Contabyte')
      raise Exception('Errore inizializzazione del Contabyte')

  def run(self):
    global analyzer_flag
    global shared_buffer
    global condition
    shared_buffer.clear()
    analyzer_flag.set()
    condition.acquire()
    condition.wait(1)
    condition.release()
    while (self._run_contabyte == 1):  
      condition.acquire()
      while (len(shared_buffer) <= 0 and analyzer_flag.isSet()):
        condition.wait(1)
      
      if(len(shared_buffer) > 0):    
        try:
          contabyte_data = shared_buffer.popleft()
          if (contabyte_data['blocks_num'] > 10):
            logger.debug("|%d|" % contabyte_data['blocks_num'])
          contabyte.analyze(contabyte_data['py_byte_array'], contabyte_data['block_size'], contabyte_data['blocks_num'], contabyte_data['datalink'])
          condition.notify()
        except:
          logger.error("Errore nello Contabyte: %s" % str(sys.exc_info()[0]))
          raise
      
      condition.release()


  def stop(self):
    global analyzer_flag
    global shared_buffer
    analyzer_flag.clear()
    while (len(shared_buffer) != 0):
      None
    self._run_contabyte = 0
    while (self.isAlive()):
      None
    contabyte_stop = contabyte.close()
    return contabyte_stop


  def getstat(self):
    contabyte_stat = contabyte.getstat()
    return contabyte_stat


  def join(self, timeout=None):
    #logger.debug('ALIVE CONTABYTE: %s' % str(self.isAlive()))
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

  print "Debug Mode Sniffer:", debug_mode
  if (sniffer_init['err_flag'] == 0):
    print "Success Sniffer\n"
  else:
    print "Fail Sniffer:", sniffer_init['err_flag']
    print "Error Sniffer:", sniffer_init['err_str']

  mycontabyte = Contabyte(mydev, mynem, debug)

  print "Debug Mode Contabyte:", debug_mode
  if (contabyte_init == 0):
    print "Success Contabyte\n"
  else:
    print "Fail Contabyte\n"


  print "Start Sniffer And Contabyte...."

  mysniffer.start()
  mycontabyte.start()

  print "Sniffing And Analyzing...."

  raw_input("Enter When Finished!!")
  #time.sleep(30)

  contabyte_stop = mycontabyte.stop()
  if (contabyte_stop == 0):
    print "Success Contabyte"
  else:
    print "Fail\n"

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



