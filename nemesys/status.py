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

from logger import logging
from os import path
from xml.dom.minidom import parseString
import paths

logger = logging.getLogger()

class Status:

  def __init__(self, icon, message):
    if isinstance (icon, Status):
      self._trayicon = icon.baseicon
    else:
      self._trayicon = icon.decode('utf-8')

    self._message = message.decode('utf-8')

  @property
  def baseicon(self):
    return self._trayicon.encode('ascii', 'xmlcharrefreplace')

  @property
  def icon(self):
    return path.join(paths.ICONS, self.baseicon)

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

    icon = xml.createElement('icon')
    icon.appendChild(xml.createTextNode(self.baseicon))
    status.appendChild(icon)

    message = xml.createElement('message')
    message.appendChild(xml.createTextNode(self.message))
    status.appendChild(message)

    return xml.toxml()

ERROR = Status('nemesys_red.png', 'Impossibile contattare il sistema che effettua le misure.')
PAUSE = Status('nemesys_white.png', 'Ne.Me.Sys. non deve effettuare misure nell\'ora corrente.')
PLAY = Status('nemesys_green.png', 'Ne.Me.Sys. sta effettuando una misura.')
FINISHED = Status('nemesys_cyan.png', 'Ne.Me.Sys. ha terminato di fare i test sulla linea ADSL. Controllare lo stato complessivo della misura.')
READY = Status('nemesys_amber.png', 'Ne.Me.Sys. pronto e in attesa di eseguire una misura.')
LOGO = Status('nemesys_logo.png', 'Ne.Me.Sys. (Network Measurement System). Sistema collegato e funzionante.')
LOGOSTATOMISURA2 = Status('logo_nemesys_stato_misura.png', 'Ne.Me.Sys. (Network Measurement System).')
LOGOSTATOMISURA1 = Status('misintw_stato_misura.jpg', 'Misura Internet.')
