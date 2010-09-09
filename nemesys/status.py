# status.py
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

import paths
from logger import logging
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError

logger = logging.getLogger()

class Status:

    def __init__(self, icon, message):
        self._icon = icon
        self._message = message

    @property
    def icon(self):
        path = paths.ICONS + paths.DIR_SEP + self._icon 
        return path

    @property
    def message(self):
        return self._message
    
    def getxml(self):
        start = '''<status xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'/>'''
        xml = parseString(start)
        status = xml.getElementsByTagName('status')[0]
        
        icon = xml.createElement('icon')
        icon.appendChild(xml.createTextNode(self._icon.decode('utf8', 'replace')))
        status.appendChild(icon)

        message = xml.createElement('message')
        message.appendChild(xml.createTextNode(self._message.decode('utf8', 'replace')))
        status.appendChild(message)
        
        return xml.toxml()

ERROR = Status(u'nemesys_red.png', 'Impossibile contattare il demone che effettua le misure.')
PAUSE = Status(u'nemesys_white.png', 'Il server è in pausa. Non verranno effettuate misure nella prossima ora.')
PLAY = Status(u'nemesys_green.png', 'Nemesys sta effettuando una misura...')
FINISHED = Status(u'nemesys_cyan.png', 'Nemesys ha terminato le misurazioni')
READY = Status(u'nemesys_amber.png', 'Nemesys effettuerà una misura nella prossima ora')
LOGO = Status(u'nemesys_logo.png', 'Nemesys (Network Measurement System)')

