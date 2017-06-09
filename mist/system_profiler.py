# encoding: utf-8
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
import threading
import time
from collections import OrderedDict

from common import iptools
from mist import gui_event
from mist.sysmonitor import SysMonitor
from mist.system_resource import RES_OS, RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_HOSTS, RES_TRAFFIC

logger = logging.getLogger(__name__)

ALL_RES = [RES_OS, RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_HOSTS, RES_TRAFFIC]
MESSAGE = ALL_RES


class SystemProfiler(object):
    def __init__(self, event_dispatcher, client, from_tester=False):

        self._event_dispatcher = event_dispatcher
        self._stop = False
        if from_tester:
            self._message_flag = False
            self._report_device = False
        else:
            self._message_flag = True
            self._report_device = True
        self._device = None
        self._sys_monitor = SysMonitor(check_speed=(not client.is_oneshot()),
                                       bw_up=client.profile.upload,
                                       bw_down=client.profile.download,
                                       ispid=client.isp.id)
        self._lock = threading.Lock()

    def get_os(self):
        return self._sys_monitor.check_os().value

    def profile_once_and_call_back(self, callback, resources=set(ALL_RES), report_progress=False):
        profiling_thread = threading.Thread(target=self._do_profile, args=(resources, callback, report_progress))
        profiling_thread.daemon = True
        profiling_thread.start()

    def profile_once(self, resources=set(ALL_RES)):
        return self._do_profile(resources=resources)

    def profile_in_background(self, resources=set(ALL_RES), callback=None):
        self._stop = False
        profiling_thread = threading.Thread(target=self._do_background_profile, args=(resources, callback))
        profiling_thread.daemon = True
        profiling_thread.start()

    def stop_background_profiling(self):
        self._stop = True

    def _do_background_profile(self, resources=set(ALL_RES), callback=None):
        while not self._stop:
            self._do_profile(resources, callback)
            time.sleep(1.0)

    def _do_profile(self, resources=set(ALL_RES), callback=None, report_progress=False):
        with self._lock:
            if report_progress:
                i = 0
                self._event_dispatcher.postEvent(gui_event.ProgressEvent(i))
            self._check_device()
            sysmon_results = OrderedDict([])
            for res in resources:
                if res in ALL_RES:
                    if res == RES_HOSTS:
                        result = self._sys_monitor.checkres(res)
                    else:
                        result = self._sys_monitor.checkres(res)
                    sysmon_results[res] = result
                    if report_progress:
                        i += 1
                        self._event_dispatcher.postEvent(gui_event.ProgressEvent(float(i) / len(resources)))
                    if res in MESSAGE:
                        self._event_dispatcher.postEvent(gui_event.ResourceEvent(res, result, self._message_flag))

            results = {}
            for key in sysmon_results:
                results[key] = sysmon_results[key].value
            if callback is not None:
                callback(results)
            else:
                return results

    def _check_device(self):
        try:
            ip = iptools.getipaddr()
            dev = iptools.get_dev()
        except Exception as e:
            logger.error("Impossibile ottenere ip e device", exc_info=True)
            if self._message_flag:
                self._event_dispatcher.postEvent(gui_event.ErrorEvent(e))
            return

        if self._device is None:
            self._device = dev
            if self._report_device:
                self._event_dispatcher.postEvent(gui_event.UpdateEvent("Indirizzo IP di rete: %s" % ip))
                self._event_dispatcher.postEvent(gui_event.UpdateEvent("Interfaccia di rete in esame: %s" % dev))

        elif dev != self._device:
            # TODO: handle at higher level
            self._event_dispatcher.postEvent(
                gui_event.ErrorEvent("Test interrotto per variazione interfaccia di rete di riferimento."))
            self._event_dispatcher.postEvent(gui_event.StopEvent())
