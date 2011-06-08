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

import ntplib
import time
SERVERNTP = "tempo.cstv.to.cnr.it"

def timestampNtp():
  x = ntplib.NTPClient()
  try:
    TimeRX = x.request(SERVERNTP, version=3)
    timestamp = TimeRX.tx_time
  except Exception as e:
    timestamp = time.time()
  return timestamp

if __name__ == '__main__':
  n = timestampNtp()
  print n
