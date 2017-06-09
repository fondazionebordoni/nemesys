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
import time
from collections import OrderedDict

from common import checkhost
from common import iptools
from common import nem_exceptions
from common import netstat
from common import profiler
from common.nem_exceptions import SysmonitorException
from mist import system_resource

# Soglie di sistema
# ------------------------------------------------------------------------------
# Massima quantità di host in rete
TH_HOST = 1
# Minima memoria disponibile
th_avMem = 134217728
# Massimo carico percentuale sulla memoria
th_memLoad = 95
# Massimo carico percentuale sulla CPU
th_cpu = 85

logger = logging.getLogger(__name__)


class SysMonitor(object):
    def __init__(self, check_speed=False, bw_up=1000, bw_down=1000, ispid='fub001'):
        self._check_speed = check_speed
        self._bw_up = bw_up
        self._bw_down = bw_down
        self._ispid = ispid
        self._profiler = profiler.Profiler()
        self._netstat = netstat.Netstat(iptools.get_dev())
        self._checks = OrderedDict([(system_resource.RES_OS, self.check_os),
                                    (system_resource.RES_CPU, self.checkcpu),
                                    (system_resource.RES_RAM, self.checkmem),
                                    (system_resource.RES_ETH, self.is_ethernet_active),
                                    (system_resource.RES_WIFI, self.checkwireless),
                                    (system_resource.RES_HOSTS, self.checkhosts),
                                    (system_resource.RES_TRAFFIC, self.check_traffic)])

    def checkres(self, res):
        return self._checks[res]()

    def log_interfaces(self):
        all_devices = self._profiler.get_all_devices()
        for device in all_devices:
            logger.info("============================================")
            device_dict = device.dict()
            for key in device_dict:
                logger.info("| %s : %s" % (key, device_dict[key]))
            logger.info("============================================")

    def check_os(self):
        value = 'unknown'
        try:
            value = platform.platform()
            info = ("Sistema Operativo %s" % value)
            status = True
        except Exception as e:
            info = e
            status = False
        return system_resource.SystemResource(system_resource.RES_OS, status, value, info)

    def checkcpu(self):
        value = -1
        try:
            value = self._profiler.cpuLoad()
            if value < 0 or value > 100:
                raise SysmonitorException('Valore di occupazione della cpu non conforme.', nem_exceptions.BADCPU)

            if value > th_cpu:
                raise SysmonitorException('CPU occupata', nem_exceptions.WARNCPU)
            info = 'Utilizzato il %s%% del processore' % value
            status = True
        except Exception as e:
            info = e
            status = False
        return system_resource.SystemResource(system_resource.RES_CPU, status, value, info)

    def checkmem(self):
        try:
            av_mem = self._profiler.total_memory()
            if av_mem < th_avMem:
                logger.debug("Memoria disponibile: %2f" % av_mem)
                if av_mem < 0:
                    raise SysmonitorException('Valore di memoria disponibile non conforme.', nem_exceptions.BADMEM)
                else:
                    raise SysmonitorException('Memoria disponibile non sufficiente.', nem_exceptions.LOWMEM)

            mem_load = self._profiler.percentage_ram_usage()
            if mem_load < 0 or mem_load > 100:
                logger.debug("Memoria occupata: %d%%" % mem_load)
                raise SysmonitorException('Valore di occupazione della memoria non conforme.',
                                          nem_exceptions.INVALIDMEM)
            if mem_load > th_memLoad:
                logger.debug("Memoria occupata: %d%%" % mem_load)
                raise SysmonitorException('Memoria occupata.', nem_exceptions.OVERMEM)

            info = 'Utilizzato il %s%% di %d GB della memoria' % (mem_load, av_mem / (1000 * 1000 * 1000))
            status = True
        except Exception as e:
            mem_load = -1
            info = e
            status = False
        return system_resource.SystemResource(system_resource.RES_RAM, status, mem_load, info)

    def checkwireless(self):
        try:
            if self._profiler.is_wireless_active():
                raise SysmonitorException('Wireless LAN attiva.', nem_exceptions.WARNWLAN)
            else:
                value = 0
                info = 'Dispositivi wireless non attivi.'
                status = True
        except SysmonitorException as e:
            value = 1
            info = e
            status = False
        except Exception as e:
            logger.error("ERRORE", exc_info=True)
            value = -1
            info = e
            status = False
        return system_resource.SystemResource(system_resource.RES_WIFI, status, value, info)

    def checkhosts(self, use_arp=True):
        value = None
        try:
            ip = iptools.getipaddr()
            mask = iptools.get_network_mask(ip)
            dev = iptools.get_dev(ip=ip)

            logger.info("Indirizzo ip/mask: %s/%d, device: %s" % (ip, mask, dev))

            if iptools.is_public_ip(ip):
                status = True
                info = 'La scheda di rete in uso ha un IP pubblico. Non controllo il numero degli altri host in rete.'
            else:
                if mask != 0:
                    value = checkhost.count_hosts(ip, mask, self._bw_up, self._bw_down, self._ispid, use_arp)
                    logger.info('Trovati %d host in rete.' % value)
                    if value < 0:
                        raise SysmonitorException('impossibile determinare il numero di host in rete.',
                                                  nem_exceptions.BADHOST)
                    elif value == 0:
                        if use_arp:
                            logger.warning("Passaggio a PING per controllo host in rete")
                            return self.checkhosts(False)
                        else:
                            raise SysmonitorException('impossibile determinare il numero di host in rete.',
                                                      nem_exceptions.BADHOST)
                    elif value > TH_HOST:
                        raise SysmonitorException('Presenza altri host in rete.', nem_exceptions.TOOHOST)
                    else:
                        status = True
                        info = 'Trovati %d host in rete.' % value
                else:
                    raise SysmonitorException('Impossibile recuperare il valore della maschera dell\'IP: %s' % ip,
                                              nem_exceptions.BADMASK)
        except Exception as e:
            info = e
            status = False
        return system_resource.SystemResource(system_resource.RES_HOSTS, status, value, info)

    def is_ethernet_active(self):
        value = 0
        status = False
        info = ''
        try:
            devices = self._profiler.get_all_devices()
            for device in devices:
                dev_type = device.type
                if dev_type == 'Ethernet 802.3':
                    if device.is_enabled and device.is_active:
                        value = 1
                        info = 'Dispositivi ethernet attivi.'
                        status = True
                        if self._check_speed:
                            if (device.speed * 1000 < self._bw_up) or (device.speed * 1000 < self._bw_down):
                                raise SysmonitorException(("Dispositivi ethernet attivi, ma la scheda di rete di "
                                                           "{0}Mb/s non è sufficiente per misurare correttamente il "
                                                           "profilo riportato in fase "
                                                           "di registrazione.").format(device.speed),
                                                          nem_exceptions.WARNETH)
            if value == 0:
                raise SysmonitorException("Dispositivi ethernet non attivi o non presenti.", nem_exceptions.WARNETH)
        except Exception as e:
            info = e
            status = False
        return system_resource.SystemResource(system_resource.RES_ETH, status, value, info)

    def check_traffic(self, sec=2):

        value = 'unknown'
        try:
            # TODO: check for modified ip or dev
            ip = iptools.getipaddr()
            dev = iptools.get_dev(ip=ip)
            logger.debug("getting stats from dev " + dev)
            start_rx_bytes = self._netstat.get_rx_bytes()
            start_tx_bytes = self._netstat.get_tx_bytes()
            logger.debug("start rx %d, start tx %d" % (start_rx_bytes, start_tx_bytes))
            start_time = time.time()
            time.sleep(sec)
            end_rx_bytes = self._netstat.get_rx_bytes()
            end_tx_bytes = self._netstat.get_tx_bytes()
            measure_time_millis = (time.time() - start_time) * 1000
            logger.debug("end rx %d, end tx %d" % (end_rx_bytes, end_tx_bytes))
            logger.debug("total time millis %d" % measure_time_millis)

            up_kbps = (end_tx_bytes - start_tx_bytes) * 8 / measure_time_millis
            down_kbps = (end_rx_bytes - start_rx_bytes) * 8 / measure_time_millis
            if (up_kbps < 0) or (down_kbps < 0):
                raise SysmonitorException("Ottenuto valore di traffico negativo, potrebbe dipendere dall'azzeramento "
                                          "dei contatori.",
                                          nem_exceptions.FAILREADPARAM)
            value = (down_kbps, up_kbps)
            info = ("{0:.1f} kbps in download e {1:.1f} kbps in upload di traffico globale attuale sull'interfaccia "
                    "di rete in uso.".format(down_kbps, up_kbps))

            if int(up_kbps) < 20 and int(down_kbps) < 200:
                value = 'LOW'
            elif int(up_kbps) < 180 and int(down_kbps) < 1800:
                value = 'MEDIUM'
            else:
                value = 'HIGH'
            if value != 'LOW':
                raise Exception(info)
            status = True
        except Exception as e:
            info = e
            status = False
        return system_resource.SystemResource(system_resource.RES_TRAFFIC, status, value, info)

    def mediumcheck(self):
        self.checkcpu()
        self.checkmem()
        self.checkwireless()

    def checkall(self, use_arp=True):
        self.mediumcheck()
        self.checkhosts(use_arp)
        # TODO: Reinserire questo check quanto corretto il problema di determinazione del dato
        # checkdisk()
