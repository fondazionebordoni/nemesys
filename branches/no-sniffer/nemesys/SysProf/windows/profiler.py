'''
Created on 20/ott/2010

@author: antonio

'''
from ..LocalProfilerFactory import LocalProfiler
from ..RisorsaFactory import Risorsa
from ..NemesysException import RisorsaException
import win32com.client
import time
import socket
import xml.etree.ElementTree as ET
from ctypes import *
from ctypes.wintypes import DWORD, ULONG
import struct
import pythoncom
import psutil

def executeQuery(wmi_class, whereCondition=""):   
    try: 
        objWMIService = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        objSWbemServices = objWMIService.ConnectServer(".", "root\cimv2")
        colItems = objSWbemServices.ExecQuery("SELECT * FROM " + wmi_class + whereCondition)
    except:
        raise RisorsaException("Errore nella query al server root\cimv2")
        
    return colItems
    
class RisorsaWin(Risorsa):
    def __init__(self):
        Risorsa.__init__(self)
        self.whereCondition = ""
        
    def getSingleInfo(self, obj, attr):
        val = obj.__getattr__(attr)
        if val != None:
            return val
        else:
            return None
#            print ("non riesco a recuperare il parametro %s" %attr) 
#            raise AttributeError("Parametro %s non trovato" %attr)
    
    def getStatusInfo(self, root):
        try:
            for wmi_class in self._params:
                items = executeQuery(wmi_class, self.whereCondition)
                if len(items) == 0:
                    raise RisorsaException("La risorsa con le caratteristiche richieste non e' presente nel server")
                else:
                    for obj in items:
                        for val in self._params[wmi_class]:
                            tag = val
                            cmd = getattr(self, tag)
                            xmlres = cmd(obj)
                            if (xmlres is not None):
                              root.append(xmlres)
        except AttributeError as e:
            raise RisorsaException("errore get status info")
        except RisorsaException as e:
            raise RisorsaException(e)
        except:
            raise RisorsaException("errore query")
        return root
    
class CPU(RisorsaWin):
   
    def __init__(self):
        RisorsaWin.__init__(self)
        self._params = {'Win32_Processor':['processor', 'cores', 'cpuLoad']}
        
    def processor(self, obj):
        infos = ['Name', 'Description', 'Manufacturer']
        proc = []
        try:
            for i in infos:
                val = self.getSingleInfo(obj, i)
                proc.append(val)
        except AttributeError as e:
            raise AttributeError(e)
        ris = ", ".join(proc)
        return self.xmlFormat("processor", ris)    
    
    def cpuLoad(self, obj):
#         try:
#             val = self.getSingleInfo(obj, 'LoadPercentage')
#         except AttributeError as e:
#             raise AttributeError(e)
#         return self.xmlFormat("cpuLoad", val)
        val = psutil.cpu_percent(0.5)
        return self.xmlFormat('cpuLoad', val)

    def cores(self, obj):
        try:
            val = self.getSingleInfo(obj, 'NumberOfCores')
        except AttributeError as e:
            raise AttributeError(e)
        return self.xmlFormat("cores", val)
    
class RAM(RisorsaWin):
    def __init__(self):
        RisorsaWin.__init__(self)
        self._params = {'Win32_ComputerSystem':['total_memory'], 'Win32_OperatingSystem':['percentage_ram_usage']}
        
        
    def total_memory(self, obj):
        try:
            val = self.getSingleInfo(obj, 'TotalPhysicalMemory')
        except AttributeError as e:
            raise AttributeError(e)
        return self.xmlFormat("totalPhysicalMemory", val)
        
    def percentage_ram_usage(self, obj):
        try:
            free = self.getSingleInfo(obj, 'FreePhysicalMemory')
            total = self.getSingleInfo(obj, 'TotalVisibleMemorySize')        
            if total != 0:
                load = int((1.0 - (float(free) / float(total))) * 100.0)
                return self.xmlFormat("RAMUsage", load)
            else:
                raise AttributeError("Impossibile calcolare la percentuale di ram utilizzata")
        except AttributeError as e:
            raise AttributeError(e)
    
class sistemaOperativo(RisorsaWin):
    def __init__(self):
        RisorsaWin.__init__(self)
        self._params = {'Win32_OperatingSystem':['version']}
        
    def version (self, obj):
        var = ['Caption', 'Version'] # ci sarebbe anche 'OSArchitecture' ma su windows xp non e' definita
        versione = []
        try:
            for v in var:
                val = self.getSingleInfo(obj, v)
                versione.append(val)
        except AttributeError as e:
            raise AttributeError(e)
        ris = ", ".join(versione)
        return self.xmlFormat("OperatingSystem", ris)
    
