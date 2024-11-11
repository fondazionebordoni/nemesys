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


from common.host import Host


class Server(Host):
    def __init__(self, uuid, ip, name=None, location=None):
        Host.__init__(self, ip=ip, name=name)
        self.uuid = uuid
        self.location = location

    def __str__(self):
        return f"uuid: {self.uuid}; ip: {self.ip}; name: {self.name}; location: {self.location}"


if __name__ == "__main__":
    s = Server("namexrm", "192.168.1.1", "Namex server")
    print(s)
    s = Server(id="namexrm", ip="192.168.1.1")
    print(s)
    s = Server("namexrm", "192.168.1.1")
    print(s)
