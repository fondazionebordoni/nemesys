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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import ntplib
import time

from common import ping

SERVER_NTP_IT = "tempo.cstv.to.cnr.it"
SERVERNTP = ["ntp.spadhausen.com", "ntp.fub.it", "time.windows.com", "0.pool.ntp.org", "1.pool.ntp.org",
             "2.pool.ntp.org", "3.pool.ntp.org"]


def _ping(server):
    delay = ping.do_one("%s" % server, 1) * 1000
    return delay


def _timestamp(server):
    TimeRX = ntplib.NTPClient().request(server, version=3)
    return TimeRX.tx_time


def timestampNtp():
    x = ntplib.NTPClient()
    try:
        TimeRX = x.request(SERVER_NTP_IT, version=3)
        timestamp = TimeRX.tx_time
    except Exception:
        timestamp = time.time()
    return timestamp


def timestampNtpMist():
    for server in SERVERNTP:
        try:
            delay = _ping(server)
            if delay is not None:
                timestamp = _timestamp(server)
                if timestamp is not None:
                    return timestamp
        except Exception:
            pass
    return time.time()


if __name__ == '__main__':
    n = timestampNtp()
    print n
