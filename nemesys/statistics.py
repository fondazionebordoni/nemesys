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

  def __init__(self, byte_up_nem = 0, byte_up_all = 0, 
               byte_down_nem = 0, byte_down_all = 0):

    self._byte_up_nem = byte_up_nem
    self._byte_up_all = byte_up_all
    
    self._byte_down_nem = byte_down_nem
    self._byte_down_all = byte_down_all
    

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

  def __str__(self):
    return 'Byte up Nemesys: %d | Byte up all: %d | Byte down Nemesys: %d | Byte down all: %d | ' % (\
      self.byte_up_nem, self.byte_up_all, self.byte_down_nem, self.byte_down_all)

if __name__ == '__main__':
  s = Statistics()
  print s
