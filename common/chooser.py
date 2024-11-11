# chooser.py
# -*- coding: utf-8 -*-
# Copyright (c) 2024 Fondazione Ugo Bordoni.
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
from time import sleep

import requests

from common import ping
from common.server import Server
from common.nem_exceptions import NO_AVAILABLE_SERVERS, NemesysException

logger = logging.getLogger(__name__)


class Chooser(object):
    """
    Handles the download of tasks
    """

    def __init__(self, url, client, version, timeout=5):
        self._url = url
        self._client = client
        self._version = version
        self._httptimeout = timeout

    def get_servers(self):
        params = {"clientid": self._client.id, "version": self._version}
        response = requests.get(self._url, params=params, timeout=self._httptimeout)
        servers = []

        try:
            data = response.json()
            for server in data:
                servers.append(Server(uuid=server["uuid"], ip=server["ip"], name=server["fqdn"]))
        except Exception as e:
            logger.warning("Failed to decode servers list from %s: %s", data, e)

        return servers

    def choose_server(self, callback):
        max_attempts = 4
        best_server = {"start_time": None, "delay": float("inf"), "server": None}
        round_trip_times = {}

        servers = self.get_servers()
        if not servers:
            return None

        for server in servers:
            round_trip_times[server.name] = best_server["delay"]

        for _ in range(max_attempts):
            sleep(0.5)
            for server in servers:
                try:
                    delay = ping.do_one(server.ip, 1) * 1000
                    round_trip_times[server.name] = min(delay, round_trip_times[server.name])
                    if delay < best_server["delay"]:
                        best_server["delay"] = delay
                        best_server["server"] = server
                except Exception:
                    pass

        if best_server["server"] is not None:
            for server in servers:
                if round_trip_times[server.name] != float("inf"):
                    callback(f"Round-trip time to {server.name}: {round_trip_times[server.name]:.1f} ms")
                else:
                    callback(f"Round-trip time to {server.name}: Timeout")
        else:
            error_message = "Failed to execute tests. Servers are unreachable from this line. Contact the Misurainternet project helpdesk for information on resolving the issue."
            raise NemesysException(error_message, NO_AVAILABLE_SERVERS)

        logger.info("Selected server: %s", best_server["server"])
        return best_server["server"]
