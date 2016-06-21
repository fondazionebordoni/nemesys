# nem_exceptions_test.py
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

import nem_exceptions
import unittest

'''
Make sure that errorcode works!
'''

class ErrorcodeTests(unittest.TestCase):
    
    def test_unknown(self):
        e = Exception('pippo')
        code = nem_exceptions.errorcode_from_exception(e)
        self.assertEqual(99999, code)
        
    def test_errno110(self):
        e = Exception('110')
        code = nem_exceptions.errorcode_from_exception(e)
        self.assertEqual(99984, code)

    def test_measurementexception_unknown(self):
        e = nem_exceptions.MeasurementException('110')
        code = nem_exceptions.errorcode_from_exception(e)
        self.assertEqual(nem_exceptions.UNKNOWN, code)

    def test_measurementexception(self):
        e = nem_exceptions.MeasurementException('110', 12345)
        code = nem_exceptions.errorcode_from_exception(e)
        self.assertEqual(12345, code)

    def test_measurementexception_real(self):
        e = nem_exceptions.MeasurementException("Test non risucito - tempo ritornato dal server non corrisponde al tempo richiesto.", nem_exceptions.SERVER_ERROR)
        code = nem_exceptions.errorcode_from_exception(e)
        self.assertEqual(nem_exceptions.SERVER_ERROR, code)
        
    def test_sysmonitorexception(self):
        e = nem_exceptions.SysmonitorException("Test", 5008)
        code = nem_exceptions.errorcode_from_exception(e)
        self.assertEqual(5008, code)
