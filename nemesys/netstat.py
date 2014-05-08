'''
Created on 13/nov/2013

@author: ewedlund
'''

import platform
import re
import netifaces
import psutil

LINUX_RESOURCE_PATH="/sys/class/net"


def get_netstat(if_device):
	if not if_device:
		raise NetstatException("No device identified")
	platform_name = platform.system().lower()
	if platform_name.startswith('win'):
		return NetstatWindows(if_device)
	elif platform_name.startswith('lin'):
 		return NetstatLinux(if_device)
	elif platform_name.startswith('darwin'):
		return NetstatDarwin(if_device)

'''
Eccezione istanzazione Risorsa
'''
class NetstatException(Exception):

	def __init__(self, message):
		Exception.__init__(self, message)


class Netstat(object):

	def __init__(self, if_device=None):
		self.if_device = if_device

	def get_if_device(self):
		return self.if_device

	def get_rx_bytes(self):
		if not self.if_device:
			raise NetstatException("No device identified")
		# Handle different versions of psutil
		try:
			counters_per_nic = psutil.network_io_counters(pernic=True)
		except AttributeError:
			counters_per_nic = psutil.net_io_counters(pernic=True)
		if self.if_device in counters_per_nic:
			rx_bytes = counters_per_nic[self.if_device].bytes_recv
		else:
			raise NetstatException("Could not find counters for device %s" % str(self.if_device))
		return long(rx_bytes)

	def get_tx_bytes(self):
		if not self.if_device:
			raise NetstatException("No device identified")
		# Handle different versions of psutil
		try:
			counters_per_nic = psutil.network_io_counters(pernic=True)
		except AttributeError:
			counters_per_nic = psutil.net_io_counters(pernic=True)
		if self.if_device in counters_per_nic:
			tx_bytes = counters_per_nic[self.if_device].bytes_sent
		else:
			raise NetstatException("Could not find counters for device %s" % str(self.if_device))
		return long(tx_bytes)


class NetstatWindows(Netstat):
	'''
    Netstat funcions on Windows platforms
    '''

	def __init__(self, if_device_guid=None):
		super(NetstatWindows, self).__init__(if_device_guid)
		self._device_guid = if_device_guid
		if (if_device_guid != None):
			self.device_id,self.if_device = self._get_psutil_device_from_guid(if_device_guid)
		else:
			raise NetstatException("No device given!")


	def is_device_active(self, if_device_guid=None):
		is_active = False
		if if_device_guid:
			whereCondition = " WHERE SettingID = \"" + if_device_guid + "\""
			entry_name = "Index"
			index = self._get_entry_generic("Win32_NetworkAdapterConfiguration", whereCondition, entry_name)
		else:
			index = self.device_id
		whereCondition = " WHERE DeviceId = \"" + str(index) + "\""
		entry_name = "NetConnectionStatus"
		status = self._get_entry_generic("Win32_NetworkAdapter", whereCondition, entry_name)
		if (status and (int(status) == 2 or int(status) == 9)):
			is_active = True
		return is_active


	def _get_psutil_device_from_guid(self, guid):
		# Since Win32_NetworkAdapter does not have GUID on windows XP
		# We need to get the NetConnectionID in two phases
		# 1. get the id of the interface from Win32_NetworkAdapterConfiguration
		try:
			whereCondition = " WHERE SettingID = \"" + guid + "\""
			entry_name = "Index"
			index = self._get_entry_generic("Win32_NetworkAdapterConfiguration", whereCondition, entry_name)
		except Exception as e:
			raise NetstatException("Could not get index for device with GUID %s" % str(guid))
		if index != None:
