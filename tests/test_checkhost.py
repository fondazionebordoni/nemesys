# test_checkhost.py
# -*- coding: utf-8 -*-

# Copyright (c) 2017 Fondazione Ugo Bordoni.
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
import common.checkhost

HOSTS_OLD_TECHNICOLOR = {
    '192.168.1.253': 'c6:ea:1d:4d:e6:70', '192.168.1.254]': 'c4:ea:1d:4d:e6:70'}
HOSTS_NEW_TECHNICOLOR = {
    '192.168.1.254': 'e0:b9:e5:59:d6:22', '192.168.1.148': 'e2:b9:e5:59:d6:2b'}
HOSTS_NEWER_TECHNICOLOR = {
    '192.168.1.24': 'a6:91:b1:17:7c:73', '192.168.1.1': 'a4:91:b1:17:7c:6a'}
HOSTS_EVEN_NEWER_TECHNICOLOR = {
    '192.168.1.24': '22:b0:01:9d:70:1', '192.168.1.1': '20:b0:01:9d:70:08'}
HOSTS_NOT_TECHNICOLOR = {
    '192.168.1.254': 'f0:b9:e5:59:d6:22', '192.168.1.148': 'f2:b9:e5:59:d6:2b'}


class TestCheckhost(unittest.TestCase):
    def test_old_technicolor(self):
        res = common.checkhost.filter_out_technicolor(HOSTS_OLD_TECHNICOLOR)
        self.assertEqual(1, res)

    def test_new_technicolor(self):
        res = common.checkhost.filter_out_technicolor(HOSTS_NEW_TECHNICOLOR)
        self.assertEqual(1, res)

    def test_newer_technicolor(self):
        res = common.checkhost.filter_out_technicolor(HOSTS_NEWER_TECHNICOLOR)
        self.assertEqual(1, res)

    def test_even_newer_technicolor(self):
        res = common.checkhost.filter_out_technicolor(HOSTS_EVEN_NEWER_TECHNICOLOR)
        self.assertEqual(1, res)

    def test_not_technicolor(self):
        res = common.checkhost.filter_out_technicolor(HOSTS_NOT_TECHNICOLOR)
        self.assertEqual(2, res)


def main():
    unittest.main()


if __name__ == '__main__':
    main()
