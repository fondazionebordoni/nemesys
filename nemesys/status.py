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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from logger import logging
from xml.dom.minidom import parseString

logger = logging.getLogger()

class Status(object):

    def __init__(self, color, message):
        if isinstance (color, Status):
            self._color = color.color
        else:
            self._color = color.decode('utf-8')

        self._message = message.decode('utf-8')

    @property
    def color(self):
        return self._color.encode('ascii', 'xmlcharrefreplace')

    @property
    def message(self):
        return self._message.encode('ascii', 'xmlcharrefreplace')

    def setmessage(self, message):
        self._message = message.decode('utf-8')

    def __str__(self):
        return self.getxml()

    def getxml(self):
        xml = parseString('<status />')
        status = xml.getElementsByTagName('status')[0]

        color = xml.createElement('color')
        color.appendChild(xml.createTextNode(self.color))
        status.appendChild(color)

        message = xml.createElement('message')
        message.appendChild(xml.createTextNode(self.message))
        status.appendChild(message)

        return xml.toxml()

ERROR = Status('red', 'Impossibile contattare il sistema che effettua le misure.')
PAUSE = Status('dark grey', 'Nemesys non deve effettuare misure nell\'ora corrente.')
PLAY = Status('orange', 'Nemesys sta effettuando una misura.')
FINISHED = Status('blue', 'Nemesys ha terminato di fare i test sulla linea ADSL. Controllare lo stato complessivo della misura.')
READY = Status('dark grey', 'Nemesys pronto e in attesa di eseguire una misura.')
OK = Status('dark green', 'Misura terminata con successo.')
MESSAGE = Status('blue', 'Avviso dal server centrale.')
LOGO = Status('purple', 'Nemesys (Network Measurement System). Sistema collegato e funzionante.')
LOGOSTATOMISURA2 = Status('logo_nemesys.png', 'Nemesys (Network Measurement System).')
LOGOSTATOMISURA1 = Status('logo_misurainternet.png', 'Misura Internet.')
