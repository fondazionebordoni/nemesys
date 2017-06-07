# measure.py
# -*- coding: utf8 -*-

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

# import logging
# from xml.dom.minidom import parseString
from string import Template

import system_resource

XML_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<measure id="$measure_id" start="$start_time" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:noNamespaceSchemaLocation="measure.xsd">

<header>
$header
</header>
<body>
$test_results
</body>
</measure>'''

HEADER_TEMPLATE = '''
<server id="$server_id"/>
<client id="$client_id">
<mac>$mac_address</mac>
<ip>$ip_address</ip>
<os>$os</os>
<version>$version</version>
</client>
<time>
<start>$start_time</start>
<stop>$stop_time</stop>
</time>'''

TEST_RESULT_TEMPLATE = '''
<test type="$test_type">
<profiler>
$profiler
</profiler>
<value>
<done>$num_tests</done>
<time>$duration</time>
<bytes>
<byte type="nemesys">$bytes_nem</byte>
<byte type="other">$bytes_other</byte>
</bytes>
</value>
</test>'''

PROFILER_TEMPLATE = '''
<cpu>$cpu_load</cpu>
<ram>$ram_usage</ram>
<interfaces>
$interfaces
</interfaces>
<hosts>$num_hosts</hosts>
<traffic>$traffic_level</traffic>'''

INTERFACE_TEMPLATE = '''
<interface type="$if_type">$is_active</interface>'''


class Measure:
    def __init__(self, client, start, server, ip, os, mac, version=None):
        """
        Costruisce un oggetto Measure utilizzando i parametri ricevuti nella
        chiamata.
        Istanzia un oggetto XML in cui vengono salvati i test che costituiscono
        la misura. L'id della misura viene postposto all'id del client per generare
        l'id del file di misura XML.
        """

        self._client = client
        self._start = start
        self._stop = None
        self._server = server
        self._ip = ip
        self._os = os
        self._mac = mac
        self._version = version
        self._test_results = []

    def savetest(self, test):
        self._test_results.append(test)

    def savetime(self, start_time, stop_time):
        self._start = start_time
        self._stop = stop_time

    @property
    def id(self):
        return str(self._start.strftime('%Y%m%d%H%M%S'))

    @property
    def server(self):
        return self._server

    @property
    def client(self):
        return self._client

    def build_header(self):
        header_template = Template(HEADER_TEMPLATE)
        return header_template.substitute(server_id=self._server.id,
                                          client_id=self.client.id,
                                          mac_address=self._mac,
                                          ip_address=self._ip,
                                          os=self._os,
                                          version=self._version,
                                          start_time=self._start.isoformat(),
                                          stop_time=self._stop.isoformat())

    def build_interfaces(self, profiler_info):
        interfaces_string = ''
        interface_template = Template(INTERFACE_TEMPLATE)
        # <interface type="$if_type">$is_active</interface>

        for res in [system_resource.RES_WIFI, system_resource.RES_ETH]:
            try:
                status = profiler_info[res]
                if status != -1:
                    val = interface_template.safe_substitute(if_type=res.lower(), is_active=str(status == 1).lower())
                    interfaces_string = '{}{}'.format(interfaces_string, val)
            except AttributeError:
                pass
        return interfaces_string

    def build_test_string(self, test):
        profiler_info = test.profiler_info
        interfaces_string = self.build_interfaces(profiler_info)
        profiler_template = Template(PROFILER_TEMPLATE)
        test_template = Template(TEST_RESULT_TEMPLATE)
        profiler_string = profiler_template.safe_substitute(cpu_load=profiler_info[system_resource.RES_CPU],
                                                            ram_usage=profiler_info[system_resource.RES_RAM],
                                                            interfaces=interfaces_string,
                                                            num_hosts=profiler_info[system_resource.RES_HOSTS],
                                                            traffic_level=profiler_info[system_resource.RES_TRAFFIC])

        proof = test.proof

        return test_template.safe_substitute(test_type=proof.type,
                                             profiler=profiler_string,
                                             num_tests=test.n_tests_done,
                                             duration=proof.duration,
                                             bytes_nem=proof.bytes_nem,
                                             bytes_other=proof.bytes_tot - proof.bytes_nem)

    def __str__(self):
        header_string = self.build_header()
        tests_string = ''
        for test in self._test_results:
            test_string = self.build_test_string(test)
            tests_string = '{}{}'.format(tests_string, test_string)

        xml_template = Template(XML_TEMPLATE)
        measure_id = str(self._client.id) + str(self._start.strftime('%Y%m%d%H%M%S'))
        return xml_template.safe_substitute(measure_id=measure_id,
                                            start_time=self._start.isoformat(),
                                            header=header_string,
                                            test_results=tests_string)
