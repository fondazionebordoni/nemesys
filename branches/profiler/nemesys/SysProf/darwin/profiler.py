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

import psutil
import platform
import os


class CPU(Risorsa):
    
    
    def __init__(self):
        Risorsa.__init__(self)
        self._chisono = "sono una CPU"
        self._params = ['num_cpu', 'num_core']
        
    def num_cpu(self):
        ncpu = subprocess.Popen(["sysctl", "-n", "hw.ncpu"], stdout=subprocess.PIPE)
        print platform.processor()
        print os.getloadavg()
        return ncpu.communicate()[0].split('\n')[0]
    
    def num_core(self):
        return '2'
    
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
        descriptors = ['Ethernet/MAC Address', 'type', 'operstate']
        self.ipaddr = self.getipaddr()
        cmdline = 'system_profiler SPNetworkDataType -xml'
        try:
            spxml = ET.parse(os.popen(cmdline))
            devices = spxml.findall('array/dict/array/dict')
        except:
            raise Error('errore in darwin system_profiler')
        for dev in devices:
            s=0 # manca il parsing dei valori di ciascun device
        return 0
        
       
class Profiler(LocalProfiler):
    
    def __init__(self):
        available_resources = {'CPU', 'RAM', 'sistemaOperativo','rete'}
        LocalProfiler.__init__(self, available_resources)

    def profile(self, resource={}):
        return super(Profiler, self).profile(__name__, resource)