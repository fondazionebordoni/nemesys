# errorcode_test.py
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

import errorcode
from measurementexception import MeasurementException
import unittest

'''
Make sure that errorcode works!
'''

class ErrorcodeTests(unittest.TestCase):
    
    def test_unknown(self):
        e = Exception('pippo')
        code = errorcode.from_exception(e)
        self.assertEqual(99999, code)
        
    def test_errno110(self):
        e = Exception('110')
        code = errorcode.from_exception(e)
        self.assertEqual(99984, code)

    def test_measurementexception_unknown(self):
        e = MeasurementException('110')
        code = errorcode.from_exception(e)
        self.assertEqual(errorcode.UNKNOWN, code)

    def test_measurementexception(self):
        e = MeasurementException('110', 12345)
        code = errorcode.from_exception(e)
        self.assertEqual(12345, code)

    def test_measurementexception_real(self):
        e = MeasurementException("Test non risucito - tempo ritornato dal server non corrisponde al tempo richiesto.", errorcode.SERVER_ERROR)
        code = errorcode.from_exception(e)
        self.assertEqual(errorcode.SERVER_ERROR, code)