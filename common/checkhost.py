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

from common import arp


MAX_PING_HOSTS = 128
TECHNICOLOR_MAC_REGEX = ('^F..94.E3|^F..91.14|^F..52.8D|^E..B9.E5|^E..88.5D|^D..B2.C4|^D..8A.91|'
                         '^D..5A.00|^C..EA.1D|^C..35.40|^C..27.95|^C..03.FA|^B..C2.87|^B..C2.3A|'
                         '^B..2A.0E|^A..B1.E9|^A..91.B1|^A..7C.6A|^9..97.26|^8..F7.C7|^8..C6.AB|'
                         '^8..B2.34|^8..29.94|^8..04.FF|^7..7E.2D|^7..5A.9E|^6..3D.26|^5..A6.5C|'
                         '^5..98.35|^5..23.8C|^5..09.59|^4..F7.C0|^4..32.C8|^4..00.33|^3..9A.77|'
                         '^3..91.8F|^3..17.E1|^2..BE.9B|^1..C2.5A|^1..B7.F8|^1..98.7D|^1..62.D0|'
                         '^1..13.31|^0..95.2A|^0..90.D0|^0..90.64|^0..80.EE|^0..76.FF|^0..26.44|'
                         '^0..26.24|^0..24.D1|^0..24.17|^0..1F.9F|^0..1E.69|^0..1D.68|^0..19.DF|'
                         '^0..18.F6|^0..18.9B|^0..14.7F|^0..11.E3|^0..10.95|^0..0E.80|^0..0E.50|'
                         '^0..07.C3|^0..02.27')

logger = logging.getLogger(__name__)


def filter_out_technicolor(ip_table):
    """
    This check is needed to ignore routers that respond to ARP and ping with two
    addresses, typically this happens with routers from Technicolor.
    If the MAC address is the same, except for the first byte and last, then it
    is considered Technicolor and ignored
    """
    n_hosts = len(ip_table)
    if n_hosts < 2:
        return n_hosts

    temp_table = []
    for ip_address in ip_table:
        mac_address = ip_table[ip_address]
        if re.search(TECHNICOLOR_MAC_REGEX, mac_address, re.I):
            logger.warn('Trovato possibile router Technicolor: [%s, %s]', ip_address, mac_address)
            temp_table.append(mac_address[3:14])
        else:
            temp_table.append(mac_address)
    unique_addresses = set(temp_table)
    return len(unique_addresses)


class PingSender(threading.Thread):
    def __init__(self, dest_ip):
        threading.Thread.__init__(self)
        self.ip = dest_ip
        self.status = 0
        self.elapsed = 0

    def run(self):
        try:
            self.elapsed = ping.do_one('%s' % self.ip, 1)
            if self.elapsed > 0:
                self.status = 1
        except Exception:
            self.status = 0


def count_hosts(ip_address, netmask, bandwidth_up, bandwidth_down, provider='fub001', use_arp=False):
    if ((provider == "fst001") or (provider.startswith('fub0'))) and (not bool(re.search('^192\.168\.', ip_address))):
        real_subnet = False
        if bandwidth_up == bandwidth_down and not bool(re.search('^10\.', ip_address)):
            # profilo fibra
            netmask_to_use = 29
            logger.debug('Sospetto profilo Fastweb in Fibra. Modificata sottorete in %d', netmask_to_use)
        else:
            # profilo ADSL
            netmask_to_use = 30
            logger.debug('Sospetto profilo Fastweb ADSL o Fibra con indirizzo 10.*. Modificata sottorete in %d',
                         netmask_to_use)

        logger.info('Indirizzo: %s/%d; Realsubnet: %s', ip_address, netmask, real_subnet)
        n_host = _count_net_hosts(ip_address, netmask_to_use, real_subnet, use_arp)
        # Only return if found host, otherwise continue with regular netmask
        if n_host > 0:
            return n_host

    real_subnet = True
    netmask_to_use = netmask
    logger.info('Indirizzo: %s/%d; Realsubnet: %s', ip_address, netmask, real_subnet)
    n_host = _count_net_hosts(ip_address, netmask_to_use, real_subnet, use_arp)
    return n_host


def _count_net_hosts(dev_ip_address, netmask, real_subnet=True, use_arp=False):
    """
    Ritorna il numero di host che rispondono al ping nella sottorete ipAddress/net_mask.
    Di default effettua i ping dei soli host appartenenti alla sottorete indicata (escludendo il
    primo e ultimo ip).
    """
    n_hosts = 0
    ip_network = ipcalc.Network('%s/%d' % (dev_ip_address, netmask))
    net = ip_network.network()
    bcast = ip_network.broadcast()

    ip_destinations = []
    for ip_address in ip_network:
        if (ip_address.hex() == net.hex() or ip_address.hex() == bcast.hex()) and real_subnet:
            logger.debug('Saltato ip %s', ip_address)
        elif ip_address.dq == dev_ip_address:
            logger.debug('Salto il mio ip %s', dev_ip_address)
        else:
            ip_destinations.append(ip_address)

    if use_arp:
        try:
            # ip_table = arp.do_arping(dev_ip_address, netmask, real_subnet)
            ip_table = arp.do_arping(ip_destinations)
        except Exception as e:
            logger.warn('Errore durante la ricerca host con ARP: %s', e)
            return 0
        hosts = 'HOSTS: '
        for key in ip_table:
            hosts += '[{}|{}] '.format(ip_table[key], key)
        logger.info(hosts)
        # Check for router that responds with 2 IP addresses
        # with slightly different Ethernet addresses
        n_hosts = filter_out_technicolor(ip_table)
    else:
        ping_threads = []
        i = 0
        for ip_address in ip_destinations:
            i += 1
            try:
                ping_thread = PingSender(ip_address)
                ping_thread.start()
                ping_threads.append(ping_thread)
            except Exception as e:
                logger.warn('Errore durante la ricerca host con PING: %s', e)
                break
            if i == MAX_PING_HOSTS:
                break

        for ping_thread in ping_threads:
            ping_thread.join()

            if ping_thread.status:
                logger.info('Trovato host: %s (in %.2f ms)', ping_thread.ip, ping_thread.elapsed * 1000)
                n_hosts += 1

    if not real_subnet:
        n_hosts += 1

    return n_hosts


if __name__ == '__main__':
    import log_conf
    import iptools
    log_conf.init_log()
    ip = iptools.getipaddr('www.fub.it', 80)

    print "PING:", count_hosts(ip, 24, 200, 2000, 'fub001', False)
    print "ARP:", count_hosts(ip, 24, 200, 2000, 'fub001', True)
#     print count_hosts(ip, 24, 2000, 2000, 'fst001', 4, 1)
