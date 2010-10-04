# sysmonitor.py
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
from xml.etree import ElementTree as ET
import paths

tag_results = 'SystemProfilerResults'
tag_threshold = 'SystemProfilerThreshold'
tag_vers = 'vers'
tag_avMem = 'availableMemory'
tag_wireless = 'wirelessON'
tag_fw = 'firewall'
tag_memLoad = 'memoryLoad'
tag_ip = 'ipAddr'
tag_sys = 'system'
tag_wdisk = 'diskWrite'
tag_cpu = 'cpuLoad'
tag_mac = 'macAddr'
tag_rdisk = 'diskRead'
tag_release = 'release'
tag_cores = 'cores'
tag_arch = 'arch'
tag_proc = 'processor'
tag_hosts = 'hostNumber'
tag_conn = 'activeConnections'
tag_proc = 'processList'

# Soglie di sistema
# ------------------------------------------------------------------------------

th_host = 2
th_avMem = 134217728
th_memLoad = 80
th_wdisk = 104857600
th_cpu = 60
th_rdisk = 104857600
bad_conn = [80, 8080, 110, 25]
bad_proc = ['amule', 'emule', 'bittorrent']

logger = logging.getLogger()

try:
  from SystemProfiler import systemProfiler
except Exception as e:
  logger.warning('Impossibile importare SystemProfiler')
  pass

def getstatus(d):

  data = ''

  try:
    data = systemProfiler('test', d)
  except Exception as e:
    logger.warning('Non sono riuscito a trovare lo stato del computer con SystemProfiler.')
    data = open(paths.RESULTS).read()

  return getvalues(data, tag_results)

def connectionCheck():
  '''
  Effettua il controllo sulle connessioni attive
  '''
  d = {tag_conn:''}
  values = getstatus(d)
  connActive = values[tag_conn]

  if connActive == None or len(connActive) <= 0:
    return True

  c = []
  for j in connActive.split(';'):
    c.append(int(j.split(':')[1]))

  for i in bad_conn:
    if i in c:
      raise Exception, 'Sono attive connessioni non desiderate: porta %d aperta ed utilizzata.' % i

  return True

def taskCheck():
  '''
  Ettettua il controllo sui processi
  '''
  d = {tag_proc:''}
  values = getstatus(d)
  taskActive = values[tag_proc]

  if taskActive == None or len(taskActive) <= 0:
    return True

  t = []
  for j in taskActive.split(';'):
    t.append(str(j))

  for i in bad_proc:
    if i in t:
      raise Exception, 'Sono attivi processi non desiderati. Chiudere l\'applicazione "%s" per continuare le misure.' % i

  return True

def fastcheck():
  '''
  Esegue un controllo veloce dello stato del pc dell'utente.
  Ritorna True se le condizioni per effettuare le misure sono corrette,
  altrimenti solleva un'eccezione
  '''

  connectionCheck()
  taskCheck()

  d = {tag_avMem:'', tag_memLoad:'', tag_cpu:''}
  values = getstatus(d)

  if eval(values[tag_avMem]) < th_avMem:
    raise Exception('Memoria non sufficiente.')
  if eval(values[tag_memLoad]) > th_memLoad:
    raise Exception('Memoria non sufficiente.')
  if eval(values[tag_cpu]) > th_cpu:
    raise Exception('CPU occupata.')

  return True

def mediumcheck():

  fastcheck()

  d = {tag_wireless:'', tag_fw:''}
  values = getstatus(d)

  if bool(eval(values[tag_fw])):
    raise Exception('Firewall attivo.')
  if bool(eval(values[tag_wireless])):
    raise Exception('Wireless LAN attiva.')

  return True

def checkall():

  mediumcheck()

  d = {tag_wdisk:'', tag_rdisk:'', tag_hosts:''}
  values = getstatus(d)

  if eval(values[tag_wdisk]) > th_wdisk:
    raise Exception('Eccessivo carico in scrittura del disco.')
  if eval(values[tag_rdisk]) > th_rdisk:
    raise Exception('Eccessivo carico in lettura del disco.')
  if int(values[tag_hosts]) > int(th_host):
    raise Exception('Presenza altri host in rete.')

  return True

def getMac():
  '''
  restituisce indirizzo MAC del computer
  '''
  d = {tag_mac:''}
  values = getstatus(d)

  return values[tag_mac]

def getSys():
  '''
  Restituisce array con informazioni sul sistema utilizzato per il test
  '''
  d = {tag_vers:'', tag_sys:'', tag_mac:'', tag_release:'', tag_cores:'', tag_arch:'', tag_proc:''}
  values = getstatus(d)

  r = []

  for i in values:
    r.append(values[i])

  return r

def getvalues(string, tag):
  '''
  Estrae informazioni dal SystemProfiler 
  '''
  values = {}
  for subelement in ET.XML(string):
    values.update({subelement.tag:subelement.text})

  return values

if __name__ == '__main__':
  print '_______________________________________\n'
  print 'Test sysmonitor fastcheck: %s' % fastcheck()
  print 'Test sysmonitor mediumcheck: %s' % mediumcheck()
  print 'Test sysmonitor checkall: %s' % checkall()
  print '\nTest sysmonitor getMac: %s' % getMac()
  print '\nTest sysmonitor getSys: %s' % getSys()
