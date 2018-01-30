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

from common import backend_response


class TestBackendResponse(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestBackendResponse, cls).setUpClass()
        import nemesys.log_conf as log_conf
        log_conf.init_log()

    def test_happycase(self):
        xml_string = '''<?xml version="1.0" encoding="UTF-8"?>
        <response><message>Misura ricevuta ma non salvata sul database</message>
        <code>301</code></response>'''
        code, message = backend_response.parse(xml_string)
        assert code == 301
        assert message == 'Misura ricevuta ma non salvata sul database'

    def test_missing_code(self):
        xml_string = '''<?xml version="1.0" encoding="UTF-8"?>
        <response><message>Misura ricevuta ma non salvata sul database</message>
        </response>'''
        code, message = backend_response.parse(xml_string)
        assert code == 999
        assert message == 'Misura ricevuta ma non salvata sul database'

    def test_missing_message(self):
        xml_string = '''<?xml version="1.0" encoding="UTF-8"?>
        <response>
        <code>301</code></response>'''
        code, message = backend_response.parse(xml_string)
        assert code == 301
        assert message == ''

    def test_not_response(self):
        xml_string = '''<?xml version="1.0" encoding="UTF-8"?>
        <message>Misura ricevuta ma non salvata sul database</message>
        <code>301</code>'''
        code, message = backend_response.parse(xml_string)
        assert code == 999
        assert message == ''

    def test_broken_xml(self):
        xml_string = '''<?xml version="1.0" encoding="UTF-8"?>
        <response><message>Misura ricevuta ma non salvata sul database</message>
        <code>301</code>'''
        code, message = backend_response.parse(xml_string)
        assert code == 999
        assert message == ''

    def test_none(self):
        xml_string = None
        code, message = backend_response.parse(xml_string)
        assert code == 999
        assert message == ''


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testBasic']
    unittest.main()
