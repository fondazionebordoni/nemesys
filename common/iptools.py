# iptools.py
# -*- coding: utf-8 -*-
# Copyright (c) 2016 Fondazione Ugo Bordoni.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Some useful functions for IP and Ethernet"""

import logging
import psutil
import re
import socket

from common.nem_exceptions import NemesysException
from common import nem_exceptions

logger = logging.getLogger(__name__)


def getipaddr(host='finaluser.agcom244.fub.it', port=443):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((host, port))
        ipaddr = s.getsockname()[0]
    except socket.gaierror:
        raise NemesysException("Impossibile ottenere indirizzo IP "
                               "della scheda di rete attiva")
    return ipaddr


def get_if_ipaddress(ifname):
    try:
        for if_info in psutil.net_if_addrs()[ifname]:
            if if_info.family == socket.AF_INET:
                return if_info.address
    except KeyError:
        pass
    raise NemesysException("Impossibile ottenere l'indirizzo IP "
                           "dell'interfaccia %s" % ifname)


def get_if_speed(ifname):
    try:
        if_stats = psutil.net_if_stats()[ifname]
        return if_stats.speed
    except KeyError:
        pass
    raise NemesysException("Impossibile ottenere la velocita' "
                           "dell'interfaccia %s" % ifname)


def get_mac_address(dev=None):
    if not dev:
        ifname = get_dev()
    else:
        ifname = dev
    try:
        for if_info in psutil.net_if_addrs()[ifname]:
            if if_info.family == psutil.AF_LINK:
                return if_info.address
    except KeyError:
        pass
    raise NemesysException("Impossibile ottenere l'indirizzo MAC "
                           "dell'interfaccia %s" % ifname)


def get_dev(host='finaluser.agcom244.fub.it', port=443, ip=None):
    """
    restituisce scheda attiva (guid della scheda su Windows
    """
    if not ip:
        local_ip_address = getipaddr(host, port)
    else:
        local_ip_address = ip

    try:
        net_if_addrs = psutil.net_if_addrs()
    except Exception as e:
        raise nem_exceptions.SysmonitorException('Impossibile ottenere il dettaglio '
                                                 'dell\'interfaccia di rete: %s' % e,
                                                 nem_exceptions.UNKDEV)
    for (if_name, if_info) in list(net_if_addrs.items()):
        for addr_type in if_info:
            if addr_type.family == socket.AF_INET:
                if addr_type.address == local_ip_address:
                    return if_name
    raise nem_exceptions.SysmonitorException('Impossibile ottenere il dettaglio '
                                             'dell\'interfaccia di rete',
                                             nem_exceptions.UNKDEV)


def get_network_mask(ip):
    """
        Returns netmask for the given IP
        as a number, e.g. '24' as set on
        the network device.

        If ip is None or empty, gets the
        IP address of the active interface
        and uses that.

        In case no netmask is found,
        it returns a default
        netmask of 24
    """
    default_netmask = '255.255.255.0'
    if not ip:
        local_ip_address = getipaddr()
    else:
        local_ip_address = ip

    for (_, if_info) in list(psutil.net_if_addrs().items()):
        for addr_type in if_info:
            if addr_type.family == socket.AF_INET and addr_type.address == local_ip_address:
                try:
                    return _mask_conversion(addr_type.netmask)
                except (ValueError, TypeError, AttributeError):
                    break
    logger.warn("Impossibile calcolare il netmask, uso il default")
    return _mask_conversion(default_netmask)


def is_public_ip(ip):
    return bool(re.search('^10\.|^172\.(1[6-9]|2[0-9]|3[01])\.|^192\.168\.', ip)) is False


def is_loopback_ip(ip):
    return ip.startswith('127')


def is_ip_address(ip):

    try:
        socket.inet_aton(ip)
        parts = ip.split('.')
        if len(parts) != 4:
            return False
    except Exception:
        return False

    return True


def _mask_conversion(netmask):
    return sum([bin(int(x)).count('1') for x in netmask.split('.')])
