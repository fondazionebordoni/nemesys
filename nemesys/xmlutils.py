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
import status

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
  try:
    xml = parseString(data)
  except ExpatError:
    logger.error('Il dato ricevuto non è in formato XML: %s' % data)
    return None

  return xml

# Trasforma l'XML dei task nel prossimo Task da eseguire
def xml2task(data):

  if (len(data) < 1):
    logger.error('Nessun dato da processare')
    return None

  #logger.debug('Dati da convertire in XML:\n%s' % data)
  try:
    xml = parseString(data)
  except ExpatError as e:
    logger.error('Il dato ricevuto non è in formato XML: %s\n%s' % (e, data))
    return None

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
    return None

  # Aggancio dei dati opzinali
  try:
    servername = getvalues(node, tag_servername)
    multiplier = node.getElementsByTagName(tag_upload)[0].getAttribute(att_multiplier)
    nicmp = node.getElementsByTagName(tag_ping)[0].getAttribute(att_icmp)
    delay = node.getElementsByTagName(tag_ping)[0].getAttribute(att_delay)
    now = node.getElementsByTagName(tag_start)[0].getAttribute(att_now)
  except IndexError:
    pass

  # Verifica che i dati siano compatibili
  # Dati numerici/booleani
  try:
    if (len(upload) <= 0):
      logger.error('L\'XML non contiene il numero di upload da effettuare')
      return None
    else:
      upload = int(upload)

    if (len(download) <= 0):
      logger.error('L\'XML non contiene il numero di download da effettuare')
      return None
    else:
      download = int(download)

    if (len(ping) <= 0):
      logger.error('L\'XML non contiene il numero di ping da effettuare')
      return None
    else:
      ping = int(ping)

    if (len(multiplier) <= 0):
      logger.warn('L\'XML non contiene il multiplicatore per la grandezza del file di upload (default = 5)')
      multiplier = 5
    else:
      multiplier = int(multiplier)

    if (len(nicmp) <= 0):
      logger.warn('L\'XML non contiene il numero di pacchetti icmp per la prova ping da effettuare (default = 4)')
      nicmp = 4
    else:
      nicmp = int(nicmp)

    if (len(delay) <= 0):
      logger.warn('L\'XML non contiene il valore di delay, in secondi, tra un ping e l\'altro (default = 1)')
      delay = 1
    else:
      delay = int(delay)

    if (len(now) <= 0):
      logger.warn('L\'XML non contiene indicazione se il task deve essere iniziato subito (default = 0)')
      now = False
    else:
      now = bool(now)

  except TypeError:
    logger.error('Errore durante la verifica della compatibilità dei dati numerici di task')
    return None

  # Date
  try:
    start = datetime.strptime(start, startformat)
  except ValueError:
    logger.error('Errore durante la verifica della compatibilità dei dati orari di task')
    logger.debug('XML: %s' % data)
    return None

  # Ip
  # TODO Controllare validità dati IP

  server = Server(serverid, serverip, servername)
  return Task(id=id, start=start, server=server, ftpdownpath=ftpdownpath, ftpuppath=ftpuppath, upload=upload, download=download, multiplier=multiplier, ping=ping, nicmp=nicmp, delay=delay, now=now)


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
  if (len(data) < 1):
    logger.error('Nessun dato da processare')
    raise Exception('Il demone che effettua le misure non invia informazioni sul suo stato.');

  #logger.debug('Dati da convertire in XML:\n%s' % data)
  try:
    xml = parseString(data)
  except ExpatError:
    logger.error('Il dato ricevuto non è in formato XML: %s' % data)
    raise Exception('Errore di formattazione del messaggio di stato del demone delle misure.');

  nodes = xml.getElementsByTagName('status')
  if (len(nodes) < 1):
    logger.debug('Nessun status trovato nell\'XML:\n%s' % xml.toxml())
    raise Exception('Nessuna informazione sullo stato del demone delle misure ricevuta.');

  node = nodes[0]

  # Aggancio dei dati richiesti
  try:
    icon = getvalues(node, 'icon')
    message = getvalues(node, 'message')
  except IndexError:
    logger.error('L\'XML ricevuto non contiene tutti i dati richiesti. XML: %s' % data)
    raise Exception('I messaggi di stato del demone non contengono tutte le informazioni richieste.');

  return Status(icon, message)
