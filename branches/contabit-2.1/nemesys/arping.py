# arping.py
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from exceptions import Exception
import random
import select
import signal
import socket
import string
import struct
import sys
import time
from logger import logging

IS_WIN = False

ETH_P_ALL = 3
ETH_P_ARP = 0x0806
ARP_REPLY = 0x0002

logger = logging.getLogger()

def display_mac(value):
    return string.join(["%02X" % ord(b) for b in value], ':')


def receive_one_arping(my_socket, IPdst, timeSend, timeout):
  
  global ARP_REPLY
  
  hwsrc = my_socket.getsockname()[-1]
  timeLeft = timeout
  
  while True:
    startedSelect = time.time()
    whatReady = select.select([my_socket], [], [], timeLeft)
    howLongInSelect = time.time() - startedSelect
    if whatReady[0] == []:  # Timeout
      raise RuntimeWarning('Timeout during ARP socket select')
    
    if IS_WIN:
      timeReceived = time.clock()
    else:
      timeReceived = time.time()
    
    Pkt = my_socket.recv(128)
    #hwdst_eth, hwsrc_eth, proto = struct.unpack("!6s6sh", Pkt[:14])
    ArpPkt = Pkt[14:]
    if struct.unpack('!H', ArpPkt[6:8])[0] == ARP_REPLY:
      hwsrc_arp, psrc_arp, hwdst_arp, pdst_arp = struct.unpack('!6s4s6s4s', ArpPkt[8:28])
      IPsrc_arp = socket.inet_ntoa(psrc_arp)
      if (hwdst_arp == hwsrc and IPsrc_arp == IPdst):
        logger.debug('Trovato Host IP:%s MAC:%s  ' % (IPdst,display_mac(hwsrc_arp)))
        return timeReceived - timeSend

    timeLeft = timeLeft - howLongInSelect
    if timeLeft <= 0:
      raise RuntimeWarning('Timeout during ARP packet receive (timeout = %f)'
                  % timeout)


def send_one_arping(my_socket, IPsrc, IPdst):
  
  global ETH_P_ARP
  
  proto = ETH_P_ARP
  
  hwdst = "\xFF"*6
  hwsrc = my_socket.getsockname()[-1]
  
  psrc = socket.inet_aton(IPsrc)
  pdst = socket.inet_aton(IPdst)
  
  ArpPkt = struct.pack('!HHbbH6s4s6s4s', 0x1, 0x0800, 6, 4, 1, hwsrc, psrc, '\x00', pdst)
  
  EthPkt = struct.pack("!6s6sh", hwdst, hwsrc, proto) + ArpPkt

  Pkt = EthPkt + (60-len(EthPkt)) * '\x00'
  
  if IS_WIN:
    timeSend = time.clock()
  else:
    timeSend = time.time()

  my_socket.send(Pkt)

  return timeSend


def do_one(IPsrc, IPdst, timeout):
  """
  Returns either the delay (in seconds) or none on timeout.
  """
  global ETH_P_ARP
  global IS_WIN
  IPdst = socket.gethostbyname(IPdst)

  try:
    my_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ARP))
    my_socket.bind(("eth0", ETH_P_ARP))
    my_socket.setblocking(0)
  except socket.error, (errno, msg):
    if errno == 1: # Operation not permitted
      msg = msg \
        + ' - Note that Arp messages can only be sent from processes running as root.'
      raise socket.error(msg)
    raise   # raise the original error  

  if sys.platform[0:2] == 'win':
    IS_WIN = True
    time.clock()
  else:
    IS_WIN = False

  timeSend = send_one_arping(my_socket, IPsrc, IPdst)
  delay = receive_one_arping(my_socket, IPdst, timeSend, timeout)
  
  my_socket.close()
  return delay


def verbose_arping(dest_addr, timeout=20, count=4):
    """
    Send >count< arping to >dest_addr< with the given >timeout< and display
    the result.
    """

    source_addr = '192.168.208.53'

    for i in xrange(count):
        print 'arping %s...' % dest_addr,
        try:
            delay = do_one(source_addr, dest_addr, timeout)
        except socket.gaierror, e:
            print "failed. (socket error: '%s')" % e[1]
            break

    if delay == None:
        print 'failed. (timeout within %ssec.)' % timeout,
    else:
        delay = delay * 1000
        print 'get arping in %0.4fms' % delay,
    print


if __name__ == '__main__':
    for i in range(1,255):
        try:
            verbose_arping("192.168.208.%d" %i, 1, 1)
        except Exception as e:
            print

