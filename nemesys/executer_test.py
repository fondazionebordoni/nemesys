# executer_test.py
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
import threading

from common import nem_exceptions, _generated_version, task
from common.deliverer import Deliverer
from common.server import Server
from nemesys import nem_options
from nemesys.executer import Executer
from nemesys.sysmonitor import SysProfiler
from nemesys import restart

logger = logging.getLogger(__name__)


class MockScheduler(object):
    def __init__(self):
        server = Server('fubsrvrmnmx03', '193.104.137.133', 'Namex server')
        self.task_default = task.Task(now=True,
                                      server=server,
                                      upload=1,
                                      download=1,
                                      ping=4,
                                      message='Test message')
        self.task_ping = task.Task(now=True,
                                   server=server,
                                   upload=0,
                                   download=0,
                                   ping=4)
        self.task_up = task.Task(now=True,
                                 server=server,
                                 upload=1,
                                 download=0,
                                 ping=0)
        self.task_down = task.Task(now=True,
                                   server=server,
                                   upload=0,
                                   download=1,
                                   ping=0)
        self.task_wait = task.new_wait_task(wait_secs=5, message="Ciao")

        #         self._tasks = ([self.task_wait,
        #                         self.task_ping,
        #                         self.task_wait,
        #                         self.task_up,
        #                         self.task_wait,
        #                         self.task_down,
        #                         self.task_wait])
        #         self._tasks = [self.task_wait, self.task_default]
        self._tasks = [self.task_default, self.task_wait]
        self._i = -1

    def download_task(self):
        #         return self.task_wait
        self._i += 1
        if self._i == len(self._tasks):
            self._i = 0
        return self._tasks[self._i]


class MockDeliverer(object):
    def uploadall_and_move(self, from_dir=None, to_dir=None, do_remove=False):
        logger.info("Move all from %s to %s, do remove is %s", from_dir, to_dir, do_remove)
        return True

    def upload_and_move(self, f=None, to_dir=None, do_remove=False):
        logger.info("Move file %s to %s, do remove is %s", f, to_dir, do_remove)
        return True


class MockDysfunctDeliverer(object):
    def uploadall_and_move(self, from_dir=None, to_dir=None, do_remove=False):
        logger.info("Move all from %s to %s, do remove is %s", from_dir, to_dir, do_remove)
        msg = ("Misura terminata ma "
               "un errore si è verificato durante il suo invio.")
        raise nem_exceptions.NemesysException(msg, nem_exceptions.DELIVERY_ERROR)

    def upload_and_move(self, f=None, to_dir=None, do_remove=False):
        logger.info("Move file %s to %s, do remove is %s", f, to_dir, do_remove)
        return False


def main():
    from . import log_conf
    log_conf.init_log()

    (options, _, md5conf) = nem_options.parse_args(_generated_version.__version__)
    from common import client
    c = client.getclient(options)
    # c = Client('245e843ec08897fd0df7e5a780bbdcc8',
    #            Profile('8981', 100000, 100000),
    #            Isp('fub000', None), '41.843646,12.485726')
    sys_profiler = SysProfiler(c.profile.upload,
                               c.profile.download,
                               c.isp.id,
                               bypass=True,
                               bw_upload_min=c.profile.upload_min,
                               bw_download_min=c.profile.download_min)
    # d = MockDeliverer()
    #     d = MockDysfunctDeliverer()
    d = Deliverer(options.repository,
                  c.isp.certificate,
                  options.httptimeout)
    scheduler = MockScheduler()
    exe = Executer(client=c,
                   scheduler=scheduler,
                   deliverer=d,
                   sys_profiler=sys_profiler,
                   isprobe=False)

    restart_scheduler = restart.RestartScheduler()
    restart_scheduler.start()

    loop_thread = threading.Thread(target=exe.loop)
    loop_thread.start()
    input("Press Enter to stop...")
    print("Stopping...")
    exe.stop()
    loop_thread.join()


if __name__ == '__main__':
    main()
