# checkhosts.py
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

from logger import logging
from threading import Thread
import ipcalc
import ping
import re
import time

logger = logging.getLogger()

class sendit(Thread):
  def __init__ (self, ip):
     Thread.__init__(self)
     self.ip = ip
     self.status = 0
     self.elapsed = 0

  def run(self):
    try:
     self.elapsed = ping.do_one("%s" % self.ip, 1)
     if (self.elapsed > 0):  
       self.status = 1
    except Exception as e:
      self.status = 0
      pass
    

def countHosts(ipAddress, netMask, bandwidthup, bandwidthdown, provider=None, threshold=4):
  realSubnet = True
  if(provider == "fst001" and not bool(re.search('^192\.168\.', ipAddress))):
    realSubnet = False
    if bandwidthup == bandwidthdown and not bool(re.search('^10\.', ipAddress)):
      #profilo fibra
      netMask = 29
      logger.debug("Profilo Fastweb in fibra. Modificata sottorete in %d" % netMask)
    else:
      #profilo ADSL
      netMask = 30
      logger.debug("Profilo Fastweb ADSL. Modificata sottorete in %d" % netMask)

  # Controllo che non siano indirizzi pubblici, in quel caso ritorno 1, effettuo la misura
  elif not bool(re.search('^10\.|^172\.(1[6-9]|2[0-9]|3[01])\.|^192\.168\.', ipAddress)):
		return 1

  logger.info("%s / %d, %s, %d" % (ipAddress, netMask, realSubnet, threshold))

  n_host = _countNetHosts(ipAddress, netMask, realSubnet, threshold)
  return n_host

def _countNetHosts(ipAddress, netMask, realSubnet=True, threshold=4):
  '''
  Ritorna il numero di host che rispondono al ping nella sottorete ipAddress/net_mask.
  Di default effettua i ping dei soli host appartenenti alla sottorete indicata (escludendo il 
  primo e ultimo ip).
  '''
  nHosts = 0  
  ips = ipcalc.Network('%s/%d' % (ipAddress, netMask))
  net = ips.network()
  bcast = ips.broadcast()
  pinglist = []
  logger.debug('mask: %s; rete: %s; broadcast: %s' % (netMask, net, bcast))
  for ip in ips:
    if ((ip.hex() == net.hex() or ip.hex() == bcast.hex()) and realSubnet):
      logger.debug("saltato ip %s" % ip)
      continue
    else:
      current = sendit(ip)
      pinglist.append(current)
      current.start()
	
  for pingle in pinglist:
    pingle.join()
  
    if(pingle.status):
      logger.debug("Trovato host: %s (in %.2f ms)" % (pingle.ip, pingle.elapsed*1000))
      nHosts = nHosts + 1
    if(nHosts >= threshold):
      break
      
  return nHosts		


if __name__ == '__main__':
	n = countHosts("192.168.208.0", 24, 2000, 2000, 'tlc003', 255)
	print '%d (%d)' % (n, 0)

	n = countHosts("192.168.1.1", 24, 2000, 2000, "fst001")
	print '%d (%d)' % (n, 0)

	#n = countHosts("192.168.208.250", 24, 200, 2000, "fst001")
	#print '%d (%d)' % (n, 0)
  