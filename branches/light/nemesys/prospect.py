# prospect.py
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

from datetime import datetime
from logger import logging
from os import path
from timeNtp import timestampNtp
from urlparse import urlparse
from xml.dom.minidom import parse, parseString
from xmlutils import iso2datetime
from client import Client
from measure import Measure
from profile import Profile
from isp import Isp
from server import Server
from proof import Proof
import httputils
import paths

logger = logging.getLogger()

# TODO Il file di progresso deve poter avere start nullo

class Prospect:
  def __init__(self):
    if not path.exists(paths.MEASURE_PROSPECT):
      logger.debug('Non trovato nessun file di progresso delle misure in %s' % paths.MEASURE_STATUS)
      self._xml = self._newxml()
      self._saveonfile()
    else:
      logger.debug('Trovato file con il progresso delle misure')
      self._xml = parse(paths.MEASURE_PROSPECT)

    logger.debug('XML con lo stato delle misure:\n%s' % self._xml.toxml())

  def _newxml(self):
    logger.debug('Creo il file dello stato delle misure.')
    xml = parseString('<?xml-stylesheet type="text/xsl" href="prospect.xsl"?><prospect />')
    measure = xml.getElementsByTagName('prospect')[0]

    content = xml.createElement('content')
    measure.appendChild(content)

    return xml

  def _saveonfile(self):
    f = open(paths.MEASURE_PROSPECT, 'w')
    f.write(str(self))
    f.close()

  def __str__(self):
    return self._xml.toxml('UTF-8')

  def save_measure(self, measure):
    '''
    Salva l'oggetto Test ricevuto nel file XML interno.
    '''
    #node = self.measure2node(measure)
    body = self._xml.getElementsByTagName('content')[0]
    body.appendChild(measure._xml.getElementsByTagName('measure')[0])

    self._saveonfile()

  def measure2node(self, measure):
    xml = self._xml

    t = xml.createElement('measure')
    t.appendChild(measure.getxml())

    return t

if __name__ == '__main__':
  p = Prospect()
  c = Client('fub0010000001', Profile('1mb512kb', 1024, 512), Isp('fub001'), 'geo')
  m = Measure(1, Server(id = 'fubsrvnmx01', ip = '127.0.0.1'), c)
  m.savetest(Proof('download', datetime.utcnow(), .020, 1024 * 1024), {})
  m.savetest(Proof('upload', datetime.utcnow(), .020, 1024 * 1024), {})
  p.save_measure(m)
  m = Measure(1, Server(id = 'fubsrvnmx01', ip = '127.0.0.1'), c)
  m.savetest(Proof('download', datetime.utcnow(), .030, 1024 * 1024), {})
  m.savetest(Proof('upload', datetime.utcnow(), .030, 1024 * 1024), {})
  p.save_measure(m)
  print p
  p._saveonfile()
