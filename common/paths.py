# paths.py
# -*- coding: utf-8 -*-

# Copyright (c) 2018 Fondazione Ugo Bordoni.
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

import logging
import sys
from os import mkdir, path

from common import utils

logger = logging.getLogger(__name__)

if hasattr(sys, 'frozen'):
    # Dovrebbe darmi il percorso in cui sta eseguendo l'applicazione
    _APP_DIR = path.dirname(sys.executable)
else:
    _APP_DIR = path.abspath(path.dirname(__file__))

_APP_PATH = path.normpath(path.join(_APP_DIR, '..'))

# Resources path
OUTBOX_DIR = path.join(_APP_PATH, 'outbox')
SENT_DIR = path.join(_APP_PATH, 'sent')

# Configuration dirs and files
_CONF_DIR = path.join(_APP_PATH, 'config')
LOG_DIR = path.join(_APP_PATH, 'logs')
NEMESYS_LOG_FILE = path.join(LOG_DIR, 'nemesys.log')
MIST_LOG_FILE = path.join(LOG_DIR, 'misurainternet-speedtest.log')

CONF_LOG = path.join(_CONF_DIR, 'log.conf')
CONF_MAIN = path.join(_CONF_DIR, 'client.conf')

# Resources path
if utils.is_darwin():
    ICONS = path.join(_APP_PATH, 'Resources', 'icons')
else:
    ICONS = path.join(_APP_PATH, 'mist', 'resources', 'icons')

def create_nemesys_dirs():
    create_dirs(dirs=[LOG_DIR, OUTBOX_DIR, SENT_DIR, _CONF_DIR])


def create_mist_dirs():
    create_dirs(dirs=[LOG_DIR, OUTBOX_DIR, _CONF_DIR])


def create_dirs(dirs=[]):
    for d in dirs:
        if not path.exists(d):
            mkdir(d)
            logger.debug('Creata la cartella "%s".', d)
