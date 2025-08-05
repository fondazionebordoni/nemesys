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


class Task:
    def __init__(self, start=None, server=None, upload=1, download=1, ping=4,
                 nicmp=1, delay=1, now=False, message=None, is_wait=False):
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
            return f'delay: {self.delay}; message: {self.message}'
        ip = self.server.ip if self.server else None
        return (f"start: {self.start}; serverip: {ip}; upload: {self.upload}; "
                f"download: {self.download}; ping: {self.ping}; delay: {self.delay}; "
                f"now: {self.now}; message: {self.message}")


def new_wait_task(wait_secs, message=None):
    return Task(now=True, delay=wait_secs, message=message, is_wait=True)


def xml2task(xml):
    try:
        if isinstance(xml, bytes):
            xml = xml.decode('utf-8')
        xml_dict = xmltodict.parse(xml)
    except Exception as e:
        logger.error('Impossibile fare parsing del task: %s', xml)
        raise TaskException(f"Impossibile fare il parsing del task ricevuto: {e}")

    if not xml_dict or 'calendar' not in xml_dict:
        raise TaskException("Ricevuto task invalido")
    if not xml_dict['calendar'] or 'task' not in xml_dict['calendar']:
        raise TaskException(f"Ricevuto task vuoto: {xml}")

    task_dict = xml_dict['calendar']['task']
    message = task_dict.get('message') or ""

    if task_dict.get('@wait', '').lower() == 'true':
        delay = task_dict.get('delay', 300)
        return new_wait_task(int(delay), message)

    nup = task_dict.get('nup') or task_dict.get('nhttpup') or task_dict.get('nftpup') or 0
    if isinstance(nup, OrderedDict):
        nup = nup.get('#text')
    ndown = task_dict.get('ndown') or task_dict.get('nhttpdown') or task_dict.get('nftpdown') or 0
    if isinstance(ndown, OrderedDict):
        ndown = ndown.get('#text')
    nping = task_dict.get('nping')
    if isinstance(nping, OrderedDict):
        nping = nping.get('#text')

    start = task_dict.get('start')
    now = False
    if isinstance(start, OrderedDict):
        now = start.get('@now') in ['1', 'true', 'True']
        start = start.get('#text')

    try:
        starttime = datetime.strptime(start, DATE_TIME_FORMAT)
    except Exception:
        logger.debug('XML start time value: %s', start)
        raise TaskException('Le informazioni orarie per la programmazione delle misure sono errate.')

    srvid = task_dict.get('srvid') or "id-server-mancante"
    srvip = task_dict.get('srvip')
    if not srvip:
        raise TaskException("Nel task manca l'indirizzo IP del server di misura")
    srvname = task_dict.get('srvname')

    server = Server(srvid, srvip, srvname)

    return Task(start=starttime,
                server=server,
                upload=int(nup),
                download=int(ndown),
                ping=int(nping),
                now=now,
                message=message)
