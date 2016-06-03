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

import logging.config
import os

import paths


configfile = paths.CONF_LOG
logfile = paths.LOG_FILE

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

default_no_stdout = '''
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
level=CRITICAL
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

def init_log(level=logging.INFO, use_name='Nemesys'):
    paths.check_paths()
    if not os.path.isfile(configfile):
        with open(configfile, 'w') as f:
            s = str(default_no_stdout)
            f.write(s) 

    logging.config.fileConfig(configfile, disable_existing_loggers=False)
