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

from datetime import datetime
import unittest

from common.client import Client
from common.isp import Isp
from nemesys.measure import Measure
from common.profile import Profile
from common.proof import Proof
from common.server import Server


class TestMeasure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestMeasure, cls).setUpClass()
        import nemesys.log_conf as log_conf
        log_conf.init_log()

    def testBasic(self):
        c = Client('fub0010000001',
                   Profile('1mb512kb', 1024, 512),
                   Isp('fub001'),
                   'geo')
        m = Measure(1,
                    Server(uuid='fubsrvnmx01', ip='127.0.0.1', name='Test server'),
                    c)
        start_time = datetime.utcnow()
        p = Proof(test_type='download_http',
                  start_time=start_time,
                  duration=10000,
                  bytes_nem=1048576,
                  bytes_tot=1048579,
                  spurious=0.01)
        m.savetest(p)
        xml_string = str(m)
        self.assertIsNotNone(xml_string)

    def testPing(self):
        c = Client('fub0010000001',
                   Profile('1mb512kb', 1024, 512),
                   Isp('fub001'), 'geo')
        m = Measure(1,
                    Server(uuid='fubsrvnmx01', ip='127.0.0.1', name='Test server'),
                    c)
        start_time = datetime.utcnow()
        p = Proof(test_type='download_http',
                  start_time=start_time,
                  duration=10000)
        m.savetest(p)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testBasic']
    unittest.main()
