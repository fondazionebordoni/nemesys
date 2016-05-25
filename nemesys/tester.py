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
import logging
from optparse import OptionParser
import ping
import socket

import errorcode
from host import Host
import iptools
from testerhttpdown import HttpTesterDown
from testerhttpup import HttpTesterUp
from proof import Proof
from timeNtp import timestampNtp


HTTP_BUFF = 8*1024
BW_3M = 3000000
BW_100M = 100000000
logger = logging.getLogger(__name__)


class Tester(object):

    def __init__(self, dev, host, username = 'anonymous', password = 'anonymous@', timeout = 60):
        self._host = host
        self._username = username
        self._password = password
        self._timeout = timeout
        socket.setdefaulttimeout(self._timeout)
        self._testerhttpup = HttpTesterUp(dev, HTTP_BUFF)
        self._testerhttpdown = HttpTesterDown(dev, HTTP_BUFF)

    def testhttpdown(self, callback_update_speed=None, num_sessions=7):
        url = "http://%s/file.rnd" % self._host.ip
        return self._testerhttpdown.test_down(url, 10, callback_update_speed, num_sessions=num_sessions)        
 
    def testhttpup(self, callback_update_speed=None, bw=BW_100M):
        url = "http://%s:8080/file.rnd" % self._host.ip
        if bw < BW_3M:
            num_sessions = 1
            tcp_window_size = 22 * 1024
        elif bw == BW_3M:
            num_sessions = 1
            tcp_window_size = 65 * 1024
        else:
            num_sessions = 6
            tcp_window_size = 65 * 1024
        return self._testerhttpup.test_up(url, callback_update_speed, num_sessions=num_sessions, tcp_window_size=tcp_window_size)        
         
    def testping(self, timeout = 10):
        # si utilizza funzione ping.py
        test_type = 'ping'
        start = datetime.fromtimestamp(timestampNtp())
        elapsed = 0

        try:
            # Il risultato deve essere espresso in millisecondi
            elapsed = ping.do_one(self._host.ip, timeout) * 1000

        except Exception as e:
            error = errorcode.from_exception(e)
            error_msg = '[%s] Errore durante la misura %s: %s' % (error, test_type, e)
            logger.error(error_msg)
            raise Exception(error_msg)

        if (elapsed == None):
            elapsed = 0

        return Proof(test_type=test_type, start_time=start, duration=elapsed, bytes_nem=0)


def main():
    import time
    #Aggancio opzioni da linea di comando
    
    parser = OptionParser(version = "0.10.1.$Rev$",
                                                description = "A simple bandwidth tester able to perform HTTP upload/download and PING tests.")
    parser.add_option("-t", "--type", choices = ('httpdown', 'httpup', 'ftpup', 'ping'),
                                    dest = "testtype", default = "httpdown", type = "choice",
                                    help = "Choose the type of test to perform: httpdown (default), httpup, ping")
    parser.add_option("-b", "--bandwidth", dest = "bandwidth", default = "100M", type = "string",
                                    help = "The expected bandwith to measure, used in upload tests, e.g. 512k, 2M")
#     parser.add_option("-w", "--tcp-window", dest = "tcp_window_size", default = "66560", type = "int",
#                                     help = "The TCP window size, only for HTTP upload, e.g. 22528")
#     parser.add_option("--ping-timeout", dest = "ping_timeout", default = "20.0", type = "float",
#                                     help = "Ping timeout")
#     parser.add_option("--sessions-up", dest = "sessions_up", default = "1", type = "int",
#                                     help = "Number of sessions in upload (only HTTP)")
#     parser.add_option("--sessions-down", dest = "sessions_down", default = "7", type = "int",
#                                     help = "Number of sessions in download")
    parser.add_option("-n", "--num-tests", dest = "num_tests", default = "1", type = "int",
                                    help = "Number of tests to perform")
    parser.add_option("-H", "--host", dest = "host", default = "eagle2.fub.it",
                                    help = "An ipaddress or FQDN of server host")
    
    (options, _) = parser.parse_args()
#        This is for lab environment
#         ip = iptools.getaddr(host=options.host, port=80)
#         dev = iptoold.get_dev(host=options.host, port=80)
    ip = iptools.getipaddr()
    dev = iptools.get_dev(ip = ip)
#     def __init__(self, dev, host, username = 'anonymous', password = 'anonymous@', timeout = 60):
    t = Tester(dev, Host(options.host), timeout = 10.0)
    if options.bandwidth.endswith("M"):
        bw = int(options.bandwidth[:-1]) * 1000000
    elif options.bandwidth.endswith("k"):
        bw = int(options.bandwidth[:-1]) * 1000
    else:
        print "Please specify bandwith in the form of 2M or 512k"
        return

    #     test = None
    print "==============================================="
    print ('Testing: %s' % options.host)
    for i in range(1, options.num_tests + 1):
        print "-----------------------------------------------"
        if i != 1:
            print "Sleeping...."
            print "-----------------------------------------------"
            time.sleep(5)
        print('test %d %s' % (i, options.testtype))
        if options.testtype == 'httpup':
            try:
                res = t.testhttpup(None, bw=bw)
                printout_http(res)
            except Exception as e:
                print("Error: %s" % str(e))
        elif options.testtype == 'ping':
            try:
                res = t.testping()
                print("Ping: %.2f milliseconds" % res.value)
            except Exception as e:
                print("Error: %s" % str(e))
        else:
            try:
                res = t.testhttpdown(None)
                printout_http(res)
            except Exception as e:
                print("Error: %s" % str(e))
    print "==============================================="


def printout_http(res):
    byte_nem = res.counter_stats.byte_down_nem
    byte_all = res.counter_stats.byte_down_all
    if byte_nem == byte_all == 0:
        byte_nem = res.counter_stats.byte_up_nem
        byte_all = res.counter_stats.byte_up_all


    print("Medium speed: %d kbps" % (int(byte_all*8/10000.0)))
    print("Spurious traffic: %.2f%%" % (float(byte_all - byte_nem)/byte_all*100.0))



if __name__ == '__main__':
    import log_conf
    log_conf.init_log()
    main()
