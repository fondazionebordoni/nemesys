# fakefile.py
# -*- coding: utf-8 -*-

# Copyright (c) 2015 Fondazione Ugo Bordoni.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import random


class Fakefile(object):

    def __init__(self, file_size):
        self._initial_bytes = int(file_size)
        self._bytes = self._initial_bytes
        self.data = None
        self.data_len = None

    def read(self, bufsize=-1):
        if bufsize <= 0:
            bufsize = 8192
        if (self._bytes < bufsize):
            bufsize = self._bytes
        if bufsize <= 0:
            bufsize = 8192
        if (self._bytes < bufsize):
            bufsize = self._bytes
        if self._bytes <= 0:
            return None

        if not self.data or self.data_len != bufsize:
            # data random between 0 and FFFFF...FF,
            # e.g. 0-FF  in case of one byte buffer
            data = '%x' % random.randint(0, 2 ** (8 * bufsize) - 1)
            # if hex number is e.g. 6, pad with one 0 to 06
            data = data.rjust(bufsize * 2, '0')
            # transform into a string
            self.data = data.decode('hex')
            self.data_len = len(self.data)
        self._bytes -= self.data_len
        return self.data

    def get_bytes_read(self):
        return int(self._initial_bytes - self._bytes)
