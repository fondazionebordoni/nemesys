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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import ipcalc
import logging
import ping
import re
import threading

from arp import do_arping


MAX_PING_HOSTS = 128

logger = logging.getLogger(__name__)

class sendit(threading.Thread):
    def __init__ (self, ip):
        threading.Thread.__init__(self)
        self.ip = ip
        self.status = 0
        self.elapsed = 0

    def run(self):
        try:
            self.elapsed = ping.do_one("%s" % self.ip, 1)
            if self.elapsed > 0:
                self.status = 1
        except Exception:
            self.status = 0
            pass

def countHosts(ipAddress, netMask, bandwidthup, bandwidthdown, provider = None, arping = 0):

    if(provider == "fst001" and not bool(re.search('^192\.168\.', ipAddress))):
        realSubnet = False
        if bandwidthup == bandwidthdown and not bool(re.search('^10\.', ipAddress)):
            #profilo fibra
            netmask_to_use = 29
            logger.debug("Sospetto profilo Fastweb in Fibra. Modificata sottorete in %d" % netmask_to_use)
        else:
            #profilo ADSL
            netmask_to_use = 30
            logger.debug("Sospetto profilo Fastweb ADSL o Fibra con indirizzo 10.*. Modificata sottorete in %d" % netmask_to_use)

        logger.info("Indirizzo: %s/%d; Realsubnet: %s" % (ipAddress, netMask, realSubnet))
        n_host = _countNetHosts(ipAddress, netmask_to_use, realSubnet, arping)
        if n_host > 0:
            return n_host
        
    realSubnet = True
    netmask_to_use = netMask
    logger.info("Indirizzo: %s/%d; Realsubnet: %s" % (ipAddress, netMask, realSubnet))
    n_host = _countNetHosts(ipAddress, netmask_to_use, realSubnet, arping)
    return n_host


def _countNetHosts(ipAddress, netMask, realSubnet = True, arping = 0):
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

    if (arping == 1):
        try:
            nHosts = do_arping(ipAddress, netMask, realSubnet)
        except Exception as e:
            logger.debug('Errore durante l\'arping: %s' % e)

    else:
        i = 0
        for ip in ips:
            if ((ip.hex() == net.hex() or ip.hex() == bcast.hex()) and realSubnet):
                logger.debug("Saltato ip %s" % ip)
            elif(ip.dq == ipAddress):
                logger.debug("Salto il mio ip %s" % ipAddress)
            else:
                i += 1
                ping_thread = sendit(ip)
                pinglist.append(ping_thread)
                ping_thread.start()
            if i == MAX_PING_HOSTS:
                break

        for ping_thread in pinglist:
            ping_thread.join()

            if(ping_thread.status):
                logger.debug("Trovato host: %s (in %.2f ms)" % (ping_thread.ip, ping_thread.elapsed * 1000))
                nHosts = nHosts + 1

    if not realSubnet:
        nHosts += 1
    
    return nHosts


if __name__ == '__main__':
    import log_conf
    import iptools
    log_conf.init_log()
    ip = iptools.getipaddr('www.fub.it', 80)

    print countHosts(ip, 24, 200, 2000, 'fub001', 4, 0)
#     print countHosts(ip, 24, 2000, 2000, 'fst001', 4, 1)
