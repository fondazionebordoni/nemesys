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


from collections import OrderedDict
import psutil
import socket

import iptools


IF_TYPE_ETHERNET = 'Ethernet 802.3'
LINUX_RESOURCE_PATH = '/sys/class/net/'
WIFI_WORDS = ['wireless', 'wifi', 'wi-fi', 'senzafili', 'wlan', 'fili']
ERROR_NET_IF = 'Impossibile ottenere informazioni sulle interfacce di rete'


class Device(object):

    def __init__(self, name):
        self._name = name
        self._ipaddr = 'Unknown'
        self._netmask = 'Unknown'
        self._macaddr = 'Unknown'
        self._type_string = 'Unknown'
        self._is_active = False
        self._is_enabled = False

    def __str__(self, *args, **kwargs):
        d = self.dict()
        s = ''
        for key in d:
            s += "%s : %s\n" % (key, d[key])
        return s

    def dict(self):
        return OrderedDict([('Name', self._name),
                            ('IP', self._ipaddr),
                            ('Mask', self._netmask),
                            ('MAC', self._macaddr),
                            ('Type', self._type_string),
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


class Profiler(object):

    def __init__(self):
        self.ipaddr = ""

    def cpuLoad(self):
        return psutil.cpu_percent(0.5)

    def total_memory(self):
        return psutil.virtual_memory().total

    def percentage_ram_usage(self):
        meminfo = psutil.virtual_memory()
        total = meminfo.total
        used = meminfo.used
        try:
            buffers = meminfo.buffers
        except AttributeError:
            buffers = 0
        try:
            cached = meminfo.cached
        except AttributeError:
            cached = 0
        real_used = used - buffers - cached
        return int(float(real_used) / float(total) * 100.0)

    def is_wireless_active(self):
        for (if_name, if_info) in psutil.net_if_stats().items():
            if if_info.isup:
                for wifi_word in WIFI_WORDS:
                    if wifi_word in str(if_name).lower():
                        return True

    def get_all_devices(self):
        self.ipaddr = iptools.getipaddr()
        devices = []
        for (if_name, if_addrs) in psutil.net_if_addrs().items():
            device = Device(if_name)
            try:
                if (if_name.startswith('eth') or if_name.startswith('en') or
                        ('(LAN)' in if_name)):
                    device.set_type(IF_TYPE_ETHERNET)
                for if_addr in if_addrs:
                    if if_addr.family == socket.AF_INET:
                        ip_addr = if_addr.address
                        device.set_ipaddr(ip_addr)
                        if ip_addr == self.ipaddr:
                            device.set_active(True)
                        device.set_netmask(if_addr.netmask)
                    elif if_addr.family == psutil.AF_LINK:
                        device.set_macaddr(if_addr.address)
            except Exception as e:
                pass
            devices.append(device)

        net_if_stats = psutil.net_if_stats()
        for device in devices:
            stats = net_if_stats.get(device.name)
            if stats:
                device.set_speed(stats.speed)
                device.set_enabled(stats.isup)
                device.set_duplex(stats.duplex)

        return devices


if __name__ == '__main__':
    profiler = Profiler()
    all_devices = profiler.get_all_devices()
    for device in all_devices:
        print("============================================")
        device_dict = device.dict()
        for key in device_dict:
            print("| %s : %s" % (key, device_dict[key]))
    print("============================================")
