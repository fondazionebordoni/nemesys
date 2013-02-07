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
from Tkinter import *
import tkMessageBox
import paths
from threading import Thread
from getconf import getconf
import netifaces

_clientConfigurationFile = 'client.conf'
_configurationServer = 'https://finaluser.agcom244.fub.it/Config'

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

class GetCodeGui(Frame):
    """
    finestra di codice licenza
    """
    
    def sendMsg(self):
        self.result = self.code.get()
        self.quit()

    def createWidgets(self):
        self.Title = Label(self)
        self.Title["text"] = "\nInserire codice di licenza per NeMeSys.\nIl codice licenza e' riportato nella propria area privata sul sito www.misurainternet.it,\nnella sezione Licenze e PDF misure."
        self.Title.pack({"side": "top"})

        self.invio = Button(self)
        self.invio["text"] = "invio",
        self.invio["command"] = self.sendMsg
        self.invio.pack({"side": "bottom"})        

        self.code = Entry(self)
        self.code.pack({"side": "bottom"})
        

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.master.wm_iconbitmap('..\\Nemesys.ico')
        self.pack(side=BOTTOM)
        self.createWidgets()

def GCGmain():
    """
    Lancia la finestra di codice licenza @return: il codice scritto
    """
    rootGCG = Tk()
    appGCG = GetCodeGui(master=rootGCG)
    appGCG.master.title("Codice licenza Nemesys")
    appGCG.mainloop()
    appresult = str(appGCG.result)
    rootGCG.destroy()
    return appresult

def ErrorDialog(message):
    root = Tk()
    root.wm_iconbitmap('..\\Nemesys.ico')
    root.withdraw()
    title = 'Nemesys Error'
    tkMessageBox.showerror(title, message, parent=root)
    root.destroy()

def ACEmain():
    """
    Errore in caso di Codice errato
    """
    message = "Errore nella lettura del codice di attivazione.\nControllare il file di configurazione cfg.properties."
    ErrorDialog(message)

def Downloadmain():
    """
    Errore in caso di Download errato
    """
    message = "Impossibile installare Ne.Me.Sys., errore nel download del file di configurazione o codice licenza non corretto."
    ErrorDialog(message)

def CodeError():
    """
    Errore in caso di codice di attivazione non attivo
    """
    message = "Codice di attivazione inserito errato.\nControllare il codice nella propria area personale del sito www.misurainternet.it"
    ErrorDialog(message)


def FinalError():
    """
    Errore in caso di terzo tentativo di download non andato a buon fine
    """
    message = "Il download del file di configurazione non è andato a buon fine.\nVerificare la correttezza del codice di licenza e di avere accesso alla rete.\n\nDopo 5 tentativi falliti, sarà necessario disinttallare Ne.Me.Sys. e reinstallarlo nuovamente."
    ErrorDialog(message)


def MaxError():
    """
    Errore in caso di quinto inserimento errato di codice licenza
    """
    message = "Il file di configurazione non è stato scaricato dopo 5 tentativi.\nProcedere con la procedura di disinstallazione e reinstallare nuovamente per inserire il corretto codice di licenza."
    ErrorDialog(message)
    
    
def OkDialog():
    root = Tk()
    root.wm_iconbitmap('..\\nemesys.ico')
    root.withdraw()
    title = 'Nemesys codice corretto'
    message = 'Codice licenza corretto e verificato'
    tkMessageBox.showinfo(title, message, parent=root)
    root.destroy()

           

### Function to Download Configuration File ###
def getActivationFile(appresult,path):
    '''
      Scarica il file di configurazione. Ritorna True se tutto è andato bene
    '''
    nemesys.info('getActivationFile function')
    
    ac = appresult 
    nemesys.info('Activation Code found: %s' % ac)
    
    try:
      download = getconf(ac, path, _clientConfigurationFile, _configurationServer)
      nemesys.info('download = %s' % str(download))
      if download != True:
          nemesys.error('Cannot download the configuration file')
          ACEmain()
          return False
      else:
          nemesys.info('Configuration file successfully downloaded')
          myProp.writeProps(_PATH+"cfg"+os.sep+"cfg.properties",'\nregistered','ok')
          _prop=myProp.readProps(_PATH+"cfg"+os.sep+"cfg.properties")
          OkDialog()
          return True

    except Exception as e:
      nemesys.error('Cannot download the configuration file: ' + str(e))
      Downloadmain()
      return False


