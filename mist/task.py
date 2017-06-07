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
from collections import OrderedDict
from datetime import datetime

import xmltodict

from common import httputils
from common.server import Server

logger = logging.getLogger(__name__)
DATE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class TaskException(Exception):
    pass


class Task(object):
    def __init__(self, task_id, start, server, ping=4, nicmp=1, delay=1, now=False, message=None, http_download=4,
                 http_upload=4):
        self._id = task_id
        self._start = start
        self._server = server
        self._ftpup_bytes = 0
        self._http_upload = http_upload
        self._http_download = http_download
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
    def http_download(self):
        return self._http_download

    @property
    def http_upload(self):
        return self._http_upload

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

    @property
    def ftpup_bytes(self):
        return self._ftpup_bytes

    def set_ftpup_bytes(self, num_bytes):
        self._ftpup_bytes = num_bytes

    @property
    def dict(self):
        task = OrderedDict([
            ('Task id', self.id),
            ('Start time', self.start),
            ('Server id', self.server.id),
            ('Server name', self.server.name),
            ('Server ip', self.server.ip),
            ('Server location', self.server.location),
            ('Ping number', self.ping),
            ('Ping repeat', self.nicmp),
            ('Ping delay', self.delay),
            ('Download HTTP number', self.http_download),
            ('Upload HTTP number', self.http_upload),
            ('Now parameter', self.now),
            ('Message', self.message)
        ])
        return task


def xml2task(xml):
    try:
        xml_dict = xmltodict.parse(xml)
    except Exception as e:
        raise TaskException("Impossibile fare il "
                            "parsing del task ricevuto: %s" % e)

    if (not xml_dict or
        'calendar' not in xml_dict or
            not xml_dict['calendar'] or
            'task' not in xml_dict['calendar']):
        raise TaskException("Ricevuto task vuoto")
    task_dict = xml_dict['calendar']['task']
    message = task_dict.get('message') or ""
    # if '@wait' in task_dict and task_dict['@wait'].lower() == 'true':
    #     '''wait task, just get delay and message'''
    #     if 'delay' in task_dict:
    #         delay = task_dict['delay']
    #     else:
    #         logger.warn("Task di attesa, ma manca il tempo di attesa, "
    #                     "uso il default 5 minuti")
    #         delay = 5*60
    #     return new_wait_task(int(delay), message)
    # else:
    task_id = task_dict.get('id') or 0
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
        logger.debug('XML: %s' % start)
        raise Exception("Le informazioni orarie "
                        "per la programmazione delle misure sono errate.")
    # TODO: scartare se id mancante?
    srvid = task_dict.get('srvid') or "id-server-mancante"
    if 'srvip' not in task_dict:
        raise TaskException("Nel task manca l'indirizzo IP "
                            "del server di misura")
    else:
        srvip = task_dict.get('srvip')
    srvname = task_dict.get('srvname')
    server = Server(srvid, srvip, srvname)
    # def __init__(self, task_id, start, server, ping=4, nicmp=1, delay=1, now=False, message=None, http_download=4,
    #              http_upload=4):
    return Task(task_id,
                starttime,
                server,
                int(nup),
                int(ndown),
                int(nping),
                now,
                message)


def download_task(url, certificate, client_id, version, md5conf, timeout, server=None):
    """Scarica il prossimo task dallo scheduler"""

    try:
        connection = httputils.get_verified_connection(url=url, certificate=certificate, timeout=timeout)
        if server is not None:
            connection.request('GET', '%s?clientid=%s&version=%s&confid=%s&server=%s' % (
                url.path, client_id, version, md5conf, server.ip))
        else:
            connection.request('GET', '%s?clientid=%s&version=%s&confid=%s' % (url.path, client_id, version, md5conf))

        data = connection.getresponse().read()
        task = xml2task(data)

        if task is None:
            logger.info('Lo scheduler ha inviato un task vuoto.')
        else:
            logger.info("--------[ TASK ]--------")
            for key, val in task.dict.items():
                logger.info("%s : %s" % (key, val))
            logger.info("------------------------")

    except Exception as e:
        logger.error('Impossibile scaricare lo scheduling. Errore: %s.' % e, exc_info=True)
        return None

    return task

    # def get_n_test(self, t_type):
    #     if t_type == test_type.PING:
    #         test_todo = self.ping
    #     elif test_type.is_http_down(t_type):
    #         test_todo = self.http_download
    #     elif test_type.is_http_up(t_type):
    #         test_todo = self.http_upload
    #     else:
    #         logger.warn("Tipo di test da effettuare non definito: %s" % test_type.get_string_type(t_type))
    #         test_todo = 0
    #     return test_todo

    def __str__(self):
        return (
            'id: {0}; start: {1}; serverip: {2}; ping {3}; ncimp: {4}; delay: {4}; now {5}; message: {6};'
            ' http_download: {7}; http_upload: {8}'.format(
                self.id, self.start, self.server.ip, self.ping, self.nicmp, self.delay, self.now, self.message,
                self.http_download, self.http_upload))
