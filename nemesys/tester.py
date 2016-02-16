# tester.py
# -*- coding: utf8 -*-

# Copyright (c) 2010 Fondazione Ugo Bordoni.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
from host import Host
from logger import logging
from optparse import OptionParser
from proof import Proof
# from statistics import Statistics
from testerftp import FtpTester
from testerhttp import HttpTester
from timeNtp import timestampNtp
import errorcode
import ping
import socket
import sys

logger = logging.getLogger()


class Tester(object):

    def __init__(self, dev, host, username = 'anonymous', password = 'anonymous@', timeout = 60):
        self._host = host
        self._username = username
        self._password = password
        self._timeout = timeout
        socket.setdefaulttimeout(self._timeout)
        self._ftp_tester = FtpTester(dev, host, username, password, timeout)
        self._http_tester = HttpTester(dev)

    def testftpup(self, num_bytes, path):
        return self._ftp_tester.testftpup(num_bytes, path)

    def testftpdown(self, filename):
        return self._ftp_tester.testftpdown(filename)

    def testhttpdown(self, num_sessions = 7):
        url = "http://%s/file.rnd" % self._host.ip
        return self._http_tester.test_down(url, num_sessions = num_sessions)

    def testhttpup(self, num_sessions = 1):
            url = "http://%s/file.rnd" % self._host.ip
            return self._http_tester.test_up(url, num_sessions = num_sessions)        

    def testping(self):
        # si utilizza funzione ping.py
        test_type = 'ping'
        start = datetime.fromtimestamp(timestampNtp())
        elapsed = 0

        try:
            # Il risultato deve essere espresso in millisecondi
            elapsed = ping.do_one(self._host.ip, self._timeout) * 1000

        except Exception as e:
            error = errorcode.from_exception(e)
            error_msg = '[%s] Errore durante la misura %s: %s' % (error, test_type, e)
            logger.error(error_msg)
            raise Exception(error_msg)

        if (elapsed == None):
            elapsed = 0

        return Proof(test_type, start = start, value = elapsed, bytes = 0)


def main():
    #Aggancio opzioni da linea di comando

    parser = OptionParser(version = "0.10.1.$Rev$",
                                                description = "A simple bandwidth tester able to perform FTP upload/download and PING tests.")
    parser.add_option("-t", "--type", choices = ('ftpdown', 'ftpup', 'ping'),
                                        dest = "testtype", default = "ftpdown", type = "choice",
                                        help = "Choose the type of test to perform: ftpdown (default), ftpup, ping")
    parser.add_option("-f", "--file", dest = "filename",
                                        help = "For FTP download, the name of the file for RETR operation")
    parser.add_option("-b", "--byte", dest = "bytes", type = "int",
                                        help = "For FTP upload, the size of the file for STOR operation")
    parser.add_option("-H", "--host", dest = "host",
                                        help = "An ipaddress or FQDN of testing host")
    parser.add_option("-u", "--username", dest = "username", default = "anonymous",
                                        help = "An optional username to use when connecting to the FTP server")
    parser.add_option("-p", "--password", dest = "password", default = "anonymous@",
                                        help = "The password to use when connecting to the FTP server")
    parser.add_option("-P", "--path", dest = "path", default = "",
                                        help = "The path where put uploaded file")
    parser.add_option("--timeout", dest = "timeout", default = "30", type = "int",
                                        help = "Timeout in seconds for FTP blocking operations like the connection attempt")

    (options, _) = parser.parse_args()
    #TODO inserire controllo host

    t = Tester(sysmonitor.getIp(), Host(options.host), options.username, options.password)
    print ('Prova: %s' % options.host)

    tests = {
        'ftpdown': t.testftpdown(options.filename),
        'ftpup': t.testftpup(options.bytes, options.path),
        'ping': t.testping(),
    }
    test = tests.get(options.testtype)

    print test


if __name__ == '__main__':
    if len(sys.argv) < 2:
        s = socket.socket(socket.AF_INET)
        s.connect(('www.fub.it', 80))
        ip = s.getsockname()[0]
        s.close()
        nap = '193.104.137.133'

        TOT = 1

        import sysmonitor
        dev = sysmonitor.getDev()
        t1 = Tester(dev, Host(ip = nap), 'nemesys', '4gc0m244')

#         for i in range(1, TOT + 1):
#             logger.info('Test Download %d/%d' % (i, TOT))
#             test = t1.testftpdown('/download/1000.rnd')
#             logger.info(test)
# 
#         for i in range(1, TOT + 1):
#             logger.info('Test Upload %d/%d' % (i, TOT))
#             test = t1.testftpup(2048, '/upload/r.raw')
#             logger.info(test)

        for i in range(1, TOT + 1):
            logger.info('Test Download %d/%d' % (i, TOT))
            test = t1.testhttpdown()
            logger.info(test)

        for i in range(1, TOT + 1):
            logger.info('Test Upload %d/%d' % (i, TOT))
            test = t1.testhttpup()
            logger.info(test)

        for i in range(1, TOT + 1):
            logger.info('\nTest Ping %d/%d' % (i, TOT))
            test = t1.testping()
            logger.info(test)

    else:
        main()
