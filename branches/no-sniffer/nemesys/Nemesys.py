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

import hashlib
import pythoncom
import win32serviceutil
import win32service
import win32event
import win32api
import servicemanager
import executer
import time
import os,sys
import logging
import myProp
import paths
from threading import Thread

###  DISCOVERING PATH  ###
try:
    _PATH = os.path.dirname(sys.argv[0])
    if _PATH == '':
            _PATH="."+os.sep
    if _PATH[len(_PATH)-1] != os.sep: _PATH=_PATH+os.sep
except Exception as e:
    pass


###  READING PROPERTIES  ###
try:
    _prop= myProp.readProps(_PATH+"cfg"+os.sep+"cfg.properties")
except Exception as e:
    pass


### Logging Functionality ###
# quando esegui da linea di comando il file di prop e' in C:\Python26\Lib\site-packages\win32\cfg !!
nemesys = logging.getLogger("nemesys")
nemesys.setLevel(logging.DEBUG)
fh1 = logging.FileHandler(_PATH+_prop['nemlog'])
fh1.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh1.setFormatter(formatter)
nemesys.addHandler(fh1)
nemesys.info('PATH: '+ _PATH)


### Executer Thread ###
class execThread (Thread):
    def __init__(self):
        Thread.__init__(self)
        self.pid = os.getpid()
    
    def run(self):
        executer.main()
          
### Service Running ###
class aservice(win32serviceutil.ServiceFramework):
   _svc_name_ = "NeMeSys"
   _svc_display_name_ = "NeMeSys Service"
   _svc_description_ = "Sistema per la valutazione della connessione broadband"
   

   def __init__(self,args):
      win32serviceutil.ServiceFramework.__init__(self,args)
      self.isAlive = True

   def SvcDoRun(self):
      servicemanager.LogInfoMsg("NeMeSys Service - started")
      ex = execThread()
      ex.start()
      pid=ex.pid
      servicemanager.LogInfoMsg("NeMeSys Service - executer started - "+str(pid))      
      i = 1
      while self.isAlive:
         # Aspetta il segnale di stop per il tempo di timeout (30 secs)
         #rc = win32event.WaitForSingleObject(self.hWaitStop, 30000)
         time.sleep(1)
         i+=0
         #servicemanager.LogInfoMsg("NeMeSys Service Up&Running")
         
      if self.isAlive == False:
          #Stop Signal received
          servicemanager.LogInfoMsg("NeMeSys Service Stopped")
          # disalloco la memoria COM prima di uccidere il processo
          #ex.couni()
          os.popen('taskkill /pid '+str(pid))

   def SvcStop(self):
      servicemanager.LogInfoMsg("Stopping NeMeSys Service - stop signal received ")
      self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
      self.isAlive = False
      #win32event.SetEvent(self.hWaitStop)

   SvcShutdown = SvcStop
   
def ctrlHandler(ctrlType):
   return True

def mainArg(argv):
    if len(argv) == 1:
        start = 'start'
        sys.argv.append(start)
        es = os.popen('Net START EventSystem').read()
        nemesys.info('Starting EventSystem - %s' % es)
    elif 'start' in argv:
        es = os.popen('Net START EventSystem').read()
        nemesys.info('Starting EventSystem - %s' % es)
    elif 'restart' in argv:
        es = os.popen('Net START EventSystem').read()
        nemesys.info('Starting EventSystem - %s' % es)


if __name__ == '__main__':
    mainArg(sys.argv)
    # Lancio il servizio Nemesys
    win32api.SetConsoleCtrlHandler(ctrlHandler, True)
    win32serviceutil.HandleCommandLine(aservice)