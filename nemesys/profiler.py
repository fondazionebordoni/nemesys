# sysmonitor.py
# -*- coding: utf8 -*-

# Copyright (c) 2016 Fondazione Ugo Bordoni.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import platform
import psutil
import os

import iptools
from collections import OrderedDict


LINUX_RESOURCE_PATH='/sys/class/net/'
WIFI_WORDS = ['wireless', 'wifi', 'wi-fi', 'senzafili', 'wlan', 'fili']
ERROR_NET_IF = 'Impossibile ottenere informazioni sulle interfacce di rete'

class Device(object):
    
    def __init__(self, name):
        self._name = name
        self._ipaddr = '0.0.0.0'
        self._macaddr = '00:00:00:00:00:00'
        self._type_string = 'Unknown'
        self._is_active = False
        self._is_enabled = False 
        self._guid = None
    
    def __str__(self, *args, **kwargs):
        d = self.dict()
        s = ''
        for key in d: 
            s += "%s : %s\n" % (key, d[key])
        return s

    def dict(self):
        return OrderedDict([('Name', self._name),\
#TODO:        ('Descr',self._description),\
                ('IP', self._ipaddr),\
#TODO:        ('Mask',self._mask),\
                ('MAC', self._macaddr),\
                ('Type', self._type_string),\
                ('isEnabled', self._is_enabled),\
                ('isActive', self._is_active)\
                ])

    @property
    def name(self):
        return self._name
    
    def set_ipaddr(self, ipaddr):
        self._ipaddr = ipaddr
    
    @property
    def ipaddr(self):
        return self._ipaddr
    
    def set_macaddr(self, macaddr):
        self._macaddr = macaddr
    
    @property
    def macaddr(self):
        return self._macaddr
    
    def set_active(self, is_active):
        self._is_active = is_active 

    @property
    def is_active(self):
        return self._is_active
        
    def set_enabled(self, is_enabled):
        self._is_enabled = is_enabled
        
    @property
    def is_enabled(self):
        return self._is_enabled

    def set_type(self, type_string):
        self._type_string = type_string
    
    @property
    def type(self):
        return self._type_string
    
    def set_guid(self, guid):
        self._guid = guid
    
    @property
    def guid(self):
        return self._guid
    
    
    
def get_profiler():
    platform_name = platform.system().lower()
    if platform_name.startswith('win'):
        return ProfilerWindows()
    elif platform_name.startswith('lin'):
        return ProfilerLinux()
    elif platform_name.startswith('darwin'):
        return ProfilerDarwin()

'''
Exception from Profiler
'''
class ProfilerException(Exception):

    def __init__(self, message):
        Exception.__init__(self, message)


class Profiler(object):

    def __init__(self):
        self.ipaddr = ""

    def cpuLoad(self):
        return psutil.cpu_percent(0.5)

    def total_memory(self):
        return psutil.virtual_memory().total

    def percentage_ram_usage(self):
        meminfo = psutil.virtual_memory()
        total = meminfo.total
        used = meminfo.used
        try:
            buffers = meminfo.buffers
        except AttributeError:
            buffers = 0
        try:
            cached = meminfo.cached
        except AttributeError:
            cached = 0
        real_used = used - buffers - cached
        return int(float(real_used) / float(total) * 100.0)


class ProfilerLinux(Profiler):
    
    def __init__(self):
        super(ProfilerLinux, self).__init__()

    def is_wireless_active(self):
        descriptors = ['type', 'operstate']
        val = {'type': ' ', 'operstate': ' '}
        devlist = os.listdir(LINUX_RESOURCE_PATH)
        if len(devlist) > 0:
            for dev in devlist:
                for descriptor in descriptors:
                    fname = LINUX_RESOURCE_PATH + str(dev) + '/' + str(descriptor)
                    f = open(fname)
                    val[descriptor] = f.readline()

                if val['operstate'].rstrip() == "up":
                    # Device is enabled
                    wifipath = LINUX_RESOURCE_PATH + str(dev)
                    inner_folders = os.listdir(wifipath)
                    for folder in inner_folders:
                        for mot in WIFI_WORDS:
                            if str(folder).lower() == mot:
                                return True
        return False


    def get_all_devices(self):
        'TODO: get netmask too?'
        wireless = ['wireless', 'wifi', 'wi-fi', 'senzafili', 'wlan']
        descriptors = ['address', 'type', 'operstate', 'uevent']
        
        self.ipaddr = iptools.getipaddr()
        devlist = os.listdir(LINUX_RESOURCE_PATH)
        devices = []
        if len(devlist) > 0:
            for dev in devlist:
                val = {}
                for des in descriptors:
                    fname = LINUX_RESOURCE_PATH + str(dev) + '/' + str(des)
                    f = open(fname)
                    val[des] = f.read().strip('\n')

                device = Device(dev)

                ipdev = iptools.get_if_ipaddress(dev)
                device.set_ipaddr(ipdev)
                device.set_active(ipdev == self.ipaddr)
                device.set_enabled(val['operstate'] != "down") # Can be 'unknown'
                    
                if (val['type'] == '1'):
                    device.set_type('Ethernet 802.3')
                elif (val['type'] == '512'):
                    device.set_type('WWAN')
                elif (val['type'] == '772'):
                    device.set_type('loopback')
                
                for word in wireless:
                    if word in val['uevent']:
                        device.set_type('Wireless')
                
                device.set_macaddr(val['address'])
                devices.append(device)
        return devices



