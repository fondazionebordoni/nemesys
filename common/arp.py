#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Fondazione Ugo Bordoni.
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
#
# This code is derived from: arprequest.py by Antoine Millet
# Original version:
#   -> https://pypi.python.org/pypi/arprequest

import Queue
import logging
import platform
import re
import socket
import struct
from subprocess import Popen, PIPE
from threading import Thread

import ping

logger = logging.getLogger(__name__)

is_windows = (platform.system().startswith("Windows"))

if is_windows:
    import ctypes

    """ Loading Windows system libraries should not be a problem """
    """ Iphplpapi should work on Win 2000 and above              """
    try:
        iphlpapi = ctypes.windll.Iphlpapi
        ws2_32 = ctypes.windll.ws2_32
    except OSError:
        """ Should it still fail """
        logger.error("Error loading windows system libraries!")
        raise Exception("Manca uno o più delle librerie Iphlapi.dll e ws2_32.dll")


def mac_straddr(mac, printable=False, delimiter=None):  # TODO this should be the same as _print_mac
    """
    Convert c_ulong*2 to a hexadecimal string or a printable ascii
    string delimited by the 3rd parameter

    Expect a list of length 2 returned by arp_query
     """
    if len(mac) != 2:
        return -1
    if printable:
        if delimiter:
            m = ""
            for c in mac_straddr(mac):
                m += "%02x" % ord(c) + delimiter
            return m.rstrip(delimiter)

        return repr(mac_straddr(mac)).strip("\'")

    return struct.pack("L", mac[0]) + struct.pack("H", mac[1])


def do_arping(dest_addresses):
    if is_windows:
        return do_win_arping(dest_addresses)
    else:
        return do_unix_arping(dest_addresses)


def do_unix_arping(ip_destinations, timeout=0.01):
    """ping using OS command. Not very pretty, but works..."""
    arp_table = {}
    for ip_destination in ip_destinations:
        mac = _send_one_mac_arp(str(ip_destination), timeout)
        if mac:
            arp_table[ip_destination] = mac
    return arp_table


def _send_one_mac_arp(ip_address, timeout=0.01):
    # Remove any existing entry
    pid = Popen(["arp", "-d", ip_address], stdout=PIPE, stderr=PIPE)
    pid.communicate()[0]
    # Now ping the destination
    try:
        ping.do_one("%s" % ip_address, timeout)
    except Exception:
        pass  # Timeout
    pid = Popen(["arp", "-n", ip_address], stdout=PIPE, stderr=PIPE)
    s = pid.communicate()[0]
    my_match = re.search(r"(([a-fA-F\d]{1,2}\:){5}[a-fA-F\d]{1,2})", s)
    if my_match:
        return _pad_mac_string(my_match.groups()[0])


def _pad_mac_string(mac_str):
    parts = mac_str.split(':')
    padded_mac_str = ":".join('%02x' % int(n, 16) for n in parts)
    return padded_mac_str


def do_win_arping(ip_destinations):
    """Windows ARP"""
    result_queue = Queue.Queue()
    threads = []
    for ip_dest in ip_destinations:
        t = Thread(target=_send_one_win_arp, args=(ip_dest, result_queue))
        threads.append(t)

    [x.start() for x in threads]
    [x.join() for x in threads]

    arp_table = {}
    while not result_queue.empty():
        try:
            ip, mac = result_queue.get_nowait()
            if ip not in arp_table:
                arp_table[ip] = mac
        except Queue.Empty:
            break  # Should not happen
    return arp_table


def _send_one_win_arp(ip_address, result_queue):
    ip_address = str(ip_address)
    mac_addr = (ctypes.c_ulong * 2)()
    addr_len = ctypes.c_ulong(6)
    ip_dest = ws2_32.inet_addr(ip_address)

    ip_src = ws2_32.inet_addr(socket.gethostbyname(socket.gethostname()))

    error = iphlpapi.SendARP(ip_dest, ip_src, ctypes.byref(mac_addr), ctypes.byref(addr_len))

    if error:
        if (int(error) != 31) and (int(error) != 67):
            logger.error("Warning: SendARP failed! Error code: %d", int(error))
    else:
        mac_str = mac_straddr(mac_addr, True, ":")
        result_queue.put((ip_address, mac_str))
