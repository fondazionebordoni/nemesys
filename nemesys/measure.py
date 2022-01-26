# measure.py
# -*- coding: utf-8 -*-

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

import platform
from datetime import datetime
from xml.dom.minidom import parseString

from common import ntptime


class Measure(object):
    def __init__(self, measure_id, server, client, version=None,
                 start=datetime.fromtimestamp(ntptime.timestamp()).isoformat()):
        """
        Costruisce un oggetto Measure utilizzando i parametri ricevuti nella
        chiamata.
        Istanzia un oggetto XML in cui vengono salvati i test che costituiscono
        la misura. L'id della misura viene postposto all'id del client
        per generare l'id del file di misura XML.
        """
        try:
            self._os = '%s %s' % (platform.system(), platform.release())
        except Exception:
            self._os = 'n.d.'
        self._id = measure_id
        self._server = server
        self._client = client
        self._version = version
        self._start = start
        self._xml = self.getxml()

    def getxml(self):
        start = ("<measure xmlns:xsi="
                 "'http://www.w3.org/2001/XMLSchema-instance' "
                 "xsi:noNamespaceSchemaLocation='measure.xsd'/>")
        xml = parseString(start)
        measure = xml.getElementsByTagName('measure')[0]
        measure.setAttribute('id', str(self._client.id) + str(self._id))
        measure.setAttribute('start', str(self._start))

        # TODO: Aggiungere l'invio del mac address

        # Header
        # --------------------------------------------------------------------------
        header = xml.createElement('header')

        # Operator
        operator = xml.createElement('operator')
        operator.setAttribute('id', str(self._client.isp.id))
        header.appendChild(operator)

        # Client
        client = xml.createElement('client')
        client.setAttribute('id', str(self._client.id))

        profile = xml.createElement('profile')
        profile.setAttribute('id', str(self._client.profile.id))

        upload = xml.createElement('upload')
        xml_node = xml.createTextNode(str(self._client.profile.upload))
        upload.appendChild(xml_node)
        profile.appendChild(upload)

        download = xml.createElement('download')
        xml_node = xml.createTextNode(str(self._client.profile.download))
        download.appendChild(xml_node)
        profile.appendChild(download)

        client.appendChild(profile)

        geocode = xml.createElement('geocode')
        geocode.appendChild(xml.createTextNode(str(self._client.geocode)))
        client.appendChild(geocode)

        geocode = xml.createElement('so')
        geocode.appendChild(xml.createTextNode(str(self._os)))
        client.appendChild(geocode)

        geocode = xml.createElement('version')
        geocode.appendChild(xml.createTextNode(str(self._version)))
        client.appendChild(geocode)

        header.appendChild(client)

        # Server
        server = xml.createElement('server')
        server.setAttribute('id', str(self._server.id))
        header.appendChild(server)

        measure.appendChild(header)

        # Body
        # --------------------------------------------------------------------------
        measure.appendChild(xml.createElement('body'))
        return xml

    def savetest(self, proof):
        """
        Salva l'oggetto Test ricevuto nel file XML interno.
        """
        node = self.test2node(proof)
        body = self._xml.getElementsByTagName('body')[0]
        body.appendChild(node)

    def add_proofs(self, proofs):
        for proof in proofs:
            self.savetest(proof)

    def test2node(self, proof):
        xml = self._xml

        t = xml.createElement('test')
        t.setAttribute('type', str(proof.type))

        time = xml.createElement('time')

        start = xml.createElement('start')
        start.appendChild(xml.createTextNode(str(proof.start.isoformat())))
        time.appendChild(start)

        end = xml.createElement('end')
        date_string = str(datetime.fromtimestamp(ntptime.timestamp()).isoformat())
        end.appendChild(xml.createTextNode(date_string))
        time.appendChild(end)

        t.appendChild(time)

        value = xml.createElement('value')
        value.appendChild(xml.createTextNode(str(proof.duration)))
        t.appendChild(value)

        bytes_element = xml.createElement('byte')
        bytes_element.appendChild(xml.createTextNode(str(proof.bytes_tot)))
        t.appendChild(bytes_element)

        error = proof.errorcode
        if error is not None:
            errorcode = xml.createElement('errcode')
            errorcode.appendChild(xml.createTextNode(str(error)))
            t.appendChild(errorcode)

        return t

    @property
    def id(self):
        return self._id

    @property
    def server(self):
        return self._server

    @property
    def client(self):
        return self._client

    def __str__(self):
        return self._xml.toxml()
