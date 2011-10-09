# fakefile.py
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

import random

class Fakefile:

  def __init__(self, bytes):
    self._bytes = bytes
  
  def read(self, bufsize):
  
    if self._bytes <= 0:
      return None    
  
    data = '%s' % random.getrandbits(min(bufsize, self._bytes))
    self._bytes -= len(data)
    return data