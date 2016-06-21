# iptools.py
# -*- coding: utf-8 -*-

# Copyright (c) 2016 Fondazione Ugo Bordoni.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
'''
Created on 14/apr/2016

@author: ewedlund
'''
'''
Some useful functions for IP and Ethernet
'''

import logging
import netifaces
import re
import socket

import nem_exceptions

logger = logging.getLogger(__name__)

def getipaddr(host = 'finaluser.agcom244.fub.it', port = 443):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((host, port))
        ipaddr = s.getsockname()[0]
        #TODO: if not checkipsyntax(value):
    except socket.gaierror:
        ipaddr = ""
    return ipaddr

    
def get_if_ipaddress(ifname):
    neti_names = netifaces.interfaces()
    ipval = '127.0.0.1'
    for nn in neti_names:
        if ifname == nn:
            try:
                ipval = netifaces.ifaddresses(ifname)[netifaces.AF_INET][0]['addr']
            except:
                ipval = '127.0.0.1'
    return ipval

def get_mac_address(ip = None):
    '''Get mac address of the device with the given IP address.
    If ip == None, then get MAC address of device
    used for connecting to the Internet.'''
    if ip != None:
        ipaddr = ip
    else:
        ipaddr = getipaddr()
        
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

def get_dev(host = 'finaluser.agcom244.fub.it', port = 443, ip = None):
    '''
    restituisce scheda attiva (guid della scheda su Windows 
    '''
    if not ip:
        local_ip_address = getipaddr(host, port)
    else:
        local_ip_address = ip
    
    ''' Now get the associated device '''
    for ifName in netifaces.interfaces():
        all_addresses = netifaces.ifaddresses(ifName)
        if (netifaces.AF_INET in all_addresses):
            ip_addresses = all_addresses[netifaces.AF_INET]
            for address in ip_addresses:
                if ('addr' in address) and (address['addr'] == local_ip_address):
                    return ifName
    raise nem_exceptions.SysmonitorException('Impossibile ottenere il dettaglio dell\'interfaccia di rete', nem_exceptions.UNKDEV)
    
def get_network_mask(ip):
    '''
    Restituisce un intero rappresentante la maschera di rete, in formato CIDR, 
    dell'indirizzo IP in uso. In caso non si trova una maschera, torna 24 di default
    '''
    netmask = '255.255.255.0'

    inames = netifaces.interfaces()
    for i in inames:
        try:
            addrs = netifaces.ifaddresses(i)
            try:
                ipinfo = addrs[socket.AF_INET][0]
                address = ipinfo['addr']
                if (address == ip):
                    netmask = ipinfo['netmask']
                    return _maskConversion(netmask)
            except KeyError:
                pass
        except Exception as e:
            logger.warning("Errore durante il controllo dell'interfaccia %s. %s" % (i, e), exc_info=True)
    
    return _maskConversion(netmask)

def is_public_ip(ip):
    return (bool(re.search('^10\.|^172\.(1[6-9]|2[0-9]|3[01])\.|^192\.168\.', ip)) == False)
   
def checkipsyntax(ip):

    try:
        socket.inet_aton(ip)
        parts = ip.split('.')
        if len(parts) != 4:
            return False
    except Exception:
        return False
    
    return True

def _maskConversion(netmask):
    nip = str(netmask).split(".")
    if(len(nip) == 4):
        i = 0
        bini = range(0, len(nip))
        while i < len(nip):
            bini[i] = int(nip[i])
            i += 1
        bins = _convertDecToBin(bini)
        lastChar = 1
        maskcidr = 0
        i = 0
        while i < 4:
            j = 0
            while j < 8:
                if (bins[i][j] == 1):
                    if (lastChar == 0):
                        return 0
                    maskcidr = maskcidr + 1
                lastChar = bins[i][j]
                j = j + 1
            i = i + 1
    else:
        return 0
    return maskcidr
    
def _convertDecToBin(dec):
    i = 0
    binval = range(0, 4)
    for x in range(0, 4):
        binval[x] = range(0, 8)
    for i in range(0, 4):
        j = 7
        while j >= 0:
            binval[i][j] = (dec[i] & 1) + 0
            dec[i] /= 2
            j = j - 1
    return binval

