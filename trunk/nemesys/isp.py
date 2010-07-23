# isp.py
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

class Isp:

  def __init__(self, id, certificate=None):
    self._id = id
    if (certificate == None):
      self._certificate = id + '.pem'
    else:
      self._certificate = certificate

  @property
  def id(self):
    return self._id

  @property
  def certificate(self):
    return self._certificate

  def __str__(self):
    return 'id: %s; certificate: %s' % (self.id, self.certificate)

if __name__ == '__main__':
  i = Isp('etl005')
  print i

