# getconf.py
# -*- coding: utf-8 -*-
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
"""
Created on 13/giu/2016

@author: ewedlund
"""
import logging
import urllib.parse

from common import httputils, task
from common.nem_exceptions import TaskException

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Handles the download of tasks
    """

    def __init__(self, scheduler_url, client, md5conf, version, timeout):
        self._url = scheduler_url
        self._client = client
        self._md5conf = md5conf
        self._version = version
        self._httptimeout = timeout

    def download_task(self, server=None):
        """
        Download task from scheduler, returns a Task
        """
        url = urllib.parse.urlparse(self._url)
        certificate = self._client.isp.certificate
        request_string = f'{url.path}?clientid={self._client.id}&version={self._version}&confid={self._md5conf}'

        if server:
            request_string += f'&server={server.ip}'

        try:
            connection = httputils.get_verified_connection(
                url=url,
                certificate=certificate,
                timeout=self._httptimeout
            )
            connection.request('GET', request_string)
            response = connection.getresponse()
            data = response.read()
        except Exception as e:
            logger.error("Errore nella richiesta HTTP al scheduler: %s", e)
            raise TaskException("Errore durante la connessione al server per ottenere un task") from e
        finally:
            if connection:
                connection.close()

        return task.xml2task(data)
