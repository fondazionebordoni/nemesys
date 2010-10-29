'''
Created on 20/ott/2010

@author: antonio

Le parti commentate sono relative precedenti all'integrazione nell'unico metodo in LocalProfiler
'''
from SysProf.LocalProfilerFactory import LocalProfiler
from SysProf.RisorsaFactory import Risorsa
import subprocess
from SysProf.NemesysException import RisorsaException
import SysProf.RisorsaFactory
import xml.etree.ElementTree as ET
import sys
import platform
import os
'''
def package_home(rest): 

    return ".".join([__name__,rest])
'''    
class CPU(Risorsa):
    
    
    def __init__(self):
        Risorsa.__init__(self)
        self._chisono="sono una CPU"
        self._params=['num_cpu','num_core']
        
        
    def num_cpu(self):
        ncpu = subprocess.Popen(["sysctl", "-n", "hw.ncpu"], stdout=subprocess.PIPE)
        print platform.processor()
        print os.getloadavg()
        return ncpu.communicate()[0].split('\n')[0]
    
    def num_core(self):
        return '2'
    
    #
    '''
    def getStatusInfo(self,root):
        try:
            for key in self._params:
                tag=key
                cmd = getattr(self,tag)            
                root.append(self.xmlFormat(tag, cmd()))
        except AttributeError as e:
            raise RisorsaException(e)
        return root
      #
      '''  
class Profiler(LocalProfiler):
    
    def __init__(self):
        LocalProfiler.__init__(self)
        self._resources =['CPU']
       
    #
    '''     
    def profile(self):
        result = ET.Element("SystemProfilerResults")
        try:
            for r in self._resources:
                ris = RisorsaFactory.getRisorsa(package_home(r), r)
                result=ris.getStatusInfo(result)
                del ris
                
        except AttributeError:
            raise NotImplementedError("Risorsa non monitorabile")
        except RisorsaException:
            raise RisorsaException

        return result
      #
      '''  
    '''
    necessario racchiudere anche la chiamata al profile della superclasse in un try/except?
    '''
    def profile(self):
        return super(Profiler,self).profile(__name__)