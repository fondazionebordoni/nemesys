# test_profiler.py
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

from common import profiler
import nemesys.sysmonitor as sysmonitor


class TestProfiler(unittest.TestCase):
    """
    Note: some of these tests are platform and/or
    configuration dependent!
    """

    @classmethod
    def setUpClass(cls):
        super(TestProfiler, cls).setUpClass()
        import nemesys.log_conf as log_conf
        log_conf.init_log()

    def setUp(self):
        unittest.TestCase.setUp(self)

    def test_cpu_load(self):
        cpu_load = profiler.cpu_load()
        self.assertGreaterEqual(cpu_load, 0)
        self.assertLessEqual(cpu_load, 100)

    def test_mem_total(self):
        total_mem = profiler.total_memory()
        self.assertGreater(total_mem, 0)
        self.assertGreater(total_mem, sysmonitor.TH_AV_MEM)

    def test_mem_usage(self):
        usage = profiler.percentage_ram_usage()
        self.assertGreater(usage, 0)
        self.assertLess(usage, sysmonitor.TH_MEM_LOAD)

    def test_wireless(self):
        is_active = profiler.is_wireless_active()
        self.assertFalse(is_active)

    def test_wireless_name(self):
        if_name = 'wlp000'
        is_wireless = profiler.is_wireless(if_name)
        self.assertTrue(is_wireless)


if __name__ == '__main__':
    unittest.main()
