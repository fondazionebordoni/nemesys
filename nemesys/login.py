# login.py
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
from Tkinter import *
import tkFont
from threading import Thread
import time
import tkMessageBox
import os
import myProp
import paths
from getconf import getconf
import utils


import logging

logger = logging.getLogger()

_clientConfigurationFile = 'client.conf'
_configurationServer = 'https://finaluser.agcom244.fub.it/Config'


### Activation code ###
def getCode():
  '''
  Apre una finestra che chiede il codice licenza. Resituisce il codice licenza e chiude la finestra.
  '''
  appresult = None
  root = None
  try:
    root = Tk()
    if utils.is_windows():
        root.wm_iconbitmap('../Nemesys.ico')
    app = LoginGui(master=root)
    app.master.title("Attivazione Ne.Me.Sys")
    app.mainloop()
    appresult = str(app.result)
    logger.info(appresult)

    if appresult == '' or len(appresult) < 4:
      appresult = None
      logger.error('Exit: wrong activation code')
      CodeError()
      raise Exception('Wrong username/password')

  except Exception as e:
      logger.error('Exception at activation code: %s' % str(e))
      
  finally:
      if root:
          root.destroy()
      return appresult

def CodeError():
    """
    Errore in caso di credenziali errate
    """
    message = "Credenziali di autenticazione non riconosciute.\nControllare i dati di accesso al sito www.misurainternet.it"
    ErrorDialog(message)
    

def FinalError():
    """
    Errore in caso di tentativo di download non andato a buon fine
    """
    message = "Si è verificato un errore. Controllare:\n\n\t- di avere accesso alla rete,\n\t- di aver digitato correttamente le credenziali di accesso,\n\t- di avere una licenza attiva,\n\t- di non aver ottenuto un certificato con Ne.Me.Sys. meno di 45 giorni antecedenti ad oggi.\n\nDopo 5 tentativi di accesso falliti, sarà necessario disinstallare Ne.Me.Sys e reinstallarlo nuovamente."
    ErrorDialog(message)
    

def MaxError():
    """
    Errore in caso di quinto inserimento errato di credenziali
    """
    message = "Le credenziali non sono corrette o la licenza non è più valida..\nProcedere con la disinstallazione e reinstallare nuovamente Ne.Me.Sys. dopo aver controllato user-id e password che ti sono state invitate in fase di registrazione o a richiedere una nuova licenza dalla tua area privata sul sito misurainternet.it."
    ErrorDialog(message)
    
    
def ErrorDialog(message):
    root = Tk()
    if utils.is_windows():
        root.wm_iconbitmap('../Nemesys.ico')
    root.withdraw()
    title = 'Errore'
    tkMessageBox.showerror(title, message, parent=root)
    root.destroy()


def OkDialog():
    root = Tk()
    if utils.is_windows():
        root.wm_iconbitmap('../Nemesys.ico')
    root.withdraw()
    title = 'Ne.Me.Sys autenticazione corretta'
    message = 'Username e password corrette e verificate'
    tkMessageBox.showinfo(title, message, parent=root)
    root.destroy()


### Function to Download Configuration File ###
def getActivationFile(appresult,path, config_path):
    '''
      Scarica il file di configurazione. Ritorna True se tutto è andato bene
    '''
    logger.info('getActivationFile function')
    
    ac = appresult 
    logger.info('Codici ricevuti: %s' % ac)
    
    download = False
    try:
        download = getconf(ac, path, _clientConfigurationFile, _configurationServer)
        logger.info('download = %s' % str(download))
    except Exception as e:
        logger.error('Cannot download the configuration file: %s' % str(e))
    if download != True:
        logger.info('Received error from server, wrong credentials or license not active')
          #ACEmain()
        return False
    else:
        logger.info('Configuration file successfully downloaded')
        myProp.writeProps(config_path,'\nregistered','ok')
        _prop=myProp.readProps(config_path)
        OkDialog()
        return True

    
