# test_netstat.py
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

import re
import unittest

import common.iptools as iptools

from common.nem_exceptions import NemesysException


class TestNetstat(unittest.TestCase):
    '''
    Note: some of these tests are platform and/or
    configuration dependent!
    '''

    @classmethod
    def setUpClass(cls):
        super(TestNetstat, cls).setUpClass()
        import nemesys.log_conf as log_conf
        log_conf.init_log()

    def testGetDev(self):
        dev = iptools.get_dev()
        self.assertNotEqual(None, dev)

    def testGetDevFalseIp(self):
        try:
            iptools.get_dev(ip='1.2.3')
            self.assertNotEqual(False, True)
        except NemesysException as e:
            self.assertEqual(("Impossibile ottenere il dettaglio "
                              "dell'interfaccia di rete"), str(e))

    def testGetDevIp(self):
        dev = iptools.get_dev()
        ip = iptools.get_if_ipaddress(dev)
        self.assertNotEqual(None, ip)

    def testGetInexistingDevIp(self):
        dev = 'pippo124'
        try:
            iptools.get_if_ipaddress(dev)
            self.assertNotEqual(False, True)
        except NemesysException as e:
            self.assertEqual(True,
                             "Impossibile ottenere l'indirizzo" in str(e))

    def testGetNetmask(self):
        ip = iptools.getipaddr()
        mask = iptools.get_network_mask(ip)
        self.assertEqual(24, mask)

    def testGetInexistingNetmask(self):
        mask = iptools.get_network_mask('123')
        self.assertEqual(24, mask)

    def testGetMac(self):
        dev = iptools.get_dev()
        mac = iptools.get_mac_address(dev)
        self.assertNotEqual(None, mac)
        re_mac = ("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
        self.assertNotEqual(None, re.match(re_mac, mac, re.I))

    def testGetInexistingMac(self):
        mask = iptools.get_network_mask('123')
        self.assertEqual(24, mask)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testGetDev']
    unittest.main()
