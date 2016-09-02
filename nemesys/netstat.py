# netstat.py
# -*- coding: utf-8 -*-

# Copyright (c) 2013-2016 Fondazione Ugo Bordoni.
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
import psutil


class NetstatException(Exception):
    '''
    Netstat specific exception
    '''

    def __init__(self, message):
        Exception.__init__(self, message)


class Netstat(object):

    def __init__(self, if_device):
        self.if_device = if_device

    def get_if_device(self):
        return self.if_device

    def get_rx_bytes(self):
        if not self.if_device:
            raise NetstatException("Nessun identificatore di device")
        counters_per_nic = psutil.net_io_counters(pernic=True)
        if self.if_device in counters_per_nic:
            rx_bytes = counters_per_nic[self.if_device].bytes_recv
            if rx_bytes is None:
                raise NetstatException("Ottenuto contatore vuoto "
                                       "per il device %d"
                                       % self.if_device)
        else:
            raise NetstatException("Contatore non trovato per il device %s"
                                   % self.if_device)
        return long(rx_bytes)

    def get_tx_bytes(self):
        if not self.if_device:
            raise NetstatException("Nessun identificatore di device")
        counters_per_nic = psutil.net_io_counters(pernic=True)
        if self.if_device in counters_per_nic:
            tx_bytes = counters_per_nic[self.if_device].bytes_sent
            if tx_bytes is None:
                raise NetstatException("Ottenuto contatore vuoto "
                                       "per il device %s"
                                       % str(self.if_device))
        else:
            raise NetstatException("Contatore non trovato per il device %s"
                                   % str(self.if_device))
        return long(tx_bytes)


if __name__ == '__main__':
    import iptools
    dev = iptools.get_dev()
    my_netstat = Netstat(dev)
    print "RX bytes", my_netstat.get_rx_bytes()
    print "TX bytes", my_netstat.get_tx_bytes()
