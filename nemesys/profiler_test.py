# sysmonitor.py
# -*- coding: utf8 -*-

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
import profiler
import sysmonitor
from nemesys.profiler import ProfilerDarwin

'''
Test new sysmonitor
'''

class ProfilerTests(unittest.TestCase):
    
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.profiler = profiler.get_profiler()

    def test_cpu_load(self):
        cpu_load = self.profiler.cpuLoad()
        self.assertGreater(cpu_load, 0)
        self.assertLess(cpu_load, 100)
        
    def test_mem_total(self):
        total_mem = self.profiler.total_memory()
        self.assertGreater(total_mem, 0)
        self.assertGreater(total_mem, sysmonitor.th_avMem)
        
    def test_mem_usage(self):
        usage = self.profiler.percentage_ram_usage()
        self.assertGreater(usage, 0)
        self.assertLess(usage, sysmonitor.th_memLoad)
        
    def test_wireless(self):
        is_active = self.profiler.is_wireless_active()
        self.assertFalse(is_active)
        
    def test_get_ip(self):
        ipaddr = self.profiler.getipaddr()
        self.assertIsNotNone(ipaddr)

    def test_get_mac(self):
        mac = self.profiler.get_mac_address(None)
        self.assertIsNotNone(mac)


    '''Platform dependent tests'''
    def test_wireless_macos(self):
        import os
        test_file_name = os.path.dirname(os.path.realpath(__file__)) + os.sep + "test" + os.sep + "system_profiler_output.xml"
        mac_profiler = ProfilerDarwin()
        with open(test_file_name) as xml_file:
            is_wireless_active = mac_profiler.is_wireless_active_from_xml(xml_file)
        self.assertFalse(is_wireless_active)


if __name__ == '__main__':
    unittest.main()