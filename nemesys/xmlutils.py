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
from string import join
from task import Task
from xml.dom import Node
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError
from server import Server

tag_task = 'task'
tag_id = 'id'
tag_upload = 'nftpup'
att_multiplier = 'mult'
tag_download = 'nftpdown'
tag_ping = 'nping'
att_icmp = 'icmp'
att_delay = 'delay'
tag_start = 'start'
tag_serverid = 'srvid'
tag_serverip = 'srvip'
tag_servername = 'srvname'
tag_ftpdownpath = 'ftpdownpath'
tag_ftpuppath = 'ftpuppath'
startformat = '%Y-%m-%d %H:%M:%S'

logger = logging.getLogger()

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

  logger.debug('Dati da convertire in XML:\n%s' % data)
  try:
    xml = parseString(data)
  except ExpatError:
    logger.error('Il dato ricevuto non è in formato XML: %s' % data)
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
  except IndexError:
    pass

  # Verifica che i dati siano compatibili
  # Dati numerici
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
  return Task(id=id, start=start, server=server, ftpdownpath=ftpdownpath, ftpuppath=ftpuppath, upload=upload, download=download, multiplier=multiplier, ping=ping, nicmp=nicmp, delay=delay)


def getvalues(node, tag=None):

  if (tag == None):
    values = []
    for child in node.childNodes:
      if child.nodeType == Node.TEXT_NODE:
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

