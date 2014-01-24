#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Fondazione Ugo Bordoni.
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
#
# This code is derived from: arprequest.py by Antoine Millet
# Original version:
#   -> https://pypi.python.org/pypi/arprequest

import ipcalc
from threading import Thread
import string
import re
from logger import logging
import socket
import platform
is_windows = (platform.system().startswith("Windows"))
logger = logging.getLogger()

if (is_windows):
    from ctypes import *
    import struct
    from threading import Thread
    import Queue
    """ Loading Windows system libraries should not be a problem """
    """ Iphplpapi should work on Win 2000 and above              """
    try:
        iphlpapi = windll.Iphlpapi
        ws2_32 = windll.ws2_32
    except WindowsError:
        """ Should it still fail """
        logger.error("Error loading windows system libraries!")
        raise Exception("Manca uno o più delle librerie Iphlapi.dll e ws2_32.dll")
else:
    from struct import pack, unpack
    import time
    import select

HW_TYPE_ETH = 0x0001
ETH_P_IP = 0x0800
ETH_P_ARP = 0x0806
ARP_REQUEST = 0x0001
ARP_REPLY = 0x0002
MAC_ADDR_LEN = 0x0006
IP_ADDR_LEN = 0x0004
TECHNICOLOR_MACS = ['^A..B1.E9']
TECHNICOLOR_IPS = ['192.168.1.253']


def _print_mac(value):
    return string.join(["%02X" % ord(b) for b in value], ':')

## TODO: this should be the same as _print_mac
""" Convert c_ulong*2 to a hexadecimal string or a printable ascii
string delimited by the 3rd parameter"""
def mac_straddr(mac, printable=False, delimiter=None):
    """ Expect a list of length 2 returned by arp_query """
    if len(mac) != 2:
        return -1
    if printable:
        if delimiter:
            m = ""
            for c in mac_straddr(mac):
                m += "%02x" % ord(c) + delimiter
            return m.rstrip(delimiter)

        return repr(mac_straddr(mac)).strip("\'")

    return struct.pack("L", mac[0])+struct.pack("H", mac[1])


def _print_ip(value):
    return string.join(["%d" % ord(b) for b in value], '.')

def _val2int(val):
    '''Hex to Integer.'''
    return int(''.join(['%02d'%ord(c) for c in val]), 16)

def _is_technicolor(ip, mac):
  if (not re.match("([0-9A-F]{2}:){5}[0-9A-F]", mac, re.I)):
    logger.warn("Errore nell'utilizzo della funzione _is_technicolor: formato MAC non corretto (%s)" % mac)

  for ip_technicolor in TECHNICOLOR_IPS:
    if (ip == ip_technicolor):
      logger.debug("Trovato possibile IP spurio di router Technicolor: %s" % ip)
      for mac_technicolor in TECHNICOLOR_MACS:
        if re.search(mac_technicolor, mac, re.I):
          logger.info("Trovato IP spurio di router Technicolor: %s [%s]" % (ip, mac))
          return True

  return False

def do_arping(if_dev_name, IPsrc, NETmask, realSubnet = True, timeout = 1, mac = None, threshold = 1):
    if is_windows:
        IPTable = do_win_arping(IPsrc, NETmask, realSubnet)
    else:
        IPTable = do_unix_arping(if_dev_name, IPsrc, NETmask, realSubnet, timeout, mac, threshold)

    hosts = "HOSTS: "
    for key in IPTable:
        hosts = hosts+"[%s|%s] " % (IPTable[key], key)
    logger.info(hosts)
    nHosts = len(IPTable)
    return nHosts


def do_unix_arping(if_dev_name, IPsrc, NETmask, realSubnet = True, timeout = 1, mac = None, threshold = 1):

    # Initialize a raw socket (requires super-user access
    my_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.SOCK_RAW)
    HOST = socket.gethostbyname(socket.gethostname())
#    my_socket.bind((HOST, socket.SOCK_RAW))
    my_socket.bind((if_dev_name, socket.SOCK_RAW))
