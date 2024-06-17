# tester.py
# -*- coding: utf8 -*-

# Copyright (c) 2010-2016 Fondazione Ugo Bordoni.
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

import logging
import socket
from datetime import datetime
from optparse import OptionParser

from common import iptools, utils
from common import nem_exceptions
from common import ntptime
from common import ping
from common.host import Host
from common.nem_exceptions import MeasurementException
from common.proof import Proof
from common.testerhttpdown import HttpTesterDown
from common.testerhttpup import HttpTesterUp

HTTP_BUFF = 8 * 1024
BW_1M = 1 * 10**6
BW_3M = 3 * 10**6
BW_5M = 5 * 10**6
BW_25M = 25 * 10**6
BW_100M = 100 * 10**6
BW_300M = 300 * 10**6
BW_500M = 500 * 10**6
BW_1000M = 1 * 10**9
BW_2000M = 2 * 10**9
BW_2500M = 2.5 * 10**9
BW_5000M = 5 * 10**9

logger = logging.getLogger(__name__)
logger_csv = logging.getLogger("csv")


class Tester(object):
    def __init__(self, dev, host, timeout=11):
        self._host = host
        self._timeout = timeout
        socket.setdefaulttimeout(self._timeout)
        self._testerhttpup = HttpTesterUp(dev)
        self._testerhttpdown = HttpTesterDown(dev)

    def testhttpdown(self, callback_update_speed=None, bw=BW_100M):
        url = f"http://{self._host.ip}:{self._host.port}/file.rnd"
        if bw <= BW_1M:
            num_sessions = 1
        elif bw <= BW_5M:
            num_sessions = 4
        elif bw <= BW_100M:
            num_sessions = 8
        elif bw <= BW_500M:
            num_sessions = 16
        elif bw <= BW_1000M:
            num_sessions = 20
        else:
            num_sessions = 24
            if utils.is_darwin():
                num_sessions = 32

        buffer_size = int(bw / (4 * 10**3))

        logger.debug(f"Variabili di misura per banda={bw:,}: num_session={num_sessions}, buffer_size={buffer_size:,}")
        logger_csv.debug(f"down;{bw:,};{num_sessions};{buffer_size:,}")
        return self._testerhttpdown.test(url, callback_update_speed, num_sessions=num_sessions, buffer_size=buffer_size)

    def testhttpup(self, callback_update_speed=None, bw=BW_100M):
        url = f"http://{self._host.ip}:{self._host.port}/file.rnd"

        if bw <= BW_1M:
            num_sessions = 1
        elif bw <= BW_5M:
            num_sessions = 4
        elif bw <= BW_500M:
            num_sessions = 12
        elif bw <= BW_2000M:
            num_sessions = 16
            if utils.is_darwin():
                num_sessions = 24
        else:
            num_sessions = 24

        tcp_window_size = -1
        buffer_size = int(bw / (2 * 10**3))

        logger.debug(
            f"Variabili di misura per banda={bw:,}: num_session={num_sessions}, tcp_window_size={tcp_window_size}, buffer_size={buffer_size:,}"
        )
        logger_csv.debug(f"up;{bw:,};{num_sessions};{buffer_size:,}")
        return self._testerhttpup.test(
            url, callback_update_speed, num_sessions=num_sessions, tcp_window_size=tcp_window_size, buffer_size=buffer_size
        )

    def testping(self, timeout=10):
        # si utilizza funzione ping.py
        start = datetime.fromtimestamp(ntptime.timestamp())
        try:
            rtt = ping.do_one(self._host.ip, timeout)
        except Exception as e:
            if "Timeout" in str(e):
                rtt = None
            else:
                raise MeasurementException("Impossibile effettuare il ping: %s" % e, nem_exceptions.PING_ERROR)

        if rtt is None:
            raise MeasurementException("Ping timeout", nem_exceptions.PING_TIMEOUT)

        return Proof(test_type="ping", start_time=start, duration=rtt * 1000, bytes_nem=0)


def main():
    import time

    # Aggancio opzioni da linea di comando

    parser = OptionParser(
        version="0.10.1.$Rev$", description="A simple bandwidth tester able to perform HTTP upload/download and PING tests."
    )
    parser.add_option(
        "-t",
        "--type",
        choices=("down", "up", "ping"),
        dest="testtype",
        default="down",
        type="choice",
        help="Choose the type of test to perform: down (default), up, ping",
    )
    parser.add_option(
        "-b",
        "--bandwidth",
        dest="bandwidth",
        default="100M",
        type="string",
        help="The expected bandwith to measure, used in upload tests, e.g. 512k, 2M",
    )
    parser.add_option("-n", "--num-tests", dest="num_tests", default="1", type="int", help="Number of tests to perform")
    parser.add_option("-H", "--host", dest="host", default="193.104.137.133", help="An ipaddress or FQDN of server host")
    parser.add_option("-P", "--port", dest="port", default="80", help="Port number of server host")

    (options, _) = parser.parse_args()
    try:
        dev = iptools.get_dev(host=options.host, port=80)
    except Exception:
        print("Impossibile ottenere indirizzo e device, verificare la connessione all'host")
        import sys

        sys.exit(2)
    print(f"Misure su interfaccia: {dev}")
    t = Tester(dev, Host(options.host, options.port), timeout=10)
    if options.bandwidth.endswith("M"):
        bw = int(options.bandwidth[:-1]) * 1000000
    elif options.bandwidth.endswith("k"):
        bw = int(options.bandwidth[:-1]) * 1000
    else:
        print("Please specify bandwidth in the form of 2M or 512k")
        return

    print("===============================================")
    print(f"Testing: {options.host}")
    for i in range(1, options.num_tests + 1):
        print("-----------------------------------------------")
        if i != 1:
            print("Sleeping...")
            print("-----------------------------------------------")
            time.sleep(10)
        print(f"test {i} {options.testtype}")
        if options.testtype == "up":
            try:
                res = t.testhttpup(None, bw=bw)
                printout_http(res)
            except MeasurementException as e:
                print("Error: [%d] %s" % (e.errorcode, str(e)))
        elif options.testtype == "ping":
            try:
                res = t.testping()
                print("Ping: %.2f milliseconds" % res.duration)
                logger_csv.debug("ping;;;;%.2f;;;;;;;;;;;;;;;;;;;" % res.duration)
            except Exception as e:
                print("Error: [%d] %s" % (e.errorcode, str(e)))
        else:
            try:
                res = t.testhttpdown(bw=bw)
                printout_http(res)
            except MeasurementException as e:
                print("Error: %s" % str(e))
    print("===============================================")


def printout_http(res):
    speed = int(res.bytes_tot * 8 / float(res.duration))
    print(f"Medium speed: {speed:,} kbps")
    print("Spurious traffic: %.2f%%" % (res.spurious * 100.0))
    logger_csv.debug(f";{speed:,}")
    logger_csv.debug(";%.2f%%" % (res.spurious * 100.0))


if __name__ == "__main__":
    from nemesys import log_conf

    log_conf.init_log()
    main()
