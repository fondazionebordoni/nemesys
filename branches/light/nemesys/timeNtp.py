# timeNtp.py
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

from datetime import datetime
from logger import logging
from threading import Thread
import Queue
import ntplib
import time

SERVERNTP = ["0.pool.ntp.org","1.pool.ntp.org","2.pool.ntp.org","3.pool.ntp.org","ntp.fub.it","time.windows.com"]

logger = logging.getLogger()

def _request(server, result):
  x = ntplib.NTPClient()
  try:
    TimeRX = x.request(server, version=3)
    result.put(TimeRX.tx_time)
  except Exception as e:
    result.put(str(e))

def timestampNtp():
  timestamp = None
  type = 'Internet'
  result = Queue.Queue()
  for server in SERVERNTP:
    request = Thread(target=_request, args=(server, result))
    request.start()
  timestamp = result.get()
  if not isinstance(timestamp, float):
    timestamp = time.time()
    type = 'Local'
  #logger.debug("%s Time: %s" % (type, datetime.fromtimestamp(timestamp).strftime('%Y/%m/%d %H:%M:%S')))
  return timestamp

if __name__ == '__main__':
  request_num = 150
  for x in range(request_num):
   logger.debug("Richiesta %s di %s: %s" % (x+1,request_num,timestampNtp()))
