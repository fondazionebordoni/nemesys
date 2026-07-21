# Nemesys.py
# -*- coding: utf-8 -*-

# Copyright (c) 2010 Fondazione Ugo Bordoni.
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

try:
    import win32serviceutil
    import win32service
    import win32api
    import servicemanager
except ImportError:
    raise Exception("Non trovo le librerie necessarie su Windows, impossibile continuare")

import logging
import os
import sys
from threading import Thread, Event

from nemesys import executer

### Rilevamento del path dell'eseguibile ###
# sys.argv[0] punta all'exe compilato da py2exe; usato per scrivere il log
# nella stessa cartella dell'eseguibile.
try:
    _PATH = os.path.dirname(sys.argv[0])
    if _PATH == '':
        _PATH = "." + os.sep
    if _PATH[len(_PATH) - 1] != os.sep:
        _PATH = _PATH + os.sep
except Exception:
    _PATH = "." + os.sep

### Logging ###
# Log dedicato al wrapper del servizio Windows, separato dal log di executer.
# time non è necessario: i timestamp sono gestiti internamente da logging.Formatter.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
_fh = logging.FileHandler(_PATH + 'log_nemesys.log')
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(_fh)
logger.info('PATH: %s', _PATH)


### Thread che esegue il loop principale di Nemesys ###
class execThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        # daemon=True: il thread viene terminato automaticamente quando il
        # processo principale esce, senza bisogno di un kill esplicito.
        self.daemon = True

    def run(self):
        executer.main()


### Definizione del servizio Windows ###
class aservice(win32serviceutil.ServiceFramework):
    _svc_name_ = "NeMeSys"
    _svc_display_name_ = "NeMeSys Service"
    _svc_description_ = "Sistema per la valutazione della connessione broadband"
    _svc_deps_ = ["EventSystem", "Tcpip", "Netman", "EventLog"]

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self._stop_event = Event()

    def SvcDoRun(self):
        servicemanager.LogInfoMsg("NeMeSys Service - started")
        # Notifica al SCM che il servizio è in esecuzione prima di bloccarsi.
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        ex = execThread()
        ex.start()
        servicemanager.LogInfoMsg("NeMeSys Service - executer started")
        # Attende il segnale di stop senza busy-wait.
        self._stop_event.wait()
        servicemanager.LogInfoMsg("NeMeSys Service - stopped")

    def SvcStop(self):
        servicemanager.LogInfoMsg("NeMeSys Service - stop signal received")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._stop_event.set()

    SvcShutdown = SvcStop


def ctrlHandler(ctrlType):
    return True


def _set_failure_actions(opts):
    # Riavvia il servizio automaticamente in caso di crash (3 tentativi, 60s di
    # ritardo); richiamato da HandleCommandLine dopo install/update.
    hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
    try:
        hs = win32service.OpenService(hscm, aservice._svc_name_, win32service.SERVICE_ALL_ACCESS)
        try:
            win32service.ChangeServiceConfig2(
                hs, win32service.SERVICE_CONFIG_FAILURE_ACTIONS_FLAG, True)
            win32service.ChangeServiceConfig2(
                hs, win32service.SERVICE_CONFIG_FAILURE_ACTIONS,
                {
                    'ResetPeriod': 0,
                    'RebootMsg': '',
                    'Command': '',
                    'Actions': [
                        (win32service.SC_ACTION_RESTART, 60000),
                        (win32service.SC_ACTION_RESTART, 60000),
                        (win32service.SC_ACTION_RESTART, 60000),
                    ],
                })
        finally:
            win32service.CloseServiceHandle(hs)
    finally:
        win32service.CloseServiceHandle(hscm)


### Entry point ###
if __name__ == '__main__':
    if len(sys.argv) == 1:
        # Lanciato dal SCM (Service Control Manager): avvia il dispatcher.
        # Pattern corretto per eseguibili py2exe con pywin32.
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(aservice)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Lanciato da riga di comando (install / start / stop / remove).
        win32api.SetConsoleCtrlHandler(ctrlHandler, True)
        win32serviceutil.HandleCommandLine(aservice, customOptionHandler=_set_failure_actions)
