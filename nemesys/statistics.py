# statistics.py
# -*- coding: utf8 -*-

# Copyright (c) 2011 Fondazione Ugo Bordoni.
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

class Statistics:

  def __init__(self, packet_up_all = 0, packet_down_all = 0, packet_tot_all = 0, 
               payload_up_nem = 0, byte_up_all = 0, 
               payload_down_nem = 0, byte_down_all = 0,  
               packet_drop = 0):

    self._packet_up_all = packet_up_all
    self._packet_down_all = packet_down_all
    self._packet_tot_all = packet_tot_all

    self._payload_up_nem = payload_up_nem
    self._byte_up_all = byte_up_all
    
    self._payload_down_nem = payload_down_nem
    self._byte_down_all = byte_down_all
    
    self._packet_drop = packet_drop

  @property
  def byte_up_nem(self):
    return self._byte_up_nem

  @property
  def byte_up_all(self):
    return self._byte_up_all

  @property
  def byte_down_nem(self):
    return self._byte_down_nem

  @property
  def byte_down_all(self):
    return self._byte_down_all

  @property
  def packet_drop(self):
    return self._packet_drop

#   def __str__(self):
#     return '''\
# [PACKET] | packet_drop: %d | tot_all: %d | tot_all_net: %d | tot_nem: %d | tot_nem_net: %d | tot_oth: %d | tot_oth_net: %d | down_all: %d | down_all_net: %d | down_nem: %d | down_nem_net: %d | down_oth: %d | down_oth_net: %d | up_all: %d | up_all_net: %d | up_nem: %d | up_nem_net: %d | up_oth: %d | up_oth_net: %d | \
# [BYTE] | tot_all: %d | tot_all_net: %d | tot_nem: %d | tot_nem_net: %d | tot_oth: %d | tot_oth_net: %d | down_all: %d | down_all_net: %d | down_nem: %d | down_nem_net: %d | down_oth: %d | down_oth_net: %d | up_all: %d | up_all_net: %d | up_nem: %d | up_nem_net: %d | up_oth: %d | up_oth_net: %d | \
# [PAYLOAD] | tot_all: %d | tot_all_net: %d | tot_nem: %d | tot_nem_net: %d | tot_oth: %d | tot_oth_net: %d | down_all: %d | down_all_net: %d | down_nem: %d | down_nem_net: %d | down_oth: %d | down_oth_net: %d | up_all: %d | up_all_net: %d | up_nem: %d | up_nem_net: %d | up_oth: %d | up_oth_net: %d | \
# ''' % (\
#       self.packet_drop, self.packet_tot_all, self.packet_tot_all_net, self.packet_tot_nem, self.packet_tot_nem_net, self.packet_tot_oth, self.packet_tot_oth_net, \
#       self.packet_down_all, self. packet_down_all_net, self.packet_down_nem, self.packet_down_nem_net, self.packet_down_oth, self.packet_down_oth_net, \
#       self.packet_up_all, self.packet_up_all_net, self.packet_up_nem, self.packet_up_nem_net, self.packet_up_oth, self.packet_up_oth_net, \
#       self.byte_tot_all, self.byte_tot_all_net, self.byte_tot_nem, self.byte_tot_nem_net, self.byte_tot_oth, self.byte_tot_oth_net, \
#       self.byte_down_all, self. byte_down_all_net, self.byte_down_nem, self.byte_down_nem_net, self.byte_down_oth, self.byte_down_oth_net, \
#       self.byte_up_all, self.byte_up_all_net, self.byte_up_nem, self.byte_up_nem_net, self.byte_up_oth, self.byte_up_oth_net, \
#       self.payload_tot_all, self.payload_tot_all_net, self.payload_tot_nem, self.payload_tot_nem_net, self.payload_tot_oth, self.payload_tot_oth_net, \
#       self.payload_down_all, self. payload_down_all_net, self.payload_down_nem, self.payload_down_nem_net, self.payload_down_oth, self.payload_down_oth_net, \
#       self.payload_up_all, self.payload_up_all_net, self.payload_up_nem, self.payload_up_nem_net, self.payload_up_oth, self.payload_up_oth_net \
#       )

if __name__ == '__main__':
  s = Statistics()
  print s
