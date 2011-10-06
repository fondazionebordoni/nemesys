'''
Created on 20/ott/2010

@author: Albenzio Cirillo

Le parti commentate sono relative precedenti all'integrazione nell'unico metodo in LocalProfiler

N.B.: funziona con psutil 0.3.0 o superiore

'''
from ..LocalProfilerFactory import LocalProfiler
from ..RisorsaFactory import Risorsa
from ..NemesysException import RisorsaException
import xml.etree.ElementTree as ET
import psutil, os, time
import dmidecode
import socket

class CPU(Risorsa):
      
    def __init__(self):
        Risorsa.__init__(self)
        self._chisono="sono una CPU"
        self._params=['processor','cores','cpuLoad']
#        print psutil.__version__
        
        
    def processor(self):
        val = dmidecode.processor().values()
        return self.xmlFormat('processor',val[0]['data']['Version'])
    
    def cores(self):
        val = dmidecode.processor().values()
#        val = os.environ['NUMBER_OF_PROCESSORS']
        return self.xmlFormat('cores',val[0]['data']['Core Enabled'])
    
    def cpuLoad(self):
        interval = 0.1
        val = psutil.cpu_percent(interval)
        return self.xmlFormat('cpuLoad',val)
    
class RAM(Risorsa):
    def __init__(self):
        Risorsa.__init__(self)
        self._params=['total_memory','percentage_ram_usage']
        
    def total_memory(self):
        val = psutil.phymem_usage()
        return self.xmlFormat('total_memory',val[0])
    
    def percentage_ram_usage(self):
        val = psutil.phymem_usage()
        return self.xmlFormat('percentage_ram_usage',val[3])
    
class sistemaOperativo(Risorsa):
    
    def __init__(self):
        Risorsa.__init__(self)
        self._params=['version']
        
    def version (self):
        val = os.uname()
        valret = val[3] + ' with ' + val[0]+ ' ' + val[2]
        return self.xmlFormat('version',valret)
    
class disco(Risorsa):
    
    def __init__(self):
        Risorsa.__init__(self)
        self._params=['byte_transfer']
        
    def byte_transfer(self):
        return 0
    
class rete(Risorsa):
    
    def __init__(self):
        Risorsa.__init__(self)
        self._params=['profileDevice']
        
    def getipaddr(self):
        if self.ipaddr =="":
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("www.fub.it",80))
                self.ipaddr= s.getsockname()[0]
            except socket.gaierror:
                pass
                #raise RisorsaException("Connessione Assente")
        else:
            pass
        return self.ipaddr
    
    def profileDevice(self):
        features = {'Name':' ','AdapterType':' ','MACAddress':' ','Availability':' '}
        devpath='/sys/class/net/'
        descriptors = ['address','type','operstate']
        val ={'address': ' ', 'type': ' ', 'operstate': ' '}
        devlist=os.listdir(devpath)
        if len(devlist) > 0:
            for dev in devlist:
                devxml=ET.Element('NetworkDevice')
                for des in descriptors:
                    fname= devpath + str(dev) + '/' + str(des)
                    f=open(fname)
                    val[des]=f.readline()
                devxml.append(self.xmlFormat('Name',dev))
                devxml.append(self.xmlFormat('Type',val['type']))
                devxml.append(self.xmlFormat('MACAddress',val['address']))
                devxml.append(self.xmlFormat('isActive','True'))
                devxml.append(self.xmlFormat('Status',val['operstate']))
        
        return devxml

        
    def profileDevice_backup(self):
        features = {'Name':'','AdapterType':'','MACAddress':'','Availability':''}
        descriptors = {'description':'AdapterType', 'product':'Name', 'serial':'MACAddress'} 
        devName= 'unknown'
        devType= 'unknown'
        devMac = 'unknown'
        devIsActive = 'False'
        devStatus = 'unknown'
        command_line = "lshw -class network"
        f = os.popen(command_line)
        for line in f:
            val = line.split(':',1)            
            if (len(val) > 1):
                for keys in descriptors:
                    if val[0].lstrip() == keys:
                        features[descriptors[keys]] = val[1]
        devIsActive = 'True'
        devStatus = 'Enabled'
        if (features['Name']):
                devName=features['Name']
        if (features['AdapterType']):
            devType=features['AdapterType']
        if (features['MACAddress']):
            devMac=features['MACAddress']
        devxml = ET.Element('NetworkDevice')
        devxml.append(self.xmlFormat('Name',devName))
        devxml.append(self.xmlFormat('Type',devType))
        devxml.append(self.xmlFormat('MACAddress',devMac))
        devxml.append(self.xmlFormat('isActive',devIsActive))
        devxml.append(self.xmlFormat('Status',devStatus))
        return devxml
         
   
class Profiler(LocalProfiler):
    
    def __init__(self):
        LocalProfiler.__init__(self)
        self._resources =['CPU','RAM','sistemaOperativo','rete']

    '''
    necessario racchiudere anche la chiamata al profile della superclasse in un try/except?
    '''
    def _setResource(self,res):
        self._resources=res    
        
    def profile(self):
        return super(Profiler,self).profile(__name__)