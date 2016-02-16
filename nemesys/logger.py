# logger.py 
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

from os import path
from os import mkdir
import logging.config
import paths

config_file_name = paths.CONF_LOG
logfile = paths.FILE_LOG

default = '''
[loggers]
keys=root

[handlers]
keys=console,file

[formatters]
keys=formatter

[logger_root]
level=INFO
handlers=console,file

[handler_console]
class=StreamHandler
level=INFO
formatter=formatter
args=(sys.stdout,)

[handler_file]
class=FileHandler
level=INFO
formatter=formatter
args=(''' + repr(logfile) + ''',)

[formatter_formatter] 
format=%(asctime)s Nemesys %(filename)s.%(funcName)s():%(lineno)d [%(levelname)s] %(message)s
datefmt=%b %d %H:%M:%S
'''

if not path.exists(paths.LOG_DIR):
    mkdir(paths.LOG_DIR)

# Se il file configurazione di log non esiste, creane uno con le impostazioni base
if (not path.exists(config_file_name)):

    with open(config_file_name, 'w') as config_file:
        s = str(default)
        config_file.write(s)

logging.config.fileConfig(config_file_name)

# create logger
class Logger(logging.getLoggerClass()):

    def __init__(self):
        pass
