# errorcode.py
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



UNKNOWN = 99999
# Errori nella misura HTTP
BROKEN_CONNECTION = 80001
COUNTER_RESET = 80002
CONNECTION_FAILED = 80003
MISSING_SESSION = 80004
ZERO_SPEED = 80005
SERVER_ERROR = 80006

from measurementexception import MeasurementException
from sysmonitorexception import SysmonitorException

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
    if isinstance(exception, SysmonitorException):
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
