# getconf.py
# -*- coding: utf-8 -*-
from nemesys.nem_exceptions import TaskException

# Copyright (c) 2016 Fondazione Ugo Bordoni.
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
'''
Created on 13/giu/2016

@author: ewedlund
'''
import logging
import urlparse

import httputils
import task


logger = logging.getLogger(__name__)


class Scheduler(object):
    '''
    Handles the download of tasks
    '''

    def __init__(self, scheduler_url, client, md5conf, version, timeout):
        self._url = scheduler_url
        self._client = client
        self._md5conf = md5conf
        self._version = version
        self._httptimeout = timeout

    def download_task(self):
        '''
        Download task from scheduler, returns a Task
        '''
        url = urlparse.urlparse(self._url)
        certificate = self._client.isp.certificate
        connection = httputils.getverifiedconnection(url=url,
                                                     certificate=certificate,
                                                     timeout=self._httptimeout)

        try:
            connection.request('GET', '%s?clientid=%s&version=%s&confid=%s'
                               % (url.path,
                                  self._client.id,
                                  self._version,
                                  self._md5conf))
            data = connection.getresponse().read()
        except Exception as e:
            logger.error('Impossibile scaricare lo scheduling. Errore: %s.'
                         % e)
            raise Exception('Impossibile dialogare con '
                            'lo scheduler delle misure')
        try:
            t = task.xml2task(data)
            return t
        except TaskException as e:
            logger.error("Impossibile interpretare il task ricevuto: %s", (e))
            logger.error("Dati del task: %s", (data))
            raise Exception('Il task ricevuto dallo scheduler'
                            'non e\' in un formato valido')
