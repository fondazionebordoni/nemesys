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

from datetime import datetime
from errorcoder import Errorcoder
from fakefile import Fakefile
from ftplib import FTP
from host import Host
from logger import logging
from pcapper import Sniffer, Contabyte
from optparse import OptionParser
from proof import Proof
from statistics import Statistics
from timeNtp import timestampNtp
import ftplib
import paths
import ping
import socket
import sys
import sysmonitor
import timeit
import time

ftp = None
file = None
filepath = None
size = 0

#Parametri Sniffer:
BUFF = 44 * 1024000  #MegaByte
SNAPLEN = 150         #Byte
TIMEOUT = 1           #MilliSecondsù
PROMISC = 1           #Promisc Mode ON/OFF

logger = logging.getLogger()
errors = Errorcoder(paths.CONF_ERRORS)

# Calcolo dei byte totali scaricati
def totalsize(data):
  global size
  size += len(data)


class Tester:

  def __init__(self, if_ip, host, username = 'anonymous', password = 'anonymous@', timeout = 60):
    self._if_ip = if_ip
    self._host = host
    self._username = username
    self._password = password
    self._timeout = timeout
    socket.setdefaulttimeout(self._timeout)
    self._sniffer = self.sniffer_start()

  def sniffer_start(self):
    try:
      sniffer = Sniffer(self._if_ip, BUFF, SNAPLEN, TIMEOUT, PROMISC)
      sniffer.start()
    except:
      logger.error('Errore di inizializzazione dello sniffer')
      raise Exception('Errore di inizializzazione dello sniffer')
    return sniffer

  def sniffer_stop(self):
    try:
      sniff_stop = self._sniffer.stop()
      self._sniffer.join()
    except:
      logger.error('Errore nello stop dello sniffer: %s' % sniff_stop['err_str'])
    return sniff_stop

  def testftpup(self, bytes, path):
    global ftp, file, size, filepath
    filepath = path
    size = 0
    elapsed = 0
    try:
      counter = Contabyte(self._if_ip, self._host.ip)
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
      return Proof('upload', start, elapsed, size, Statistics(), errorcode)	# inserire codifica codici errore

    # TODO Se la connessione FTP viene invocata con timeout, il socket è non-blocking e il sistema può terminare i buffer di rete: http://bugs.python.org/issue8493
    function = '''ftp.storbinary('STOR %s' % filepath, file, callback=totalsize)'''
    setup = 'from %s import file, ftp, totalsize, filepath' % __name__
    timer = timeit.Timer(function, setup)

    try:
      counter.start()

      # Il risultato deve essere espresso in millisecondi
      elapsed = timer.timeit(1) * 1000

      counter.stop()
      counter.join()
      counter_stats = counter.getstat()

    except ftplib.all_errors as e:
      logger.error("Impossibile effettuare l'upload: %s" % e)
      errorcode = errors.geterrorcode(e)
      return Proof('upload', start, 0, 0, 0, Statistics(), errorcode)

    ftp.quit()

    return Proof('upload', start, elapsed, size, counter_stats)

  def testftpdown(self, filename):
    global ftp, file, size
    size = 0
    elapsed = 0
    try:
      counter = Contabyte(self._if_ip, self._host.ip)
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
      return Proof('download', start, elapsed, size, Statistics(), errorcode)	# inserire codifica codici errore

    function = '''ftp.retrbinary('RETR %s' % file, totalsize)'''
    setup = 'from %s import ftp, file, totalsize' % __name__
    timer = timeit.Timer(function, setup)

    try:
      counter.start()

      # Il risultato deve essere espresso in millisecondi
      elapsed = timer.timeit(1) * 1000

      counter.stop()
      counter.join()
      counter_stats = counter.getstat()

    except ftplib.all_errors as e:
      logger.error("Impossibile effettuare il download: %s" % e)
      errorcode = errors.geterrorcode(e)
      return Proof('download', start, 0, 0, Statistics(), errorcode)

    ftp.quit()

    return Proof('download', start, elapsed, size, counter_stats)

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
      return Proof('ping', start = start, value = 0, bytes = 0, errorcode = errorcode)

    if (elapsed == None):
      elapsed = 0

    return Proof('ping', start = start, value = elapsed, bytes = 0)


def main():
  #Aggancio opzioni da linea di comando

  parser = OptionParser(version = "0.10.1.$Rev$",
                        description = "A simple bandwidth tester able to perform FTP upload/download and PING tests.")
  parser.add_option("-t", "--type", choices = ('ftpdown', 'ftpup', 'ping'),
                    dest = "testtype", default = "ftpdown", type = "choice",
                    help = "Choose the type of test to perform: ftpdown (default), ftpup, ping")
  parser.add_option("-f", "--file", dest = "filename",
                    help = "For FTP download, the name of the file for RETR operation")
  parser.add_option("-b", "--byte", dest = "bytes", type = "int",
                    help = "For FTP upload, the size of the file for STOR operation")
  parser.add_option("-H", "--host", dest = "host",
                    help = "An ipaddress or FQDN of testing host")
  parser.add_option("-u", "--username", dest = "username", default = "anonymous",
                    help = "An optional username to use when connecting to the FTP server")
  parser.add_option("-p", "--password", dest = "password", default = "anonymous@",
                    help = "The password to use when connecting to the FTP server")
  parser.add_option("-P", "--path", dest = "path", default = "",
                    help = "The path where put uploaded file")
  parser.add_option("--timeout", dest = "timeout", default = "30", type = "int",
                    help = "Timeout in seconds for FTP blocking operations like the connection attempt")

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
    TOT = 3

    t1 = Tester('192.168.1.133', Host(ip = '193.104.137.133'), 'nemesys', '4gc0m244')
  
    time.sleep(5)
    
    for i in range(1, TOT + 1):
      logger.info('Test Download %d/%d' % (i, TOT))
      test = t1.testftpdown('/download/1000.rnd')
      logger.info(test)      

    for i in range(1, TOT + 1):
      logger.info('Test Upload %d/%d' % (i, TOT))
      test = t1.testftpup(2048, '/upload/r.raw')
      logger.info(test)

    t1.sniffer_stop()
    '''
    for i in range(1, TOT + 1):
      logger.info('\nTest Ping %d/%d' % (i, TOT))
      test = t1.testping()
      logger.info(test)
    '''

  else:
    main()

