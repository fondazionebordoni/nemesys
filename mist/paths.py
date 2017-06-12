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

import os
import sys
from datetime import datetime
from os import mkdir, path, sep

from common.timeNtp import timestampNtp
from common import utils

DATE = datetime.fromtimestamp(timestampNtp())


def formatdate(mode='sec'):
    if mode == 'day':
        format_date = str(DATE.strftime('%Y%m%d'))
    elif mode == 'sec':
        format_date = str(DATE.strftime('%Y%m%d_%H%M%S'))
    return format_date


DAY = formatdate('day')
SEC = formatdate('sec')

if hasattr(sys, 'frozen'):
    # Dovrebbe darmi il percorso in cui sta eseguendo l'applicazione
    _APP_PATH = path.dirname(sys.executable) + sep + '..'
else:
    _APP_PATH = path.abspath(path.dirname(__file__)) + sep + '..'

_APP_PATH = path.normpath(_APP_PATH)

# Resources path
if utils.is_darwin():
    ICONS = path.join(_APP_PATH, 'Resources', 'icons')
else:
    ICONS = path.join(_APP_PATH, 'mist', 'resources', 'icons')

# SENT
SENT_DIR = path.join(_APP_PATH, 'sent')
SENT_DAY_DIR = path.join(SENT_DIR, DAY)

# OUTBOX
OUTBOX_DIR = path.join(_APP_PATH, 'outbox')
OUTBOX_DAY_DIR = path.join(OUTBOX_DIR, DAY)

# LOG
LOG_DIR = path.join(_APP_PATH, 'logs')
LOG_FILE = path.join(LOG_DIR, 'misurainternet-' + DAY + '.log')

# Configuration dirs and files
_CONF_DIR = path.join(_APP_PATH, 'config')
CONF_LOG = path.join(_CONF_DIR, 'log.conf')
CONF_MAIN = path.join(_CONF_DIR, 'client.conf')

# THRESHOLD = path.join(_CONF_DIR, 'threshold.xml')
# RESULTS = path.join(_CONF_DIR, 'result.xml')
# MEASURE_STATUS = path.join(_CONF_DIR, 'progress.xml')
# MEASURE_PROSPECT = path.join(OUTBOX_DIR, 'prospect.xml')


def check_paths():
    dirs = [LOG_DIR, OUTBOX_DIR, OUTBOX_DAY_DIR,
            SENT_DIR, SENT_DAY_DIR, _CONF_DIR]
    for d in dirs:
        if not path.exists(d):
            mkdir(d)


def remove_temp_dirs():
    remove_empty_dir(OUTBOX_DIR)
    remove_empty_dir(SENT_DIR)


def remove_empty_dir(topdir):
    subdirs = os.walk(topdir, topdown=False)
    for root, dirs, _ in subdirs:
        for filedir in range(len(dirs)):
            dirs[filedir] = os.path.join(root, dirs[filedir])
            dirs.append(root)
        for filedir in dirs:
            if os.path.exists(filedir):
                if not os.listdir(filedir):    # to check wither the dir is empty
                    os.removedirs(filedir)
