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
import urlparse

from common import httputils, task
from common.nem_exceptions import TaskException

logger = logging.getLogger(__name__)


class Scheduler(object):
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
        url = urlparse.urlparse(self._url)
        certificate = self._client.isp.certificate
        request_string = '{path}?clientid={client_id}&version={version}&confid={conf_id}'.format(
            path=url.path,
            client_id=self._client.id,
            version=self._version,
            conf_id=self._md5conf)
        if server:
            request_string = '{str}&server={server}'.format(str=request_string, server=server.ip)
        connection = None
        try:
            connection = httputils.get_verified_connection(url=url,
                                                           certificate=certificate,
                                                           timeout=self._httptimeout)
            connection.request('GET', request_string)
            data = connection.getresponse().read()
        except Exception as e:
            logger.error('Impossibile scaricare lo scheduling: %s', e)
            raise TaskException('Download del task fallito')
        finally:
            if connection:
                try:
                    connection.close()
                except Exception:
                    pass
        return task.xml2task(data)
