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
import arpinger
import ipcalc
import random
import select
import signal
import socket
import string
import struct
import sys
import time
from logger import logging


ETH_P_IP = 0x0800
ETH_P_ARP = 0x0806
ARP_REPLY = 0x0002

logger = logging.getLogger()


def display_mac(value):
    return string.join(["%02X" % ord(b) for b in value], ':')


def send_arping(IPsrc, IPdst):
  
  hwdst = "\xFF"*6
  hwsrc = "\x00\x26\x2d\x70\x51\xcd"
  
  psrc = socket.inet_aton(IPsrc)
  pdst = socket.inet_aton(str(IPdst))
  
  ArpPkt = struct.pack('!HHbbH6s4s6s4s', 0x0001, 0x0800, 6, 4, 0x0001, hwsrc, psrc, '\x00', pdst)
  
  EthPkt = struct.pack("!6s6sh", hwdst, hwsrc, 0x0806) + ArpPkt

  Pkt = EthPkt + (60-len(EthPkt)) * '\x00'
      
  logger.debug('Arping host %s' % IPdst)  
    
  sended = arpinger.send(Pkt)
  if (sended['err_flag'] != 0):
    logger.debug("%s:" %received['err_str'])
    

def receive_arping():
  
  hwsrc = "\x00\x26\x2d\x70\x51\xcd"
  
  nHosts = 0
  
  while True:
    
    received = arpinger.receive()
  
    PktRcv = received['py_pcap_data']
  
    if (received['err_flag'] < 1):
      logger.debug("%s" %received['err_str'])
      break
        
    elif (len(PktRcv) > 30):
      
      hwdst_eth, hwsrc_eth, proto = struct.unpack("!6s6sh", PktRcv[:14])
      
      if (hwdst_eth == hwsrc):
      
        ArpPkt = PktRcv[14:]
        if struct.unpack('!H', ArpPkt[6:8])[0] == ARP_REPLY:
          hwsrc_arp, psrc_arp, hwdst_arp, pdst_arp = struct.unpack('!6s4s6s4s', ArpPkt[8:28])
          IPsrc_arp = socket.inet_ntoa(psrc_arp)
          IPdst_arp = socket.inet_ntoa(pdst_arp)
          logger.debug('Trovato Host %s con indirizzo fisico %s' % (IPsrc_arp,display_mac(hwsrc_arp)))
          nHosts += 1
  
  return nHosts

  
def do_arping(IPsrc, NETmask, realSubnet=True, timeout=1):  
  
  IPsrc = socket.gethostbyname(IPsrc)
  IPnet = ipcalc.Network('%s/%d' % (IPsrc, NETmask))
  net = IPnet.network()
  bcast = IPnet.broadcast()
    
  filter = "rarp or arp dst host " + IPsrc

  rec_init = arpinger.initialize(IPsrc,filter,timeout*1000)
  if (rec_init['err_flag'] != 0):
    logger.debug("%s:" %rec_init['err_str'])
    
  for IPdst in IPnet:
    if ((IPdst.hex() == net.hex() or IPdst.hex() == bcast.hex()) and realSubnet):
      logger.debug("Saltato ip %s" % IPdst)
    else:
      send_arping(IPsrc, IPdst)
      
  nHosts = receive_arping()
  
  arpinger.close()
    
  return nHosts




if __name__ == '__main__':
  
  do_arping('192.168.208.53', 24, True, 1)

