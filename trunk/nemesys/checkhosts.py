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

import ipcalc
import ping
import re
from logger import logging

logger = logging.getLogger()

def countHosts(ipAddress, netMask, bandwidthup, bandwidthdown, provider=None, threshold=4):
  realSubnet=True
  if(provider=="fst001" and not bool(re.search('^192\.', ipAddress))):
    realSubnet=False
    if bandwidthup==bandwidthdown:
      #profilo fibra
      netMask=29
      logger.debug("Profilo Fastweb in fibra. Modificata sottorete in %d" %netMask)
    else:
      #profilo ADSL
      netMask=30
      logger.debug("Profilo Fastweb ADSL. Modificata sottorete in %d" %netMask)
  logger.debug("%s / %d, %s, %d" %(ipAddress, netMask, realSubnet, threshold))
  n_host=_countNetHosts(ipAddress, netMask, realSubnet, threshold)
  return n_host

def _countNetHosts(ipAddress, netMask, realSubnet=True, threshold=4):
  '''
  Ritorna il numero di host che rispondono al ping nella sottorete ipAddress/net_mask.
  Di default effettua i ping dei soli host appartenenti alla sottorete indicata (escludendo il 
  primo e ultimo ip).
  '''
  nHosts=0  
  ips=ipcalc.Network('%s/%d' %(ipAddress,netMask))
  net=ips.network()
  bcast=ips.broadcast()

  for ip in ips:
    try:
      if ((ip.hex()==net.hex() or ip.hex()==bcast.hex()) and realSubnet):
        logger.debug("saltato ip %s" %ip)
        continue
      else:
        elapsed=ping.do_one('%s' %ip, 1)
        if elapsed>0:
    			nHosts=nHosts+1

        if nHosts > threshold:
          break    
    except Exception as e:
		  logger.debug('Errore durante il ping del seguente host %s: %s' %(ip, e))
			
  return nHosts		

if __name__ == '__main__':
  n = countHosts("151.100.4.1", 20, 2000, 2000, "fst001")
  print '%d (%d)' % (n, 0)

  n = countHosts("192.168.208.100", 26, 2000, 2000, "fst001")
  print '%d (%d)' % (n, 0)

  n = countHosts("192.168.208.250", 24, 200, 2000, "fst001")
  print '%d (%d)' % (n, 0)
  


	
	
	

