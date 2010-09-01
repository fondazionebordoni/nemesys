# paths.py
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

import os
import sys

DIR_SEP=os.sep

if hasattr(sys,"frozen"):
    APP_PATH=os.path.dirname(sys.executable)
else:
    APP_PATH=os.path.abspath(os.path.dirname(__file__))#os.path.dirname(__file__) dovrebbe darmi il percorso in cui sta eseguendo l'applicazione

if(os.name!='nt'):
    HOME_DIR=os.path.expanduser('~')
else:
    HOME_DIR=os.path.expanduser("~").decode(sys.getfilesystemencoding())

ICON_PATH=APP_PATH+DIR_SEP+'icon'#percorso in cui trovo le icone
XML_DIR_NAME='.config'+DIR_SEP+'nemesys'
XML_DIR=HOME_DIR+DIR_SEP+XML_DIR_NAME #percorso in cui trovo il file measure.xml
