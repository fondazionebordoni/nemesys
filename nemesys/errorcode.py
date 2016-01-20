# errorcoder.py
# -*- coding: utf-8 -*-

# Copyright (c) 2015 Fondazione Ugo Bordoni.
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



INTERNAL_ERROR = 00000  # codice di errore utilizzato in presenza errori di errorcoder.py
UNKNOWN = 99999

# Errori nella misura HTTP
BROKEN_CONNECTION = 80001
COUNTER_RESET = 80002
CONNECTION_FAILED = 80003
MISSING_SESSION = 80004
ZERO_SPEED = 80005
SERVER_ERROR = 80006


from measurementexception import MeasurementException

'''
This is a new version of error code handling. Instead of
using a configuration file, the error codes are declared 
in this file (since they do not change) in order to 
hopefully make things clearer and easier to maintain.
'''


def from_exception(exception):
    '''
    Restituisce il codice di errore relativo al messaggio di errore (errormsg)
    contenuto nell'exception.
    '''
    if isinstance(exception, MeasurementException):
        return exception.errorcode
    try:
        error = str(exception.args[0]).replace(':', ',')
    except AttributeError:
        error = str(exception).replace(':', ',')
    
    try:
        errorcode = CODE_MAPPING[error]
        return errorcode
    except (KeyError):
        return UNKNOWN
    


'''
These are the old codes
'''
CODE_MAPPING = {
'errore durante il recupero dello stato del computer.': 5001,
'non sono riuscito a trovare lo stato del computer con systemprofiler.': 5001,
'errore in lettura del paramentro "cpuload" di systemprofiler.': 5010,
'valore di occupazione della cpu non conforme.': 5011,
'cpu occupata.': 5012,
'errore in lettura del paramentro "availablememory" di systemprofiler.': 5020,
'valore di memoria disponibile non conforme.': 5021,
'memoria disponibile non sufficiente.': 5022,
'errore in lettura del paramentro "memoryload" di systemprofiler.': 5023,
'valore di occupazione della memoria non conforme.': 5024,
'memoria occupata.': 5025,
# Removed 'errore in lettura del paramentro "tasklist" di systemprofiler.': 5030,
'errore nella determinazione dei processi attivi.': 5031,
'sono attivi processi non desiderati.': 5032,
# Removed 'tasklist': 5035,
# Removed 'errore in lettura del paramentro "activeconnections" di systemprofiler.': 5040,
'accesso ad internet da programmi non legati alla misura. se possibile, chiuderli.': 5041,
# Removed 'errore nella determinazione delle connessioni attive.': 5041,
'errore in lettura del paramentro "firewall" di systemprofiler.': 5050,
'impossibile determinare il parametro "firewall".': 5051,
'firewall attivo.': 5052,
# Removed 'errore in lettura del paramentro "wirelesson" di systemprofiler.': 5060,
# Removed 'impossibile determinare il parametro "wirelesson".': 5061,
'wireless lan attiva.': 5063,
'errore in lettura del paramentro "ipaddr" di systemprofiler.': 5070,
'impossibile ottenere il dettaglio dell\'indirizzo ip': 5071,
# Removed 'errore in lettura del paramentro "hostnumber" di systemprofiler.': 5080,
'presenza altri host in rete.': 5081,
'impossibile determinare il numero di host in rete.': 5082,
'errore in lettura del paramentro "processor" di systemprofiler.': 5090,
'errore inizializzazione dello sniffer': 99976,
'10013': 99977,
'425 security: bad ip connecting.': 99978,
'host unreachable': 99979,
'10051': 99980,
'530 login incorrect.': 99981,
'113': 99982,
'111': 99983,
'110': 99984,
'10053': 99985,
'104': 99986,
'port unreachable': 99987,
'10061': 99988,
'10054': 99989,
'10065': 99990,
'35': 99991,
'530 this ftp server is anonymous only.': 99992,
'553 could not create file.': 99993,
'timed out': 99994,
'10060': 99995,
'550 failed to open file.': 99996,
'timeout during icmp socket select': 99997,
'operation not permitted - note that icmp messages can only be sent from processes running as root.': 99998
}
