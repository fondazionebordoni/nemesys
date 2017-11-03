# ntptime.py
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
import threading

import ntplib
import time

NTP_SERVERS = ['time.ien.it',
               '0.pool.ntp.org',
               '1.pool.ntp.org',
               '2.pool.ntp.org',
               '3.pool.ntp.org']


_time_diff = 0
_time_received = False
_last_try = 0
_ntp_lock = threading.Lock()


def _ntp_time(server):
    ntp_time = ntplib.NTPClient().request(server, version=3, timeout=1)
    return ntp_time.tx_time


def _get_time_diff():
    global _time_diff, _time_received
    for server in NTP_SERVERS:
        try:
            _time_diff = time.time() - _ntp_time(server)
            _time_received = True
            break
        except Exception:
            pass


def timestamp():
    global _last_try, _ntp_lock
    if not _time_received:
        with _ntp_lock:
            if time.time() - _last_try > 3600:
                _get_time_diff()
                _last_try = time.time()
    return time.time() - _time_diff


if __name__ == '__main__':
    print timestamp()
