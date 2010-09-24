# progress.py
# -*- coding: utf-8 -*-

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

from xmlutils import iso2datetime
from datetime import datetime
from os import path
import paths
from xml.dom.minidom import parse
from xml.dom.minidom import parseString
from logger import logging

logger = logging.getLogger()

MAX_DAYS = 3

class Progress:

  def __init__(self, create=False):
    if not path.exists(paths.MEASURE_STATUS) and create:
      self._xml = self._newxml()
      self._saveonfile()
    else:
      self._xml = parse(paths.MEASURE_STATUS)

    logger.debug('XML con lo stato delle misure:\n%s' % self._xml.toxml())

  @property
  def id(self):
    return self._id

  def start(self):
    '''
    Restituisce l'orario di inizio delle misure (datetime) come ricavato dall'XML
    '''
    start = self._xml.documentElement.getElementsByTagName('start')[0].firstChild.data
    return iso2datetime(start)

  def isdone(self, hour):
    '''
    Controlla lo stato delle misure nell'ora indicata: restituisce
    True se per l'ora indicata sono già presenti degli "slot" validi
    '''

    slots = self._xml.documentElement.getElementsByTagName('slot')
    for slot in slots:
      slottime = iso2datetime(slot.firstChild.data)
      if (hour == slottime.hour):
        return True

    return False

  def howmany(self, hour):
    '''
    Retituisce il numero di misure effettuate nell'ora indicata.
    '''
    n = 0
    slots = self._xml.documentElement.getElementsByTagName('slot')
    for slot in slots:
      slottime = iso2datetime(slot.firstChild.data)
      if (hour == slottime.hour):
        n += 1

    return n

  def onair(self):
    '''
    Restituisce true se non sono trascorsi ancora MAX_DAYS dallo start delle misure
    '''
    start = self.start()
    delta = datetime.now() - start
    if (delta.days > MAX_DAYS):
      return False

    return True

  # TODO Implementare funzione doneall()
  def doneall(self):
    '''
    Restituisce true se ho effettuato almeno una misura per ciascuna ora
	  '''
    for i in range(0, 24):
      if not self.isdone(i):
        return False
    return True

  def _newxml(self):
    logger.debug('Creo il file dello stato delle misure.')
    xml = parseString('<measure />')
    measure = xml.getElementsByTagName('measure')[0]

    start = xml.createElement('start')
    start.appendChild(xml.createTextNode(datetime.now().isoformat()))
    measure.appendChild(start)

    content = xml.createElement('content')
    measure.appendChild(content)

    return xml

  def _saveonfile(self):
    f = open(paths.MEASURE_STATUS, 'w')
    f.write(str(self))
    f.close()

  def putstamp(self):
    '''
    Salva l'oggetto Test ricevuto nel file XML interno.
    '''
    content = self._xml.getElementsByTagName('content')[0]
    slot = self._xml.createElement('slot')
    slot.appendChild(self._xml.createTextNode(datetime.now().isoformat()))
    content.appendChild(slot)
    self._saveonfile()

  def __str__(self):
    return self._xml.toxml('UTF-8')

if __name__ == '__main__':
  t = Progress('cli00000001')
  print t

