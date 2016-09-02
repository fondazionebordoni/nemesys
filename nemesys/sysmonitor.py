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
MAX_HOSTS = 1
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


class SysProfiler():

    def __init__(self, bw_upload, bw_download, isp_id, bypass=False):
        self._bw_upload = bw_upload
        self._bw_download = bw_download
        self._isp_id = isp_id
        self._bypass = bypass
        self._checks = OrderedDict([
            (RES_ETH, self.check_device),
            (RES_CPU, self.checkcpu),
            (RES_RAM, self.checkmem),
            (RES_WIFI, self.checkwireless),
            (RES_HOSTS, self.checkhosts),
            ])
        self._profiler = profiler.Profiler()

    def check_device(self):
        try:
            ip = iptools.getipaddr()
            iptools.get_network_mask(ip)
        except Exception as e:
            raise SysmonitorException("Impossibile ottenere indirizzo IP "
                                      "della scheda di rete attiva: %s" % (e))
        if iptools.is_loopback_ip(ip):
            raise SysmonitorException("Indirizzo IP {0} punta sull'interfaccia"
                                      " di loopback - Firewall attivo?"
                                      .format(ip), nem_exceptions.LOOPBACK)
        try:
            dev_name = iptools.get_dev(ip=ip)
        except Exception as e:
            raise SysmonitorException("Impossibile identificare "
                                      "la scheda di rete attiva: %s" % (e))
        device_speed = iptools.get_if_speed(dev_name)
        if device_speed < (self._bw_download / 1000):
            raise SysmonitorException("La velocita' della scheda di rete e' "
                                      "{0} Mb/s, che e' minore della "
                                      "velocita' del profilo: {1} Mb/s"
                                      .format(device_speed,
                                              self._bw_download/1000))

        return dev_name

    def checkcpu(self):
        value = self._profiler.cpuLoad()
        if value < 0 or value > 100:
            raise SysmonitorException('Valore di occupazione della cpu '
                                      'non conforme.', nem_exceptions.BADCPU)
        if value > th_cpu:
            raise SysmonitorException('CPU occupata al %d%%' % value,
                                      nem_exceptions.WARNCPU)

    def checkmem(self):
        avMem = self._profiler.total_memory()
        logger.debug("Memoria disponibile: %2f" % avMem)
        if avMem < 0:
            raise SysmonitorException('Valore di memoria disponibile '
                                      'non conforme.', nem_exceptions.BADMEM)
        if avMem < th_avMem:
            raise SysmonitorException('Memoria disponibile '
                                      'non sufficiente.',
                                      nem_exceptions.LOWMEM)

        memLoad = self._profiler.percentage_ram_usage()
        logger.debug("Memoria occupata: %d%%" % memLoad)
        if memLoad < 0 or memLoad > 100:
            raise SysmonitorException('Valore di occupazione della memoria '
                                      'non conforme.',
                                      nem_exceptions.INVALIDMEM)
        if memLoad > th_memLoad:
            raise SysmonitorException('Memoria occupata.',
                                      nem_exceptions.OVERMEM)

    def checkwireless(self):
        if self._profiler.is_wireless_active():
            raise SysmonitorException('Wireless LAN attiva.',
                                      nem_exceptions.WARNWLAN)

    def checkhosts(self, do_arp=True):
        try:
            ip = iptools.getipaddr()
            dev = iptools.get_dev(ip=ip)
            mask = iptools.get_network_mask(ip)
        except Exception as e:
            logger.error("Cannot get info on network device: %s" % (e))
            raise SysmonitorException("Impossibile ottenere informazioni "
                                      "sulla scheda di rete attiva: %s" % (e),
                                      errorcode=nem_exceptions.UNKDEV)
        if iptools.is_loopback_ip(ip):
            raise SysmonitorException("Indirizzo IP {0} punta sull'interfaccia"
                                      " di loopback - Firewall attivo?"
                                      .format(ip), nem_exceptions.LOOPBACK)
        logger.info("Indirizzo ip/mask: %s/%d, device: %s, provider: %s"
                    % (ip, mask, dev, self._isp_id))
        if not iptools.is_public_ip(ip):
            value = checkhost.countHosts(ip,
                                         mask,
                                         self._bw_upload,
                                         self._bw_download,
                                         self._isp_id,
                                         do_arp)
            logger.info('Trovati %d host in rete.' % value)
            if value < 0:
                raise SysmonitorException('impossibile determinare il '
                                          'numero di host in rete.',
                                          nem_exceptions.BADHOST)
            elif (value == 0):
                if do_arp:
                    logger.warning("Passaggio a PING "
                                   "per controllo host in rete")
                    return self._checkhosts(do_arp=False)
                else:
                    raise SysmonitorException('impossibile determinare il '
                                              'numero di host in rete.',
                                              nem_exceptions.BADHOST)
            elif value > MAX_HOSTS:
                raise SysmonitorException('Presenza altri host in rete.',
                                          nem_exceptions.TOOHOST)

    def checkall(self, callback=None):
        e = None
        passed = True
        error_code = None
        error_msg = ""

        for resource, check_method in self._checks.items():
            try:
                check_method()
                if callback:
                    callback(resource, True)
            except Exception as e:
                error_code = nem_exceptions.errorcode_from_exception(e)
                error_msg = str(e)
                passed = False
                if callback:
                    callback(resource, False, str(e), error_code)
        if not passed and not self._bypass:
            if error_code:
                raise SysmonitorException(error_msg, error_code)
            raise SysmonitorException("Profilazione del sistema fallito, "
                                      "ultimo errore: %s" % e,
                                      nem_exceptions.FAILPROF)