class LoginGui(Frame):
    """
    finestra di codice licenza
    """
    
    def sendMsg(self):
        inserted_username = self.username.get()
        inserted_password = self.password.get()
        if (inserted_username and inserted_password):
            self.result = "%s|%s" % (self.username.get(), hashlib.sha1(self.password.get()).hexdigest())
        self.quit()

    def createWidgets(self):
        self.Title = Label(self, padx=60, pady=8)
        self.Title["text"] = "Inserisci i codici di accesso (username e password)\nche hai usato per accedere all'area personale"
        self.Title.grid(column=0, row=0, columnspan=2)

        username_label = Label(self, text="username:")
        username_label.grid(column=0, row=1)

        self.username = Entry(self, width=30)
        self.username.grid(column=1, row=1)

        password_label = Label(self, text="password:")
        password_label.grid(column=0, row=2)

        self.password = Entry(self, width=30)
        self.password["show"] = "*"
        self.password.grid(column=1, row=2)

        self.invio = Button(self)
        self.invio["text"] = "Accedi",
        self.invio["command"] = self.sendMsg
        self.invio.grid(column=0, row=3, columnspan=2, pady=8)

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.config(width="800")
        if utils.is_windows():
            self.master.wm_iconbitmap(os.path.join('..', 'nemesys.ico'))
        self.pack()
        self.createWidgets()
        self.result = None


def main():
    ###  DISCOVERING PATH  ###
    try:
        _PATH = os.path.dirname(sys.argv[0])
        if _PATH == '':
                _PATH="."+os.sep
        if _PATH[len(_PATH)-1] != os.sep: _PATH=_PATH+os.sep
    except Exception as e:
        pass
    
    config_path = _PATH+"cfg"+os.sep+"cfg.properties" 

    ###  READING PROPERTIES  ###
    _prop = None
    try:
        _prop= myProp.readProps(config_path)
    except Exception as e:
        logger.error("Could not read configuration file from %s" % config_path)
        ErrorDialog("File di configurazione non trovata in %s, impossibile procedere con l'installazione" % config_path)
        sys.exit(1)

    if not 'code' in _prop:
        result = False
        j=0
        # Al massimo faccio fare 5 tentativi di inserimento codice di licenza
        while not result and j<5:    
                # Prendo un codice licenza valido sintatticamente
            appresult = None
            #TODO: Do not continue forever, and make last dialog
#            while not appresult:
            appresult = getCode()
                # Prendo il file di configurazione
            i = 0
            try:
                result = getActivationFile(appresult, paths._CONF_DIR, config_path)
            except Exception as e:
                logger.error("Caught exception while downloading configuration file: %s" % str(e) )
                
#            TODO:
            if result==False and j<4:
                FinalError()
                logger.warning('Final Error occurred at attempt number %d' %j)
            j+=1
    
        if result == False:
            MaxError()
            logger.warning('MaxError occurred at attempt number 5')
            myProp.writeProps(config_path,'\ncode',appresult)
            _prop=myProp.readProps(config_path)
            myProp.writeProps(config_path,'\nregistered','nok')
            _prop=myProp.readProps(config_path)
            sys.exit(1)
        elif result == True:
            logger.info('License file successfully downloaded')
            myProp.writeProps(config_path,'\ncode',appresult)
            _prop=myProp.readProps(config_path)    
    else:
        logger.debug('Activation Code found')
        if 'registered' in _prop:
            #Ho tentato almeno una volta il download
            logger.debug('Registered in _prop')
            status = str(_prop['registered'])
            if status == 'ok':
                # Allora posso continuare lo start del servizio
                logger.debug('Status of registered is Ok')
                logger.info('Configuration file already downloaded')
            else:
                # Il servizio non può partire
                logger.error('Login previously failed. ')
                # Dialog to unistall and retry
                MaxError()
  


if __name__ == '__main__':
    main()