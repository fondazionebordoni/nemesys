# task.py
# -*- coding: utf-8 -*-

# Copyright (c) 2010-2016 Fondazione Ugo Bordoni.
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
from collections import OrderedDict
from datetime import datetime

import xmltodict

from common.nem_exceptions import TaskException
from common.server import Server

logger = logging.getLogger(__name__)

DATE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class Task(object):
    def __init__(self, start=None, server=None, upload=1,
                 download=1, ping=4, nicmp=1, delay=1,
                 now=False, message=None, is_wait=False):
        self._start = start
        self._server = server
        self._upload = upload
        self._download = download
        self._ping = ping
        self._nicmp = nicmp
        self._delay = delay
        self._now = bool(now)
        self._message = message
        self._is_wait = is_wait

    @property
    def is_wait(self):
        return self._is_wait

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
        if self.is_wait:
            return 'delay: %s; message: %s' % (self.delay, self.message)
        if self.server is not None:
            ip = self.server.ip
        else:
            ip = None
        return "start: {0}; " \
               "serverip: {1}; " \
               "upload: {2}; " \
               "download: {3}; " \
               "ping {4}; " \
               "delay: {5}; " \
               "now {6}; " \
               "message: {7}" \
               "".format(self.start,
                         ip,
                         self.upload,
                         self.download,
                         self.ping,
                         self.delay,
                         self.now,
                         self.message)


def new_wait_task(wait_secs, message=None):
    return Task(now=True, delay=wait_secs, message=message, is_wait=True)


def xml2task(xml):
    try:
        xml_dict = xmltodict.parse(xml)
    except Exception as e:
        logger.error('Impossibile fare parsing del task: %s', xml)
        raise TaskException("Impossibile fare il "
                            "parsing del task ricevuto: %s" % e)

    if not xml_dict or 'calendar' not in xml_dict:
        raise TaskException("Ricevuto task invalido")
    if not xml_dict['calendar'] or 'task' not in xml_dict['calendar']:
        raise TaskException('Ricevuto task vuoto: %s', xml)
    task_dict = xml_dict['calendar']['task']
    message = task_dict.get('message') or ""
    if '@wait' in task_dict and task_dict['@wait'].lower() == 'true':
        # wait task, just get delay and message
        if 'delay' in task_dict:
            delay = task_dict['delay']
        else:
            logger.warning("Task di attesa, ma manca il tempo di attesa, "
                        "uso il default 5 minuti")
            delay = 5 * 60
        return new_wait_task(int(delay), message)
    nup = (task_dict.get('nup') or
           task_dict.get('nhttpup') or
           task_dict.get('nftpup') or
           0)
    if isinstance(nup, OrderedDict):
        nup = nup.get('#text')
    ndown = (task_dict.get('ndown') or
             task_dict.get('nhttpdown') or
             task_dict.get('nftpdown') or
             0)
    if isinstance(ndown, OrderedDict):
        ndown = ndown.get('#text')
    nping = task_dict.get('nping')
    if isinstance(nping, OrderedDict):
        nping = nping.get('#text')
    start = task_dict.get('start')
    now = False
    if isinstance(start, OrderedDict):
        if '@now' in start:
            now = ((start.get('@now') == '1') or
                   (start.get('@now').lower() == 'true'))
        start = start.get('#text')
    # Date
    try:
        starttime = datetime.strptime(start, DATE_TIME_FORMAT)
    except ValueError:
        logger.debug('XML: %s', start)
        raise TaskException('Le informazioni orarie per la programmazione delle misure sono errate.')
    # TODO: scartare se id mancante?
    srvid = task_dict.get('srvid') or "id-server-mancante"
    if 'srvip' not in task_dict:
        raise TaskException('Nel task manca l\'indirizzo IP  del server di misura')
    else:
        srvip = task_dict.get('srvip')
    srvname = task_dict.get('srvname')
    server = Server(uuid=srvid, ip=srvip, name=srvname)
    return Task(start=starttime,
                server=server,
                upload=int(nup),
                download=int(ndown),
                ping=int(nping),
                now=now,
                message=message)
