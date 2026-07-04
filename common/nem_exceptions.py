# nem_exceptions.py
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

# Errori di Nemesys
TASK_ERROR = 1001
DELIVERY_ERROR = 1002

# Profilazione
FAILPROF = 5001
FAILREADPARAM = 5002
# FAILVALUEPARAM = 5003
# FAILSTATUS = 5004
BADMASK = 5005
LOOPBACK = 5006
UNKDEV = 5008
BADCPU = 5011
WARNCPU = 5012
BADMEM = 5021
LOWMEM = 5022
INVALIDMEM = 5024
OVERMEM = 5025
# BADPROC = 5031
# WARNPROC = 5032
# WARNCONN = 5041
# WARNFW = 5052
WARNWLAN = 5063
WARNETH = 5064
# UNKIP = 5071
BADHOST = 5082
TOOHOST = 5081

# Errori nella misura HTTP
BROKEN_CONNECTION = 80001
COUNTER_RESET = 80002
CONNECTION_FAILED = 80003
# MISSING_SESSION = 80004
ZERO_SPEED = 80005
SERVER_ERROR = 80006
PING_ERROR = 80007
NEGATIVE_SPEED = 80008
NO_AVAILABLE_SERVERS = 80009
PING_TIMEOUT = 99997


# These are the old codes
CODE_MAPPING = {
    "10013": 99977,
    "425 security: bad ip connecting.": 99978,
    "host unreachable": 99979,
    "10051": 99980,
    "530 login incorrect.": 99981,
    "113": 99982,
    "111": 99983,
    "110": 99984,
    "10053": 99985,
    "104": 99986,
    "port unreachable": 99987,
    "10061": 99988,
    "10054": 99989,
    "10065": 99990,
    "35": 99991,
    "530 this ftp server is anonymous only.": 99992,
    "553 could not create file.": 99993,
    "timed out": 99994,
    "10060": 99995,
    "550 failed to open file.": 99996,
    "timeout during icmp socket select": 99997,
    ("operation not permitted - note that icmp messages can only be sent " "from processes running as root."): 99998,
}


def errorcode_from_exception(exception):
    """
    Restituisce il codice di errore relativo al messaggio di errore (errormsg)
    contenuto nell'exception.
    """
    if isinstance(exception, NemesysException):
        return exception.errorcode
    try:
        error = str(exception.args[0]).replace(":", ",")
    except (AttributeError, IndexError):
        error = str(exception).replace(":", ",")

    try:
        errorcode = CODE_MAPPING[error]
        return errorcode
    except KeyError:
        return UNKNOWN


class NemesysException(Exception):
    def __init__(self, message, errorcode=UNKNOWN):
        Exception.__init__(self, message)
        try:
            self._errorcode = int(errorcode)
        except ValueError:
            self._errorcode = UNKNOWN

    @property
    def errorcode(self):
        return self._errorcode


class MeasurementException(NemesysException):
    pass


class SysmonitorException(NemesysException):
    pass


class TaskException(NemesysException):
    def __init__(self, message, errorcode=UNKNOWN):
        NemesysException.__init__(self, message, errorcode)
        if errorcode == UNKNOWN:
            self._errorcode = TASK_ERROR


class ProfilerException(NemesysException):
    """Exception from Profiler"""

    pass


class DeliveryException(NemesysException):
    """Exception from deliverer"""

    pass
