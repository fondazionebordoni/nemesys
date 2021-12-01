# test_fakefile.py
# -*- coding: utf-8 -*-

# Copyright (c) 2016 Fondazione Ugo Bordoni.
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

import unittest

import time

from common.fakefile import Fakefile


class TestFakefile(unittest.TestCase):

    def test_one_byte(self):
        ff = Fakefile(1024)
        data = ff.read(1)
        self.assertEqual(1, len(data))

    def test_mbyte(self):
        ff = Fakefile(1024)
        data = ff.read(1024)
        self.assertEqual(1024, len(data))

    def test_mbyte_equal(self):
        ff = Fakefile(2048)
        data1 = ff.read(1024)
        data2 = ff.read(1024)
        self.assertEqual(data1, data2)

    def test_tcp_buf(self):
        num_iterations = 100000
        start_time = time.time()
        ff = Fakefile(8 * 1024 * num_iterations)
        for _ in range(0, num_iterations):
            data = ff.read(8 * 1024)
            self.assertEqual(8 * 1024, len(data))
        end_time = time.time()
        print((end_time - start_time)/num_iterations)


def main():
    unittest.main()


if __name__ == '__main__':
    main()
