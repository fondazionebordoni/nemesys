# sysmonitorexception.py
# -*- coding: utf8 -*-

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


class SysmonitorException(Exception):

  def __init__(self, alert_type, message):
    Exception.__init__(self, message)
    if isinstance (alert_type, SysmonitorException):
      self._alert_type = alert_type.alert_type.decode('utf-8')
    else:
      self._alert_type = alert_type.decode('utf-8')
        
    self._message = message.decode('utf-8')
 
  @property
  def alert_type(self):
    return self._alert_type.encode('ascii', 'xmlcharrefreplace')

  @property
  def message(self):
    return self._message.encode('ascii', 'xmlcharrefreplace')
 
#Error while trying to recover the System Profile
FAILPROF = SysmonitorException('FAILPROF', 'Non sono riuscito a trovare lo stato del computer con SystemProfiler.')      
#Error on param reading
FAILREADPARAM = SysmonitorException('FAILREADPARAM', 'Errore in SystemProfiler.')
#Error  on determining param's value
FAILVALUEPARAM = SysmonitorException('FAILVALUEPARAM', 'Errore in SystemProfiler.')  
#Error on connection list
BADCONN = SysmonitorException('BADCONN', 'Lista delle connessioni attive non conforme.')          
#Warning on the possibility of further programs accessing to internet
WARNCONN = SysmonitorException('WARNCONN', 'Accesso ad Internet da programmi non legati alla misura. Se possibile, chiuderli.')
#Error in retrieving active processes
BADPROC = SysmonitorException('BADPROC', 'Errore nella determinazione dei processi attivi.')  
#Warning on active processes
WARNPROC = SysmonitorException('WARNPROC', 'Sono attivi processi non desiderati.')      
#Error while retrieving CPU load
BADCPU = SysmonitorException('BADCPU', 'Valore di occupazione della CPU non conforme.')         
#Warning on CPU overload
WARNCPU = SysmonitorException('WARNCPU', 'CPU occupata.')  
#Error while retrieving Memory usage
BADMEM = SysmonitorException('BADMEM', 'Valore di memoria disponibile non conforme.')         
#Warning because of low Memory
LOWMEM = SysmonitorException('LOWMEM', 'Memoria disponibile non sufficiente.')   
#Error while retrieving Memory usage
INVALIDMEM = SysmonitorException('INVALIDMEM', 'Valore di occupazione della memoria non conforme.')    
#Warning busy memory
OVERMEM = SysmonitorException('OVERMEM', 'Memoria occupata.')  
#Warning firewall is activated
WARNFW = SysmonitorException('WARNFW', 'Firewall attivo.') 
#Warning Wireless is activated
WARNWLAN = SysmonitorException('WARNWLAN', 'Wireless LAN attiva.') 
#Error while retrieving the number of online Host
BADHOST = SysmonitorException('BADHOST', 'Impossibile determinare il numero di host in rete.')   
#Warning because of the presence of other hosts online
TOOHOST = SysmonitorException('TOOHOST', 'Presenza altri host in rete.')   
#Error while retrieving Mask from IP
BADMASK = SysmonitorException('BADMASK', 'Errore nella lettura della maschera.') 
#Error while examining writing procedure on the hard disk
UNKDISKLOAD = SysmonitorException('UNKDISKLOAD', 'Impossibile detereminare il carico in lettura del disco.')     
#Warning Disk is overloaded with writing procedures
DISKOVERLOAD = SysmonitorException('DISKOVERLOAD', 'Eccessivo carico in scrittura del disco.')   
#Error retrieving IP address
UNKIP = SysmonitorException('UNKIP', 'Impossibile ottenere il dettaglio dell\'indirizzo IP')         
#Error retrieving network device
UNKDEV = SysmonitorException('UNKDEV', 'Impossibile ottenere il dettaglio dell\'interfaccia di rete')         
#Error retrieving the Profile Status (reading params)
FAILSTATUS = SysmonitorException('FAILSTATUS', 'Errore durante il recupero dello stato del computer.')
