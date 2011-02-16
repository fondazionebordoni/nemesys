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
MAX = 128

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
      logger.debug('Errore durante il ping dell\'host %s: %s' % (self.ip, e))
      self.status = 0
      pass
    

def countHosts(ipAddress, netMask, bandwidthup, bandwidthdown, provider=None, threshold=4):
  realSubnet = True
  if(provider == "fst001" and not bool(re.search('^192\.168\.', ipAddress))):
    realSubnet = False
    if bandwidthup == bandwidthdown and not bool(re.search('^10\.', ipAddress)):
      #profilo fibra
      netMask = 29
      logger.debug("Profilo Fastweb in Fibra. Modificata sottorete in %d" % netMask)
    else:
      #profilo ADSL
      netMask = 30
      logger.debug("Profilo Fastweb ADSL o Fibra con indirizzo 10.*. Modificata sottorete in %d" % netMask)

  # Controllo che non siano indirizzi pubblici, in quel caso ritorno 1, effettuo la misura
  elif not bool(re.search('^10\.|^172\.(1[6-9]|2[0-9]|3[01])\.|^192\.168\.', ipAddress)):
    return 1

  logger.info("Indirizzo: %s/%d; Realsubnet: %s; Threshold: %d" % (ipAddress, netMask, realSubnet, threshold))

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

  i = 0
  lasting = 2 ** (32 - netMask)
  for ip in ips:
    lasting -= 1
    if ((ip.hex() == net.hex() or ip.hex() == bcast.hex()) and realSubnet):
      logger.debug("Saltato ip %s" % ip)
    else:
      logger.debug('Ping host %s' % ip)
      current = sendit(ip)
      pinglist.append(current)
      current.start()
      i += 1

    if (i > MAX or lasting <= 0):
      i = 0
      for pingle in pinglist:
        pingle.join()
      
        if(pingle.status):
          logger.debug("Trovato host: %s (in %.2f ms)" % (pingle.ip, pingle.elapsed * 1000))
          nHosts = nHosts + 1

      pinglist = []
        
    if(nHosts > threshold):
      break
        
  return nHosts		


if __name__ == '__main__':
  n = countHosts("10.10.0.100", 24, 2000, 2000, 'fst001', 255)
  print '%d (%d)' % (n, 0)

  n = countHosts("192.168.1.1", 24, 2000, 2000, "fst001")
  print '%d (%d)' % (n, 0)

  #n = countHosts("192.168.208.250", 24, 200, 2000, "fst001")
  #print '%d (%d)' % (n, 0)
  
