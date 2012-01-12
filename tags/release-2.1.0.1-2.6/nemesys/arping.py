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
import arpinger
import ipcalc
import socket
import string
import struct

logger = logging.getLogger()

ETH_P_IP = 0x0800
ETH_P_ARP = 0x0806
ARP_REPLY = 0x0002

MAX = 128

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
    arpinger.clear()

    if (received['err_flag'] < 1):
      logger.debug("(%s) Numero di Host trovati: %d" % (received['err_str'], len(IPtable)))
      break

    elif (len(received['py_pcap_hdr']) >= 16 and len(received['py_pcap_data']) >= 42):

      pktHdr = received['py_pcap_hdr']

      pktSec, pktUsec, pktCaplen, pktLen = struct.unpack("LLII", pktHdr)

      pktTimeStamp = float(pktSec) + (float(pktUsec) / 1000000)

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


def do_arping(IPsrc, NETmask, realSubnet = True, timeout = 1, mac = None, threshold = 2):

  nHosts = 0

  if (mac):
    MACsrc = "".join(chr(int(macEL, 16)) for macEL in mac.split(':'))
  else:
    return 0
  MACdst = "\xFF"*6
  
  logger.debug("MAC_source = %s" % mac)
  IPsrc = socket.gethostbyname(IPsrc)
  IPnet = ipcalc.Network('%s/%d' % (IPsrc, NETmask))
  net = IPnet.network()
  bcast = IPnet.broadcast()

  pcap_filter = "rarp or arp dst host " + IPsrc

  rec_init = arpinger.initialize(IPsrc, pcap_filter, timeout * 1000)
  logger.debug("Inizializzato arpinger (%s, %s)" % (IPsrc, pcap_filter))
  if (rec_init['err_flag'] != 0):
    raise Exception (rec_init['err_str'])
  else:

    lasting = 2 ** (32 - NETmask)
    i = 0

    for IPdst in IPnet:
      if ((IPdst.hex() == net.hex() or IPdst.hex() == bcast.hex()) and realSubnet):
        logger.debug("Saltato ip %s" % IPdst)
      elif(IPdst.dq == IPsrc):
        logger.debug("Salto il mio ip %s" % IPdst)
      else:
        #logger.debug('Arping host %s' % IPdst)
        send_arping(IPsrc, IPdst, MACsrc, MACdst)
        i += 1

      lasting -= 1

      if (i >= MAX or lasting <= 0):
        i = 0

        try:
          nHosts += receive_arping(MACsrc)
        except Exception as e:
          logger.warning("Errore durante la ricezione degli arping: %s" % e)

      if(nHosts > threshold):
        break

    logger.debug("Totale host: %d" % nHosts)
    arpinger.close()

  return nHosts

if __name__ == '__main__':

  s = socket.socket(socket.AF_INET)
  s.connect(('www.fub.it', 80))
  ip = s.getsockname()[0]
  s.close()
  mymac='F0:4D:A2:53:AD:AE'
  print mymac.split(':')

  if ip != None:
    for i in range (1,1000):
      print("Trovati: %d host" % do_arping(ip, 24, True, 1, 'F0:4D:A2:53:AD:AE', 15))

