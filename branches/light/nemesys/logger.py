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
from datetime import datetime
from timeNtp import timestampNtp
import logging.config
import paths
import re

configfile = paths.CONF_LOG
#logfile = paths.FILE_LOG

def getdate(mode='sec'):
  this_date = datetime.fromtimestamp(timestampNtp())
  if mode == 'day':
    format_date = str(this_date.strftime('%Y%m%d'))
  elif mode == 'sec':
    format_date = str(this_date.strftime('%Y%m%d_%H%M%S'))
  return format_date

DAY_LOG_DIR = path.join(paths.LOG_DIR,getdate('day'))
logfile = path.join(DAY_LOG_DIR, getdate('sec')+'.log')

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
  
if not path.exists(DAY_LOG_DIR):
  mkdir(DAY_LOG_DIR)

# Se il file configurazione di log non esiste, creane uno con le impostazioni base
if (not path.exists(configfile)):

  with open(configfile, 'w') as file:
    s = str(default)
    file.write(s)

else:

  ind = 0
  data = None
  
  with open(configfile, 'r') as file:
    data = file.readlines()
    for line in data:
      ind += 1
      if (re.search('logs',line)):
        data[ind-1]="args=("+repr(logfile)+",)\n"
        
  with open(configfile, 'w') as file:
    file.writelines(data)
        

logging.config.fileConfig(configfile)
    
# create logger
class Logger(logging.getLoggerClass()):

  def __init__(self):
    pass
