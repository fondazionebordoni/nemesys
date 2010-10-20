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
from os import path as Path
import paths
import re

# TODO Decidere se, quando non riesco a determinare i valori, sollevo eccezione
STRICT_CHECK = True

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
th_cpu = 80
th_rdisk = 104857600
bad_conn = [80, 8080, 110, 25]
bad_proc = ['amule', 'emule', 'bittorrent', 'skype', 'dropbox', 'chrome', 'iexplore', 'firefox', ]

logger = logging.getLogger()

# TODO Caricare da threshold SOLO se è una sonda
if Path.isfile(paths.THRESHOLD):

  th_values = {}
  try:
    for subelement in ET.XML(open(paths.THRESHOLD).read()):
      th_values.update({subelement.tag:subelement.text})
  except Exception as e:
    logger.warning('Errore durante il recupero delle soglie da file: %s' % e)
    raise Exception('Errore durante il recupero delle soglie da file.')

  try:
    th_host = int(th_values[tag_hosts])
    th_avMem = float(th_values[tag_avMem])
    th_memLoad = float(th_values[tag_memLoad])
    th_wdisk = float(th_values[tag_wdisk])
    th_cpu = float(th_values[tag_cpu])
    th_rdisk = float(th_values[tag_rdisk])
    bad_conn = []
    for j in th_values[tag_conn].split(';'):
      bad_conn.append(int(j))
    bad_proc = []
    for j in th_values[tag_proc].split(';'):
      bad_proc.append(str(j))
  except Exception as e:
      logger.error('Errore in lettura dei paramentri di threshold.')
      raise Exception('Errore in lettura dei paramentri di threshold.')

else:
  pass

try:
  from SystemProfiler import systemProfiler
except Exception as e:
  logger.warning('Impossibile importare SystemProfiler')
  pass

def getstatus(d):

  data = ''

  if Path.isfile(paths.RESULTS):
    data = open(paths.RESULTS).read()
  else:
    try:
      data = systemProfiler('test', d)
    except Exception as e:
      logger.warning('Non sono riuscito a trovare lo stato del computer con SystemProfiler.')

  return getvalues(data, tag_results)

def getfloattag(tag, value):
  d = {tag:''}
  values = getstatus(d)

  try:
    value = float(values[tag])
  except Exception as e:
    logger.error('Errore in lettura del paramentro "%s" di SystemProfiler: %s' % (tag, e))
    if STRICT_CHECK:
      raise Exception('Errore in lettura del paramentro "%s" di SystemProfiler.' % tag)
  
  return value

def getbooltag(tag, value):
  d = {tag:''}
  values = getstatus(d)

  try:
    value = str(values[tag]).lower()
  except Exception as e:
    logger.error('Errore in lettura del paramentro "%s" di SystemProfiler: %s' % (tag, e))
    if STRICT_CHECK:
      raise Exception('Errore in lettura del paramentro "%s" di SystemProfiler.' % tag)
  
  if STRICT_CHECK:
    if value != 'false' and value != 'true':
      logger.warning('Impossibile determinare il parametro "%s".' % tag)
      raise Exception('Impossibile determinare il parametro "%s".' % tag)

  if value == 'true':
    return True
  
  if value == 'false':
    return False

  return value

def checkconnections():
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
    try:
      c.append(int(j.split(':')[1]))
    except Exception as e:
      logger.error('Errore in lettura del paramentro "%s" di SystemProfiler: %s' % (tag_conn, e))
      if STRICT_CHECK:
        raise Exception('Errore in lettura del paramentro "%s" di SystemProfiler.' % tag_conn)

  for i in bad_conn:
    if i in c:
      raise Exception('Porta %d aperta ed utilizzata.' % i)

  return True

def checktasks():
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
    try:
      t.append(str(j))
    except Exception as e:
      logger.error('Errore in lettura del paramentro "%s" di SystemProfiler: %s' % (tag_proc, e))
      if STRICT_CHECK:
        raise Exception('Errore in lettura del paramentro "%s" di SystemProfiler.' % tag_proc)

  for i in bad_proc:
    for k in t:
      if (bool(re.search(i, k, re.IGNORECASE))):
        raise Exception('Sono attivi processi non desiderati: chiudere il programma "%s" per proseguire le misure.' % i)

  return True

def checkcpu():
  
  value = getfloattag(tag_cpu, th_cpu - 1)
  if value > th_cpu:
    raise Exception('CPU occupata.')

  return True

def checkmem():
  
  avMem = getfloattag(tag_avMem, th_avMem + 1)
  if avMem < th_avMem:
    raise Exception('Memoria non sufficiente.')

  memLoad = getfloattag(tag_memLoad, th_memLoad - 1)
  if memLoad > th_memLoad:
    raise Exception('Memoria non sufficiente.')

  return True

def checkfw():
  
  value = getbooltag(tag_fw, 'False')
  if value:
    raise Exception('Firewall attivo.')
  
  return True

def checkwireless():
  
  value = getbooltag(tag_wireless, 'False')
  if value:
    raise Exception('Wireless LAN attiva.')

  return True

def checkhosts():
  
  value = getfloattag(tag_hosts, th_host - 1)
  if value > th_host:
    raise Exception('Presenza altri host in rete.')

  return True

def checkdisk():

  value = getfloattag(tag_wdisk, th_wdisk - 1)
  if value > th_wdisk:
    raise Exception('Eccessivo carico in scrittura del disco.')

  value = getfloattag(tag_wdisk, th_rdisk - 1)
  if value > th_rdisk:
    raise Exception('Eccessivo carico in lettura del disco.')

  return True

def fastcheck():
  '''
  Esegue un controllo veloce dello stato del pc dell'utente.
  Ritorna True se le condizioni per effettuare le misure sono corrette,
  altrimenti solleva un'eccezione
  '''

  checkcpu()
  checkmem()
  checktasks()
  checkconnections()

  return True

def mediumcheck():

  fastcheck()
  checkfw()
  checkwireless()

  return True

def checkall():

  mediumcheck()
  # TODO Reinserire questo check quanto corretto il problema di determinazione del dato
  #checkdisk()

  ip = getIp()
  if bool(re.search('^10\.|^172\.(1[6-9]|2[0-9]|3[01])\.|^192\.168\.', ip)):
    checkhosts()

  return True

def getMac():
  '''
  restituisce indirizzo MAC del computer
  '''
  d = {tag_mac:''}
  values = getstatus(d)

  return values[tag_mac]

def getIp():
  '''
  restituisce indirizzo IP del computer
  '''
  d = {tag_ip:''}
  values = getstatus(d)

  return values[tag_ip]

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
  try:
    for subelement in ET.XML(string):
      values.update({subelement.tag:subelement.text})
  except Exception as e:
    logger.warning('Errore durante il recupero dello stato del computer. %s' % e)
    raise Exception('Errore durante il recupero dello stato del computer.')

  return values

if __name__ == '__main__':
  print 'Test sysmonitor fastcheck: %s' % fastcheck()
  print 'Test sysmonitor mediumcheck: %s' % mediumcheck()
  print 'Test sysmonitor checkall: %s' % checkall()
  print 'Test sysmonitor getMac: %s' % getMac()
  print 'Test sysmonitor getIP: %s' % getIp()
  print 'Test sysmonitor getSys: %s' % getSys()
