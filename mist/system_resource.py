"""
Created on 15/apr/2016

@author: ewedlund
"""

RES_OS = 'OS'
RES_CPU = 'CPU'
RES_RAM = 'RAM'
RES_ETH = 'Ethernet'
RES_WIFI = 'Wireless'
# RES_DEV = 'Device'
# RES_MAC = 'MAC'
# RES_IP = 'IP'
# RES_MASK = 'MASK'
RES_HOSTS = 'Hosts'
RES_TRAFFIC = 'Traffic'


class SystemResource(object):
    def __init__(self, res=None, status=None, value=None, info=None):
        self._res = res
        self._status = status
        self._value = value
        self._info = info

    def __str__(self):
        s = ""
        s += "Resource: %s\n" % self._res
        s += "Status: %s\n" % self._status
        s += "Value: %s\n" % self._value
        s += "Info: %s\n" % self._info
        return s

    @property
    def res(self):
        return self._res

    @property
    def status(self):
        return self._status

    @property
    def value(self):
        return self._value

    @property
    def info(self):
        return self._info
