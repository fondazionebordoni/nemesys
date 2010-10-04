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
import paths
from xml.dom.minidom import parseString

logger = logging.getLogger()

class Status:

  def __init__(self, icon, message):
    if isinstance (icon, Status):
      self._trayicon = icon._trayicon
    else:
      self._trayicon = icon
            
    self._message = message

  @property
  def icon(self):
    path = paths.ICONS + paths.DIR_SEP + self._trayicon
    return path

  @property
  def message(self):
    return self._message
    
  def setmessage(self, message):
    self._message = message
    
  def __str__(self):
    return self.getxml()
    
  def getxml(self):
    xml = parseString('<status />')
    status = xml.getElementsByTagName('status')[0]
        
    icon = xml.createElement('icon')
    icon.appendChild(xml.createTextNode(self._trayicon.decode('utf8', 'replace')))
    status.appendChild(icon)

    message = xml.createElement('message')
    message.appendChild(xml.createTextNode(self._message.decode('utf8', 'replace')))
    status.appendChild(message)
        
    return xml.toxml()

# TODO Gestire TUTTI i caratteri utf8 !!!
ERROR = Status('nemesys_red.png', 'Impossibile contattare il demone che effettua le misure.')
PAUSE = Status('nemesys_white.png', 'NeMeSys non deve effettuare misure nell\'ora corrente.')
PLAY = Status('nemesys_green.png', 'NeMeSys sta effettuando una misura.')
FINISHED = Status('nemesys_cyan.png', 'NeMeSys ha terminato le misurazioni. Controllare lo stato complessivo della misura.')
READY = Status('nemesys_amber.png', 'NeMeSys pronto e in attesa di eseguire una misura.')
LOGO = Status('nemesys_logo.png', 'NeMeSys (Network Measurement System). Sistema collegato e funzionante.')

