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

NIC_TYPE = { \
0:'Ethernet 802.3', \
1:'Token Ring 802.5', \
2:'Fiber Distributed Data Interface (FDDI)', \
3:'Wide Area Network (WAN)', \
4:'LocalTalk', \
5:'Ethernet using DIX header format', \
6:'ARCNET', \
7:'ARCNET (878.2)', \
8:'ATM', \
9:'Wireless', \
10:'Infrared Wireless', \
11:'Bpc', \
12:'CoWan', \
13:'1394' \
}

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
        self.whereCondition = {}
        
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
            classCondition = ""
            for wmi_class in self._params:
                if wmi_class in self.whereCondition:
                    classCondition = self.whereCondition[wmi_class]
                items = executeQuery(wmi_class, classCondition)
                if len(items) == 0 and (wmi_class != 'Win32_NetworkAdapter') and (wmi_class != 'Win32_POTSModem'):
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
        try:
            val = self.getSingleInfo(obj, 'LoadPercentage')
        except AttributeError as e:
            raise AttributeError(e)
        return self.xmlFormat("cpuLoad", val)

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
        self.whereCondition = {'Win32_PerfFormattedData_PerfDisk_PhysicalDisk':" WHERE Name= \"_Total\""} #problema, conta tutti i byte trasferiti, anche tra memorie esterne che non coinvolgono il disco del pc
    
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
        self._params = {'Win32_NetworkAdapter':['profileDevice'],'Win32_POTSModem':['profileModem']}
        self.whereCondition = {'Win32_NetworkAdapter':" WHERE Manufacturer != 'Microsoft' "} # " AND NOT PNPDeviceID LIKE 'ROOT\\*' "
      
    def _is_wireless_text(self,text):
      keywords = ['wireless', 'wlan', 'wifi', 'wi-fi','fili']
      ltext=text.lower()
      words=ltext.split(' ')
      for w in words:
        for key in keywords:
          if w==key:
            return True
      return False
      
    def InterfaceInfo(self, index):
        features = {'SettingID':'', 'MACAddress':'', 'IpAddress':'', 'DefaultIPGateway':'', 'IpSubnet':''}
        info = {'GUID':'unknown', 'MAC':'unknown', 'IP':'unknown', 'Gateway':'unknown', 'Mask':'unknown'}
        items = executeQuery('Win32_NetworkAdapterConfiguration', " WHERE index = %s" % index)
        if (items):
            try:
                for obj in items:
                    keys = features.keys()
                    for key in keys:
                        features[key] = self.getSingleInfo(obj, key)
            except:
                raise RisorsaException("Impossibile ritrovare le informazioni sul dispositivo di rete") 
            finally:
                if (features['SettingID']):
                    info['GUID'] = features['SettingID']
                if (features['MACAddress']):
                    info['MAC'] = features['MACAddress']
                if (features['IpAddress']):
                    info['IP'] = features['IpAddress'][0]
                if (features['DefaultIPGateway']):
                    info['Gateway'] = features['DefaultIPGateway'][0]
                if (features['IpSubnet']):
                    info['Mask'] = features['IpSubnet'][0]
                return info
        else:
            raise RisorsaException("E' impossibile interrogare le risorse di rete")
      
    def profileDevice(self, obj):
        running = 0X3 #running Net Interface CODE
        features = {'Name':None, 'NetConnectionID':None, 'AdapterTypeId':None, 'GUID':None, 'NetConnectionStatus':None}
        dev = {'Name':'unknown', 'Descr':'unknown', 'Type':'unknown', 'GUID':'unknown', 'Status':0}
        
        try:
            devIndex = self.getSingleInfo(obj, 'Index')
            devInfo = self.InterfaceInfo(devIndex)
        except RisorsaException as e:
            raise RisorsaException(e)
        
        try:
            keys = features.keys()
            for key in keys:
                features[key] = self.getSingleInfo(obj, key)
        finally:
            if (features['Name'] != None):
                dev['Name'] = features['Name']
            if (features['NetConnectionID'] != None):
                dev['Descr'] = features['NetConnectionID']
                devNetConnID = features['NetConnectionID']
                if(self._is_wireless_text(devNetConnID) and features['AdapterTypeId'] != 9):
                    features['AdapterTypeId'] = 9
            if (features['AdapterTypeId'] != None):
                devType = features['AdapterTypeId']  
                dev['Type'] = NIC_TYPE[devType]
            if (features['GUID'] != None):
                dev['GUID'] = features['GUID']
            if (features['NetConnectionStatus'] != None):
                dev['Status'] = features['NetConnectionStatus']
            
            dev.update(devInfo)
            
            devxml = ET.Element('NetworkDevice')
            keys = dev.keys()
            for key in keys:
              devxml.append(self.xmlFormat(key, dev[key]))
            return devxml
            
    def profileModem(self, obj):
        features = {'Name':'', 'DeviceType':'', 'DeviceID':''}
        devName = 'unknown'
        devType = 'unknown'
        devID = 'unknown'
        try:
            keys = features.keys()
            for key in keys:
                features[key] = self.getSingleInfo(obj, key)
        finally:
            if (features['Name']):
                devName = features['Name']
            if (features['DeviceType']):
                devType = features['DeviceType']
            if (features['DeviceID']):
                devID = features['DeviceID']
            devxml = ET.Element('NetworkDevice')
            devxml.append(self.xmlFormat('Name', devName))
            devxml.append(self.xmlFormat('Type', devType))
            devxml.append(self.xmlFormat('ID', devID))
            return devxml
                   
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
        available_resources = set(['CPU', 'RAM', 'sistemaOperativo', 'rete', 'disco'])
        LocalProfiler.__init__(self, available_resources)

    def profile(self, resource=set()):
        pythoncom.CoInitialize()
        data = super(Profiler, self).profile(__name__, resource)
        pythoncom.CoUninitialize()
        return data
