# pcapper.py
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

from contabyte import Contabyte
from random import randint
from statistics import Statistics
from threading import Thread, Event
import logging
import sniffer
import socket
import sys
import time

logger = logging.getLogger()

if __name__ == '__main__':

  online = 0

  ip = '192.168.62.10'
  nap = '192.168.140.22'

  if len(sys.argv) != 4:
    print 'Usage: dumper.py <pcap filename> <pkt start> <pkt stop>'
    sys.exit(1)

  filename = sys.argv[1]
  print ("\nFILE: %s" % filename)

  pkt_start = int(sys.argv[2])
  pkt_stop = int(sys.argv[3])
  print ("PACKET: %i ---> %i\n" % (pkt_start,pkt_stop))

  analyzer = Contabyte(ip, nap)

  status = 0
  pcap_buff = 16 * 1024 * 1024

  sniffer.debugmode(0)

  status = sniffer.initialize(ip, pcap_buff, 150, 1, 1, online, filename, pkt_start, pkt_stop)

  if (status['err_flag'] != 0):
    logger.error('Errore inizializzazione dello Sniffer: %s' % str(r['err_str']))

  status = 1

  while(status > 0):
    mypkt = sniffer.start(1)
    sniffer.clear()
    if (mypkt != None):
      status = mypkt['err_flag']
      if (status == 1):
        analyzer.analyze(mypkt['py_pcap_hdr'], mypkt['py_pcap_data'])

  stats = analyzer.statistics
  print stats
  print sniffer.getstat()
  
  print ("\nDOWNLOAD\tPacket\t\tPayload\t\tWireByte")
  print ("Nemesys\t\t%i\t\t%i\t\t%i" % (stats.packet_down_nem_net,stats.payload_down_nem_net,stats.byte_down_nem_net))
  print ("Other\t\t%i\t\t%i\t\t%i" % (stats.packet_down_oth_net,stats.payload_down_oth_net,stats.byte_down_oth_net))
  print ("All\t\t%i\t\t%i\t\t%i" % (stats.packet_down_all_net,stats.payload_down_all_net,stats.byte_down_all_net))
  
  print ("\nUPLOAD\t\tPacket\t\tPayload\t\tWireByte")
  print ("Nemesys\t\t%i\t\t%i\t\t%i" % (stats.packet_up_nem_net,stats.payload_up_nem_net,stats.byte_up_nem_net))
  print ("Other\t\t%i\t\t%i\t\t%i" % (stats.packet_up_oth_net,stats.payload_up_oth_net,stats.byte_up_oth_net))
  print ("All\t\t%i\t\t%i\t\t%i" % (stats.packet_up_all_net,stats.payload_up_all_net,stats.byte_up_all_net))
  
  sniffer.stop()



