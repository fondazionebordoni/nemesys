# sysmonitor.py
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from collections import OrderedDict
import logging
import platform

import checkhost
import iptools
import profiler
from nem_exceptions import SysmonitorException
import nem_exceptions


logger = logging.getLogger(__name__)
platform_name = platform.system().lower()

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

# RES_OS = 'OS'
RES_CPU = 'CPU'
RES_RAM = 'RAM'
RES_ETH = 'Ethernet'
RES_WIFI = 'Wireless'
# RES_DEV = 'Device'
# RES_MAC = 'MAC'
# RES_IP = 'IP'
# RES_MASK = 'MASK'
RES_HOSTS = 'Hosts'
RES_TRAFFIC = 'Traffic'

my_profiler = profiler.get_profiler()


def check_device():
    try:
        ip = iptools.getipaddr()
        iptools.get_network_mask(ip)
    except Exception as e:
        raise SysmonitorException("Impossibile ottenere indirizzo IP della scheda di rete attiva: %s" % (e))
    try:
        dev = iptools.get_dev(ip=ip)
    except Exception as e:
        raise SysmonitorException("Impossibile identificare la scheda di rete attiva: %s" % (e))
    return dev


def checkcpu():

    value = my_profiler.cpuLoad()
    if value < 0 or value > 100:
        raise SysmonitorException('Valore di occupazione della cpu non conforme.', nem_exceptions.BADCPU)

    if value > th_cpu:
        raise SysmonitorException('CPU occupata al %d%%' % value, nem_exceptions.WARNCPU)


def checkmem():

    avMem = my_profiler.total_memory()
    logger.debug("Memoria disponibile: %2f" % avMem)
    if avMem < 0:
        raise SysmonitorException('Valore di memoria disponibile non conforme.', nem_exceptions.BADMEM)
    if avMem < th_avMem:
        raise SysmonitorException('Memoria disponibile non sufficiente.', nem_exceptions.LOWMEM)
    
    memLoad = my_profiler.percentage_ram_usage()
    logger.debug("Memoria occupata: %d%%" % memLoad)
    if memLoad < 0 or memLoad > 100:
        raise SysmonitorException('Valore di occupazione della memoria non conforme.', nem_exceptions.INVALIDMEM)
    if memLoad > th_memLoad:
        raise SysmonitorException('Memoria occupata.', nem_exceptions.OVERMEM)


def checkwireless():
    if my_profiler.is_wireless_active():
        raise SysmonitorException('Wireless LAN attiva.', nem_exceptions.WARNWLAN)
            

def checkhosts(bandwidth_up, bandwidth_down, ispid, arping = 1):

    ip = iptools.getipaddr()
    mask = iptools.get_network_mask(ip)
    dev = iptools.get_dev(ip=ip)
    
    logger.info("Indirizzo ip/mask: %s/%d, device: %s, provider: %s" % (ip, mask, dev, ispid))
    if not iptools.is_public_ip(ip):
    
        if (arping == 0):
            thres = th_host + 1
        else:
            thres = th_host
        
        if (mask != 0):
            
            value = checkhost.countHosts(ip, mask, bandwidth_up, bandwidth_down, ispid, arping)
            logger.info('Trovati %d host in rete.' % value)
            
            if value < 0:
                raise SysmonitorException('impossibile determinare il numero di host in rete.', nem_exceptions.BADHOST)
            elif (value == 0):
                if arping == 1:
                    logger.warning("Passaggio a PING per controllo host in rete")
                    return checkhosts(bandwidth_up, bandwidth_down, ispid, 0)
                else:
                    raise SysmonitorException('impossibile determinare il numero di host in rete.', nem_exceptions.BADHOST)
            elif value > thres:
                raise SysmonitorException('Presenza altri host in rete.', nem_exceptions.TOOHOST)
        else:
            raise SysmonitorException('Impossibile recuperare il valore della maschera dell\'IP: %s' % ip, nem_exceptions.BADMASK)


class SysProfiler():
    
    def __init__(self, bypass=False):
        self._bypass = bypass
        self._checks = OrderedDict \
            ([ \
            (RES_ETH, check_device),\
            (RES_CPU, checkcpu),\
            (RES_RAM, checkmem),\
            (RES_WIFI, checkwireless),\
            (RES_HOSTS, checkhosts),\
            ])
        
    def checkall(self, up, down, ispid, arping=True, callback=None):
    
        e = None
        passed = True
        error_code = None
        error_message = None
        
        for resource, check_method in self._checks.items():
            
            try:
                if resource == RES_HOSTS:
                    checkhosts(up, down, ispid, arping)
                else:
                    check_method()
                if callback:
                    callback(resource, True)
            except Exception as e:
                error_code = nem_exceptions.errorcode_from_exception(e)
                error_message = str(e)
                passed = False
                if callback:
                    logger.debug('calling sysmon callback with error: %s' % e)
                    callback(resource, False, str(e))
            
        if not passed and not self._bypass:
            if error_code:
                raise SysmonitorException(error_message, error_code)
            raise SysmonitorException("Profilazione del sistema fallito, ultimo errore: %s" % e, nem_exceptions.FAILPROF)

if __name__ == '__main__':
    import log_conf
    log_conf.init_log()
    
#     try:
#         print '\ncheckall'
#         print 'Test sysmonitor checkall: %s' % checkall(1000, 2000, 'fst001')
#     except Exception as e:
#         print 'Errore [%d]: %s' % (nem_exceptions.errorcode_from_exception(e), e)
#     
    try:
        print '\ncheckhosts (arping)'
        print 'Test sysmonitor checkhosts: %s' % checkhosts(2000, 2000, 'fst001', 1)  #ARPING
    except Exception as e:
        print 'Errore [%d]: %s' % (nem_exceptions.errorcode_from_exception(e), e)
    
    try:
        print '\ncheckhosts (ping)'
        print 'Test sysmonitor checkhosts: %s' % checkhosts(2000, 2000, 'fst001', 0)  #PING
    except Exception as e:
        print 'Errore [%d]: %s' % (nem_exceptions.errorcode_from_exception(e), e)
    
    try:
        print '\ncheckcpu'
        print 'Test sysmonitor checkcpu: %s' % checkcpu()
    except Exception as e:
        print 'Errore [%d]: %s' % (nem_exceptions.errorcode_from_exception(e), e)
    
    try:
        print '\ncheckmem'
        print 'Test sysmonitor checkmem: %s' % checkmem()
    except Exception as e:
        print 'Errore [%d]: %s' % (nem_exceptions.errorcode_from_exception(e), e)
    
    try:
        print '\ncheckwireless'
        print 'Test sysmonitor checkwireless: %s' % checkwireless()
    except Exception as e:
        print 'Errore [%d]: %s' % (nem_exceptions.errorcode_from_exception(e), e)
    

