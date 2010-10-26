# paths.py
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

import sys

from os import mkdir
from os import name
from os import path
from os import sep

DIR_SEP = sep

if hasattr(sys, 'frozen'):
  # Dovrebbe darmi il percorso in cui sta eseguendo l'applicazione
  _APP_PATH = path.dirname(sys.executable) + DIR_SEP + '..'
else:
  _APP_PATH = path.abspath(path.dirname(__file__)) + DIR_SEP + '..'

if name != 'nt':
  HOME_DIR = path.expanduser('~')
else:
  HOME_DIR = path.expanduser('~').decode(sys.getfilesystemencoding())

# Resources path
ICONS = _APP_PATH + DIR_SEP + 'icons'
OUTBOX = _APP_PATH + DIR_SEP + 'outbox'
SENT = _APP_PATH + DIR_SEP + 'sent'

# Configuration dirs and files
_CONF_DIR = _APP_PATH + DIR_SEP + 'config'
LOG_DIR = _APP_PATH + DIR_SEP + 'logs'
FILE_LOG = LOG_DIR + DIR_SEP + 'nemesys.log'
CONF_LOG = _CONF_DIR + DIR_SEP + 'log.conf'
CONF_MAIN = _CONF_DIR + DIR_SEP + 'client.conf'
CONF_ERRORS = _CONF_DIR + DIR_SEP + 'errorcodes.conf'
THRESHOLD = _CONF_DIR + DIR_SEP + 'threshold.xml'
RESULTS = _CONF_DIR + DIR_SEP + 'result.xml'
MEASURE_STATUS = _CONF_DIR + DIR_SEP + 'progress.xml'

from logger import logging
def check_paths():
  logger = logging.getLogger()

  if not path.exists(_CONF_DIR):
    mkdir(_CONF_DIR)
    logger.debug('Creata la cartella "%s".' % _CONF_DIR)

  if not path.exists(OUTBOX):
    mkdir(OUTBOX)
    logger.debug('Creata la cartella "%s".' % OUTBOX)

  if not path.exists(SENT):
    mkdir(SENT)
    logger.debug('Creata la cartella "%s".' % SENT)

