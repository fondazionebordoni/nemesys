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
from sys import platform
from threading import Thread

import pktman
import ipcalc
import socket
import string
import struct
import subprocess
import re

logger = logging.getLogger()

ETH_P_IP = 0x0800
ETH_P_ARP = 0x0806
ARP_REQUEST = 0x0001
ARP_REPLY = 0x0002
TECHNICOLOR_MACS = ['^A..B1.E9'] 
TECHNICOLOR_IPS = ['192.168.1.253']

MAX = 128

def display_mac(value):
    return string.join(["%02X" % ord(b) for b in value], ':')

def send_arping(IPsrc, IPdst, MACsrc, MACdst, sock):

  hwsrc = MACsrc
  hwdst = MACdst

  psrc = socket.inet_aton(IPsrc)
  pdst = socket.inet_aton(IPdst)

  arpPkt = struct.pack('!HHbbH6s4s6s4s', 0x0001, ETH_P_IP, 6, 4, ARP_REQUEST, hwsrc, psrc, '\x00', pdst)

  ethPkt = struct.pack("!6s6sh", hwdst, hwsrc, ETH_P_ARP) + arpPkt

  netPkt = ethPkt + (60 - len(ethPkt)) * '\x00'

  if (platform.startswith('win')):
    sock.sendto(netPkt, (IPdst, 0))
  else:
    sended = pktman.push(netPkt)
    if (sended['err_flag'] != 0):
      logger.debug("%s" % sended['err_str'])

def _is_technicolor(ip, mac):
  if (not re.match("([0-9A-F]{2}:){5}[0-9A-F]", mac, re.I)):
    logger.warn("Errore nell'utilizzo della funzione _is_technicolor: formato MAC non corretto (%s)" % mac)
  
  for ip_technicolor in TECHNICOLOR_IPS:
    if (ip == ip_technicolor):
      logger.debug("Trovato possibile IP spurio di router Technicolor: %s" % ip)
      for mac_technicolor in TECHNICOLOR_MACS:
        if re.search(mac_technicolor, mac, re.I):
          logger.info("Trovato IP spurio di router Technicolor: %s [%s]" % (ip, mac))
          return True
      
  return False

def receive_arping(MACsrc):

  hwsrc = MACsrc

  IPtable = {}

  while True:

    received = pktman.pull(1)
    # pktman.clear()
    if (received['err_flag'] < 1):
      logger.debug("(%s) Numero di Host trovati: %d" % (received['err_str'], len(IPtable)))
      break

    elif (len(received['py_pcap_hdr']) >= 16 and len(received['py_pcap_data']) >= 42):

      pktHdr = received['py_pcap_hdr']

      pktSec, pktUsec, pktCaplen, pktLen = struct.unpack("LLII", pktHdr)

      # pktTimeStamp = float(pktSec) + (float(pktUsec) / 1000000)

      pktData = received['py_pcap_data']

      hwdst_eth, hwsrc_eth, proto = struct.unpack("!6s6sh", pktData[:14])

      if (hwdst_eth == hwsrc):

        arpPkt = pktData[14:]
        if struct.unpack('!H', arpPkt[6:8])[0] == ARP_REPLY:
          hwsrc_arp, psrc_arp, hwdst_arp, pdst_arp = struct.unpack('!6s4s6s4s', arpPkt[8:28])
          IPsrc_arp = socket.inet_ntoa(psrc_arp)
          IPdst_arp = socket.inet_ntoa(pdst_arp)
          if (IPsrc_arp not in IPtable):
            if (not _is_technicolor(IPsrc_arp, display_mac(hwsrc_arp))):
              IPtable[IPsrc_arp] = display_mac(hwsrc_arp)
              logger.info('Trovato Host %s con indirizzo fisico %s' % (IPsrc_arp, display_mac(hwsrc_arp)))
            
  return IPtable

def do_arping(dev, IPsrc, NETmask, realSubnet = True, timeout = 1, mac = None, threshold = 1):
  nHosts = 0

  if (mac):
    MACsrc = "".join(chr(int(macEL, 16)) for macEL in mac.split(':'))
  else:
    logger.warn("Richiesta esecuzione di arping senza la specifica del MAC address.")
    return 0
  MACdst = "\xFF"*6
  
  logger.debug("MAC_source = %s" % mac)
  IPsrc = socket.gethostbyname(IPsrc)
  IPnet = ipcalc.Network('%s/%d' % (IPsrc, NETmask))
  net = IPnet.network()
  bcast = IPnet.broadcast()

  pcap_filter = "rarp or arp dst host " + IPsrc

  pktman.debugmode(0)

  if dev == None:
    dev = IPsrc

  rec_init = pktman.initialize(dev, 1024000, 150, timeout*1000)
  
  if (rec_init['err_flag'] != 0):
    raise Exception (rec_init['err_str'])
  
  rec_init = pktman.setfilter(pcap_filter)
  logger.info("Inizializzato sniffer (%s, %s)" % (dev, pcap_filter))
  if (rec_init['err_flag'] != 0):
    raise Exception (rec_init['err_str'])
  else:
  
    if (platform.startswith('win')):
      subprocess.call('netsh interface ip delete arpcache', shell=True)
      sock = socket.socket(socket.AF_INET, socket.SOCK_RAW)
      sock.setblocking(True)
    else:
      sock = None
    
    lasting = 2 ** (32 - NETmask)
    index = 0

    for IPdst in IPnet:
      if ((IPdst.hex() == net.hex() or IPdst.hex() == bcast.hex()) and realSubnet):
        logger.info("Saltato ip %s" % IPdst)
      elif(IPdst.dq == IPsrc):
        logger.info("Salto il mio ip %s" % IPdst)
      else:
        IPdst = str(IPdst)
        # logger.debug('Arping host %s' % IPdst)
        send = Thread(target=send_arping, args=(IPsrc, IPdst, MACsrc, MACdst, sock))
        send.start()
        index += 1

      lasting -= 1

      if (index >= MAX or lasting <= 0):
        index = 0

        try:
          IPtable = receive_arping(MACsrc)
          hosts = "HOSTS: "
          for key in IPtable:
            hosts = hosts+"[%s|%s] " % (IPtable[key], key)
          logger.info(hosts)
          nHosts = len(IPtable) 
        except Exception as e:
          logger.warning("Errore durante la ricezione degli arping: %s" % e)

      if(nHosts > threshold):
        break

    logger.debug("Totale host: %d" % nHosts)
    pktman.close()
    if (platform.startswith('win')):
      sock.close()

  return nHosts

if __name__ == '__main__':

  s = socket.socket(socket.AF_INET)
  s.connect(('www.fub.it', 80))
  ip = s.getsockname()[0]
  s.close()
  mymac = 'F0:4D:A2:53:AD:AE'

  if ip != None:
    logger.debug('Inizio check degli host su %s (%s)' % (ip, mymac))
    print("Trovati: %d host" % do_arping(IPsrc=ip, NETmask=24, mac=mymac))

