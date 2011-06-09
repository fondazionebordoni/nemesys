# xmlutils.py
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
from logger import logging
from server import Server
from status import Status
from string import join
from task import Task
from xml.dom import Node
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError
from timeNtp import timestampNtp
import re

tag_task = 'task'
tag_id = 'id'
tag_upload = 'nftpup'
att_multiplier = 'mult'
tag_download = 'nftpdown'
tag_ping = 'nping'
att_icmp = 'icmp'
att_delay = 'delay'
tag_start = 'start'
att_now = 'now'
tag_serverid = 'srvid'
tag_serverip = 'srvip'
tag_servername = 'srvname'
tag_ftpdownpath = 'ftpdownpath'
tag_ftpuppath = 'ftpuppath'
tag_message = 'message'
startformat = '%Y-%m-%d %H:%M:%S'

logger = logging.getLogger()

def iso2datetime(s):
  '''
  La versione 2.5 di python ha un bug nella funzione strptime che non riesce
  a leggere i microsecondi (%f)
  '''
  p = s.split('.')
  dt = datetime.strptime(p[0], '%Y-%m-%dT%H:%M:%S')

  # Gstione dei microsecondi
  ms = 0
  try:
    if len(p) > 1:
      ms = int(p[1])
  except:
    ms = 0
  dt.replace(microsecond=ms)
  return dt

def getxml(data):
  
  if (len(data) < 1):
    logger.error('Nessun dato da processare')
    raise Exception('Ricevuto un messaggio vuoto');

  logger.debug('Dati da convertire in XML:\n%s' % data)
  try:
    xml = parseString(data)
  except ExpatError:
    logger.error('Il dato ricevuto non è in formato XML: %s' % data)
    raise Exception('Errore di formattazione del messaggio');

  return xml

# Trasforma l'XML dei task nel prossimo Task da eseguire
def xml2task(data):
  
  try:
    xml = getxml(data)
  except Exception as e:
    logger.error('Errore durante la conversione dei dati di task')
    raise Exception('Le informazioni per la programmazione delle misure non sono corrette. %s' % e)

  nodes = xml.getElementsByTagName(tag_task)
  if (len(nodes) < 1):
    logger.debug('Nessun task trovato nell\'XML:\n%s' % xml.toxml())
    return None

  # Considera solo il primo task
  node = nodes[0]
  #logger.debug('Task trovato:\n%s' % nodedata(node))

  # Aggancio dei dati richiesti
  try:
    id = getvalues(node, tag_id)
    upload = getvalues(node, tag_upload)
    download = getvalues(node, tag_download)
    ping = getvalues(node, tag_ping)
    start = getvalues(node, tag_start)
    serverid = getvalues(node, tag_serverid)
    serverip = getvalues(node, tag_serverip)
    ftpdownpath = getvalues(node, tag_ftpdownpath)
    ftpuppath = getvalues(node, tag_ftpuppath)
  except IndexError:
    logger.error('L\'XML ricevuto non contiene tutti i dati richiesti. XML: %s' % data)
    raise Exception('Le informazioni per la programmazione delle misure sono incomplete.')

  # Aggancio dei dati opzionali
  servername = None
  message = None
  try:
    servername = getvalues(node, tag_servername)
    multiplier = node.getElementsByTagName(tag_upload)[0].getAttribute(att_multiplier)
    nicmp = node.getElementsByTagName(tag_ping)[0].getAttribute(att_icmp)
    delay = node.getElementsByTagName(tag_ping)[0].getAttribute(att_delay)
    now = node.getElementsByTagName(tag_start)[0].getAttribute(att_now)
    message = getvalues(node, tag_message)
  except IndexError:
    pass

  # Verifica che i dati siano compatibili
  # Dati numerici/booleani
  try:
    if (len(upload) <= 0):
      logger.error('L\'XML non contiene il numero di upload da effettuare')
      raise Exception('Le informazioni per la programmazione delle misure sono errate.')
    else:
      upload = int(upload)

    if (len(download) <= 0):
      logger.error('L\'XML non contiene il numero di download da effettuare')
      raise Exception()
    else:
      download = int(download)

    if (len(ping) <= 0):
      logger.error('L\'XML non contiene il numero di ping da effettuare')
      raise Exception()
    else:
      ping = int(ping)

    if (len(multiplier) <= 0):
      logger.info('L\'XML non contiene il multiplicatore per la grandezza del file di upload (default = 5)')
      multiplier = 5
    else:
      multiplier = int(multiplier)

    if (len(nicmp) <= 0):
      logger.info('L\'XML non contiene il numero di pacchetti icmp per la prova ping da effettuare (default = 4)')
      nicmp = 4
    else:
      nicmp = int(nicmp)

    if (len(delay) <= 0):
      logger.info('L\'XML non contiene il valore di delay, in secondi, tra un ping e l\'altro (default = 1)')
      delay = 1
    else:
      delay = int(delay)

    if (len(now) <= 0):
      logger.info('L\'XML non contiene indicazione se il task deve essere iniziato subito (default = 0)')
      now = False
    else:
      now = bool(now)

  # TODO Testare catena di eccezioni
  except TypeError:
    logger.error('Errore durante la verifica della compatibilità dei dati numerici di task')
    raise Exception()

  except Exception:
    raise Exception('Le informazioni per la programmazione delle misure sono errate.')

  # Date
  try:
    start = datetime.strptime(start, startformat)
  except ValueError:
    logger.error('Errore durante la verifica della compatibilità dei dati orari di task')
    logger.debug('XML: %s' % data)
    print data
    raise Exception('Le informazioni orarie per la programmazione delle misure sono errate.')

  # Ip
  # TODO Controllare validità dati IP

  server = Server(serverid, serverip, servername)
  return Task(id=id, start=start, server=server, ftpdownpath=ftpdownpath, ftpuppath=ftpuppath, upload=upload, download=download, multiplier=multiplier, ping=ping, nicmp=nicmp, delay=delay, now=now, message=message)

