'''
Created on 20/ott/2010

@author: Albenzio Cirillo

Profiler per Piattaforme Darwin

N.B.: funziona con psutil 0.3.0 o superiore
'''
from ..LocalProfilerFactory import LocalProfiler
from ..RisorsaFactory import Risorsa
import subprocess
from ..NemesysException import RisorsaException

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
       
class Profiler(LocalProfiler):
    
    def __init__(self):
        available_resources = {'CPU', 'RAM', 'sistemaOperativo','rete'}
        LocalProfiler.__init__(self, available_resources)

    def profile(self, resource={}):
        return super(Profiler, self).profile(__name__, resource)