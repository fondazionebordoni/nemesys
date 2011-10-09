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
import psutil, os, time
import dmidecode
import socket, fcntl, struct

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
        val = int(float(used)/float(total) * 100.0)
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
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
            0x8915, # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
            )[20:24])
    
    def profileDevice(self):
        features = {'Name':' ', 'AdapterType':' ', 'MACAddress':' ', 'Availability':' '}
        devpath = '/sys/class/net/'
        descriptors = ['address', 'type', 'operstate']
        val = {'address': ' ', 'type': ' ', 'operstate': ' '}
        ipaddr = self.getipaddr()       
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
                if val['operstate'].rstrip() == "up":
                    devxml = ET.Element('NetworkDevice')
                    devxml.append(self.xmlFormat('Status', 'Enabled'))
                    devxml.append(self.xmlFormat('Name', dev))
                    devxml.append(self.xmlFormat('Type', val['type']))
                    devxml.append(self.xmlFormat('MACAddress', val['address']))
                    devxml.append(self.xmlFormat('isActive', devIsAct))
                    maindevxml.append(devxml)
                    del devxml

        return maindevxml

        
    def profileDevice_backup(self):
        features = {'Name':'', 'AdapterType':'', 'MACAddress':'', 'Availability':''}
        descriptors = {'description':'AdapterType', 'product':'Name', 'serial':'MACAddress'} 
        devName = 'unknown'
        devType = 'unknown'
        devMac = 'unknown'
        devIsActive = 'False'
        devStatus = 'unknown'
        command_line = "lshw -class network"
        f = os.popen(command_line)
        for line in f:
            val = line.split(':', 1)            
            if (len(val) > 1):
                for keys in descriptors:
                    if val[0].lstrip() == keys:
                        features[descriptors[keys]] = val[1]
        devIsActive = 'True'
        devStatus = 'Enabled'
        if (features['Name']):
                devName = features['Name']
        if (features['AdapterType']):
            devType = features['AdapterType']
        if (features['MACAddress']):
            devMac = features['MACAddress']
        devxml = ET.Element('NetworkDevice')
        devxml.append(self.xmlFormat('Name', devName))
        devxml.append(self.xmlFormat('Type', devType))
        devxml.append(self.xmlFormat('MACAddress', devMac))
        devxml.append(self.xmlFormat('isActive', devIsActive))
        devxml.append(self.xmlFormat('Status', devStatus))
        return devxml
         
   
class Profiler(LocalProfiler):
    
    def __init__(self):
        available_resources = {'CPU', 'RAM', 'sistemaOperativo'}
        LocalProfiler.__init__(self, available_resources)

    def profile(self, resource={}):
        return super(Profiler, self).profile(__name__, resource)
