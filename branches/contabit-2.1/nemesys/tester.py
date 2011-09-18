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
from netran import Sniffer, Contabyte 

ftp = None
file = None
filepath = None
size = 0
BUFFER_CONTABIT_MB = 32

logger = logging.getLogger()
errors = Errorcoder(paths.CONF_ERRORS)

# Calcolo dei byte totali scaricati
def totalsize(data):
  global size
  size += len(data)


class Tester:

  def __init__(self, if_ip, host, username='anonymous', password='anonymous@', timeout=60):
    self._debug = 0
    self._if_ip = if_ip
    self._host = host
    self._username = username
    self._password = password
    self._timeout = timeout
    socket.setdefaulttimeout(self._timeout)
    try:
      self._test_sniffer = Sniffer(self._if_ip,BUFFER_CONTABIT_MB*1024000,180,1,1,self._debug)
      self._test_sniffer.start()
    except: 
      logger.error('Errore di inizializzazione dello sniffer')
      raise Exception('Errore di inizializzazione dello sniffer')
    
  def testftpup(self, bytes, path):
    global ftp, file, size, filepath
    filepath = path
    size = 0
    elapsed = 0
    counter_total_pay = 0
    counter_ftp_pay = 0 
    try:
      counter = Contabyte(self._if_ip, self._host.ip,self._debug)
    except:
      logger.error("Errore di inizializzazione del Contabyte")
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
      counter.start()
      #logger.debug('ALIVE CONTABYTE: %s' % str(counter.isAlive()))
      
      # Il risultato deve essere espresso in millisecondi
      elapsed = timer.timeit(1) * 1000
      
      counter.stop()
      #logger.debug('ALIVE CONTABYTE: %s' % str(counter.isAlive()))
        
      counter_stats = counter.getstat()
      if (counter_stats != None):  
        counter_total_pay = counter_stats['payload_up_all']
        counter_ftp_pay = counter_stats['payload_up_nem']
        #logger.debug("Statistiche contabit:\n %s \n" % counter_stats)
        
      counter.join()
      
    except ftplib.all_errors as e:
      logger.error("Impossibile effettuare l'upload: %s" % e)
      errorcode = errors.geterrorcode(e)
      return Proof('upload', start, 0, 0, 0, 0, errorcode)
    
    ftp.quit()
    
    return Proof('upload', start, elapsed, size, counter_total_pay, counter_ftp_pay)

  def testftpdown(self, filename):
    global ftp, file, size
    size = 0
    elapsed = 0
    counter_total_pay = 0
    counter_ftp_pay = 0
    try:
      counter = Contabyte(self._if_ip, self._host.ip,self._debug)
    except:
      logger.error("Errore di inizializzazione del Contabyte")
      counter = None
      
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
      counter.start()
      #logger.debug('ALIVE CONTABYTE: %s' % str(counter.isAlive()))
        
      # Il risultato deve essere espresso in millisecondi
      elapsed = timer.timeit(1) * 1000
      
      counter.stop()
      #logger.debug('ALIVE CONTABYTE: %s' % str(counter.isAlive()))  
        
      counter_stats = counter.getstat()
      if (counter_stats != None):  
        counter_total_pay = counter_stats['payload_down_all']
        counter_ftp_pay = counter_stats['payload_down_nem']
        #logger.debug("Statistiche contabit:\n%s\n" % counter_stats)
      
      counter.join()

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

  def teststopsniffer(self):
    #funzione per terminare l'attività dello sniffer avviata con l'inizializzazione del tester o tramite teststartsniffer
    try:
      checkstopsniffer = self._test_sniffer.stop()
      self._test_sniffer.join()
    except:
      logger.error('Errore nello stop dello sniffer: %s' %checkstopsniffer['err_str'])
        
  def teststartsniffer(self):
    try:
      self._test_sniffer = Sniffer(self._if_ip,BUFFER_CONTABIT_MB*1024000,180,1,1,self._debug)
      self._test_sniffer.start()
    except: 
      logger.error('Errore di inizializzazione dello sniffer')
      raise Exception('Errore di inizializzazione dello sniffer')

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
    
  t = Tester(sysmonitor.getIp, Host(options.host), options.username, options.password)
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
    t1 = Tester('192.168.88.8', Host(ip='193.104.137.133'), 'nemesys', '4gc0m244')
    #t1 = Tester('192.168.208.53', Host(ip='192.168.208.183'), 'QoS_lab', '')
    
    for k in range(1,11):
      print "[-------- TEST 20-20-10 numero:%d --------]" % k
      for i in range(1,21):
        print 'Test Download %d.%d:' % (k,i)
        test = t1.testftpdown('/download/1000.rnd')
        print test
        print("\n")
      for i in range(1,21):
        print 'Test Upload %d.%d:' % (k,i)
        test = t1.testftpup(512000, '/upload/r.raw')
        print test
        print("\n")
      for i in range(1,11):
        print 'Test Ping %d.%d:' % (k,i)
        test = t1.testping()
        print test
        print("\n")
  
    t1.teststopsniffer()

  else:
    main()