class disco(RisorsaWin):
    def __init__(self):
        RisorsaWin.__init__(self)
        self._params = {'Win32_PerfFormattedData_PerfDisk_PhysicalDisk':['byte_transfer']}
        self.whereCondition = " WHERE Name= \"_Total\"" #problema, conta tutti i byte trasferiti, anche tra memorie esterne che non coinvolgono il disco del pc
    
    def byte_transfer(self, obj):
        var = 'DiskBytesPersec'
        total = 0;
        try:
            for i in range(5):
                bd = self.getSingleInfo(obj, var)
                total += int(bd)
                time.sleep(1)
        except AttributeError as e:
            raise AttributeError(e)
        return self.xmlFormat("ByteTransfer", total)

#class wireless(RisorsaWin):
#    def __init__(self):
#        self.CountWlan = 0
#        self.wcounted = False
#        RisorsaWin.__init__(self)
#        self._params = {'MSNdis_80211_ReceivedSignalStrength':['checkWlanPow','CountWLDev']}
#        self.whereCondition = " WHERE active = true"
#        
#    def checkWLanPow(self,obj):
#        if (obj == None):
#            return self.xmlFormat("ActiveWLAN","none")
#        else:
#            CountWlan = CountWlan +1
#    
#    def CountWLDev(self,obj):
#        if not self.wcounted:
#            self.wcounted = True
#            return self.xmlFormat("ActiveWLAN",CountWlan)
#          
        
         
class rete(RisorsaWin):
    
    def __init__(self):
        RisorsaWin.__init__(self)
        self._params = {'Win32_NetworkAdapter':['profileDevice']}
        self.ipaddr = ""
        self.whereCondition = " WHERE Manufacturer != 'Microsoft' "# AND NOT PNPDeviceID LIKE 'ROOT\\*' "
        self._activeMAC = None
        self._checked = False
        self.ipenabdic={}
           
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
    
    def findActiveInterface(self):
        items = executeQuery('Win32_NetworkAdapterConfiguration', "")
        ipaddr = self.getipaddr()
        if (items):
            try:
                for obj in items:
                    ipaddrlist = self.getSingleInfo(obj, 'IPAddress')
                    if ipaddrlist:
                        ris = self.getSingleInfo(obj, 'MACAddress')
                        self.ipenabdic[ris]=self.getSingleInfo(obj,'IPEnabled')
                        if ipaddr in ipaddrlist:
                            self._activeMAC = ris
            except:
                raise RisorsaException("Impossibile specificare l'interfaccia attiva") 
            finally:
                return True
        else:
            raise RisorsaException("E' impossibile interrogare le risorse di rete")
            
    def profileDevice(self, obj):
        running = 0X3 #running Net Interface CODE
        features = {'Name':'', 'AdapterType':'', 'MACAddress':'','NetConnectionID':''}
        devName = 'unknown'
        devType = 'unknown'
        devMac = 'unknown'
        devIsActive = 'False'
        devStatus = 'Disabled'
        devNetConnID = 'unknown'
        if (not self._checked):
            try:
                self._checked = self.findActiveInterface()
            except RisorsaException as e:
                raise RisorsaException(e) 
        try:
            keys = features.keys()
            for key in keys:
                features[key] = self.getSingleInfo(obj, key)
        finally:
            if (features['Name']):
                devName = features['Name']
            if (features['AdapterType']):
                devType = features['AdapterType']
            if (features['NetConnectionID']):
                devNetConnID = features['NetConnectionID']
                if self._is_wireless_text(devNetConnID):
                    devType = 'Wireless' #type is forced according to the NetConnectionID
            if (features['MACAddress']):
                devMac = features['MACAddress']
                if devMac == self._activeMAC:
                    devIsActive = 'True'
            if devMac in self.ipenabdic.keys():
                statnet=str(self.ipenabdic[devMac])
            else:
                statnet = 'false'
            if ( statnet.lower() == 'true' ):
                devStatus = 'Enabled'   
            devxml = ET.Element('NetworkDevice')
            devxml.append(self.xmlFormat('Name', devName))
            devxml.append(self.xmlFormat('Type', devType))
            devxml.append(self.xmlFormat('MACAddress', devMac))
            devxml.append(self.xmlFormat('isActive', devIsActive))
            devxml.append(self.xmlFormat('Status', devStatus))
            return devxml
          
    def _is_wireless_text(self,text):
      keywords = ['wireless', 'wlan', 'wifi', 'wi-fi','fili']
      ltext=text.lower()
      words=ltext.split(' ')
      for w in words:
        for key in keywords:
          if w==key:
            return True
      return False
                   
class processi(RisorsaWin):
    def __init__(self):
        RisorsaWin.__init__(self)
        self._params = {'Win32_Process':['process']}
        
    def process(self, obj):
        var = 'Name'
        try:
            ris = self.getSingleInfo(obj, var)
        except AttributeError as e:
            raise AttributeError(e)
        return self.xmlFormat("process", ris)
    
