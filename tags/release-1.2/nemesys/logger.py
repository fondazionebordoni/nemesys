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
import logging.config
import paths
import os

configfile = paths.CONF_LOG

default = '''
[loggers]
keys=root

[handlers]
keys=console

[formatters]
keys=formatter

[logger_root]
level=DEBUG
handlers=console,ntevent

[handler_console]
class=StreamHandler
level=DEBUG
formatter=formatter
args=(sys.stdout,)

[formatter_formatter] 
format=%(asctime)s Nemesys %(filename)s.%(funcName)s():%(lineno)d [%(levelname)s] %(message)s
datefmt=%b %d %H:%M:%S
'''

default_win = '''
[loggers]
keys=root

[handlers]
keys=console,ntevent

[formatters]
keys=formatter

[logger_root]
level=DEBUG
handlers=console,ntevent

[handler_console]
class=StreamHandler
level=DEBUG
formatter=formatter
args=(sys.stdout,)

[handler_ntevent]
class=handlers.NTEventLogHandler
level=WARNING
formatter=formatter
args=('Nemesys', '', 'Application')

[formatter_formatter] 
format=%(asctime)s Nemesys %(filename)s.%(funcName)s():%(lineno)d [%(levelname)s] %(message)s
datefmt=%b %d %H:%M:%S
'''

default_posix = '''
[loggers]
keys=root

[handlers]
keys=console,syslog

[formatters]
keys=formatter

[logger_root]
level=DEBUG
handlers=console,syslog

[handler_console]
class=StreamHandler
level=DEBUG
formatter=formatter
args=(sys.stdout,)

[handler_syslog]
class=handlers.SysLogHandler
level=WARNING
formatter=formatter
args=('/dev/log', handlers.SysLogHandler.LOG_USER)

[formatter_formatter] 
format=%(asctime)s Nemesys %(filename)s.%(funcName)s():%(lineno)d [%(levelname)s] %(message)s
datefmt=%b %d %H:%M:%S
'''

# Se il file configurazione di log non esiste, creane uno con le impostazioni base
if (not path.exists(configfile)):

  if os.name == 'nt':
    default = default_win
  elif os.name == 'posix':
    default = default_posix

  with open(configfile, 'w') as file:
    s = str(default)
    file.write(s)

logging.config.fileConfig(configfile)

# create logger
class Logger(logging.getLoggerClass()):

  def __init__(self):
    pass