#    my_socket.bind((if_dev_name, 0))

    if (mac):
        MACsrc = "".join(chr(int(macEL, 16)) for macEL in mac.split(':'))
    else:
        logger.info("Richiesta esecuzione di arping senza la specifica del MAC address.")
        return 0
    MACdst = "\xFF"*6

    logger.debug("MAC_source = %s" % mac.upper())
    IPsrc = socket.gethostbyname(IPsrc)
    logger.debug("IP source = %s" % IPsrc)
    IPnet = ipcalc.Network('%s/%d' % (IPsrc, NETmask))
    net = IPnet.network()
    bcast = IPnet.broadcast()
    logger.debug("network = %s" % net)
    lasting = 2 ** (32 - NETmask)
    index = 0

    ### Send ARP requests to all IPs ###
    for IPdst in IPnet:
        if ((IPdst.hex() == net.hex() or IPdst.hex() == bcast.hex()) and realSubnet):
            logger.debug("Saltato ip %s" % IPdst)
        elif(IPdst.dq == IPsrc):
            logger.debug("Salto il mio ip %s" % IPdst)
        else:
            # Send ARP reuqest
            IPdst = str(IPdst)
            # logger.debug('Arping host %s' % IPdst)
#             send = Thread(target=send_arp_request, args=(IPsrc, IPdst, if_dev_name, my_socket))
#             send.start()
            send_arp_request(IPsrc, IPdst, if_dev_name, my_socket)
            index += 1

        lasting -= 1

        #if (index >= MAX or lasting <= 0):
        if (lasting <= 0):
          index = 0

          try:
            IPtable = receive_arp_response(mac, my_socket, timeout)
          except Exception as e:
            logger.error("Errore durante la ricezione degli arping: %s" % e)

        #TODO why this?
#        if(nHosts > threshold):
#            break
    my_socket.close()
    return IPtable


# dev, ipAddress, netMask, realSubnet, 1, mac, threshold
def send_arp_request(src_ip, dest_ip, if_dev_name, my_socket):
    '''Send ARP request'''

    # Create packet :
    frame = [
        ###  ETHERNET part ###
        # Dest MAC address (=broadcast) : TODO should be all 0???
        pack('!6B', *(0xFF,) * 6),
        # Source MAC address :
        my_socket.getsockname()[4],
        # Protocol type (=ARP) :
        pack('!H', ETH_P_ARP),

        ### ARP part ###
        # HW and protocol types and address lenghts (=Ethernet/IP/6/4 bytes) :
        pack('!HHBB', HW_TYPE_ETH, ETH_P_IP, MAC_ADDR_LEN, IP_ADDR_LEN),
        # Operation type (=ARP Request) :
        pack('!H', ARP_REQUEST),
        # Source MAC address :
        my_socket.getsockname()[4],
        # Source IP address :
        pack('!4B', *[int(x) for x in src_ip.split('.')]),
        # Target MAC address (=00*6) :
        pack('!6B', *(0,) * 6),
        # Target IP address :
        pack('!4B', *[int(x) for x in dest_ip.split('.')])
    ]
    # Send the packet
    my_socket.send(''.join(frame))

def receive_arp_response(mac_addr, my_socket, timeout):

    IPtable = {}

    '''Wait for response'''
    timeLeft = timeout
    stopTime = time.time() + timeout;

    while True:
