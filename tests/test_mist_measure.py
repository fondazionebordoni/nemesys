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

import unittest
from datetime import datetime
from xml.dom.minidom import parseString

from common.client import Client
from common.isp import Isp
from common.profile import Profile
from common.proof import Proof
from common.server import Server
from mist.best_test import BestTest
from mist.measure import Measure
from mist.system_resource import RES_OS, RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_HOSTS, RES_TRAFFIC


class TestMistMeasure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestMistMeasure, cls).setUpClass()
        import nemesys.log_conf as log_conf
        log_conf.init_log()

    def testBasic(self):
        c = Client('fub0010000001',
                   Profile('1mb512kb', 1024, 512),
                   Isp('fub001'),
                   'geo')
        start_time = datetime.utcnow()
        m = Measure(c,
                    start_time,
                    Server(server_id='fubsrvnmx01', ip='127.0.0.1'),
                    ip='192.168.112.24',
                    os='Linux blabla',
                    mac='aa:aa:aa:aa:aa:aa',
                    version='9.9.9')
        p = Proof(test_type='download_http',
                  start_time=start_time,
                  duration=10000,
                  bytes_nem=1048576,
                  bytes_tot=1048579,
                  spurious=0.01)
        profiler_info = {RES_ETH: 1,
                         RES_TRAFFIC: 'MEDIUM',
                         RES_OS: 'os blah',
                         RES_CPU: '0.7',
                         RES_RAM: '67',
                         RES_HOSTS: '33',
                         RES_WIFI: 0}
        test = BestTest(n_tests_done=1,
                        proof=p,
                        profiler_info=profiler_info)
        m.savetest(test)
        m.savetime(start_time, start_time)
        xml_string = str(m)
        assert xml_string is not None
        assert xml_string != ''
        xml = parseString(xml_string)
        assert xml is not None

    def testTwoProofs(self):
        c = Client('fub0010000001',
                   Profile('1mb512kb', 1024, 512),
                   Isp('fub001'),
                   'geo')
        start_time = datetime.utcnow()
        m = Measure(c,
                    start_time,
                    Server(server_id='fubsrvnmx01', ip='127.0.0.1'),
                    ip='192.168.112.24',
                    os='Linux blabla',
                    mac='aa:aa:aa:aa:aa:aa',
                    version='9.9.9')
        p = Proof(test_type='download_http',
                  start_time=start_time,
                  duration=10000,
                  bytes_nem=1048576,
                  bytes_tot=1048579,
                  spurious=0.01)
        profiler_info = {RES_ETH: 1,
                         RES_TRAFFIC: 'MEDIUM',
                         RES_OS: 'os blah',
                         RES_CPU: '0.7',
                         RES_RAM: '67',
                         RES_HOSTS: '33',
                         RES_WIFI: 0}
        test = BestTest(n_tests_done=1,
                        proof=p,
                        profiler_info=profiler_info)
        m.savetest(test)
        p = Proof(test_type='ping',
                  start_time=start_time,
                  duration=22.3,
                  bytes_nem=0,
                  bytes_tot=0,
                  spurious=0)
        profiler_info = {RES_ETH: 1,
                         RES_TRAFFIC: 'SMALL',
                         RES_OS: 'os blahblah',
                         RES_CPU: '7',
                         RES_RAM: '25.5',
                         RES_HOSTS: '3',
                         RES_WIFI: 1}
        test = BestTest(n_tests_done=4,
                        proof=p,
                        profiler_info=profiler_info)
        m.savetest(test)
        m.savetime(start_time, start_time)
        xml_string = str(m)
        assert xml_string is not None
        assert xml_string != ''
        xml = parseString(xml_string)
        assert xml is not None


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testBasic']
    unittest.main()