# 			# 2. Now get NetConnectionID from Win32_NetworkAdapter
			try:
				whereCondition = " WHERE DeviceId = \"" + str(index) + "\""
				entry_name = "NetConnectionID"
				device = self._get_entry_generic("Win32_NetworkAdapter", whereCondition, entry_name)
				if not device:
					raise Exception
				return index,device
			except Exception as e:
				raise NetstatException("Could not find device with GUID %s and index %d" % (str(guid),int(index)))
		else:
			raise NetstatException("No index found for device with GUID %s" % str(guid))


	def get_device_name(self, ip_address):
		all_devices = netifaces.interfaces()
		if_dev_name = None
		found = False
		for if_dev in all_devices:
			if_ip_addresses = netifaces.ifaddresses(if_dev)[netifaces.AF_INET]
			for if_ip_address in if_ip_addresses:
				if (if_ip_address['addr'] == ip_address):
					if_dev_name = if_dev
					found = True
					break
			if found: break
	    # Now we have the "Setting ID" for the interface
	    # in class Wind32_NetworkAdapterConfiguration
	    # We now need to get the value of "Description"
	    # in the same class
		entry_value = None
		where_condition = " WHERE SettingID = \"" + if_dev_name + "\""
		entry_name = "Description"
		entry_value = self._get_entry_generic("Win32_NetworkAdapterConfiguration", whereCondition, entry_name)
		return entry_value

	def get_timestamp(self):
		timestamp = float(self._get_entry_generic(entry_name = "Timestamp_Perftime"))
		frequency = float(self._get_entry_generic(entry_name = "Frequency_Perftime"))
		return timestamp/frequency

	def _get_entry_generic(self, wmi_class=None,
						whereCondition=None,
						entry_name="*"):
		try:
    		 import pythoncom
		except ImportError:
		     raise NetstatException("Missing WMI library")
		pythoncom.CoInitialize()
		try:
    		 return self._get_entry_generic_wrapped(wmi_class, whereCondition, entry_name)
		finally:
		     pythoncom.CoUninitialize()


	def _get_entry_generic_wrapped(self, wmi_class=None,
						whereCondition=None,
						entry_name="*"):
		entry_value = None
		''' TODO: more intelligent search?'''
		if not whereCondition:
		    whereCondition=" WHERE Name Like \"" + self.if_device_search_string + "%\""
		if not wmi_class:
		    wmi_class="Win32_PerfRawData_Tcpip_NetworkAdapter"
		queryString = None
		try:
    		 import win32com.client
    		 import pythoncom
		except ImportError:
		     raise NetstatException("Missing WMI library")
		try:
			objWMIService = win32com.client.Dispatch("WbemScripting.SWbemLocator")
			objSWbemServices = objWMIService.ConnectServer(".", "root\cimv2")
			queryString = "SELECT " + entry_name + " FROM " + wmi_class + whereCondition
			result = objSWbemServices.ExecQuery(queryString)
		except Exception as e:
			raise NetstatException("Impossibile eseguire query al server root\cimv2: ")
		if (result):
			try:
				found = False
				for obj in result:
					value = obj.__getattr__(entry_name)
					if value != None:
						if found:
							raise NetstatException("Found more than one entry for search string " + whereCondition)
						else:
							found = True
							entry_value = value
			except:
				raise NetstatException("Could not get " + entry_name + " from result")
		else:
			raise NetstatException("Query for " + entry_name + " returned empty result")
		return entry_value


class NetstatLinux(Netstat):
	'''
    Netstat funcions on Linux platforms
    '''

	def __init__(self, if_device):
		super(NetstatLinux, self).__init__(if_device)

	def get_device_name(self, ip_address):
		all_devices = netifaces.interfaces()
		if_dev_name = None
		found = False
		for if_dev in all_devices:
			if_ip_addresses = netifaces.ifaddresses(if_dev)[netifaces.AF_INET]
			for if_ip_address in if_ip_addresses:
				if (if_ip_address['addr'] == ip_address):
					if_dev_name = if_dev
					found = True
					break
			if found: break
		return if_dev_name

class NetstatDarwin(NetstatLinux):
	'''
    Netstat funcions on MacOS platforms
    '''

	def __init__(self, if_device):
		super(NetstatLinux, self).__init__(if_device)

def _read_number_from_file(filename):
	with open(filename) as f:
		return int(f.readline())

if __name__ == '__main__':
	import time
	import sysmonitor
	dev = sysmonitor.getDev()
	my_netstat = get_netstat(dev)
	print "RX bytes", my_netstat.get_rx_bytes()
	print "TX bytes", my_netstat.get_tx_bytes()