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

import threading

from . import gui_event
from .speed_tester import SpeedTester
from .system_profiler import SystemProfiler


class MistController(object):
    def __init__(self, gui, version, event_dispatcher, scheduler, deliverer, mist_opts):
        self._gui = gui
        self._version = version
        self._profiler = SystemProfiler(event_dispatcher,
                                        client=mist_opts.client)
        self._tester_profiler = SystemProfiler(event_dispatcher,
                                               client=mist_opts.client,
                                               from_tester=True)
        self._event_dispatcher = event_dispatcher
        self._scheduler = scheduler
        self._deliverer = deliverer
        self._speed_tester = None
        self._mist_opts = mist_opts

    def play(self):
        """Function called from GUI"""
        self._gui.set_busy(True)
        if False:  # self._do_profile:
            self._profiler.profile_once_and_call_back(callback=self.measure, report_progress=True)
        else:
            self.measure(None)
            # self.measure()

    def check(self):
        """Function called from GUI"""
        self._gui.set_busy(True)
        self._profiler.profile_once_and_call_back(callback=self.profile_done_callback, report_progress=True)

    def profile_done_callback(self, profiler_result=None):
        """Callback when check is done"""
        self._event_dispatcher.postEvent(
            gui_event.UpdateEvent("Profilazione terminata", gui_event.UpdateEvent.MAJOR_IMPORTANCE))
        self._event_dispatcher.postEvent(gui_event.AfterCheckEvent())
        self._gui.set_busy(False)

    def measure(self, profiler_result=None):
        """Callback to continue with measurement after profiling"""
        self._speed_tester = SpeedTester(version=self._version,
                                         event_dispatcher=self._event_dispatcher,
                                         system_profiler=self._tester_profiler,
                                         scheduler=self._scheduler,
                                         deliverer=self._deliverer,
                                         mist_options=self._mist_opts)
        self._speed_tester.start()

    def kill_test(self):
        if self._speed_tester is not None and self._speed_tester.is_running():
            self._speed_tester.stop()
            for thread in threading.enumerate():
                if thread.is_alive():
                    try:
                        thread._Thread__stop()
                    except Exception:
                        self._event_dispatcher.postEvent(gui_event.ErrorEvent(
                            "Impossibile terminare il processo di misura %s" % str(thread.getName())))

    def exit(self):
        pass
