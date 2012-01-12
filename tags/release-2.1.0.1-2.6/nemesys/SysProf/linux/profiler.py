'''
Created on 20/ott/2010

@author: Albenzio Cirillo

Profiler per Piattaforme LINUX

N.B.: funziona con psutil 0.3.0 o superiore

'''
from ..LocalProfilerFactory import LocalProfiler
from ..RisorsaFactory import Risorsa
from ..NemesysException import RisorsaException
import xml.etree.ElementTree as ET
import psutil, os
import dmidecode
import netifaces
import socket

class CPU(Risorsa):

    def __init__(self):
        Risorsa.__init__(self)
        self._chisono = "sono una CPU"
        self._params = ['processor', 'cores', 'cpuLoad']
        #print psutil.__version__

    def processor(self):
        val = dmidecode.processor().values()
        return self.xmlFormat('processor', val[0]['data']['Version'])

    def cores(self):
        val = dmidecode.processor().values()
        return self.xmlFormat('cores', val[0]['data']['Core Enabled'])

    def cpuLoad(self):
        # WARN interval parameter available from v.0.2
        val = psutil.cpu_percent()
        print "ok"
        return self.xmlFormat('cpuLoad', val)

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

class disco(Risorsa):

    def __init__(self):
        Risorsa.__init__(self)
        self._params = ['byte_transfer']

    def byte_transfer(self):
        return 0

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

    def profileDevice(self):
        vocab = ['wireless', 'wifi', 'wi-fi', 'senzafili', 'wlan']
        devpath = '/sys/class/net/'
        descriptors = ['address', 'type', 'operstate']
        val = {'address': ' ', 'type': ' ', 'operstate': ' '}
        self.ipaddr = self.getipaddr()
        devlist = os.listdir(devpath)
        maindevxml = ET.Element('rete')
        if len(devlist) > 0:
            for dev in devlist:
                devIsAct = 'False' # by def
                ipdev = self.get_if_ipaddress(dev)
                if (ipdev == self.ipaddr):
                    devIsAct = 'True'
                for des in descriptors:
                    fname = devpath + str(dev) + '/' + str(des)
                    f = open(fname)
                    val[des] = f.readline()

                wifipath = devpath + str(dev)
                inner_folder = os.listdir(wifipath)
                devxml = ET.Element('NetworkDevice')

                devxml.append(self.xmlFormat('Name', dev))

                if val['operstate'].rstrip() == "up":
                    devxml.append(self.xmlFormat('Status', 'Enabled'))
                else:
                    devxml.append(self.xmlFormat('Status', 'Disabled'))
                if val['type'].split('\n')[0] == '1':
                    val['type'] = 'Ethernet 802.3'
                for folds in inner_folder:
                    for mot in vocab:
                        if str(folds).lower() == mot:
                            val['type'] = 'Wireless'
                devxml.append(self.xmlFormat('Type', val['type']))
                devxml.append(self.xmlFormat('MACAddress', val['address']))

                devxml.append(self.xmlFormat('isActive', devIsAct))
                maindevxml.append(devxml)
                del devxml

        return maindevxml


#    def profileDevice_backup(self):
#        features = {'Name':'', 'AdapterType':'', 'MACAddress':'', 'Availability':''}
#        descriptors = {'description':'AdapterType', 'product':'Name', 'serial':'MACAddress'} 
#        devName = 'unknown'
#        devType = 'unknown'
#        devMac = 'unknown'
#        devIsActive = 'False'
#        devStatus = 'unknown'
#        command_line = "lshw -class network"
#        f = os.popen(command_line)
#        for line in f:
#            val = line.split(':', 1)            
#            if (len(val) > 1):
#                for keys in descriptors:
#                    if val[0].lstrip() == keys:
#                        features[descriptors[keys]] = val[1]
#        devIsActive = 'True'
#        devStatus = 'Enabled'
#        if (features['Name']):
#                devName = features['Name']
#        if (features['AdapterType']):
#            devType = features['AdapterType']
#        if (features['MACAddress']):
#            devMac = features['MACAddress']
#        devxml = ET.Element('NetworkDevice')
#        devxml.append(self.xmlFormat('Name', devName))
#        devxml.append(self.xmlFormat('Type', devType))
#        devxml.append(self.xmlFormat('MACAddress', devMac))
#        devxml.append(self.xmlFormat('isActive', devIsActive))
#        devxml.append(self.xmlFormat('Status', devStatus))
#        return devxml
#         

class Profiler(LocalProfiler):

    def __init__(self):
        available_resources = set(['CPU', 'RAM', 'sistemaOperativo', 'rete'])
        LocalProfiler.__init__(self, available_resources)

    def profile(self, resource = set()):
        return super(Profiler, self).profile(__name__, resource)
