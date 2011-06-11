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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from server import Server
from logger import logging

BANDS = [128, 256, 384, 400, 512, 640, 704, 768, 832, 1000, 1200, 1250, 1280, 1500, 1600, 1750, 2000, 2250, 2500, 2750, 3000, 3250, 3500, 4000, 4096, 4500, 5000, 5500, 6000, 6122, 6500, 7000, 7168, 7500, 8000, 8500, 8192, 9000, 9500, 10000, 11000, 12000, 13000, 14000, 15000, 16000, 17000, 18000, 19000, 20000, 20480, 22000, 24000, 26000, 28000, 30000, 32000, 34000, 36000, 38000, 40000]
logger = logging.getLogger()

class Task:

  def __init__(self, id, start, server, ftpdownpath, ftpuppath, upload=100,
               download=100, multiplier=5, ping=100, nicmp=4, delay=1, now=False, message=None):
    self._id = id
    self._start = start
    self._server = server
    self._ftpdownpath = ftpdownpath
    self._ftpuppath = ftpuppath
    self._upload = upload
    self._download = download
    self._multiplier = multiplier
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
  def ftpdownpath(self):
    return self._ftpdownpath

  @property
  def ftpuppath(self):
    return self._ftpuppath

  @property
  def download(self):
    return self._download

  @property
  def multiplier(self):
    return self._multiplier

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

  def update_ftpdownpath(self, bandwidth):
    '''
    Aggiorna il path del file da scaricare in modo da scaricare un file di
    dimensioni le più vicine possibili alla banda specificata.
    '''
    logger.debug('Aggiornamento path per la banda in download')
    try:
      BANDS.sort(reverse=True)
      for band in BANDS:
        if (band <= bandwidth):
          ind = self.ftpdownpath.rfind('/')
          self.ftpdownpath = "%s/%d.rnd" % (self.ftpdownpath[0:ind], band)
          logger.debug("Aggiornato percorso del file da scaricare: %s" % self.ftpdownpath)
          break 
    except Exception as e:
      logger.warning("Errore durante la modifica del percorso del file di download da scaricare. %s" % e)

  def __str__(self):
    return 'id: %s; start: %s; serverip: %s; ftpdownpath: %s; ftpuppath: %s; upload: %d; download: %d; multiplier %d; ping %d; ncimp: %d; delay: %d; now %d; message: %s' % \
      (self.id, self.start, self.server.ip, self.ftpdownpath, self.ftpuppath, self.upload, self.download, self.multiplier, self.ping, self.nicmp, self.delay, self.now, self.message)

if __name__ == '__main__':
  s = Server('s1', '127.0.0.1')
  p = Task(0, '2010-01-01 10:01:00', s, 'r.raw', 'upload/r.raw')
  print p