class ProfilerWindows(Profiler):
    
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
        13:'1394', \
        14:'WWAN' \
        }

    
    def __init__(self):
        super(ProfilerWindows, self).__init__()

    def is_wireless_active(self):
        wmi_class = 'Win32_NetworkAdapter'
        where_condition = " WHERE Manufacturer != 'Microsoft' "
        self._init_query()
        mac_enabled_devices = self._get_enabled_interfaces()
        devices = self._executeQuery(wmi_class, where_condition)
        is_active = False
        try:
            if len(devices) == 0:
                raise ProfilerException(ERROR_NET_IF)
            else:
                for device in devices:
                    '''Get info about one device from WMI query result'''
                    net_connection_id = self._getSingleInfo(device, 'NetConnectionID')
                    mac_address = self._getSingleInfo(device, 'MACAddress')
                    if net_connection_id and mac_address:
                        if self._is_wireless_text(net_connection_id):
                            if mac_address in mac_enabled_devices:
                                is_active = True
                                break
        finally:
            self._exit_query()
        return is_active

    def get_all_devices(self):
        features = {'Name':None, 'NetConnectionID':None, 'AdapterTypeId':None, 'NetConnectionStatus':None, 'NetEnabled':None}
        devices = []
        self._init_query()
        items = self._executeQuery('Win32_NetworkAdapter', " WHERE Manufacturer != 'Microsoft' ")
        for obj in items:
            
            devIndex = getattr(obj, 'Index')
            device = self._get_device(devIndex)
            
            keys = features.keys()
            for key in keys:
                try:
                    features[key] = getattr(obj, key)
                except:
                    features[key] = 'unknown'
        
#                     if (features['Name'] != None):
#                         device = Device(features['Name'])
# 
# #                         dev['Name'] = features['Name']
# #                         devName = features['Name']
# #                         if(self._is_hspa_text(devName) and features['AdapterTypeId'] != 14):
# #                             features['AdapterTypeId'] = 14
#                     else:
#                         device = Device('No Name')
#                 if (features['NetConnectionID'] != None):
#                     dev['Descr'] = features['NetConnectionID']
#                     devNetConnID = features['NetConnectionID']
#                     if(self._is_wireless_text(devNetConnID) and features['AdapterTypeId'] != 9):
#                         features['AdapterTypeId'] = 9
            if (features['AdapterTypeId'] != None):
                devType = features['AdapterTypeId']  
                device.set_type(ProfilerWindows.NIC_TYPE[devType])
            device.set_active(features['NetConnectionStatus'] == 2)
            device.set_enabled(features['NetEnabled'] == True)
            devices.append(device)
        self._exit_query()
        return devices
                    
    def _init_query(self):
        try:
            import pythoncom
        except ImportError:
            raise ProfilerException("Missing WMI library")
        pythoncom.CoInitialize()

    def _exit_query(self):
        try:
            import pythoncom
        except ImportError:
            raise ProfilerException("Missing WMI library")
        pythoncom.CoUninitialize()


    def _executeQuery(self, wmi_class, whereCondition=""):
        try:
            import win32com.client
        except ImportError:
            raise ProfilerException("Missing WMI library")

        try: 
            objWMIService = win32com.client.Dispatch("WbemScripting.SWbemLocator")
            objSWbemServices = objWMIService.ConnectServer(".", "root\cimv2")
            colItems = objSWbemServices.ExecQuery("SELECT * FROM " + wmi_class + whereCondition)
        except:
            raise ProfilerException("Errore nella query al server root\cimv2")
        return colItems

    def _getSingleInfo(self, obj, attr):
        try:
            val = obj.__getattr__(attr)
            if val != None:
                return val
            else:
                return None
        except AttributeError:
            return None


    def _get_enabled_interfaces(self):
        mac_enabled_devices = []
        devices = self._executeQuery('Win32_NetworkAdapterConfiguration', "")
        if (devices):
            for device in devices:
                ipaddrlist = self._getSingleInfo(device, 'IPAddress')
                if ipaddrlist:
                    mac_address = self._getSingleInfo(device, 'MACAddress')
                    is_enabled = self._getSingleInfo(device,'IPEnabled')
                    if str(is_enabled).lower() == 'true':
                        mac_enabled_devices.append(mac_address)
        else:
            raise ProfilerException(ERROR_NET_IF)
        return mac_enabled_devices 

    def _is_wireless_text(self,text):
        ltext = text.lower()
        words = ltext.split(' ')
        for w in words:
            for key in WIFI_WORDS:
                if w == key:
                    return True
        return False

    def _get_device(self, index):
        features = {'SettingID':'', 'MACAddress':'', 'IpAddress':'', 'DefaultIPGateway':'', 'IpSubnet':'', 'Description':''}
        items = self._executeQuery('Win32_NetworkAdapterConfiguration', " WHERE index = %s" % index)
        if (items):
            try:
                for obj in items:
                    keys = features.keys()
                    for key in keys:
                        features[key] = getattr(obj, key)
            except:
                raise ProfilerException("Impossibile ritrovare le informazioni sul dispositivo di rete") 
            if (features['Description']):
                device = Device(features['Description'])
            else:
                device = Device('No Name')
            if (features['SettingID']):
                device.set_guid(features['SettingID'])
            if (features['MACAddress']):
                device.set_macaddr(features['MACAddress'])
            if (features['IpAddress']):
                device.set_ipaddr(features['IpAddress'][0])
