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

from os import mkdir, path, sep
from usbkey import get_path
import sys

if hasattr(sys, 'frozen'):
  # Dovrebbe darmi il percorso in cui sta eseguendo l'applicazione
  _APP_PATH = path.dirname(sys.executable) + sep + '..'
else:
  _APP_PATH = path.abspath(path.dirname(__file__)) + sep + '..'
  
_APP_PATH = path.normpath(_APP_PATH)

if (get_path() != []):
  _USB_PATH = path.normpath(get_path() + sep + '..')
else:
  _USB_PATH = _APP_PATH

# Resources path
ICONS = path.join(_APP_PATH, 'icons')
OUTBOX = path.join(_APP_PATH, 'outbox')
SENT = path.join(_APP_PATH, 'sent')

# Configuration dirs and files
_CONF_DIR = path.join(_APP_PATH, 'config')
LOG_DIR = path.join(_USB_PATH, 'logs')
FILE_LOG = path.join(LOG_DIR, 'nemesys.log')
CONF_LOG = path.join(_CONF_DIR, 'log.conf')
CONF_MAIN = path.join(_CONF_DIR, 'client.conf')
CONF_ERRORS = path.join(_CONF_DIR, 'errorcodes.conf')
THRESHOLD = path.join(_CONF_DIR, 'threshold.xml')
RESULTS = path.join(_CONF_DIR, 'result.xml')
MEASURE_STATUS = path.join(_CONF_DIR, 'progress.xml')
MEASURE_PROSPECT = path.join(OUTBOX, 'prospect.xml')

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

