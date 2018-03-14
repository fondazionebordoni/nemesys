# sysmonitor.py
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import socket
from collections import OrderedDict

import psutil

from common import iptools

IF_TYPE_ETHERNET = 'Ethernet 802.3'
WIFI_WORDS = ['wireless', 'wifi', 'wi-fi', 'senzafili', 'wlan', 'fili']


class Device(object):
    def __init__(self, name):
        self._name = name
        self._ipaddr = 'Unknown'
        self._netmask = 'Unknown'
        self._macaddr = 'Unknown'
        self._speed = 'Unknown'
        self._duplex = 'Unknown'
        self._type_string = 'Unknown'
        self._is_active = False
        self._is_enabled = False

    def __str__(self, *args, **kwargs):
        d = self.dict()
        s = ''
        for k in d:
            s += "%s : %s\n" % (k, d[k])
        return s

    def dict(self):
        return OrderedDict([('Name', self._name),
                            ('IP', self._ipaddr),
                            ('Mask', self._netmask),
                            ('MAC', self._macaddr),
                            ('Type', self._type_string),
                            ('Speed', self._speed),
                            ('Duplex', self._duplex),
                            ('isEnabled', self._is_enabled),
                            ('isActive', self._is_active)
                            ])

    @property
    def name(self):
        return self._name

    def set_ipaddr(self, ipaddr):
        self._ipaddr = ipaddr

    @property
    def ipaddr(self):
        return self._ipaddr

    def set_netmask(self, netmask):
        self._netmask = netmask

    @property
    def netmask(self):
        return self._netmask

    def set_macaddr(self, macaddr):
        self._macaddr = macaddr

    @property
    def macaddr(self):
        return self._macaddr

    def set_active(self, is_active):
        self._is_active = is_active

    @property
    def is_active(self):
        return self._is_active

    def set_enabled(self, is_enabled):
        self._is_enabled = is_enabled

    @property
    def is_enabled(self):
        return self._is_enabled

    def set_type(self, type_string):
        self._type_string = type_string

    @property
    def type(self):
        return self._type_string

    def set_speed(self, speed):
        self._speed = speed

    @property
    def speed(self):
        return self._speed

    def set_duplex(self, duplex):
        self._duplex = duplex

    @property
    def duplex(self):
        return self._duplex


def cpu_load():
    return psutil.cpu_percent(0.5)


def total_memory():
    return psutil.virtual_memory().total


def percentage_ram_usage():
    mem_info = psutil.virtual_memory()
    try:
        percentage = mem_info.percent
    except AttributeError:
        percentage = float(mem_info.total - mem_info.available) / float(mem_info.total) * 100.0
    return int(percentage)


def is_wireless_active():
    for (if_name, if_info) in psutil.net_if_stats().items():
        try:
            if if_info.isup:
                for wifi_word in WIFI_WORDS:
                    if wifi_word in str(if_name).lower():
                        return True
        except AttributeError:
            pass


def get_all_devices():
    active_ipaddr = iptools.getipaddr()
    devices = []
    for (if_name, if_addrs) in psutil.net_if_addrs().items():
        dev = Device(if_name)
        try:
            if (if_name.startswith('eth') or if_name.startswith('en') or
                    ('(LAN)' in if_name)):
                dev.set_type(IF_TYPE_ETHERNET)
            for if_addr in if_addrs:
                if if_addr.family == socket.AF_INET:
                    ip_addr = if_addr.address
                    dev.set_ipaddr(ip_addr)
                    if ip_addr == active_ipaddr:
                        dev.set_active(True)
                    dev.set_netmask(if_addr.netmask)
                elif if_addr.family == psutil.AF_LINK:
                    dev.set_macaddr(if_addr.address)
        except Exception as e:
            dev.set_type(str(e))
        devices.append(dev)

    net_if_stats = psutil.net_if_stats()
    for dev in devices:
        stats = net_if_stats.get(dev.name)
        if stats:
            dev.set_speed(stats.speed)
            dev.set_enabled(stats.isup)
            dev.set_duplex(stats.duplex)

    return devices