class connection(RisorsaWin):
    
    def __init__(self):
        RisorsaWin.__init__(self)
        
    def getOpenConnections(self):
        """
            This function will return a list of ports (TCP/UDP) that the current 
            machine is listening on. It's basically a replacement for parsing 
            netstat output but also serves as a good example for using the 
            IP Helper API:
            http://msdn.microsoft.com/library/default.asp?url=/library/en-
            us/iphlp/iphlp/ip_helper_start_page.asp.
            I also used the following post as a guide myself (in case it's useful 
            to anyone):
            http://aspn.activestate.com/ASPN/Mail/Message/ctypes-users/1966295
       
         """
        connectionList = ET.Element("ConnectionEstablished")
               
        NO_ERROR = 0
        NULL = ""
        bOrder = 0
        
        # define some MIB constants used to identify the state of a TCP port
        MIB_TCP_STATE_CLOSED = 1
        MIB_TCP_STATE_LISTEN = 2
        MIB_TCP_STATE_SYN_SENT = 3
        MIB_TCP_STATE_SYN_RCVD = 4
        MIB_TCP_STATE_ESTAB = 5
        MIB_TCP_STATE_FIN_WAIT1 = 6
        MIB_TCP_STATE_FIN_WAIT2 = 7
        MIB_TCP_STATE_CLOSE_WAIT = 8
        MIB_TCP_STATE_CLOSING = 9
        MIB_TCP_STATE_LAST_ACK = 10
        MIB_TCP_STATE_TIME_WAIT = 11
        MIB_TCP_STATE_DELETE_TCB = 12
        
        ANY_SIZE = 1         
        
        # defing our MIB row structures
        class MIB_TCPROW(Structure):
            _fields_ = [('dwState', DWORD),
                        ('dwLocalAddr', DWORD),
                        ('dwLocalPort', DWORD),
                        ('dwRemoteAddr', DWORD),
                        ('dwRemotePort', DWORD)]
      
        dwSize = DWORD(0)
        
        # call once to get dwSize 
        windll.iphlpapi.GetTcpTable(NULL, byref(dwSize), bOrder)
        
        # ANY_SIZE is used out of convention (to be like MS docs); even setting this
        # to dwSize will likely be much larger than actually necessary but much 
        # more efficient that just declaring ANY_SIZE = 65500.
        # (in C we would use malloc to allocate memory for the *table pointer and 
        #  then have ANY_SIZE set to 1 in the structure definition)
        
        ANY_SIZE = dwSize.value
        
        class MIB_TCPTABLE(Structure):
            _fields_ = [('dwNumEntries', DWORD),
                        ('table', MIB_TCPROW * ANY_SIZE)]
        
        tcpTable = MIB_TCPTABLE()
        tcpTable.dwNumEntries = 0 # define as 0 for our loops sake
    
        # now make the call to GetTcpTable to get the data
        if (windll.iphlpapi.GetTcpTable(byref(tcpTable),
            byref(dwSize), bOrder) == NO_ERROR):
          
            for i in range(tcpTable.dwNumEntries):
            
                item = tcpTable.table[i]
                lPort = item.dwLocalPort
                lPort = socket.ntohs(lPort)
                rPort = item.dwRemotePort
                rPort = socket.ntohs(rPort)
                lAddr = item.dwLocalAddr
                lAddr = socket.inet_ntoa(struct.pack('L', lAddr))
                rAddr = item.dwRemoteAddr
                rAddr = socket.inet_ntoa(struct.pack('L', rAddr))
                portState = item.dwState
                        
                # only record TCP ports where we're listening on our external 
                #    (or all) connections
                if str(lAddr) != "127.0.0.1" and str(rAddr) != "127.0.0.1" and portState == MIB_TCP_STATE_ESTAB:
                    localConn = ET.Element("Local")
                    localAdd = self.xmlFormat("LocalAddress", str(lAddr))
                    localPort = self.xmlFormat("LocalPort", str(lPort))
                    localConn.append(localAdd)
                    localConn.append(localPort)
                    remoteConn = ET.Element("Remote")
                    remoteAdd = self.xmlFormat("RemoteAddress", str(rAddr))
                    remotePort = self.xmlFormat("RemotePort", str(rPort))
                    remoteConn.append(remoteAdd)
                    remoteConn.append(remotePort)
                    
                    connectionList.append(localConn)
                    connectionList.append(remoteConn)
        
        else:
            raise AttributeError("Error retrieving TCP table connections") 
        
        return connectionList
    
    def getStatusInfo(self, root):
        try:
            connection = self.getOpenConnections()
            root.append(connection)
        except AttributeError:
            raise RisorsaException("Error in retrieving TCP table connections")
        return root
    
class Profiler(LocalProfiler):
    
    def __init__(self):
        available_resources = set(['CPU', 'RAM', 'sistemaOperativo', 'rete', 'wireless', 'disco'])
        LocalProfiler.__init__(self, available_resources)

    def profile(self, resource=set()):
        pythoncom.CoInitialize()
        data = super(Profiler, self).profile(__name__, resource)
        pythoncom.CoUninitialize()
        return data
