# errorGui.py
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
import time
import os,sys
import logging
import myProp
from Tkinter import *
from GetCodeGui import GetCodeGui,ACEmain,Downloadmain,GCGmain,CodeError
from threading import Thread
from getconf import getconf

_clientConfigurationFile = 'client.conf'
_configurationServer = 'https://finaluser.agcom244.fub.it/Config'

###  DISCOVERING PATH  ###
try:
    _PATH = os.path.dirname(sys.argv[0])
    if _PATH == '':
            _PATH="."+os.sep
    if _PATH[len(_PATH)-1] != os.sep: _PATH=_PATH+os.sep
    #print _PATH
    #servicemanager.LogInfoMsg('Executable path: '+str(_PATH))    
except Exception as e:
    #servicemanager.LogErrorMsg('Exception at executable path: '+str(e))
    pass


###  READING PROPERTIES  ###
try:
    _prop= myProp.readProps(_PATH+"cfg"+os.sep+"cfg.properties")
    #servicemanager.LogInfoMsg('properties path: '+str(_PATH)+'cfg\cfg.properties')
except Exception as e:
    #servicemanager.LogErrorMsg('Exception properties path: '+str(e))
    pass


### Logging Functionality ###
#quando esegui da linea di comando il file di prop e' in C:\Python26\Lib\site-packages\win32\cfg !!
nemesys = logging.getLogger("nemesys")
nemesys.setLevel(logging.DEBUG)
fh1 = logging.FileHandler(_PATH+'errorGui.log')
fh1.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh1.setFormatter(formatter)
nemesys.addHandler(fh1)
nemesys.info('PATH: '+ _PATH)

### Error displaying Thread ###
class ErrorThread (Thread):
    def __init__(self,error):
        Thread.__init__(self)
        self.error = error
    
    def run(self):
        if self.error=='ace':
            ACEmain()
        elif self.error=='download':
            Downloadmain()
        elif self.error =='code':
            CodeError()

### Function to Download Configuration File ###
def getActivationFile(prop,PATH):
    nemesys.info('getActivationFile function')
    try:
        #activation code
        ac = str(prop['code'])
        nemesys.info('Activation Code found: %s' % ac)
    except Exception as e:
        nemesys.error('Exception in reading activation code from cfg.properties: '+str(e))
        et = ErrorThread('ace')
        et.start()
        sys.exit(1)
    try:
        path=PATH+os.sep+'..'+os.sep+'config'
        download= getconf(ac, path, _clientConfigurationFile, _configurationServer)
        nemesys.info('download = %s' % str(download))
        if download != True:
            raise Exception('Download failed') 
        else:
            nemesys.info('Configuration file successfully downloaded')
            myProp.writeProps(_PATH+"cfg"+os.sep+"cfg.properties",'\nregistered','ok')
            _prop=myProp.readProps(_PATH+"cfg"+os.sep+"cfg.properties")
    except Exception as e:
        nemesys.error('Cannot download the configuration file: '+str(e))
        nemesys.error('Exit from Ne.Me.Sys.')
        myProp.writeProps(_PATH+"cfg"+os.sep+"cfg.properties",'\nregistered','nok')
        _prop=myProp.readProps(_PATH+"cfg"+os.sep+"cfg.properties")
        et=ErrorThread('download')
        et.start()
        sys.exit(1)
        

### Activation code ###
try:
    if 'code' not in _prop:
            appresult = GCGmain()
            nemesys.info('appresult')
            if appresult != '':
                    nemesys.info('appresult != ""')
                    myProp.writeProps(_PATH+"cfg"+os.sep+"cfg.properties",'\ncode',app.result)
                    _prop=myProp.readProps(_PATH+"cfg"+os.sep+"cfg.properties")
                    root.destroy()            
            else:
                    nemesys.info('appresult = ""')
                    #root.destroy()
                    nemesys.error('Exit: activation code not provided')
                    myProp.writeProps(_PATH+"cfg"+os.sep+"cfg.properties",'\nregistered','nok')
                    _prop=myProp.readProps(_PATH+"cfg"+os.sep+"cfg.properties")
                    et=ErrorThread('code')
                    et.start()
                    raise Exception('Activation Code not provided')
except Exception as e:
    servicemanager.LogWarningMsg('Exception at activation code: '+str(e))
    sys.exit(1)


try:
    if 'registered' not in _prop:
        nemesys.info('download del file di configurazione')
        #scarico il file di configurazione
        getActivationFile(_prop,_PATH)
    else:
        status = str(_prop['registered'])
        if status == 'ok':
            # Allora posso continuare lo start del servizio
            nemesys.info('Configuration file already downloaded')
        elif status == 'nok':
            # Allora il servizio non puo partire
            nemesys.info('Configuration file download previously failed. File not present.')
            raise Exception('Configuration file download previously failed.')
except Exception as e:
    nemesys.info('Error loading registering property'+str(e))
    nemesys.info('Exiting from NeMeSys')
    sys.exit(1)