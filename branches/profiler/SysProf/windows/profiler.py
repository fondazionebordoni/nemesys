'''
Created on 20/ott/2010

@author: antonio

'''
from ..LocalProfilerFactory import LocalProfiler
from ..RisorsaFactory import Risorsa
import win32com.client

class CPU(Risorsa):
   
    def __init__(self):
        Risorsa.__init__(self)
        self._chisono="sono una CPU"
        self._params=['processor','cores','cpuLoad']
        self.__objWMIService = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        self.__objSWbemServices = self.__objWMIService.ConnectServer(".","root\cimv2")
        self.__colItems = self.__objSWbemServices.ExecQuery("SELECT * FROM Win32_Processor")
        self.__objItem = self.__colItems[0]
        
    def processor(self):
        infos = ['Name','Description','Manufacturer']
        proc=[]
        for i in range(len(infos)):
            proc.append(self.__objItem.__getattr__(infos[i])) 
        return ", ".join(proc)    
    '''    
    def num_cpu(self):
        return '1'
    '''
    def cpuLoad(self):
        return self.__objItem.__getattr__('LoadPercentage')
    
    def cores(self):
        return self.__objItem.__getattr__('NumberOfCores')
    

class Profiler(LocalProfiler):
    
    def __init__(self):
        LocalProfiler.__init__(self)
        self._resources =['CPU']
       
    '''
    necessario racchiudere anche la chiamata al profile della superclasse in un try/except?
    '''
    
    def profile(self):
        return super(Profiler,self).profile(__name__)


'''
Alcuni valori che potrebbero essere di interesse

if objItem.Architecture != None:
    print "Architecture: %s" %  objItem.Architecture
if objItem.CurrentClockSpeed != None:
    print "CurrentClockSpeed: %s" %  objItem.CurrentClockSpeed
if objItem.Description != None:
    print "Description: %s" %  objItem.Description
if objItem.ExtClock != None:
    print "ExtClock: %s" %  objItem.ExtClock
if objItem.LoadPercentage != None:
    print "LoadPercentage: %s" %  objItem.LoadPercentage
if objItem.Manufacturer != None:
    print "Manufacturer: %s" %  objItem.Manufacturer
if objItem.Name != None:
    print "Name: %s" %  objItem.Name
if objItem.NumberOfCores != None:
    print "NumberOfCores: %s" %  objItem.NumberOfCores
if objItem.NumberOfLogicalProcessors != None:
    print "NumberOfLogicalProcessors: %s" %  objItem.NumberOfLogicalProcessors
if objItem.Status != None:
    print "Status: %s" % objItem.Status
if objItem.StatusInfo != None:
    print "StatusInfo: %s" % objItem.StatusInfo
'''