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


import psutil, os
import netifaces
import platform
import socket

LINUX_RESOURCE_PATH="/sys/class/net"
WIFI_WORDS = ['wireless', 'wifi', 'wi-fi', 'senzafili', 'wlan', 'fili']
ERROR_NET_IF = 'Impossibile ottenere informazioni sulle interfacce di rete'


def get_profiler():
    platform_name = platform.system().lower()
    if platform_name.startswith('win'):
        return ProfilerWindows()
    elif platform_name.startswith('lin'):
        return ProfilerLinux()
    elif platform_name.startswith('darwin'):
        return ProfilerDarwin()

'''
Eccezione istanzazione Risorsa
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


    def getipaddr(self):
        if self.ipaddr == "":
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("www.fub.it", 80))
                self.ipaddr = s.getsockname()[0]
            except socket.gaierror:
                pass
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
    
    def get_mac_address(self, ip = None):
        '''Get mac address of the device with the given IP address.
        If ip == None, then get MAC address of device
        used for connecting to the Internet.'''
        if ip != None:
            ipaddr = ip
        else:
            ipaddr = self.getipaddr()
            
        for if_dev in netifaces.interfaces():
            addrs = netifaces.ifaddresses(if_dev)
            try:
                if_mac = addrs[netifaces.AF_LINK][0]['addr']
                if_ip = addrs[netifaces.AF_INET][0]['addr']
            except IndexError: #ignore ifaces that dont have MAC or IP
                if_mac = if_ip = None
            except KeyError:
                if_mac = if_ip = None
            if if_ip == ipaddr:
                return if_mac
        return None
    



class ProfilerLinux(Profiler):
    
    def __init__(self):
        super(ProfilerLinux, self).__init__()

    def is_wireless_active(self):
        wireless_is_active = False
        devpath = '/sys/class/net/'
        descriptors = ['type', 'operstate']
        val = {'type': ' ', 'operstate': ' '}
        devlist = os.listdir(devpath)
        if len(devlist) > 0:
            for dev in devlist:
                for descriptor in descriptors:
                    fname = devpath + str(dev) + '/' + str(descriptor)
                    f = open(fname)
                    val[descriptor] = f.readline()

                if val['operstate'].rstrip() == "up":
                    # Device is enabled
                    wifipath = devpath + str(dev)
                    inner_folders = os.listdir(wifipath)
                    for folder in inner_folders:
                        for mot in WIFI_WORDS:
                            if str(folder).lower() == mot:
                                wireless_is_active = True
                                
                if wireless_is_active:
                    break

        return wireless_is_active


class ProfilerWindows(Profiler):
    
    def __init__(self):
        super(ProfilerWindows, self).__init__()

    def is_wireless_active(self):
        wmi_class = 'Win32_NetworkAdapter'
        where_condition = " WHERE Manufacturer != 'Microsoft' "
        mac_enabled_devices = self._get_enabled_interfaces()
        devices = self._executeQuery(wmi_class, where_condition)
        if len(devices) == 0:
            raise ProfilerException(ERROR_NET_IF)
        else:
            for device in devices:
                '''Get info about one device from WMI query result'''
                net_connection_id = self._getSingleInfo(device, 'NetConnectionID')
                mac_address = self._getSingleInfo(device, 'MACAddress')
                if net_connection_id and mac_address:
                    print "Checking device with mac %s" % mac_address
                    if self._is_wireless_text(net_connection_id):
                        if mac_address in mac_enabled_devices:
                            return True
            return False


    def _executeQuery(self, wmi_class, whereCondition=""):   
        try:
            import pythoncom
            import win32com.client
        except ImportError:
            raise ProfilerException("Missing WMI library")

        try: 
            objWMIService = win32com.client.Dispatch("WbemScripting.SWbemLocator")
            objSWbemServices = objWMIService.ConnectServer(".", "root\cimv2")
            colItems = objSWbemServices.ExecQuery("SELECT * FROM " + wmi_class + whereCondition)
        except:
            raise ProfilerException("Errore nella query al server root\cimv2")
        finally:
            pythoncom.CoInitialize()
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
#                         if ipaddr in ipaddrlist:
#                             self._activeMAC = mac_address
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


class ProfilerDarwin(Profiler):
    
    
    def __init__(self):
        super(ProfilerDarwin, self).__init__()


    def is_wireless_active(self):
        cmdline = 'system_profiler SPNetworkDataType -xml -detailLevel full'
        xml_from_system_profiler = os.popen(cmdline)
        return self.is_wireless_active_from_xml(xml_from_system_profiler)

    def is_wireless_active_from_xml(self, xml_text):
        import xml.etree.ElementTree as ET
        
        wireless_is_active = False
        descriptors = {}
        try:
            spxml = ET.parse(xml_text)
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

