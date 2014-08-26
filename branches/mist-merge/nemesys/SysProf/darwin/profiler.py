'''
Created on 20/ott/2010

@author: Albenzio Cirillo

Profiler per Piattaforme Darwinexit


N.B.: funziona con psutil 0.3.0 o superiore
'''
from ..LocalProfilerFactory import LocalProfiler
from ..RisorsaFactory import Risorsa
import subprocess
from ..NemesysException import RisorsaException
import xml.etree.ElementTree as ET
import socket
import netifaces
import psutil
import platform
import os


class CPU(Risorsa):


    def __init__(self):
        Risorsa.__init__(self)
        self._chisono = "sono una CPU"
        self._params = ['processor', 'cpuLoad']

    def processor(self):
        cmdline = 'system_profiler SPHardwareDataType -xml'
        try:
            spxml = ET.parse(os.popen(cmdline))
            info = spxml.find('array/dict/array/dict')
        except:
            raise Error('errore in darwin system_profiler')
        spxml._setroot(info)
        elem = spxml.getiterator()
        capture = 0
        val = 'Unknown'
        for feat in elem:
            if capture:
                val = feat.text
                capture = 0
                return self.xmlFormat('processor', val)
            if feat.tag == 'key' and feat.text == 'cpu_type':
                capture = 1
        return self.xmlFormat('processor', val)

    def cpuLoad(self):
        # WARN interval parameter available from v.0.2
        val = psutil.cpu_percent(interval = 0.5)
        return self.xmlFormat('cpuLoad', val)

'''
    def num_cpu(self):
        ncpu = subprocess.Popen(["sysctl", "-n", "hw.ncpu"], stdout=subprocess.PIPE)
        print platform.processor()
        print os.getloadavg()
        return ncpu.communicate()[0].split('\n')[0]
'''

class RAM(Risorsa):
    def __init__(self):
        Risorsa.__init__(self)
        self._params = ['total_memory', 'percentage_ram_usage']

    def total_memory(self):
        val = psutil.TOTAL_PHYMEM
        return self.xmlFormat('totalPhysicalMemory', val)

    def percentage_ram_usage(self):
        total = psutil.TOTAL_PHYMEM
        used = psutil.used_phymem()
        val = int(float(used) / float(total) * 100.0)
        return self.xmlFormat('RAMUsage', val)

class sistemaOperativo(Risorsa):

    def __init__(self):
        Risorsa.__init__(self)
        self._params = ['version']

    def version (self):
        val = os.uname()
        valret = val[3] + ' with ' + val[0] + ' ' + val[2]
        return self.xmlFormat('OperatingSystem', valret)

class rete(Risorsa):
    def __init__(self):
        Risorsa.__init__(self)
        self.ipaddr = ""
        self._params = ['profileDevice']

    def getipaddr(self):
        if self.ipaddr == "":
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("www.fub.it", 80))
                self.ipaddr = s.getsockname()[0]
            except socket.gaierror:
                pass
                #raise RisorsaException("Connessione Assente")
        else:
            pass
        return self.ipaddr

    def get_if_ipaddress(self, ifname):
        neti_names = netifaces.interfaces()
        ipval = '127.0.0.1'
        for nn in neti_names:
            if ifname == nn:
                try:
                    ipval = netifaces.ifaddresses(ifname)[netifaces.AF_INET][0]['addr']
                except:
                    ipval = '127.0.0.1'
        return ipval

    #TODO : ip dell'intefaccia recuperabile anche da XML, evitando di usare netifaces

    def profileDevice(self):
        maindevxml = ET.Element('rete')
        descriptors = {}
        self.ipaddr = self.getipaddr()
        cmdline = 'system_profiler SPNetworkDataType -xml -detailLevel full'
        try:
            spxml = ET.parse(os.popen(cmdline))
            devices = spxml.findall('array/dict/array/dict')
        except:
            raise RisorsaException('errore in darwin system_profiler')
          
        for dev in devices:
            devxml = ET.Element('NetworkDevice')
            descriptors = {}
            devIsAct = 'False' # by def
            devStatus = 'Disabled'
            app = spxml
            app._setroot(dev)
            allnodes = list(app.iter())
            for n in allnodes:
                capture = 1
                if n.tag == 'key':
                    capture = 0
                    elem_num = 0
                    prev_key = n.text     
                if capture and (n.tag == 'string' or n.tag == 'integer'):
                    descriptors[prev_key] = n.text
                            
            if 'Addresses' in descriptors:
                devStatus = 'Enabled'
            if 'NetworkSignature' in descriptors:
                devIsAct = 'True'

            if descriptors['type'].lower() == 'ethernet':
                devType = 'Ethernet 802.3'
                if descriptors['_name'].lower() == 'mbbethernet':
                    devType = 'WWAN'
            elif descriptors['type'].lower() == 'airport':
                devType = 'Wireless'
            elif descriptors['type'].lower() == 'ppp (pppserial)':
                devType = 'WWAN'
            else:
                devType = 'Other'
                
            devxml.append(self.xmlFormat('Name', descriptors['_name']))
            devxml.append(self.xmlFormat('Device', descriptors['interface']))
            devxml.append(self.xmlFormat('Status', devStatus))
            devxml.append(self.xmlFormat('isActive', devIsAct))
            devxml.append(self.xmlFormat('Type', devType))
            devxml.append(self.xmlFormat('IPaddress', descriptors.get('Addresses','unknown')))
            devxml.append(self.xmlFormat('MACaddress', descriptors.get('MAC Address','unknown')))
            
            maindevxml.append(devxml)
            del devxml

        return maindevxml


class Profiler(LocalProfiler):

    def __init__(self):
        available_resources = set(['CPU', 'RAM', 'sistemaOperativo', 'rete'])
        LocalProfiler.__init__(self, available_resources)

    def profile(self, resource = set()):
        return super(Profiler, self).profile(__name__, resource)
