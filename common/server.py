# server.py
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

from time import sleep

from common import ping
from common.host import Host


class Server(Host):
    def __init__(self, server_id, ip, name=None, location=None):
        Host.__init__(self, ip=ip, name=name)
        self._id = server_id
        self._location = location

    @property
    def id(self):
        return self._id

    @property
    def location(self):
        return self._location

    def __str__(self):
        return 'id: %s; ip: %s; name: %s; location: %s' % (self.id, self.ip, self.name, self.location)


def get_server(callback, servers={Server('NAMEX', '193.104.137.133', 'NAP di Roma'),
                                  Server('MIX', '193.104.137.4', 'NAP di Milano')}):
    max_reps = 4
    best = {'start': None,
            'delay': 8000,
            'server': None
            }
    rtt = {}

    for server in servers:
        rtt[server.name] = best['delay']

    for _ in range(max_reps):
        sleep(1.0)
        for server in servers:
            try:
                delay = ping.do_one("%s" % server.ip, 1) * 1000
                if delay < rtt[server.name]:
                    rtt[server.name] = delay
                if delay < best['delay']:
                    best['delay'] = delay
                    best['server'] = server
            except Exception:
                pass

    if best['server'] is not None:
        for server in servers:
            if rtt[server.name] != 8000:
                callback("Distanza dal %s: %.1f ms" % (server.name, rtt[server.name]))
            else:
                callback("Distanza dal %s: Timeout" % server.name)
    else:
        raise Exception("Impossibile eseguire i test poiche' i server risultano irragiungibili da questa linea. "
                        "Contattare l'helpdesk del progetto Misurainternet per avere informazioni "
                        "sulla risoluzione del problema.")
    return best['server']


if __name__ == '__main__':
    s = Server('namexrm', '192.168.1.1', 'Namex server')
    print(s)
    s = Server(server_id='namexrm', ip='192.168.1.1')
    print(s)
    s = Server('namexrm', '192.168.1.1')
    print(s)
