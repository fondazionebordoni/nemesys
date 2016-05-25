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

import logging
import platform

import checkhost
import iptools
import profiler
from sysmonitorexception import SysmonitorException
import sysmonitorexception


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

    ip = iptools.getipaddr()
    mask = iptools.get_network_mask(ip)
    dev = iptools.get_dev(ip = ip)
    
    logger.info("Indirizzo ip/mask: %s/%d, device: %s, provider: %s" % (ip, mask, dev, ispid))
    if not iptools.is_public_ip(ip):
    
        if (arping == 0):
            thres = th_host + 1
        else:
            thres = th_host
        
        if (mask != 0):
            
            value = checkhost.countHosts(ip, mask, bandwidth_up, bandwidth_down, ispid, thres, arping)
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
    # TODO: Reinserire questo check quanto corretto il problema di determinazione del dato
    #checkdisk()


if __name__ == '__main__':
    import errorcode
    import log_conf
    log_conf.init_log()
    
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
    