#             if (features['DefaultIPGateway']):
#                 device.set_gw(features['DefaultIPGateway'][0])
#             if (features['IpSubnet']):
#                 device.set_mask(features['IpSubnet'][0])
            return device
        else:
            raise ProfilerException("E' impossibile interrogare le risorse di rete")

class ProfilerDarwin(Profiler):
    
    
    def __init__(self):
        super(ProfilerDarwin, self).__init__()

    def get_all_devices(self):
        cmdline = 'system_profiler SPNetworkDataType -xml -detailLevel full'
        xml_from_system_profiler = os.popen(cmdline)
        return self.get_all_devices_from_xml(xml_from_system_profiler)

    def is_wireless_active(self):
        cmdline = 'system_profiler SPNetworkDataType -xml -detailLevel full'
        xml_from_system_profiler = os.popen(cmdline)
        return self.is_wireless_active_from_xml(xml_from_system_profiler)

    def is_wireless_active_from_xml(self, xml_file):
        import xml.etree.ElementTree as ET
        
        wireless_is_active = False
        descriptors = {}
        try:
            spxml = ET.parse(xml_file)
            devices = spxml.findall('array/dict/array/dict')
        except:
            raise ProfilerException(ERROR_NET_IF)
          
        for dev in devices:
            descriptors = {}
            app = spxml
            app._setroot(dev)
            allnodes = list(app.iter())
            for n in allnodes:
                capture = True
                if n.tag == 'key':
                    capture = False
                    prev_key = n.text     
                if capture and (n.tag == 'string' or n.tag == 'integer'):
                    descriptors[prev_key] = n.text
                            
            if 'Addresses' in descriptors:
                # Means dev is enabled
                if descriptors['type'].lower() == 'airport':
                    wireless_is_active = True

        return wireless_is_active

    #TODO: use xmltodict instead
    def get_all_devices_from_xml(self, xml_file):
        import xml.etree.ElementTree as ET
        descriptors = {}
        self.ipaddr = iptools.getipaddr()
        try:
            spxml = ET.parse(xml_file)
            xmldevices = spxml.findall('array/dict/array/dict')
        except Exception:
            raise ProfilerException(ERROR_NET_IF)
        
        devices = []
        for dev in xmldevices:
            descriptors = {}
            isActive = False
            isEnabled = False
            app = spxml
            app._setroot(dev)
            allnodes = list(app.iter())
            for n in allnodes:
                capture = 1
                if n.tag == 'key':
                    capture = 0
                    prev_key = n.text     
                if capture and (n.tag == 'string' or n.tag == 'integer'):
                    descriptors[prev_key] = n.text
                            
            if 'Addresses' in descriptors:
                isEnabled = True
            if 'NetworkSignature' in descriptors:
                isActive = True

            if descriptors['type'].lower() == 'ethernet':
                devType = 'Ethernet 802.3'
                if descriptors['_name'].lower() == 'mbbethernet':
                    devType = 'WWAN'
            elif descriptors['type'].lower() == 'airport':
                devType = 'Wireless'
            elif descriptors['type'].lower() == 'ppp (pppserial)':
                devType = 'WWAN'
            else:
                devType = 'Other'
            
            device = Device(descriptors['interface'])
            device.set_active(isActive)
            device.set_enabled(isEnabled)
            device.set_ipaddr(descriptors.get('Addresses','unknown'))
            device.set_type(devType)
            device.set_macaddr(descriptors.get('MAC Address','unknown'))
            devices.append(device)

        return devices
    

