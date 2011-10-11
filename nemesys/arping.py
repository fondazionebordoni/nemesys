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
from logger import logging
from xmlutils import getXMLvalues
from SystemProfiler import systemProfiler

import arpinger
import ipcalc
import socket
import string
import struct
import time

logger = logging.getLogger()

ETH_P_IP = 0x0800
ETH_P_ARP = 0x0806
ARP_REPLY = 0x0002


def getMac():
  '''
  restituisce indirizzo MAC del computer
  '''

  string = ''

  try:
    string = systemProfiler('test', {'macAddr':''})
  except Exception as e:
    logger.error('Non sono riuscito a trovare lo stato del computer con SystemProfiler: %s.' % e)
    #raise Exception('Non sono riuscito a trovare lo stato del computer con SystemProfiler.')
    raise sysmonitorexception.FAILPROF

  values = getXMLvalues(string, 'SystemProfilerResults')

  return values['macAddr']


def display_mac(value):
    return string.join(["%02X" % ord(b) for b in value], ':')


def send_arping(IPsrc, IPdst, MACsrc, MACdst):

  hwsrc = MACsrc
  hwdst = MACdst

  psrc = socket.inet_aton(IPsrc)
  pdst = socket.inet_aton(str(IPdst))

  arpPkt = struct.pack('!HHbbH6s4s6s4s', 0x0001, 0x0800, 6, 4, 0x0001, hwsrc, psrc, '\x00', pdst)

  ethPkt = struct.pack("!6s6sh", hwdst, hwsrc, 0x0806) + arpPkt

  netPkt = ethPkt + (60 - len(ethPkt)) * '\x00'

  sended = arpinger.send(netPkt)
  if (sended['err_flag'] != 0):
    logger.debug("%s" % sended['err_str'])


def receive_arping(MACsrc):

  hwsrc = MACsrc

  IPtable = {}

  while True:

    received = arpinger.receive()

    if (received['err_flag'] < 1):
      logger.debug("%s - Numero di Host trovati: %d" % (received['err_str'], len(IPtable)))
      break

    elif (len(received['py_pcap_hdr']) >= 16 and len(received['py_pcap_data']) >= 42):

      pktHdr = received['py_pcap_hdr']

      pktSec, pktUsec, pktCaplen, pktLen = struct.unpack("LLII", pktHdr)

      pktTimeStamp = float(pktSec) + (float(pktUsec) / 1000000)

      #logger.debug(time.localtime(pktTimeStamp))

      pktData = received['py_pcap_data']

      hwdst_eth, hwsrc_eth, proto = struct.unpack("!6s6sh", pktData[:14])

      if (hwdst_eth == hwsrc):

        arpPkt = pktData[14:]
        if struct.unpack('!H', arpPkt[6:8])[0] == ARP_REPLY:
          hwsrc_arp, psrc_arp, hwdst_arp, pdst_arp = struct.unpack('!6s4s6s4s', arpPkt[8:28])
          IPsrc_arp = socket.inet_ntoa(psrc_arp)
          IPdst_arp = socket.inet_ntoa(pdst_arp)
          if (IPsrc_arp not in IPtable):
            IPtable[IPsrc_arp] = display_mac(hwsrc_arp)
            logger.debug('Trovato Host %s con indirizzo fisico %s' % (IPsrc_arp, display_mac(hwsrc_arp)))

  return len(IPtable)


def do_arping(IPsrc, NETmask, realSubnet = True, timeout = 1):

  nHosts = 0

  MACsrc = "".join(chr(int(macEL, 16)) for macEL in getMac().split(':'))
  MACdst = "\xFF"*6

  IPsrc = socket.gethostbyname(IPsrc)
  IPnet = ipcalc.Network('%s/%d' % (IPsrc, NETmask))
  net = IPnet.network()
  bcast = IPnet.broadcast()

  filter = "rarp or arp dst host " + IPsrc

  rec_init = arpinger.initialize(IPsrc, filter, timeout * 1000)
  if (rec_init['err_flag'] != 0):
    raise Exception (rec_init['err_str'])
  else:
    for IPdst in IPnet:
      if ((IPdst.hex() == net.hex() or IPdst.hex() == bcast.hex()) and realSubnet):
        logger.debug("Saltato ip %s" % IPdst)
      else:
        #logger.debug('Arping host %s' % IPdst)
        send_arping(IPsrc, IPdst, MACsrc, MACdst)

    nHosts = receive_arping(MACsrc)

    arpinger.close()

  return nHosts




if __name__ == '__main__':

  do_arping('192.168.88.8', 24, True, 1)