#         startTime = time.time()
        timeLeft = stopTime - time.time()
        whatReady = select.select([my_socket], [], [], timeLeft)
        if whatReady[0] == []:  # Timeout
            break
        #TODO: is this really necessary?
        if time.time() > stopTime:
            break

        # Get packet frame :
        frame = my_socket.recv(1024)

        # Get protocol type :
        proto_type = _val2int(unpack('!2s', frame[12:14])[0])
        if proto_type != ETH_P_ARP:
            continue # Not ARP, skip

        # Get Operation type :
        op = _val2int(unpack('!2s', frame[20:22])[0])
        if op != ARP_REPLY:
            continue # Not ARP response, skip

        # Get addresses :
        arp_headers = frame[18:20]
        arp_headers_values = unpack('!1s1s', arp_headers)
        hw_size, pt_size = [_val2int(v) for v in arp_headers_values]
        total_addresses_byte = hw_size * 2 + pt_size * 2
        arp_addrs = frame[22:22 + total_addresses_byte]
        src_hw, src_pt, dst_hw, dst_pt = unpack('!%ss%ss%ss%ss'
                % (hw_size, pt_size, hw_size, pt_size), arp_addrs)
        dest_mac = _print_mac(dst_hw)

        # Compare dest mac address in packet to the one we looked for :
        if (dest_mac.strip().upper() == mac_addr.strip().upper()):
            src_mac = _print_mac(src_hw)
            src_ip = _print_ip(src_pt)
            # TODO add check if found enough to stop
            if (src_ip not in IPtable):
                if (not _is_technicolor(src_ip, src_mac)):
                    IPtable[src_ip] = src_mac
                    logger.info('Trovato Host %s con indirizzo fisico %s' % (src_ip, src_mac))
            else:
                logger.debug("Found response from Technicolor")
    return IPtable


###########################
## Parte windows
###########################


def do_win_arping(IPsrc = None, NETmask=24, realSubnet=True):
    IPnet = ipcalc.Network('%s/%d' % (IPsrc, NETmask))
    result_queue = Queue.Queue()
    net = IPnet.network()
    bcast = IPnet.broadcast()
    logger.debug("network = %s" % net)
    lasting = 2 ** (32 - NETmask)
    index = 0
    threads = []

    ### Send ARP requests to all IPs ###
    for IPdst in IPnet:
        if ((IPdst.hex() == net.hex() or IPdst.hex() == bcast.hex()) and realSubnet):
            logger.debug("Saltato ip \'%s\'" % IPdst)
        elif(IPdst.dq == IPsrc):
            logger.debug("Salto il mio ip \'%s\'" % IPdst)
        else:
            t = Thread(target=_send_one_win_arp, args=(IPdst, result_queue))
            threads.append(t)

    [x.start() for x in threads]
    [x.join() for x in threads]

    mytable = {}

    items_in_queue = True
    while items_in_queue:
        try:
            ip,mac = result_queue.get_nowait()
            if (ip not in mytable):
                mytable[ip] = mac
        except Queue.Empty:
            items_in_queue = False
    return mytable


def _send_one_win_arp(IPdst, result_queue):
    # Send ARP reuqest
    logger.debug("Sending ARP to \'%s\'" % IPdst)
    IPdst = str(IPdst)
    mac_addr = (c_ulong*2)()
    addr_len = c_ulong(6)
    dest_ip = ws2_32.inet_addr(IPdst)

    src_ip = ws2_32.inet_addr(socket.gethostbyname(socket.gethostname()))

    error = iphlpapi.SendARP(dest_ip, src_ip, byref(mac_addr), byref(addr_len))

    if error:
        if (int(error) != 31):
            logger.error("Warning: SendARP failed! Error code: %d", int(error))
    else:
        mac_str = mac_straddr(mac_addr, True, ":")
        if (not _is_technicolor(IPdst, mac_str)):
            result_queue.put((IPdst, mac_str))
        else :
            logger.debug("Found response from Technicolor")

if __name__ == '__main__':
    #from arprequest import ArpRequest
#     ar = ArpRequest('192.168.112.2', 'eth0', '192.168.112.24')
#     result = ar.request()
    print do_arping('eth0', '192.168.112.24', 24, True, 1, '78:2b:cb:96:55:3e', 1)
    
#    print do_arping(None, '192.168.208.4', 24, True)
#    print do_arping('{5FC94950-68BA-417F-97DC-47B0722814F5}', '172.16.141.128', 24, True, 1, '00:0c:29:cb:5f:e7', 1)
#    print do_win_arping('192.168.208.4', 24)
#     print(result)
