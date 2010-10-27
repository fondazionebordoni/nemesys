# profile.py
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

class Profile:

  def __init__(self, id, upload, download):
    self._id = id
    self._upload = upload
    self._download = download

  @property
  def id(self):
    return self._id

  @property
  def upload(self):
    return self._upload

  @property
  def download(self):
    return self._download

  def __str__(self):
    return 'id: %s; up: %d; down: %d' % (self.id, self.upload, self.download)

if __name__ == '__main__':
  p = Profile('2mb1mb', 2048, 1024)
  print p
