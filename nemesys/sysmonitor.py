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

from logger import logging
from sysmonitorexception import SysmonitorException
# from xml.etree import ElementTree as ET
import checkhost
import netifaces
import platform
import socket
import sysmonitorexception

platform_name = platform.system().lower()
import profiler

# TODO Decidere se, quando non riesco a determinare i valori, sollevo eccezione
STRICT_CHECK = True

CHECK_ALL = "ALL"
CHECK_MEDIUM = "MEDIUM"

tag_threshold = 'SystemProfilerThreshold'
tag_avMem = 'RAM.totalPhysicalMemory'
tag_memLoad = 'RAM.RAMUsage'
#tag_wireless = 'rete.NetworkDevice/Type'
tag_wireless = 'wireless.ActiveWLAN'
tag_ip = 'ipAddr' #to check
tag_cpu = 'CPU.cpuLoad'
tag_hosts = 'hostNumber'

# Soglie di sistema
# ------------------------------------------------------------------------------
# Massima quantità di host in rete
th_host = 1
# Minima memoria disponibile
th_avMem = 134217728
# Massimo carico percentuale sulla memoria
th_memLoad = 95
# Massimo carico percentuale sulla CPU
th_cpu = 85

logger = logging.getLogger()
my_profiler = profiler.get_profiler()

def checkcpu():

    value = my_profiler.cpuLoad()
    if value < 0 or value > 100:
        raise SysmonitorException('Valore di occupazione della cpu non conforme.', sysmonitorexception.BADCPU)

    if value > th_cpu:
        raise SysmonitorException('CPU occupata', sysmonitorexception.WARNCPU)


def checkmem():

    avMem = my_profiler.total_memory()
    logger.debug("Memoria disponibile: %2f" % avMem)
    if avMem < 0:
        raise SysmonitorException('Valore di memoria disponibile non conforme.', sysmonitorexception.BADMEM)
    if avMem < th_avMem:
        raise SysmonitorException('Memoria disponibile non sufficiente.', sysmonitorexception.LOWMEM)
    
    memLoad = my_profiler.percentage_ram_usage()
    logger.debug("Memoria occupata: %d%%" % memLoad)
    if memLoad < 0 or memLoad > 100:
        raise SysmonitorException('Valore di occupazione della memoria non conforme.', sysmonitorexception.INVALIDMEM)
    if memLoad > th_memLoad:
        raise SysmonitorException('Memoria occupata.', sysmonitorexception.OVERMEM)


def checkwireless():
    if my_profiler.is_wireless_active():
        raise SysmonitorException('Wireless LAN attiva.', sysmonitorexception.WARNWLAN)
            


def checkhosts(bandwidth_up, bandwidth_down, ispid, arping = 1):

    ip = getIp();
    mask = getNetworkMask(ip)
    dev = getDev(ip = ip)
    
    logger.info("Indirizzo ip/mask: %s/%d, device: %s, provider: %s" % (ip, mask, dev, ispid))
    
    if (arping == 0):
        thres = th_host + 1
    else:
        thres = th_host
    
    if (mask != 0):
        
        value = checkhost.countHosts(ip, mask, bandwidth_up, bandwidth_down, ispid, thres, arping, dev)
        logger.info('Trovati %d host in rete.' % value)
        
        if value < 0:
            raise SysmonitorException('impossibile determinare il numero di host in rete.', sysmonitorexception.BADHOST)
        elif (value == 0):
            if arping == 1:
                logger.warning("Passaggio a PING per controllo host in rete")
                return checkhosts(bandwidth_up, bandwidth_down, ispid, 0)
            else:
                raise SysmonitorException('impossibile determinare il numero di host in rete.', sysmonitorexception.BADHOST)
        elif value > thres:
            raise SysmonitorException('Presenza altri host in rete.', sysmonitorexception.TOOHOST)
    else:
        raise SysmonitorException('Impossibile recuperare il valore della maschera dell\'IP: %s' % ip, sysmonitorexception.BADMASK)


def mediumcheck():

    checkcpu()
    checkmem()
    #checktasks()
    #checkconnections()
    #checkfw()
    checkwireless()


def checkall(up, down, ispid, arping = 1):

    mediumcheck()
    checkhosts(up, down, ispid, arping)
    # TODO Reinserire questo check quanto corretto il problema di determinazione del dato
    #checkdisk()


