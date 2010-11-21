'''
Created on 20/ott/2010

@author: antonio

'''
from ..LocalProfilerFactory import LocalProfiler
from ..RisorsaFactory import Risorsa
from ..NemesysException import RisorsaException
import win32com.client
import time


def executeQuery(wmi_class,whereCondition=""):   
    try: 
        objWMIService = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        objSWbemServices = objWMIService.ConnectServer(".","root\cimv2")
        colItems = objSWbemServices.ExecQuery("SELECT * FROM " + wmi_class + whereCondition)
    except:
        raise RisorsaException("Errore nella query al server root\cimv2")
        
    return colItems
    
class RisorsaWin(Risorsa):
    def __init__(self):
        Risorsa.__init__(self)
        self.whereCondition=""
        
    def getSingleInfo(self,obj,attr):
        val= obj.__getattr__(attr)
        if val != None:
            return val
        else:
            raise AttributeError("Parametro %s non trovato" %attr)
    
    def getStatusInfo(self,root):
        try:
            for wmi_class in self._params:
                items = executeQuery(wmi_class,self.whereCondition)
                for obj in items:
                    for val in self._params[wmi_class]:
                        tag=val
                        cmd = getattr(self,tag)            
                        root.append(self.xmlFormat(tag, cmd(obj)))
        except AttributeError as e:
            print RisorsaException(e)
            raise RisorsaException("errore get status info")
        except:
            raise RisorsaException("errore query")
        return root
    
class CPU(RisorsaWin):
   
    def __init__(self):
        RisorsaWin.__init__(self)
        self._params={'Win32_Processor':['processor','cores','cpuLoad']}
        
        
    def processor(self,obj):
        infos = ['Name','Description','Manufacturer']
        proc=[]
        try:
            for i in infos:
                val = self.getSingleInfo(obj,i)
                proc.append(val)
        except AttributeError as e:
            raise AttributeError(e)
        return ", ".join(proc)    
    
    def cpuLoad(self,obj):
        try:
            val = self.getSingleInfo(obj, 'LoadPercentage')
        except AttributeError as e:
            raise AttributeError(e)
        return val

    def cores(self,obj):
        try:
            val = self.getSingleInfo(obj, 'NumberOfCores')
        except AttributeError as e:
            raise AttributeError(e)
        return val
    
class RAM(RisorsaWin):
    def __init__(self):
        RisorsaWin.__init__(self)
        self._params={'Win32_ComputerSystem':['total_memory'],'Win32_OperatingSystem':['percentage_ram_usage']}
        
    def total_memory(self,obj):
        try:
            val = self.getSingleInfo(obj, 'TotalPhysicalMemory')
        except AttributeError as e:
            raise AttributeError(e)
        return val
        
    def percentage_ram_usage(self,obj):
        try:
            free= self.getSingleInfo(obj,'FreePhysicalMemory')
            total=self.getSingleInfo(obj,'TotalVisibleMemorySize')        
            if total !=0:
                return int((1.0 - (float(free)/float(total)))*100.0)
            else:
                raise AttributeError("Impossibile calcolare la percentuale di ram utilizzata")
        except AttributeError as e:
            raise AttributeError(e)
    
    
class sistemaOperativo(RisorsaWin):
    def __init__(self):
        RisorsaWin.__init__(self)
        self._params={'Win32_OperatingSystem':['version']}
        
    def version (self,obj):
        var = ['Caption','Version'] # ci sarebbe anche 'OSArchitecture' ma su windows xp non e' definita
        versione=[]
        try:
            for v in var:
                val = self.getSingleInfo(obj, v)
                versione.append(val)
        except AttributeError as e:
            raise AttributeError(e)
        return ", ".join(versione)
    
class disco(RisorsaWin):
    def __init__(self):
        RisorsaWin.__init__(self)
        self._params={'Win32_PerfFormattedData_PerfDisk_PhysicalDisk':['byte_transfer']}
        self.whereCondition=" WHERE Name= \"_Total\"" #problema, conta tutti i byte trasferiti, anche tra memorie esterne che non coinvolgono il disco del pc
    
    def byte_transfer(self,obj):
        var = 'DiskBytesPersec'
        total = 0;
        try:
            for i in range(5):
                bd = self.getSingleInfo(obj,var)
                total += int(bd)
                time.sleep(1)
        except AttributeError as e:
            raise AttributeError(e)
        return total
                    
            
class rete(RisorsaWin):
    def __init__(self):
        RisorsaWin.__init__(self)
        self._params={'Win32_NetworkAdapterConfiguration':['active_interface_mac']}
        self.whereCondition=" WHERE IPEnabled=True AND (DNSDomain IS NOT NULL AND DNSDomain!=\"\")"
        
    def active_interface_mac(self,obj):  
        var = 'MACAddress'
        try:
            ris = self.getSingleInfo(obj, var)
        except AttributeError as e:
            raise AttributeError(e)
        return ris  
        
class processi(RisorsaWin):
    def __init__(self):
        RisorsaWin.__init__(self)
        self._params={'Win32_Process':['process']}
        
    def process(self,obj):
        var = 'Name'
        try:
            ris = self.getSingleInfo(obj, var)
        except AttributeError as e:
            raise AttributeError(e)
        return ris
           
class Profiler(LocalProfiler):
    
    def __init__(self):
        LocalProfiler.__init__(self)
        self._resources =['CPU','RAM','sistemaOperativo','disco','processi','rete']
       
    '''
    necessario racchiudere anche la chiamata al profile della superclasse in un try/except?
    '''
    
    def profile(self):
        return super(Profiler,self).profile(__name__)
