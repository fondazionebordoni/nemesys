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

import logging
from collections import OrderedDict

from common import checkhost
from common import iptools
from common import nem_exceptions
from common import profiler
from common.nem_exceptions import SysmonitorException

logger = logging.getLogger(__name__)

# Soglie di sistema
# ------------------------------------------------------------------------------
# Massima quantità di host in rete
MAX_HOSTS = 1
# Minima memoria disponibile
TH_AV_MEM = 134217728
# Massimo carico percentuale sulla memoria
TH_MEM_LOAD = 95
# Massimo carico percentuale sulla CPU
TH_CPU = 85

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


class SysProfiler(object):
    def __init__(self, bw_upload, bw_download, isp_id, bypass=False, bw_upload_min=None, bw_download_min=None):
        self._bw_upload = bw_upload
        self._bw_upload_min = bw_upload_min
        self._bw_download = bw_download
        self._bw_download_min = bw_download_min
        self._isp_id = isp_id
        self._bypass = bypass
        self._checks = OrderedDict([
            (RES_ETH, self.check_device),
            (RES_CPU, self.checkcpu),
            (RES_RAM, self.checkmem),
            (RES_WIFI, self.checkwireless),
            (RES_HOSTS, self.checkhosts),
        ])

    def log_interfaces(self):
        all_devices = profiler.get_all_devices()
        for device in all_devices:
            logger.info('============================================')
            device_dict = device.dict()
            for key in device_dict:
                logger.info('| %s : %s', key, device_dict[key])
            logger.info('============================================')

    def check_device(self):
        try:
            ip = iptools.getipaddr()
            iptools.get_network_mask(ip)
        except Exception as e:
            raise SysmonitorException('Impossibile ottenere indirizzo IP '
                                      'della scheda di rete attiva: {}'.format(e), nem_exceptions.UNKDEV)
        if iptools.is_loopback_ip(ip):
            raise SysmonitorException('Indirizzo IP {0} punta sull\'interfaccia'
                                      ' di loopback - Firewall attivo?'
                                      .format(ip), nem_exceptions.LOOPBACK)
        try:
            dev_name = iptools.get_dev(ip=ip)
        except Exception as e:
            raise SysmonitorException('Impossibile identificare '
                                      'la scheda di rete attiva: {}'.format(e), nem_exceptions.UNKDEV)
        device_speed = iptools.get_if_speed(dev_name)

        if self._bw_download_min is not None:
          if device_speed < (self._bw_download_min / 1000):
              raise SysmonitorException('La velocita\' della scheda di rete e\' '
                                        '{0} Mb/s, che e\' minore della '
                                        'velocita\' minima garantita del profilo: {1} Mb/s'
                                        .format(device_speed,
                                                self._bw_download_min / 1000))

        elif device_speed < (self._bw_download / 1000):
            raise SysmonitorException('La velocita\' della scheda di rete e\' '
                                      '{0} Mb/s, che e\' minore della '
                                      'velocita\' del profilo: {1} Mb/s'
                                      .format(device_speed,
                                              self._bw_download / 1000))

        return dev_name

    def checkcpu(self):
        value = profiler.cpu_load()
        if value < 0 or value > 100:
            raise SysmonitorException('Valore di occupazione della cpu '
                                      'non conforme.', nem_exceptions.BADCPU)
        if value > TH_CPU:
            raise SysmonitorException('CPU occupata al %d%%' % value,
                                      nem_exceptions.WARNCPU)

    def checkmem(self):
        av_mem = profiler.total_memory()
        logger.debug('Memoria disponibile: %2f', av_mem)
        if av_mem < 0:
            raise SysmonitorException('Valore di memoria disponibile '
                                      'non conforme.', nem_exceptions.BADMEM)
        if av_mem < TH_AV_MEM:
            raise SysmonitorException('Memoria disponibile '
                                      'non sufficiente.',
                                      nem_exceptions.LOWMEM)

        mem_load = profiler.percentage_ram_usage()
        logger.debug('Memoria occupata: %d%%', mem_load)
        if mem_load < 0 or mem_load > 100:
            raise SysmonitorException('Valore di occupazione della memoria '
                                      'non conforme.',
                                      nem_exceptions.INVALIDMEM)
        if mem_load > TH_MEM_LOAD:
            raise SysmonitorException('Memoria occupata.',
                                      nem_exceptions.OVERMEM)

    def checkwireless(self):
        if profiler.is_wireless_active():
            raise SysmonitorException('Wireless LAN attiva.',
                                      nem_exceptions.WARNWLAN)

    def checkhosts(self, do_arp=True):
        try:
            ip = iptools.getipaddr()
            dev = iptools.get_dev(ip=ip)
            mask = iptools.get_network_mask(ip)
        except Exception as e:
            logger.error('Errore ottenendo informazioni sulla scheda di rete: %s', e)
            raise SysmonitorException('Impossibile ottenere informazioni '
                                      'sulla scheda di rete attiva: {}'.format(e),
                                      errorcode=nem_exceptions.UNKDEV)
        if iptools.is_loopback_ip(ip):
            raise SysmonitorException('Indirizzo IP {0} punta sull\'interfaccia'
                                      ' di loopback - Firewall attivo?'
                                      .format(ip), nem_exceptions.LOOPBACK)
        logger.info('Indirizzo ip/mask: %s/%d, device: %s, provider: %s', ip, mask, dev, self._isp_id)
        if not iptools.is_public_ip(ip):
            value = checkhost.count_hosts(ip,
                                          mask,
                                          self._bw_upload,
                                          self._bw_download,
                                          self._isp_id,
                                          do_arp)
            logger.info('Trovati %d dispositivi in rete.', value)
            if value < 0:
                raise SysmonitorException('Impossibile determinare il numero di dispositivi collegati in rete.',
                                          nem_exceptions.BADHOST)
            elif value == 0:
                if do_arp:
                    logger.warning('Passaggio a PING per controllo dispositivi in rete')
                    return self.checkhosts(do_arp=False)
                else:
                    raise SysmonitorException('Non risulta nessun dispositivo collegato in rete, '
                                              'verifica connessione al router.',
                                              nem_exceptions.BADHOST)
            elif value > MAX_HOSTS:
                raise SysmonitorException('Ci sono {} altri dispositivi collegati alla tua '
                                          'rete, scollegali.'.format(value - 1),
                                          nem_exceptions.TOOHOST)

    def checkall(self, callback=None):
        e = None
        passed = True
        error_code = None
        error_msg = ''

        for resource, check_method in list(self._checks.items()):
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
            raise SysmonitorException('Profilazione del sistema fallito, '
                                      'ultimo errore: {}'.format(e), nem_exceptions.FAILPROF)
