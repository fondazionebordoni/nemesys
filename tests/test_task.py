# test_task.py
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

import common.task as task

from common.nem_exceptions import TaskException


class TestTask(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestTask, cls).setUpClass()
        import nemesys.log_conf as log_conf
        log_conf.init_log()

    def test_old_task(self):
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
 <calendar>
    <task>
     <id>1</id>
     <nftpup mult="10">20</nftpup>
     <nftpdown>20</nftpdown>
     <nping icmp="1" delay="10">10</nping>
     <start now="1">2010-01-01 00:01:00</start>
     <srvid>fubsrvrmnmx03</srvid>
     <srvip>193.104.137.133</srvip>
     <srvname>NAMEX</srvname>
     <ftpuppath>/upload/1.rnd</ftpuppath>
     <ftpdownpath>/download/8000.rnd</ftpdownpath>
    </task>
 </calendar>
    '''
        res = task.xml2task(xml)
        self.assertNotEqual(None, res)
        self.assertEqual(10, res.ping)
        self.assertEqual(20, res.upload)
        self.assertEqual(20, res.download)
        self.assertNotEqual(None, res.server)
        self.assertEqual(res.server.name, 'NAMEX')
        self.assertEqual(res.server.ip, '193.104.137.133')
        self.assertEqual(res.server.id, 'fubsrvrmnmx03')
        self.assertEqual(res.now, True)
        self.assertEqual('2010-01-01 00:01:00',
                         res.start.strftime("%Y-%m-%d %H:%M:%S"))

    def test_new_task(self):
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
 <calendar>
    <task>
     <nup>20</nup>
     <ndown>20</ndown>
     <nping>10</nping>
     <start now="True">2010-01-01 00:01:00</start>
     <srvid>fubsrvrmnmx03</srvid>
     <srvip>193.104.137.133</srvip>
     <srvname>NAMEX</srvname>
    </task>
 </calendar>
    '''
        res = task.xml2task(xml)
        self.assertNotEqual(None, res)
        self.assertEqual(10, res.ping)
        self.assertEqual(20, res.upload)
        self.assertEqual(20, res.download)
        self.assertNotEqual(None, res.server)
        self.assertEqual(res.server.name, 'NAMEX')
        self.assertEqual(res.server.ip, '193.104.137.133')
        self.assertEqual(res.server.id, 'fubsrvrmnmx03')
        self.assertEqual(res.now, True)
        self.assertEqual('2010-01-01 00:01:00',
                         res.start.strftime("%Y-%m-%d %H:%M:%S"))

    def test_new_task_without_now(self):
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
 <calendar>
    <task>
     <nup>20</nup>
     <ndown>20</ndown>
     <nping>10</nping>
     <start>2010-01-01 00:01:00</start>
     <srvid>fubsrvrmnmx03</srvid>
     <srvip>193.104.137.133</srvip>
     <srvname>NAMEX</srvname>
    </task>
 </calendar>
    '''
        res = task.xml2task(xml)
        self.assertNotEqual(None, res)
        self.assertEqual(10, res.ping)
        self.assertEqual(20, res.upload)
        self.assertEqual(20, res.download)
        self.assertNotEqual(None, res.server)
        self.assertEqual(res.server.name, 'NAMEX')
        self.assertEqual(res.server.ip, '193.104.137.133')
        self.assertEqual(res.server.id, 'fubsrvrmnmx03')
        self.assertEqual(res.now, False)
        self.assertEqual('2010-01-01 00:01:00',
                         res.start.strftime("%Y-%m-%d %H:%M:%S"))

    def test_new_task_now_false(self):
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
 <calendar>
    <task>
     <nup>20</nup>
     <ndown>20</ndown>
     <nping>10</nping>
     <start now='false'>2010-01-01 00:01:00</start>
     <srvid>fubsrvrmnmx03</srvid>
     <srvip>193.104.137.133</srvip>
     <srvname>NAMEX</srvname>
    </task>
 </calendar>
    '''
        res = task.xml2task(xml)
        self.assertNotEqual(None, res)
        self.assertEqual(10, res.ping)
        self.assertEqual(20, res.upload)
        self.assertEqual(20, res.download)
        self.assertNotEqual(None, res.server)
        self.assertEqual(res.server.name, 'NAMEX')
        self.assertEqual(res.server.ip, '193.104.137.133')
        self.assertEqual(res.server.id, 'fubsrvrmnmx03')
        self.assertEqual(res.now, False)

    def test_wait_task(self):
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
 <calendar>
    <task wait='true'>
     <delay>20</delay>
     <message>Ciao</message>
    </task>
 </calendar>
    '''
        res = task.xml2task(xml)
        self.assertNotEqual(None, res)
        self.assertEqual(20, res.delay)
        self.assertEqual(True, res.is_wait)
        self.assertEqual('Ciao', res.message)

    def test_wait_task_no_delay(self):
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
 <calendar>
    <task wait='true'>
     <nup>20</nup>
     <ndown>20</ndown>
     <nping>10</nping>
     <start now="1">2010-01-01 00:01:00</start>
     <srvid>fubsrvrmnmx03</srvid>
     <srvip>193.104.137.133</srvip>
     <srvname>NAMEX</srvname>
    </task>
 </calendar>
    '''
        res = task.xml2task(xml)
        self.assertNotEqual(None, res)
        self.assertEqual(5 * 60, res.delay)
        self.assertEqual(True, res.is_wait)

    def test_not_task_xml(self):
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <measure>
        <content/>
    </measure>
    '''
        try:
            task.xml2task(xml)
            self.assertEqual(True, False)
        except TaskException:
            self.assertEqual(True, True)

    def test_invalid_xml(self):
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <measure>
        <content/>

    '''
        try:
            task.xml2task(xml)
            self.assertEqual(True, False)
        except TaskException:
            self.assertEqual(True, True)

    def test_not_xml(self):
        xml = '''Ciao'''
        with self.assertRaises(TaskException):
            task.xml2task(xml)

    def test_empty_task(self):
        xml = '''<?xml version="1.0" encoding="UTF-8"?><calendar/>'''
        with self.assertRaises(TaskException):
            task.xml2task(xml)

    def test_none_task(self):
        xml = None
        with self.assertRaises(TaskException):
            task.xml2task(xml)

    def test_new_task_with_message(self):
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
 <calendar>
    <task>
     <nup>20</nup>
     <ndown>20</ndown>
     <nping>10</nping>
     <start now="True">2010-01-01 00:01:00</start>
     <srvid>fubsrvrmnmx03</srvid>
     <srvip>193.104.137.133</srvip>
     <srvname>NAMEX</srvname>
     <message>Ciao</message>
    </task>
 </calendar>
    '''
        res = task.xml2task(xml)
        self.assertNotEqual(None, res)
        self.assertEqual(10, res.ping)
        self.assertEqual(20, res.upload)
        self.assertEqual(20, res.download)
        self.assertNotEqual(None, res.server)
        self.assertEqual(res.server.name, 'NAMEX')
        self.assertEqual(res.server.ip, '193.104.137.133')
        self.assertEqual(res.server.id, 'fubsrvrmnmx03')
        self.assertEqual(res.now, True)
        self.assertEqual('2010-01-01 00:01:00',
                         res.start.strftime("%Y-%m-%d %H:%M:%S"))
        self.assertEqual('Ciao',
                         res.message)

    def test_10_ping_task(self):
        xml = '''<?xml version="1.0" encoding="UTF-8"?><calendar>
<task>
        <id>41311310</id>
        <nftpup mult="10">4</nftpup>
        <nftpdown>4</nftpdown>
        <nping delay="1" icmp="1">10</nping>
        <start now="1">2018-02-08 11:28:31</start>
        <srvid>fubsrvrmnmx03</srvid>
        <srvip>193.104.137.133</srvip>
        <srvname>NAMEX</srvname>
        <srvlocation>Roma</srvlocation>
        <ftpuppath>/upload/1994.rnd</ftpuppath>
        <ftpdownpath>/download/1000.rnd</ftpdownpath>
    </task>
</calendar>

    '''
        res = task.xml2task(xml)
        self.assertNotEqual(None, res)
        self.assertEqual(10, res.ping)
        self.assertEqual(4, res.upload)
        self.assertEqual(4, res.download)

if __name__ == "__main__":
    unittest.main()
