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
from xml.dom.minidom import parseString


# import xml.etree as et

# ## {{{ http://code.activestate.com/recipes/577882/ (r2)
# def data2xml(d, name='data'):
# r = et.Element(name)
# return et.tostring(buildxml(r, d))

# def buildxml(r, d):
# if isinstance(d, dict):
# for k, v in d.iteritems():
# s = et.SubElement(r, k)
# buildxml(s, v)
# elif isinstance(d, tuple) or isinstance(d, list):
# for v in d:
# s = et.SubElement(r, 'i')
# buildxml(s, v)
# elif isinstance(d, basestring):
# r.text = d
# else:
# r.text = str(d)
# return r

# print data2xml({'a':[1,2,('c',{'d':'e'})],'f':'g'})
# # <data><a><i>1</i><i>2</i><i><i>c</i><i><d>e</d></i></i></a><f>g</f></data>
# ## end of http://code.activestate.com/recipes/577882/ }}}

# logger = logging.getLogger(__name__)

class Measure:
    def __init__(self, client, start, server, ip, os, mac, version=None):
        '''
        Costruisce un oggetto Measure utilizzando i parametri ricevuti nella
        chiamata.
        Istanzia un oggetto XML in cui vengono salvati i test che costituiscono
        la misura. L'id della misura viene postposto all'id del client per generare
        l'id del file di misura XML.
        '''

        self._client = client
        self._start = start
        self._server = server
        self._ip = ip
        self._os = os
        self._mac = mac
        self._version = version

        begin = '''<measure xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="measure.xsd"/>'''
        self._xml = parseString(begin)
        self._root = None

        self.header2xml()

    def dict2node(self, node, parent=None):
        xml = self._xml
        if (parent is None):
            parent = xml

        tagName = node.get('ID', {}).get('tag', '')
        tagAttr = node.get('ID', {}).get('attr', {})

        tag = xml.createElement(tagName)

        elements = parent.getElementsByTagName(tagName)
        if (len(elements) > 0):
            for elem in elements:
                if elem.parentNode.nodeName == parent.nodeName:
                    if (len(elements) == 1) and (elem.attributes.length == 0):
                        tag = elem
                    elif elem.attributes.length == len(tagAttr):
                        match = 0
                        for attribute in tagAttr:
                            # logger.debug("Check if [ %s = %s ]" % (elem.getAttribute(attribute),str(tagAttr[attribute])))
                            if elem.getAttribute(attribute) == str(tagAttr[attribute]):
                                print('Attribute: {} value: {}'.format(attribute, str(tagAttr[attribute])))
                                match += 1
                        if (match > 0) and (match == len(tagAttr)):
                            tag = elem
                            print('Removing tag: {}'.format(tag))
                            for child in tag.childNodes:
                                tag.removeChild(child)
                            break

        attr = node.get('attr', {})
        for attribute in attr:
            tag.setAttribute(attribute, str(attr[attribute]))

        val = node.get('val', [])
        for value in val:
            if isinstance(value, dict):
                newNode = self.dict2node(value, tag)
                tag.appendChild(newNode)
            else:
                tag.appendChild(xml.createTextNode(str(value)))

        return tag

    def header2xml(self):

        measureID = str(self._client.id) + str(self._start.strftime('%Y%m%d%H%M%S'))
        measureStart = self._start.isoformat()
        measureAttr = {'id': measureID, 'start': measureStart}
        measureTagAttr = {'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                          'xsi:noNamespaceSchemaLocation': 'measure.xsd'}

        header = {'ID': {'tag': 'header'}}
        body = {'ID': {'tag': 'body'}}

        measure = {'ID': {'tag': 'measure', 'attr': measureTagAttr}, 'attr': measureAttr, 'val': [header, body]}

        self._root = self.dict2node(measure)

        ## node = {'ID':{'tag':'', 'attr':{}}, 'attr':{}, 'val':[]} ##
        mac = {'ID': {'tag': 'mac'}, 'val': [self._mac]}
        ip = {'ID': {'tag': 'ip'}, 'val': [self._ip]}
        os = {'ID': {'tag': 'os'}, 'val': [self._os]}
        version = {'ID': {'tag': 'version'}, 'val': [self._version]}

        client = {'ID': {'tag': 'client'}, 'attr': {'id': self._client.id}, 'val': [mac, ip, os, version]}
        server = {'ID': {'tag': 'server'}, 'attr': {'id': self._server.id}}

        header = {'ID': {'tag': 'header'}, 'val': [server, client]}

        self.dict2node(header, self._root)

    def savetest(self, test):
        '''
        Salva l'oggetto BestTest ricevuto nel file XML interno.
        '''
        profiler_info = test.profiler_info
        proof = test.proof

        status = {-1: "none", 0: "false", 1: "true"}

        wireless_dict = {'ID': {'tag': 'interface'}, 'attr': {'type': 'wireless'},
                         'val': [status[profiler_info['Wireless']]]}
        ethernet_dict = {'ID': {'tag': 'interface'}, 'attr': {'type': 'ethernet'},
                         'val': [status[profiler_info['Ethernet']]]}
        interfaces = {'ID': {'tag': 'interfaces'}, 'val': []}

        for interface in [ethernet_dict, wireless_dict]:
            if interface['val'][0] != 'none':
                interfaces['val'].append(interface)

        traffic_dict = {'ID': {'tag': 'traffic'}, 'val': [profiler_info['Traffic']]}
        hosts_dict = {'ID': {'tag': 'hosts'}, 'val': [profiler_info['Hosts']]}

        ram_dict = {'ID': {'tag': 'ram'}, 'val': [profiler_info['RAM']]}
        cpu_dict = {'ID': {'tag': 'cpu'}, 'val': [profiler_info['CPU']]}

        bytes_oth_dict = {'ID': {'tag': 'byte'}, 'attr': {'type': 'other'}, 'val': [proof.bytes_tot - proof.bytes_nem]}
        bytes_nem_dict = {'ID': {'tag': 'byte'}, 'attr': {'type': 'nemesys'}, 'val': [proof.bytes_nem]}

        test_bytes_dict = {'ID': {'tag': 'bytes'}, 'val': [bytes_nem_dict, bytes_oth_dict]}
        time_dict = {'ID': {'tag': 'time'}, 'val': [proof.duration]}
        done_dict = {'ID': {'tag': 'done'}, 'val': [test.n_tests_done]}

        proof_dict = {'ID': {'tag': 'value'}, 'val': [done_dict, time_dict, test_bytes_dict]}
        profiler_dict = {'ID': {'tag': 'profiler'}, 'val': [cpu_dict, ram_dict, interfaces, hosts_dict, traffic_dict]}

        test_dict = {'ID': {'tag': 'test'}, 'attr': {'type': proof.type}, 'val': [profiler_dict, proof_dict]}

        body = {'ID': {'tag': 'body'}, 'val': [test_dict]}

        self.dict2node(body, self._root)

    def savetime(self, start_time, stop_time):

        stop = {'ID': {'tag': 'stop'}, 'val': [stop_time.isoformat()]}
        start = {'ID': {'tag': 'start'}, 'val': [start_time.isoformat()]}

        time = {'ID': {'tag': 'time'}, 'val': [start, stop]}

        header = {'ID': {'tag': 'header'}, 'val': [time]}

        self.dict2node(header, self._root)

    @property
    def id(self):
        return str(self._start.strftime('%Y%m%d%H%M%S'))

    @property
    def server(self):
        return self._server

    @property
    def client(self):
        return self._client

    def __str__(self):
        return self._xml.toxml('UTF-8')