def getvalues(node, tag=None):

  if (tag == None):
    values = []
    for child in node.childNodes:
      if child.nodeType == Node.TEXT_NODE:
        #logger.debug('Trovato nodo testo.')
        values.append(child.nodeValue)

    #logger.debug('Value found: %s' % join(values).strip())
    return join(values).strip()

  else:
    return getvalues(node.getElementsByTagName(tag)[0])

def nodedata(node):
  s = ''
  for child in node.childNodes:
    if child.nodeType != Node.TEXT_NODE:
      s += '%s: %s\n' % (child.nodeName, getvalues(child))
  return s.strip('\n')

def xml2status(data):

  try:
    xml = getxml(data)
  except Exception as e:
    logger.error('Errore durante la conversione dei dati di stato del processo di misura')
    raise Exception('Le informazioni di stato del processo di misura non sono corrette. %s. Provare a riavviare il programma.' % e)

  nodes = xml.getElementsByTagName('status')
  if (len(nodes) < 1):
    logger.debug('Nessun status trovato nell\'XML:\n%s' % xml.toxml())
    raise Exception('Nessuna informazione ricevuta sullo stato del processo che effettua misure.');

  node = nodes[0]

  # Aggancio dei dati richiesti
  try:
    color = getvalues(node, 'color')
    message = getvalues(node, 'message')
  except IndexError:
    logger.error('L\'XML ricevuto non contiene tutti i dati richiesti. XML: %s' % data)
    raise Exception('I messaggi di stato del processo che effettua le misure non contengono tutte le informazioni richieste.');

  return Status(color, message)

def getcommentvalue(filename, comment, pattern='.*'):
  '''
  Ricava il valore di un commento nell'XML
  '''
  CSTART = '<!--'
  CEND = '-->'

  with open(filename) as f:
    data = f.read()

  m = re.search('%s %s (%s) %s' % (re.escape(CSTART), re.escape(comment), pattern, re.escape(CEND)), data)
  value = m.group(1)

  return value

def file2xml(filename):
  with open(filename) as f:
    data = f.read()

  return getxml(data)

