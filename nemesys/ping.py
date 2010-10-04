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

from exceptions import Exception
import os
import sys
import socket
import struct
import select
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
    thisVal = ord(source_string[count + 1]) * 256 \
      + ord(source_string[count])
    sum = sum + thisVal
    sum = sum & 0xffffffff  # Necessary?
    count = count + 2

  if countTo < len(source_string):
    sum = sum + ord(source_string[len(source_string) - 1])
    sum = sum & 0xffffffff  # Necessary?

  sum = (sum >> 16) + (sum & 65535)
  sum = sum + (sum >> 16)
  answer = ~sum
  answer = answer & 65535

  # Swap bytes. Bugger me if I know why.

  answer = answer >> 8 | answer << 8 & 0xff00

  return answer


def receive_one_ping(my_socket, ID, timeout):
  """
  Receive the ping from the socket.
  """

  timeLeft = timeout

  while True:
    startedSelect = time.time()
    whatReady = select.select([my_socket], [], [], timeLeft)
    howLongInSelect = time.time() - startedSelect
    if whatReady[0] == []:  # Timeout
      raise RuntimeWarning('Timeout during ICMP socket select')

    if IS_WIN == True:
      timeReceived = time.clock()
    else:
      timeReceived = time.time()

    (recPacket, addr) = my_socket.recvfrom(PACKET_SIZE + 64)
    icmpHeader = recPacket[20:28]
    (type, code, checksum, packetID, sequence) = \
      struct.unpack('bbHHh', icmpHeader)

    # TODO Inserire tutti i codes con i relativi errori (?)

    if type == 3:
      codes = {
        0: 'Net Unreachable',
        1: 'Host Unreachable',
        2: 'Protocol Unreachable',
        3: 'Port Unreachable',
        }

      raise Exception(codes[code])
      break

    if packetID == ID and type == 0:
      bytesInDouble = struct.calcsize('d')
      timeSent = struct.unpack('d', recPacket[28:28 + bytesInDouble])[0]
      return timeReceived - timeSent

    timeLeft = timeLeft - howLongInSelect
    if timeLeft <= 0:
      raise RuntimeWarning('Timeout during ICMP packet receive (timeout = %f)'
                  % timeout)


def send_one_ping(my_socket, dest_addr, ID):
  """
  Send one ping to the given >dest_addr<.
  """

  dest_addr = socket.gethostbyname(dest_addr)

  # global OS
  # Header is type (8bit), code (8bit), checksum (16bit), id (16bit), sequence (16bit)

  my_checksum = 0

  # Make a dummy heder with a 0 checksum.

  header = struct.pack('bbHHh', ICMP_ECHO_REQUEST, 0, my_checksum, ID, 1)
  bytesInDouble = struct.calcsize('d')
  data = (PACKET_SIZE - len(header) - bytesInDouble) * 'x'

  if IS_WIN == True:
    start = time.clock()
  else:
    start = time.time()

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
  icmp = socket.getprotobyname('icmp')
  try:
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
  except socket.error, (errno, msg):
    if errno == 1:

    # Operation not permitted

      msg = msg \
        + ' - Note that ICMP messages can only be sent from processes running as root.'
      raise socket.error(msg)
    raise   # raise the original error

  my_ID = os.getpid() & 65535

  if sys.platform[0:-2] == 'win':
    IS_WIN = True
    time.clock()
  else:
    IS_WIN = False

  send_one_ping(my_socket, dest_addr, my_ID)
  delay = receive_one_ping(my_socket, my_ID, timeout)

  my_socket.close()
  return delay


def verbose_ping(dest_addr, timeout=20, count=4):
  """
  Send >count< ping to >dest_addr< with the given >timeout< and display
  the result.
  """

  for i in xrange(count):
    print 'ping %s...' % dest_addr,
    try:
      delay = do_one(dest_addr, timeout)
    except socket.gaierror, e:
      print "failed. (socket error: '%s')" % e[1]
      break

    if delay == None:
      print 'failed. (timeout within %ssec.)' % timeout
    else:
      delay = delay * 1000
      print 'get ping in %0.4fms' % delay
  print


if __name__ == '__main__':
  verbose_ping('repubblica.it')
  verbose_ping('google.com')
  verbose_ping('192.168.208.88')
  verbose_ping('a-test-url-taht-is-not-available.com')
  verbose_ping('127.0.0.1')

