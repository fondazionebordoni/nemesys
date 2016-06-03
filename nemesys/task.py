# task.py
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

import logging

from server import Server


# BANDS = [128, 256, 384, 400, 512, 640, 704, 768, 832, 1000, 1200, 1250, 1280, 1500, 1600, 1750, 2000, 2250, 2500, 2750, 3000, 3250, 3500, 4000, 4096, 4500, 5000, 5500, 6000, 6122, 6500, 7000, 7168, 7500, 8000, 8500, 8192, 9000, 9500, 10000, 11000, 12000, 13000, 14000, 15000, 16000, 17000, 18000, 19000, 20000, 20480, 22000, 24000, 26000, 28000, 30000, 32000, 34000, 36000, 38000, 40000]
logger = logging.getLogger(__name__)

class Task(object):

    def __init__(self, task_id, start, server, upload=1,
                 download=1, ping=4, nicmp=1, delay=1, 
                 now=False, message=None):
        self._id = task_id
        self._start = start
        self._server = server
        self._upload = upload
        self._download = download
        self._ping = ping
        self._nicmp = nicmp
        self._delay = delay
        self._now = now
        self._message = message

    @property
    def id(self):
        return self._id

    @property
    def start(self):
        return self._start

    @property
    def server(self):
        return self._server

    @property
    def download(self):
        return self._download

    @property
    def upload(self):
        return self._upload

    @property
    def ping(self):
        return self._ping

    @property
    def nicmp(self):
        return self._nicmp

    @property
    def delay(self):
        return self._delay

    @property
    def now(self):
        return self._now

    @property
    def message(self):
        return self._message

    def __str__(self):
        return 'id: %s; start: %s; serverip: %s; upload: %d; download: %d; ping %d; ncimp: %d; delay: %d; now %d; message: %s' % \
            (self.id, self.start, self.server.ip, self.upload, self.download, self.ping, self.nicmp, self.delay, self.now, self.message)

if __name__ == '__main__':
    import log_conf
    log_conf.init_log()
    s = Server('s1', '127.0.0.1')
    p = Task(0, '2010-01-01 10:01:00', s, 'r.raw', 'upload/r.raw')
    print p
