# test_chooser.py
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

from common.chooser import Chooser
from common.host import Server

from common.nem_exceptions import NemesysException






class TestChooser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        import nemesys.log_conf as log_conf
        log_conf.init_log()

    def test_get_servers(self):

        chooser = Chooser('http://127.0.0.1:5000', 'test', '1.0')
        servers = chooser.get_servers()

        self.assertEqual(2, len(servers))

        for server in servers:
            self.assertIsInstance(server, Server)
        









if __name__ == "__main__":
    unittest.main()
