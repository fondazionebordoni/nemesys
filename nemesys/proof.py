# proof.py
# -*- coding: utf-8 -*-

# Copyright (c) 2010-2016 Fondazione Ugo Bordoni.
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

from datetime import datetime

class Proof(object):

    def __init__(self, test_type, start_time, duration, bytes_nem=0, bytes_tot=0, spurious=0, errorcode = 0):
        self._type = test_type
        self._start = start_time
        self._duration = duration
        self._bytes_nem = bytes_nem
        self._bytes_tot = bytes_tot
        self._spurious = spurious
        self._errorcode = errorcode

    @property
    def type(self):
        return self._type

    @property
    def start(self):
        return self._start

    @property
    def duration(self):
        '''
        Values must be saved in milliseconds.
        '''
        return self._duration

    @property
    def bytes_nem(self):
        return self._bytes_nem

    @property
    def bytes_tot(self):
        return self._bytes_tot

    @property
    def spurious(self):
        return self._spurious

    @property
    def errorcode(self):
        return self._errorcode

    def seterrorcode(self, errorcode):
        if errorcode > 99999 or errorcode < 0:
            # Faccio rimanere nelle ultime 4 cifre l'errore del test
            errorcode = (errorcode - 90000) % 99999
        self._errorcode = errorcode

    def __str__(self):
        return 'type: %s; start: %s; value: %1.3f; bytes: %d; counter_stats: {%s}; errorcode: %d' % (self.type, self.start.isoformat(), self.value, self.bytes, self.counter_stats, self.errorcode)

if __name__ == '__main__':
    t = Proof('download', datetime.now(), 20, 100000, None, 101)
    print t
    t = Proof('ping', datetime.now(), 10000, 999)
    print t
