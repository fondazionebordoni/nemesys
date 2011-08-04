# tester.py
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

import sys

from datetime import datetime
from errorcoder import Errorcoder
from fakefile import Fakefile
import ftplib
from ftplib import FTP
from host import Host
from logger import logging
from optparse import OptionParser
import paths
import ping
from proof import Proof
from timeNtp import timestampNtp
import timeit
import socket
import sysmonitor
from threading import Thread
from contabit import *

ftp = None
file = None
filepath = None
size = 0

logger = logging.getLogger()
errors = Errorcoder(paths.CONF_ERRORS)

# Calcolo dei byte totali scaricati
def totalsize(data):
  global size
  size += len(data)


class counter(Thread):

    def __init__(self, if_ip, host_ip, buffer=0):
        Thread.__init__(self)
        self._counter = initialize(if_ip, host_ip, buffer)
        if (self._counter != 0):
          e = geterr()
          logger.error('Errore inizializzazione contabit: %s' % e)
        return self._counter
        
    def getdev(self, req=None):
        self._device = getdev(req)
        return self._device

    def run(self):
        self._status_start = start()
        if (self._status_start != None):
          e = geterr()
          logger.error('Errore start contabit: %s' % e)
        
    def stop(self):
        self._status_stop = stop()
        if (self._status_stop != None):
          e = geterr()
          logger.error('Errore stop contabit: %s' % e)

    def getstat(self, req1=None, req2=None, req3=None, req4=None, req5=None,
                     req6=None, req7=None, req8=None, req9=None, req10=None,
                     req11=None, req12=None, req13=None, req14=None, req15=None,
                     req16=None, req17=None, req18=None, req19=None, req20=None):
        self._statistics = getstat(req1, req2, req3, req4, req5, req6, req7, req8, req9, req10,
                           req11, req12, req13, req14, req15, req16, req17, req18, req19, req20)
        return self._statistics

    def geterr(self):
        self._error = geterr()
        return self._error

    def join(self, timeout=None):
        Thread.join(self, timeout)


class Tester:

  def __init__(self, if_ip, host, username='anonymous', password='anonymous@', timeout=60):
    self._if_ip = if_ip
    self._host = host
    self._username = username
    self._password = password
    self._timeout = timeout
    self._counter = counter(self._if_ip, self._host.ip, 40 * 1024000) #Buffer Contabit a 40Mb
    socket.setdefaulttimeout(self._timeout)  
    
  def testftpup(self, bytes, path):
    global ftp, file, size, filepath
    filepath = path
    size = 0
    elapsed = 0
    counter_total_pay = 0
    counter_ftp_pay = 0 
    file = Fakefile(bytes)
    timeout = max(self._timeout, 1)
    start = datetime.fromtimestamp(timestampNtp())

    try:
      # TODO Il timeout non viene onorato in Python 2.6: http://bugs.python.org/issue8493
      #ftp = FTP(self._host.ip, self._username, self._password, timeout=timeout)
      ftp = FTP(self._host.ip, self._username, self._password)
    except ftplib.all_errors as e:
      logger.error('Impossibile aprire la connessione FTP: %s' % e)
      errorcode = errors.geterrorcode(e)
      return Proof('upload', start, elapsed, size, counter_total_pay, counter_ftp_pay, errorcode)	# inserire codifica codici errore

    # TODO Se la connessione FTP viene invocata con timeout, il socket è non-blocking e il sistema può terminare i buffer di rete: http://bugs.python.org/issue8493
    function = '''ftp.storbinary('STOR %s' % filepath, file, callback=totalsize)'''
    setup = 'from %s import file, ftp, totalsize, filepath' % __name__
    timer = timeit.Timer(function, setup)

    try:
      # DONE::TODO Eseguire start di contabit  
      if (self._counter == 0):
        self._counter.start()
      
      # Il risultato deve essere espresso in millisecondi
      elapsed = timer.timeit(1) * 1000
      
      # DONE::TODO Eseguire stop di contabit e analizzare il valore di ritorno
      if (self._counter == 0):
        self._counter.stop()
        
        counter_stats = self._counter.getstat('payload_up_nem', 'payload_up_all')
        if (counter_stats != None):  
          counter_total_pay = counter_stats['payload_up_all']
          counter_ftp_pay = counter_stats['payload_up_nem']

    except ftplib.all_errors as e:
      logger.error("Impossibile effettuare l'upload: %s" % e)
      errorcode = errors.geterrorcode(e)
      return Proof('upload', start, 0, 0, 0, 0, errorcode)

    ftp.quit()
    
    # TODO Estender Proof per la memorizzazione dei dati del contabit
    return Proof('upload', start, elapsed, size, counter_total_pay, counter_ftp_pay)

  def testftpdown(self, filename):
    # TODO Controllare TODO di ftpup
    global ftp, file, size
    size = 0
    elapsed = 0
    counter_total_pay = 0
    counter_ftp_pay = 0
    file = filename
    timeout = max(self._timeout, 1)
    start = datetime.fromtimestamp(timestampNtp())

    try:
      # TODO Il timeout non viene onorato in Python 2.6: http://bugs.python.org/issue8493
      #ftp = FTP(self._host.ip, self._username, self._password, timeout=timeout)
      ftp = FTP(self._host.ip, self._username, self._password)
    except ftplib.all_errors as e:
      logger.error('Impossibile aprire la connessione FTP: %s' % e)
      errorcode = errors.geterrorcode(e)
      return Proof('download', start, elapsed, size, counter_total_pay, counter_ftp_pay, errorcode)	# inserire codifica codici errore

    function = '''ftp.retrbinary('RETR %s' % file, totalsize)'''
    setup = 'from %s import ftp, file, totalsize' % __name__ 
    timer = timeit.Timer(function, setup)

    try:
      # DONE::TODO Eseguire start di contabit  
      if (self._counter == 0):
        self._counter.start()
      
      # Il risultato deve essere espresso in millisecondi
      elapsed = timer.timeit(1) * 1000
      
      # DONE::TODO Eseguire stop di contabit e analizzare il valore di ritorno
      if (self._counter == 0):
        self._counter.stop()
          
        counter_stats = self._counter.getstat('payload_down_nem', 'payload_down_all')
        if (counter_stats != None):  
          counter_total_pay = counter_stats['payload_down_all']
          counter_ftp_pay = counter_stats['payload_down_nem']

    except ftplib.all_errors as e:
      logger.error("Impossibile effettuare il download: %s" % e)
      errorcode = errors.geterrorcode(e)
      return Proof('download', start, 0, 0, 0, 0, errorcode)
    
    ftp.quit()
    
    return Proof('download', start, elapsed, size, counter_total_pay, counter_ftp_pay)

  def testping(self):
    # si utilizza funzione ping.py
    start = datetime.fromtimestamp(timestampNtp())
    elapsed = 0

    try:
      # Il risultato deve essere espresso in millisecondi
      elapsed = ping.do_one(self._host.ip, self._timeout) * 1000

    except Exception as e:
      errorcode = errors.geterrorcode(e)
      logger.debug('Errore durante il ping: %s' % e)
      return Proof('ping', start=start, value=0, bytes=0, errorcode=errorcode)

    if (elapsed == None):
      elapsed = 0

    return Proof('ping', start=start, value=elapsed, bytes=0)

