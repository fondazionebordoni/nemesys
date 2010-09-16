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
tag_task = 'taskList'
tag_conn = 'activeConnections'

logger = logging.getLogger()

# TODO modificare specifiche di valori booleani in stringa di SystemProfiler: 1 = True

def getstatus(d):

  data = ''

  try:
    from SystemProfiler import systemProfiler
    data = systemProfiler(d)
  except Exception:
    data = open(paths.RESULTS).read() #andrà sostituita con dati passati da sysProfiler

  return getvalues(data, tag_results)

def checkall():

  d = {tag_vers:'', tag_avMem:'', tag_wireless:'',  tag_fw:'',  tag_memLoad:'',  tag_ip:'',  tag_sys:'',  tag_wdisk:'',  tag_cpu:'',  tag_mac:'',  tag_rdisk:'',  tag_release:'',  tag_cores:'',  tag_arch:'',  tag_proc:'',  tag_hosts:'',  tag_task:'',  tag_conn:''}
  values = getstatus(d)
  threshold = getvalues(open(paths.THRESHOLD).read(), tag_threshold)

  # Logica di controllo del sistema

  connectionCheck(values[tag_conn], threshold[tag_conn])

  if int(values[tag_hosts]) > 1:
    raise Exception, 'Presenza altri host in rete.'
  if bool(eval(values[tag_fw])):
    raise Exception, 'Firewall attivo.'
  if bool(eval(values[tag_wireless])):
    raise Exception, 'Wireless LAN attiva.'

  # Logica di controllo con soglie lette da xml

  if eval(values[tag_avMem]) < eval(threshold[tag_avMem]):
    raise Exception('Memoria non sufficiente.')
  if eval(values[tag_memLoad]) > eval(threshold[tag_memLoad]):
    raise Exception, 'Memoria non sufficiente.'
  if eval(values[tag_cpu]) > eval(threshold[tag_cpu]):
    raise Exception, 'CPU occupata.'
  if eval(values[tag_wdisk]) > eval(threshold[tag_wdisk]):
    raise Exception, 'Eccessiva carico in scrittura del disco.'
  if eval(values[tag_rdisk]) > eval(threshold[tag_rdisk]):
    raise Exception, 'Eccessiva carico in lettura del disco.'

  return True

def mediumcheck():

#  d = {tag_avMem, tag_wireless, tag_fw, tag_memLoad, tag_cpu, tag_hosts, tag_task, tag_conn}
  d = {tag_vers:'', tag_avMem:'', tag_wireless:'',  tag_fw:'',  tag_memLoad:'',  tag_ip:'',  tag_sys:'',  tag_wdisk:'',  tag_cpu:'',  tag_mac:'',  tag_rdisk:'',  tag_release:'',  tag_cores:'',  tag_arch:'',  tag_proc:'',  tag_hosts:'',  tag_task:'',  tag_conn:''}
  values = getstatus(d)
  threshold = getvalues(open(paths.THRESHOLD).read(), tag_threshold)

  #logica di controllo del sistema

  connectionCheck(values[tag_conn], threshold[tag_conn])

  if values[tag_fw] != False:
    raise Exception, 'Firewall attivo.'
  if values[tag_wireless] != False:
    raise Exception, 'Wireless LAN attiva.'

  #logica di controllo con soglie lette da xml

  if values[tag_avMem] > threshold[tag_avMem]:
    raise Exception, 'Memoria non sufficiente.'
  if values[tag_memLoad] > threshold[tag_memLoad]:
    raise Exception, 'Memoria non sufficiente.'
  if values[tag_cpu] > threshold[tag_cpu]:
    raise Exception, 'CPU occupata.'

  return True

def fastcheck():
  '''
  Esegue un controllo veloce dello stato del pc dell'utente.
  Ritorna True se le condizioni per effettuare le misure sono corrette,
  altrimenti solleva un'eccezione
  '''

#  d = {tag_memLoad, tag_cpu, tag_task, tag_conn}
  d = {tag_vers:'', tag_avMem:'', tag_wireless:'',  tag_fw:'',  tag_memLoad:'',  tag_ip:'',  tag_sys:'',  tag_wdisk:'',  tag_cpu:'',  tag_mac:'',  tag_rdisk:'',  tag_release:'',  tag_cores:'',  tag_arch:'',  tag_proc:'',  tag_hosts:'',  tag_task:'',  tag_conn:''}
  values = getstatus(d)
  threshold = getvalues(open(paths.THRESHOLD).read(), tag_threshold)

  #logica di controllo del sistema

  connectionCheck(values[tag_conn], threshold[tag_conn])

  if values[tag_avMem] > threshold[tag_avMem]:
    raise Exception('Memoria non sufficiente.')
    return False
  if values[tag_memLoad] > threshold[tag_memLoad]:
    raise Exception, 'Memoria non sufficiente.'
  if values[tag_cpu] > threshold[tag_cpu]:
    raise Exception, 'CPU occupata.'

  return True

#creazione dizionario con risposte del SystemProfiler
def getvalues(string, tag):

  values = {}
  for subelement in ET.XML(string):
    values.update({subelement.tag:subelement.text})

  return values

def connectionCheck(connActive, connList):
  '''
  Ettettua il controllo sulle connessioni attive
  '''

  c = []
  for j in connActive.split(';'):
    c.append(j.split(':')[1])

  for i in connList.split(';'):
    if i in c:
      raise Exception, 'Sono attive connessioni non desiderate.'

  return True

if __name__ == '__main__':
  print 'Test sysmonitor: %s' % checkall()

