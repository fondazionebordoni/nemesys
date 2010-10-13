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
bad_conn = [80, 8080, 110, 25, 443]
bad_proc = ['amule', 'emule', 'bittorrent']

logger = logging.getLogger()


if Path.isfile(paths.THRESHOLD):
   
  th_values = {}
  try:
    for subelement in ET.XML(open(paths.THRESHOLD).read()):
      th_values.update({subelement.tag:subelement.text})
  except Exception as e:
    logger.warning('Errore durante il recupero delle soglie da file. %s' % e)
    raise Exception('Errore durante il recupero delle soglie da file.')
  
  # TODO eliminare NONE e bloccare esecuzione in presenza problema di casting
  # commentato controllo su lettura e scrittura disco per debug
  try:
    th_host = int(th_values[tag_hosts])
    th_avMem = float(th_values[tag_avMem])
    th_memLoad = float(th_values[tag_memLoad])
    #th_wdisk = float(th_values[tag_wdisk])
    th_cpu = float(th_values[tag_cpu])
    #th_rdisk = float(th_values[tag_rdisk])
    bad_conn = []
    for j in th_values[tag_conn].split(';'):
      bad_conn.append(int(j))
    bad_proc = []
    for j in th_values[tag_proc].split(';'):
      bad_proc.append(str(j))
  except ValueError as e:
      logger.error('errore nel casting dei paramentri di SystemProfiler!')
       #raise e
  
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
    # TODO eliminare NONE e bloccare esecuzione in presenza problema di casting
    try:
      c.append(int(j.split(':')[1]))
    except ValueError as e:
      logger.error('errore nel casting dei paramentri di SystemProfiler!')
      c = [None]
      #raise e
    
  for i in bad_conn:
    if i in c:
      raise Exception, 'Porta %d aperta ed utilizzata.' % i

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
    # TODO eliminare NONE e bloccare esecuzione in presenza problema di casting
    try:
      t.append(str(j))
    except ValueError as e:
      logger.error('errore nel casting dei paramentri di SystemProfiler!')
      t = None
      #raise e
    
  for i in bad_proc:
    for k in t:
      if (bool(re.search(i, k, re.IGNORECASE))):
       raise Exception, 'Sono attivi processi non desiderati: chiudere il programma %s per proseguire le misure.' % i
  
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

# TODO eliminare NONE e bloccare esecuzione in presenza problema di casting

  try:
    avMem = float(values[tag_avMem])
  except ValueError as e:
    logger.error('errore nel casting dei paramentri di SystemProfiler!')
    avMem = None
    pass
    #raise e

  try:
    memLoad = float(values[tag_memLoad])
  except ValueError as e:
    logger.error('errore nel casting dei paramentri di SystemProfiler!')
    memLoad = None
    pass
    #raise e

  try:
    cpu = float(values[tag_cpu])
  except ValueError as e:
    logger.error('errore nel casting dei paramentri di SystemProfiler!')
    cpu = None
    pass
    #raise e

  if avMem < th_avMem:
    raise Exception('Memoria non sufficiente.')
  if memLoad > th_memLoad:
    raise Exception('Memoria non sufficiente.')
  if cpu > th_cpu:
    raise Exception('CPU occupata.')

  return True

def mediumcheck():

  fastcheck()

  d = {tag_wireless:'', tag_fw:''}
  values = getstatus(d)

# TODO eliminare pass e bloccare esecuzione in presenza problema di casting

  try:
    fw = str(values[tag_fw])
  except ValueError as e:
    logger.error('errore nel casting dei paramentri di SystemProfiler!')
    fw = None
    pass
    #raise e

  try:
    wireless = str(values[tag_wireless])
  except ValueError as e:
    logger.error('errore nel casting dei paramentri di SystemProfiler!')
    wireless = None
    pass
    #raise e


  if fw.lower() == 'True'.lower():
    raise Exception('Firewall attivo.')
  if wireless.lower() == 'True'.lower():
    raise Exception('Wireless LAN attiva.')

  return True

def checkall():

  mediumcheck()
  # TODO Reinserire questo check quanto corretto il problema di determinazione del dato
  #checkdisk()
  
  ip = getIp()
  if bool(re.search('^10\.|^172\.(1[6-9]|2[0-9]|3[01])\.|^192\.168\.', ip)):
    checkhosts()

  return True

def checkhosts():

  d = {tag_hosts:''}
  values = getstatus(d)

  try:
    host = int(values[tag_hosts])
  except ValueError as e:
    logger.error('errore nel casting dei paramentri di SystemProfiler!')
    host = None
    #raise e

  if host > th_host:
    raise Exception('Presenza altri host in rete.')

  return True

def checkdisk():
  
  d = {tag_wdisk:'', tag_rdisk:''}
  values = getstatus(d)

  try:
    wdisk = float(values[tag_wdisk])
  except ValueError as e:
    logger.error('errore nel casting dei paramentri di SystemProfiler!')
    wdisk = None
    #raise e

  try:
    rdisk = float(values[tag_rdisk])
  except ValueError as e:
    logger.error('errore nel casting dei paramentri di SystemProfiler!')
    rdisk = None
     #raise e
     
  if wdisk > th_wdisk:
    raise Exception('Eccessivo carico in scrittura del disco.')
  if rdisk > th_rdisk:
    raise Exception('Eccessivo carico in lettura del disco.')

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
  print '\nTest sysmonitor getMac: %s' % getMac()
  print '\nTest sysmonitor getSys: %s' % getSys()
