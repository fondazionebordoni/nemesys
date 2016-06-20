'''
Created on 13/giu/2016

@author: ewedlund
'''

import hashlib
import logging
from profile import Profile
import threading

from client import Client
from executer import Executer
import executer
from isp import Isp
import paths
from scheduler import Scheduler
from server import Server
from sysmonitor import SysProfiler
import task


logger = logging.getLogger(__name__)

class MockScheduler():
    
    def __init__(self):
        server = Server('namexrm', 'eagle2.fub.it', 'Namex server')
        self.task_default = task.Task(now=True, server=server, upload=1, download=1, ping=4)
        self.task_ping = task.Task(now=True, server=server,upload=0, download=0, ping=20)
        self.task_up = task.Task(now=True, server=server,upload=1, download=0, ping=0)
        self.task_down = task.Task(now=True, server=server,upload=0, download=1, ping=0)
        self.task_wait = task.new_wait_task(wait_secs=5, message="Ciao")
        
#         self._tasks = [self.task_wait, self.task_ping, self.task_wait, self.task_up, self.task_wait, self.task_down, self.task_wait]
#         self._tasks = [self.task_wait, self.task_default]
        self._tasks = [self.task_wait, self.task_ping]
        self._i = -1
    
    def download_task(self):
#         return self.task_wait
        self._i += 1
        if self._i == len(self._tasks):
            self._i = 0
        return self._tasks[self._i]

class MockDeliverer():
    
    def uploadall_and_move(self, from_dir=None, to_dir=None, do_remove=False):
        logger.info("Move all from %s to %s, do remove is %s" % (from_dir, to_dir, do_remove))
        return True
        
                           
    def upload_and_move(self, f=None, to_dir=None, do_remove=False):
        logger.info("Move all from %s to %s, do remove is %s" % (f, to_dir, do_remove))
        return True


if __name__ == '__main__':
    import log_conf
    log_conf.init_log()

#     scheduler = MockScheduler()
    deliverer = MockDeliverer()
    sys_profiler = SysProfiler(bypass=True)
#     client = Client('fub0000000001', Profile('fub00001', 512, 512), Isp('fub000', 'fub000.pem'), '41.843646,12.485726')
    client = Client('245e843ec08897fd0df7e5a780bbdcc8', Profile('130', 100000, 100000), Isp('mcl007', None), '41.843646,12.485726')
    with open(paths.CONF_MAIN, 'r') as f:
        md5 = hashlib.md5(f.read()).hexdigest()
    scheduler = Scheduler(scheduler_url='https://finaluser.agcom244.fub.it/Scheduler', client=client, md5conf=md5, version=executer.__version__, timeout=10)
    scheduler = MockScheduler()
    executer = Executer(client, scheduler, deliverer, sys_profiler, isprobe=False)
    loop_thread = threading.Thread(target=executer.loop)
    loop_thread.start()
    raw_input("Press Enter to stop...")
    executer.stop()
    loop_thread.join()