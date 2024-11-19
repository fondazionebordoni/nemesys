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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

BW_1M = 1 * 10**6
BW_3M = 3 * 10**6
BW_5M = 5 * 10**6
BW_25M = 25 * 10**6
BW_50M = 50 * 10**6
BW_100M = 100 * 10**6
BW_200M = 200 * 10**6
BW_300M = 300 * 10**6
BW_500M = 500 * 10**6
BW_1000M = 1 * 10**9
BW_2000M = 2 * 10**9
BW_2500M = 2.5 * 10**9
BW_5000M = 5 * 10**9


class Profile(object):
    def __init__(self, profile_id, upload, download, upload_min=None, download_min=None):
        self._id = profile_id
        self._upload = upload
        self._download = download
        self._upload_min = upload_min
        self._download_min = download_min

    @property
    def id(self):
        return self._id

    @property
    def upload(self):
        return self._upload

    @property
    def download(self):
        return self._download

    @property
    def upload_min(self):
        return self._upload_min

    @property
    def download_min(self):
        return self._download_min

    def __str__(self):
        return "id: %s; up: %d; down: %d; up_min: %d; down_min: %d" % (
            self.id,
            self.upload,
            self.download,
            self.upload_min,
            self.download_min,
        )


if __name__ == "__main__":
    p = Profile("2mb1mb", 2048, 1024, 512, 256)
    print(p)
