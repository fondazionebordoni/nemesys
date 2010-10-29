# host.py
# -*- coding: utf8 -*-

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

class Host:

   def __init__(self, ip, name=None):
     self._ip = ip
     self._name = name
   
   @property
   def ip(self):
     return self._ip

   @property
   def name(self):
     return self._name

if __name__ == '__main__':
   h1 = Host('192.168.131.1', 'h1')
   h2 = Host(name='h2', ip="192.168.21.2")
   h3 = Host(ip='192.168.140.21')
   print(h1.name, h1.ip)
   print(h2.name, h2.ip)
   print(h3.name, h3.ip)