def getstarttime(filename):
  '''
  Ricava il tempo di start da un file di misura
  '''
  with open(filename) as f:
    data = f.read()
  
  try:
    xml = getxml(data)
  except Exception as e:
    logger.error('Errore durante la conversione dei dati di misura contenuti nel file.')
    raise Exception('Le informazioni di misura non sono corrette. %s' % e)

  nodes = xml.getElementsByTagName('measure')
  if (len(nodes) < 1):
    logger.debug('Nessun measure trovato nell\'XML:\n%s' % xml.toxml())
    raise Exception('Nessuna informazione di misura nel file.');

  node = nodes[0]

  # Aggancio dei dati richiesti
  try:
    start = node.getAttribute('start')
  except IndexError:
    logger.error('L\'XML ricevuto non contiene il dato di start. XML: %s' % data)
    raise Exception('Errore durante il controllo dell\'orario di inizio della misura.');

  return start

def getfinishedtime(filename):
  '''
  Ricava il tempo di chiusura da un file di misura
  '''
  try:
    pattern = '[\dT\-:\.]*'
    # TODO Migliorare riferimenti a [finished] vedi executer.
    comment = '[finished]'
    time = iso2datetime(getcommentvalue(filename, comment, pattern))
  except Exception as e:
    logger.error('Errore durante il recupero del valore finished della misura: %s' % e)
    time=datetime.fromtimestamp(timestampNtp())    
  return time


if __name__ == '__main__':
  
  empty_xml = ''
  fake_xml = 'pippo'
  generic_xml = '''<?xml version="1.0" encoding="UTF-8"?>
  <measure>
    <content/>
  </measure>
  '''
  task_xml = '''<?xml version="1.0" encoding="UTF-8"?>
 <calendar>
  <task>
   <id>1</id>
   <nftpup mult="10">20</nftpup>
   <nftpdown>20</nftpdown>
   <nping icmp="1" delay="10">10</nping>
   <start now="1">2010-01-01 00:01:00</start>
   <srvid>fubsrvrmnmx03</srvid>
   <srvip>193.104.137.133</srvip>
   <srvname>NAMEX</srvname>
   <ftpuppath>/upload/1.rnd</ftpuppath>
   <ftpdownpath>/download/8000.rnd</ftpdownpath>
  </task>
 </calendar>
  '''
  status_xml = '''<?xml version="1.0" encoding="UTF-8"?>
  <status>
    <color>orange</color>
    <message>Ne.Me.Sys. sta effettuando una misura.</message>
  </status>
  '''
  empty_xml_file = 'test/empty_xml_file.xml'
  fake_xml_file = 'test/fake_xml_file.xml'
  generic_xml_file = 'test/generic_xml_file.xml'
  measure_xml_file = 'test/measure_xml_file.xml'
  
  # Test getxml(data)
  print '(getxml) Errore dato vuoto: %s' % empty_xml
  try:
    print getxml(empty_xml)
  except Exception as e:
    print e
 
  print '(getxml) Errore xml non corretto: %s' % fake_xml
  try:
    print getxml(fake_xml)
  except Exception as e:
    print e
    
  print '(getxml) XML legittimo: %s' % generic_xml
  try:
    print getxml(generic_xml)
  except Exception as e:
    print e
  
  # Test xml2task
  print '(xml2task) XML legittimo ma non task: %s' % generic_xml
  try:
    print xml2task(generic_xml)
  except Exception as e:
    print e

  print '(xml2task) XML di task: %s' % task_xml
  try:
    print xml2task(task_xml)
  except Exception as e:
    print e
  
  # Test xml2task
  print '(xml2status) XML legittimo ma non status: %s' % generic_xml
  try:
    print xml2status(generic_xml)
  except Exception as e:
    print e
  
  print '(xml2status) XML di status: %s' % status_xml
  try:
    print xml2status(status_xml)
  except Exception as e:
    print e

  print '(file2xml) Conversione file vuoto in xml: %s' % empty_xml_file  
  try:
    print file2xml(empty_xml_file)
  except Exception as e:
    print e
  
  print '(file2xml) Conversione file vuoto in xml: %s' % fake_xml_file  
  try:
    print file2xml(fake_xml_file)
  except Exception as e:
    print e

  print '(file2xml) Conversione file vuoto in xml: %s' % generic_xml_file  
  try:
    print file2xml(generic_xml_file)
  except Exception as e:
    print e
  
  print '(getstarttime) Analisi start di misura: %s' % measure_xml_file
  try:
    print getstarttime(measure_xml_file)
  except Exception as e:
    print e
  
  