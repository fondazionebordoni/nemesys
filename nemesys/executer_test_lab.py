# executer_test_lab.py
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

"""
Executer test configurato per i server Docker locali del misurainternet-lab.

Questo file è una variante di executer_test.py specificamente configurata
per testare i server containerizzati:
- agcom-httpserver-fastify (porta 3000) - download/upload/ping
- nemesys-httpd-up (porta 8080) - upload legacy
- nemesys-httpserver (porta 8081) - download legacy

Uso:
    python -m nemesys.executer_test_lab
"""

import logging
import threading

from common import nem_exceptions, _generated_version, task
from common.deliverer import Deliverer
from common.server import Server
from nemesys.executer import Executer
from nemesys.sysmonitor import SysProfiler
from nemesys import restart

logger = logging.getLogger(__name__)


class DockerLabScheduler(object):
    """
    Scheduler configurato per testare tutti i server Docker locali.
    
    Esegue una sequenza di test su:
    1. Fastify Server (porta 3000) - download, upload e ping
    2. Python Server (porta 8080) - upload legacy
    3. Java Server (porta 8081) - download legacy
    """
    
    def __init__(self):
        # Server Fastify - moderno (upload + download + ping)
        self.server_fastify = Server(
            uuid='localhost-fastify',
            ip='127.0.0.1',
            name='Fastify Server (Docker)',
            port=3000
        )
        
        # Server Python - legacy upload  
        self.server_python = Server(
            uuid='localhost-python',
            ip='127.0.0.1',
            name='Python Upload Server (Docker)',
            port=8080
        )
        
        # Server Java - legacy download
        self.server_java = Server(
            uuid='localhost-java',
            ip='127.0.0.1',
            name='Java Download Server (Docker)',
            port=8081
        )
        
        # Task di attesa tra i test
        self.task_wait = task.new_wait_task(wait_secs=5, message="Waiting between tests...")
        
        # Test su Fastify (moderno)
        self.task_fastify_down = task.Task(
            now=True,
            server=self.server_fastify,
            upload=0,
            download=1,
            ping=0,
            message='Fastify: Download test'
        )
        
        self.task_fastify_up = task.Task(
            now=True,
            server=self.server_fastify,
            upload=1,
            download=0,
            ping=0,
            message='Fastify: Upload test'
        )
        
        self.task_fastify_ping = task.Task(
            now=True,
            server=self.server_fastify,
            upload=0,
            download=0,
            ping=4,
            message='Fastify: Ping test'
        )
        
        # Test su Python (legacy upload)
        self.task_python_up = task.Task(
            now=True,
            server=self.server_python,
            upload=1,
            download=0,
            ping=0,
            message='Python: Upload test (legacy)'
        )
        
        # Test su Java (legacy download)
        self.task_java_down = task.Task(
            now=True,
            server=self.server_java,
            upload=0,
            download=1,
            ping=0,
            message='Java: Download test (legacy)'
        )
        
        # Sequenza completa dei test
        # Testa tutti e tre i server: Fastify, Python e Java
        self._tasks = [
            self.task_wait,
            self.task_fastify_ping,
            self.task_wait,
            self.task_fastify_down,
            self.task_wait,
            self.task_fastify_up,
            self.task_wait,
            self.task_python_up,
            self.task_wait,
            self.task_java_down,
            self.task_wait,
        ]
        self._i = -1

    def download_task(self, server=None):
        """
        Restituisce il prossimo task da eseguire in modo ciclico.
        Il parametro server viene ignorato in quanto usiamo una sequenza prefissata.
        """
        self._i += 1
        if self._i >= len(self._tasks):
            self._i = 0
        return self._tasks[self._i]


class MockDeliverer(object):
    """Mock deliverer per test senza invio dati al backend."""
    
    def uploadall_and_move(self, from_dir=None, to_dir=None, do_remove=False):
        logger.info("Mock: Move all from %s to %s, do remove is %s", from_dir, to_dir, do_remove)
        return True


class MockChooser(object):
    """Mock chooser per test senza connessione al backend."""
    
    def get_servers(self):
        logger.info("Mock: get_servers() called - returning empty list")
        return []
    
    def choose_server(self, callback):
        logger.info("Mock: choose_server() called - no action")
        return None

    def upload_and_move(self, f=None, to_dir=None, do_remove=False):
        logger.info("Mock: Move file %s to %s, do remove is %s", f, to_dir, do_remove)
        return True


def main():
    """
    Main function per testare i server Docker locali.
    
    Avvia una sequenza di test su tutti i server containerizzati.
    Premi Invio per fermare i test.
    
    NOTA: Non richiede login o configurazione - usa valori di default per test locali.
    """
    from . import log_conf
    log_conf.init_log()

    # Crea un client di test con valori di default (senza richiedere login)
    from common.client import Client
    from common.profile import Profile
    from common.isp import Isp
    
    logger.info("Inizializzazione client di test (no login richiesto)...")
    c = Client(
        client_id='test-lab-local',
        profile=Profile(
            profile_id='lab-profile',
            upload=100000,      # 100 Mbps
            download=100000,    # 100 Mbps
            upload_min=10000,   # 10 Mbps
            download_min=10000  # 10 Mbps
        ),
        isp=Isp(isp_id='lab-isp', certificate=None),
        geocode='0.0,0.0'
    )
    
    sys_profiler = SysProfiler(
        c.profile.upload,
        c.profile.download,
        c.isp.id,
        bypass=True,
        bw_upload_min=c.profile.upload_min,
        bw_download_min=c.profile.download_min
    )
    
    # Usa mock deliverer e chooser per evitare connessioni al backend
    d = MockDeliverer()
    chooser = MockChooser()
    
    # Scheduler configurato per Docker Lab
    scheduler = DockerLabScheduler()
    
    logger.info("=" * 80)
    logger.info("Nemesys Docker Lab Test Suite")
    logger.info("=" * 80)
    logger.info("Configured servers:")
    logger.info("  - Fastify Server: http://127.0.0.1:3000 (download/upload/ping)")
    logger.info("  - Python Server:  http://127.0.0.1:8080 (upload legacy)")
    logger.info("  - Java Server:    http://127.0.0.1:8081 (download legacy)")
    logger.info("=" * 80)
    
    exe = Executer(
        client=c,
        chooser=chooser,
        scheduler=scheduler,
        deliverer=d,
        sys_profiler=sys_profiler,
        isprobe=False
    )

    restart_scheduler = restart.RestartScheduler()
    restart_scheduler.start()

    loop_thread = threading.Thread(target=exe.loop)
    loop_thread.start()
    
    try:
        input("\nPress Enter to stop tests...\n")
    except KeyboardInterrupt:
        pass
    
    print("\nStopping tests...")
    exe.stop()
    loop_thread.join()
    logger.info("Tests completed!")


if __name__ == '__main__':
    main()
