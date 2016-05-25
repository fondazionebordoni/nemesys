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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
import logging
from os import path
from urlparse import urlparse
from xml.dom.minidom import parse
from xml.dom.minidom import parseString

import httputils
import paths
from timeNtp import timestampNtp
from xmlutils import iso2datetime


logger = logging.getLogger(__name__)

MAX_DAYS = 3

# TODO: Il file di progresso deve poter avere start nullo

class Progress(object):
    def __init__(self, clientid, progressurl=None):
        if not path.exists(paths.MEASURE_STATUS):
            logger.debug('Non trovato nessun file di progresso delle misure in %s' % paths.MEASURE_STATUS)
            if progressurl:
                self._progressurl = progressurl
                self._clientid = clientid
                try:
                    self._xml = self._downloadprogress()
                except Exception:
                    self._xml = self._newxml()
            else:
                self._xml = self._newxml()
            self._saveonfile()
        else:
            logger.debug('Trovato file con il progresso delle misure')
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

    def expired(self):
        '''
        Restituisce true se sono trascorsi  MAX_DAYS dallo start delle misure
        '''
        start = self.start()
        delta = datetime.fromtimestamp(timestampNtp()) - start
        if (delta.days <= MAX_DAYS):
            return False

        return True

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
        start.appendChild(xml.createTextNode(datetime.fromtimestamp(timestampNtp()).isoformat()))
        measure.appendChild(start)

        content = xml.createElement('content')
        measure.appendChild(content)

        return xml

    def _saveonfile(self):
        f = open(paths.MEASURE_STATUS, 'w')
        f.write(str(self))
        f.close()

    def putstamp(self, time):
        '''
        Salva l'oggetto Test ricevuto nel file XML interno.
        '''
        content = self._xml.getElementsByTagName('content')[0]
        slot = self._xml.createElement('slot')
        slot.appendChild(self._xml.createTextNode(time.isoformat()))
        content.appendChild(slot)
        self._saveonfile()

    def _downloadprogress(self):
        url = urlparse(self._progressurl)
        connection = httputils.getverifiedconnection(url=url, timeout=5)

        try:
            connection.request('GET', '%s?clientid=%s' % (url.path, self._clientid))
            data = connection.getresponse().read()
            logger.debug('Dati di progress ricevuti: %s' % data)
            xml = parseString(data)
        except Exception as e:
            logger.error('Impossibile scaricare il progress xml. Errore: %s.' % e)
            raise Exception('Impossibile scaricare il progress xml. Errore: %s.' % e)
        
        return xml

    def __str__(self):
        return self._xml.toxml('UTF-8')

if __name__ == '__main__':
    import log_conf
    log_conf.init_log()
    t = Progress('cli00000001', 'https://finaluser.agcom244.fub.it/ProgressXML')
    print t
