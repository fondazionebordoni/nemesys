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

class Status:

    def __init__(self, icon, message):
        self._icon = icon
        self._message = message

    @property
    def icon(self):
        return self._icon

    @property
    def message(self):
        return self._message

ERROR = Status('icon_rossa.png', 'Impossibile contattare il demone che effettua le misure.')
PAUSE = Status('icon_bianca.png', 'Il server è in pausa. Non verranno effettuate misure nella prossima ora.')
PLAY = Status('icon_verde.png','NeMeSys sta effettuando una misura...')
FINISHED = Status('icon_blu.png','NeMeSys ha terminato le misurazioni')
READY = Status('icon_arancio.png','NeMeSys effettuerà una misura nella prossima ora')
