#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2010 Fondazione Ugo Bordoni.
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
# This code is derived from: ping.py by George Notaras
# Licensed under the GNU General Public License version 2,
# Original version:
#   -> http://www.g-loaded.eu/2009/10/30/python-ping/
# TODO: use the source! https://github.com/l4m3rx/python-ping/blob/master/ping.py
# Not possible at the moment since it is not thread safe, using pid to
# identify packets

import random
import select
import socket
import struct
import sys
import time

ICMP_ECHO_REQUEST = 8  # Seems to be the same on Solaris.
PACKET_SIZE = 32
IS_WIN = False


def checksum(source_string):
    """
    I'm not too confident that this is right but testing seems
    to suggest that it gives the same answers as in_cksum in ping.c
    """

    sum = 0
    countTo = len(source_string) / 2 * 2
    count = 0
    while count < countTo:
        thisVal = source_string[count + 1] * \
            256 + source_string[count]
        sum = sum + thisVal
        sum = sum & 0xffffffff  # Necessary?
        count = count + 2

    if countTo < len(source_string):
        sum = sum + source_string[len(source_string) - 1]
        sum = sum & 0xffffffff  # Necessary?

    sum = (sum >> 16) + (sum & 65535)
    sum = sum + (sum >> 16)
    answer = ~sum
    answer = answer & 65535

    # Swap bytes. Bugger me if I know why.

    answer = answer >> 8 | answer << 8 & 0xff00

    return answer


def receive_one_ping(my_socket, ID, timeout, dest_addr):
    """
    Receive the ping from the socket.
    """

    timeLeft = timeout

    while True:
        startedSelect = time.perf_counter()
        whatReady = select.select([my_socket], [], [], timeLeft)
        howLongInSelect = time.perf_counter() - startedSelect
        if whatReady[0] == []:  # Timeout
            raise RuntimeWarning('Timeout during ICMP socket select')
        
        timeReceived = time.perf_counter()

        (recPacket, addr) = my_socket.recvfrom(PACKET_SIZE + 64)
        icmpHeader = recPacket[20:28]
        (type, code, checksum, packetID, sequence) = \
            struct.unpack('bbHHh', icmpHeader)

        if addr[0] == dest_addr and packetID == ID:
            if type == 0:
                bytesInDouble = struct.calcsize('d')
                timeSent = struct.unpack('d', recPacket[28:28 + bytesInDouble])[0]
                return timeReceived - timeSent
            elif type == 3:
                codes = {
                    0: 'Net Unreachable',
                    1: 'Host Unreachable',
                    2: 'Protocol Unreachable',
                    3: 'Port Unreachable',
                }
                raise Exception(codes[code])

        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            raise RuntimeWarning('Timeout during ICMP packet receive (timeout = %f)'
                                 % timeout)


def send_one_ping(my_socket, dest_addr, ID):
    """
    Send one ping to the given >dest_addr<.
    """

    # global OS
    # Header is type (8bit), code (8bit), checksum (16bit), id (16bit), sequence (16bit)

    my_checksum = 0

    # Make a dummy heder with a 0 checksum.

    header = struct.pack('bbHHh', ICMP_ECHO_REQUEST, 0, my_checksum, ID, 1)
    bytesInDouble = struct.calcsize('d')
    data = (PACKET_SIZE - len(header) - bytesInDouble) * b'x'

    start = time.perf_counter()

    data = struct.pack('d', start) + data

    # Calculate the checksum on the data and the dummy header.

    my_checksum = checksum(header + data)

    # Now that we have the right checksum, we put that in. It's just easier
    # to make up a new header than to stuff it into the dummy.

    header = struct.pack('bbHHh', ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), ID, 1)
    packet = header + data
    my_socket.sendto(packet, (dest_addr, 1))  # Don't know about the 1


def do_one(dest_addr, timeout):
    """
    Returns either the delay (in seconds) or none on timeout.
    """

    global IS_WIN
    dest_addr = socket.gethostbyname(dest_addr)
    icmp = socket.getprotobyname('icmp')
    try:
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
        my_socket.settimeout(timeout)
    except socket.error as xxx_todo_changeme:
        (errno, msg) = xxx_todo_changeme.args
        if errno == 1:
            # Operation not permitted

            msg += ' - Note that ICMP messages can only be sent from processes running as root.'
            raise socket.error(msg)
        raise  # raise the original error

    my_ID = random.randint(1, 65535) & 65535
    send_one_ping(my_socket, dest_addr, my_ID)
    delay = receive_one_ping(my_socket, my_ID, timeout, dest_addr)

    my_socket.close()
    return delay


def verbose_ping(dest_addr, timeout=20, count=4):
    """
    Send >count< ping to >dest_addr< with the given >timeout< and display
    the result.
    """

    for i in range(count):
        print('ping %s...' % dest_addr, end=' ')
        try:
            delay = do_one(dest_addr, timeout)
        except socket.gaierror as e:
            print("failed. (socket error: '%s')" % e[1])
            break

        if delay is None:
            print('failed. (timeout within %ssec.)' % timeout)
        else:
            delay = delay * 1000
            print('get ping in %0.4fms' % delay)
    print()


if __name__ == '__main__':
    for i in range(1, 4):
        try:
            verbose_ping("192.168.208.%d" % i, 1, 1)
        except Exception as e:
            print()
    verbose_ping('repubblica.it', 5)
    verbose_ping('google.com', 5)
    #verbose_ping('a-test-url-taht-is-not-available.com', 5)
    verbose_ping('127.0.0.1', 5)
