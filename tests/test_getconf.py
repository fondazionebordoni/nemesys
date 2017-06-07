# test_measure.py
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import os
import unittest

from nemesys.getconf import getconf


class TestGetConf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestGetConf, cls).setUpClass()

    def setUp(self):
        import nemesys.log_conf as log_conf
        log_conf.init_log()
        self.temp_file = os.path.join('/tmp', 'client.conf')
        self.service = 'https://finaluser.agcom244.fub.it/Config'
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def tearDown(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def testBasic(self):
        # TODO split into different tests
        try:
            getconf('fub00000000001', '.', self.temp_file, self.service)
            assert False
        except Exception:
            assert True

        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

        try:
            getconf('', '.', self.temp_file, self.service)
            assert False
        except Exception:
            assert True

        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

        try:
            getconf('test@example.com|notaverystrongpassword',
                    '.', self.temp_file, self.service)
            assert False
        except Exception:
            assert True

        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testBasic']
    unittest.main()