def _checkipsyntax(ip):

    try:
        socket.inet_aton(ip)
        parts = ip.split('.')
        if len(parts) != 4:
            return False
    except Exception:
        return False
    
    return True

def getIp(host = 'finaluser.agcom244.fub.it', port = 443):
    '''
    restituisce indirizzo IP del computer
    '''
    s = socket.socket(socket.AF_INET)
    s.connect((host, port))
    value = s.getsockname()[0]
    
    #value = getstringtag(tag_ip, '90.147.120.2')
    
    if not _checkipsyntax(value):
        raise SysmonitorException('Impossibile ottenere il dettaglio dell\'indirizzo IP', sysmonitorexception.UNKIP)
    return value

def getDev(host = 'finaluser.agcom244.fub.it', port = 443, ip = None):
    '''
    restituisce scheda attiva (guid della scheda su Windows 
    '''
    if not ip:
        local_ip_address = getIp(host, port)
    else:
        local_ip_address = ip
        
    
    ''' Now get the associated device '''
    found = False
    for ifName in netifaces.interfaces():
        all_addresses = netifaces.ifaddresses(ifName)
        if (netifaces.AF_INET in all_addresses):
            ip_addresses = all_addresses[netifaces.AF_INET]
            for address in ip_addresses:
                if ('addr' in address) and (address['addr'] == local_ip_address):
                    found = True
                    break
            if found:
                break
    if not found:
        raise SysmonitorException('Impossibile ottenere il dettaglio dell\'interfaccia di rete', sysmonitorexception.UNKDEV)
    return ifName

def getNetworkMask(ip):
    '''
    Restituisce un intero rappresentante la maschera di rete, in formato CIDR, 
    dell'indirizzo IP in uso
    '''
    netmask = '255.255.255.0'
    
    try:
        inames = netifaces.interfaces()
        for i in inames:
            try:
                addrs = netifaces.ifaddresses(i)
                ipinfo = addrs[socket.AF_INET][0]
                address = ipinfo['addr']
                if (address == ip):
                    netmask = ipinfo['netmask']
                    return _maskConversion(netmask)
            except Exception as e:
                logger.warning("Errore durante il controllo dell'interfaccia %s. %s" % (i, e))
    except Exception as e:
        logger.warning("Errore durante il controllo della maschera per l'IP %s (assumo maschera: /24). %s" % (ip, e))
    
    return _maskConversion(netmask)

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


if __name__ == '__main__':
    import errorcode
    
    try:
        print '\ncheckall'
        print 'Test sysmonitor checkall: %s' % checkall(1000, 2000, 'fst001')
    except Exception as e:
        print 'Errore [%d]: %s' % (errorcode.from_exception(e), e)
    
    try:
        print '\ncheckhosts (arping)'
        print 'Test sysmonitor checkhosts: %s' % checkhosts(2000, 2000, 'fst001', 1)  #ARPING
    except Exception as e:
        print 'Errore [%d]: %s' % (errorcode.from_exception(e), e)
    
    try:
        print '\ncheckhosts (ping)'
        print 'Test sysmonitor checkhosts: %s' % checkhosts(2000, 2000, 'fst001', 0)  #PING
    except Exception as e:
        print 'Errore [%d]: %s' % (errorcode.from_exception(e), e)
    
    try:
        print '\ncheckcpu'
        print 'Test sysmonitor checkcpu: %s' % checkcpu()
    except Exception as e:
        print 'Errore [%d]: %s' % (errorcode.from_exception(e), e)
    
    try:
        print '\ncheckmem'
        print 'Test sysmonitor checkmem: %s' % checkmem()
    except Exception as e:
        print 'Errore [%d]: %s' % (errorcode.from_exception(e), e)
    
    try:
        print '\ncheckwireless'
        print 'Test sysmonitor checkwireless: %s' % checkwireless()
    except Exception as e:
        print 'Errore [%d]: %s' % (errorcode.from_exception(e), e)
    
    try:
        print '\ngetIP'
        print 'Test sysmonitor getIP: %s' % getIp()
    except Exception as e:
        print 'Errore [%d]: %s' % (errorcode.from_exception(e), e)
    
    try:
        print '\ngetIP (www.google.com)'
        print 'Test sysmonitor getIP: %s' % getIp('www.google.com', 80)
    except Exception as e:
        print 'Errore [%d]: %s' % (errorcode.from_exception(e), e)