def main():
  #Aggancio opzioni da linea di comando
    
  parser = OptionParser(version="0.10.1.$Rev$",
                        description="A simple bandwidth tester able to perform FTP upload/download and PING tests.")
  parser.add_option("-t", "--type", choices=('ftpdown', 'ftpup', 'ping'),
                    dest="testtype", default="ftpdown", type="choice",
                    help="Choose the type of test to perform: ftpdown (default), ftpup, ping")
  parser.add_option("-f", "--file", dest="filename",
                    help="For FTP download, the name of the file for RETR operation")
  parser.add_option("-b", "--byte", dest="bytes", type="int",
                    help="For FTP upload, the size of the file for STOR operation")
  parser.add_option("-H", "--host", dest="host",
                    help="An ipaddress or FQDN of testing host")
  parser.add_option("-u", "--username", dest="username", default="anonymous",
                    help="An optional username to use when connecting to the FTP server")
  parser.add_option("-p", "--password", dest="password", default="anonymous@",
                    help="The password to use when connecting to the FTP server")
  parser.add_option("-P", "--path", dest="path", default="",
                    help="The path where put uploaded file")
  parser.add_option("--timeout", dest="timeout", default="30", type="int",
                    help="Timeout in seconds for FTP blocking operations like the connection attempt")
    
  (options, args) = parser.parse_args()
  #TODO inserire controllo host
    
  t = Tester(if_ip=sysmonitor.getIp, Host(options.host), options.username, options.password)
  test = None
  print ('Prova: %s' % options.host)
    
  tests = {
    'ftpdown': t.testftpdown(options.filename),
    'ftpup': t.testftpup(options.bytes, options.path),
    'ping': t.testping(),
  }
  test = tests.get(options.testtype)
    
  print test
  return None


if __name__ == '__main__':
  if len(sys.argv) < 2:
    t1 = Tester('192.168.208.10', Host(ip='83.103.94.125'), 'anonymous', 'iscom')
   
    test = t1.testftpdown('r.raw')
    print 'Test Download:'
    print test
    test = t1.testftpup(1048576, '/upload/r.raw')
    print 'Test Upload:'
    print test
    test = t1.testping()
    print 'Test Ping:'
    print test
  else:
    main()

