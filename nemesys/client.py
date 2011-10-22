# client.py
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

from isp import Isp
from profile import Profile

class Client:
  
  # TODO Spostare il certificato dall'ISP al Client 

  def __init__(self, id, profile, isp, geocode, username='anonymous', password='anonymous@'):
    self._id = id
    self._profile = profile
    self._isp = isp
    self._geocode = geocode
    self._username = username
    self._password = password

  @property
  def id(self):
    return self._id

  @property
  def profile(self):
    return self._profile

  @property
  def isp(self):
    return self._isp

  @property
  def geocode(self):
    return self._geocode

  @property
  def username(self):
    return self._username

  @property
  def password(self):
    return self._password

  def __str__(self):
    return 'id: %s; profile: %s; isp: %s; geocode: %s' % (self.id, self.profile, self.isp, self.geocode)

if __name__ == '__main__':
  c = Client('fub0000000001', Profile('fub00001', 512, 512), Isp('fub000', 'fub000.pem'), '41.843646,12.485726')
  print c