### Activation code ###
def getCode():
  '''
  Apre una finestra che chiede il codice licenza. Resituisce il codice licenza e chiude la finestra.
  '''
  appresult = None
  try:
    root = Tk()
    app = GetCodeGui(master=root)
    app.master.title("Codice licenza Nemesys")
    app.mainloop()
    appresult = str(app.result)
    nemesys.info(appresult)

    if appresult == '' or len(appresult) != 32:
      appresult = None
      nemesys.error('Exit: wrong activation code')
      CodeError()
      raise Exception('Wrong activation code')

  except Exception as e:
      nemesys.error('Exception at activation code: ' + str(e))
      
  finally:
    root.destroy()
    return appresult

def isNotFirstExec():
    """
    Controlla se NON siamo alla prima esecuzione
    """
    if 'code' in _prop:
        # NON siamo alla prima esecuzione
        nemesys.debug('Activation Code not found')
        if 'registered' in _prop:
            #Ho tentato almeno una volta il download
            nemesys.debug('Registered in _prop')
            status = str(_prop['registered'])
            if status == 'ok':
                # Allora posso continuare lo start del servizio
                nemesys.debug('Status of registered is Ok')
                nemesys.info('Configuration file already downloaded')
                return True
            else:
                # Il servizio non può partire
                nemesys.error('Configuration file download previously failed. File not present.')
                nemesys.error('Exiting from NeMeSys')
                sys.exit(1)
    else:
        return False
          
### Service Running ###
class aservice(win32serviceutil.ServiceFramework):
   _svc_name_ = "NeMeSys"
   _svc_display_name_ = "NeMeSys Service"
   _svc_description_ = "Sistema per la valutazione della connessione broadband"
   

   def __init__(self,args):
      #servicemanager.LogWarningMsg('type(arg) = '+ str(type(args)))
      #servicemanager.LogWarningMsg(str(args))
      #nemesys.info("args: "+str(args))
      #servicemanager.LogWarningMsg(str(args))
      win32serviceutil.ServiceFramework.__init__(self,args)
      self.isAlive = True
      #self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

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

         #fileOutputName = str(_PATH+os.sep+'results.xml')
         #executer.main()
         #SystemProfiler(fileOutputName,diction)
         #win32api.SleepEx(120000, True)
         #i+=1
         #servicemanager.LogInfoMsg("LucianoSrvc - Stopped")

   def SvcStop(self):
      servicemanager.LogInfoMsg("Stopping NeMeSys Service - stop signal received ")
      self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
      self.isAlive = False
      #win32event.SetEvent(self.hWaitStop)

   SvcShutdown = SvcStop
   
def ctrlHandler(ctrlType):
   return True

def mainArg(argv):
    if len(argv)== 1:
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

if not isNotFirstExec():
    result = False
    j=0
    # Al massimo faccio fare 5 tentativi di inserimento codice di licenza
    while not result and j<5:    
        # Prendo un codice licenza valido sintatticamente
        appresult = None
        while appresult == None:
            appresult = getCode()
            
        # Prendo il file di configurazione
        i = 0
        result = getActivationFile(appresult, paths._CONF_DIR)
        if result==False and j<4:
            FinalError()
            nemesys.warning('Final Error occurred at attemp number %d' %j)
        j+=1

    if result == False:
        MaxError()
        nemesys.warning('MaxError occurred at attemp number 5')
        myProp.writeProps(_PATH+"cfg"+os.sep+"cfg.properties",'\ncode',appresult)
        _prop=myProp.readProps(_PATH+"cfg"+os.sep+"cfg.properties")
        myProp.writeProps(_PATH+"cfg"+os.sep+"cfg.properties",'\nregistered','nok')
        _prop=myProp.readProps(_PATH+"cfg"+os.sep+"cfg.properties")
        sys.exit(1)
    elif result == True:
        nemesys.info('License file successfully downloaded')
        myProp.writeProps(_PATH+"cfg"+os.sep+"cfg.properties",'\ncode',appresult)
        _prop=myProp.readProps(_PATH+"cfg"+os.sep+"cfg.properties")      
        

if __name__ == '__main__':
    mainArg(sys.argv)
    # Lancio il servizio Nemesys
    win32api.SetConsoleCtrlHandler(ctrlHandler, True)
    win32serviceutil.HandleCommandLine(aservice)