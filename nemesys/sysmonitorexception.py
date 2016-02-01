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

FAILPROF = 5001
FAILREADPARAM = 5002
FAILVALUEPARAM = 5003
FAILSTATUS = 5004
BADMASK = 5005
UNKDEV = 5008
BADCPU = 5011
WARNCPU = 5012
BADMEM = 5021
LOWMEM = 5022
INVALIDMEM = 5024
OVERMEM = 5025
BADPROC = 5031
WARNPROC = 5032
WARNCONN = 5041
WARNFW = 5052
WARNWLAN = 5063
UNKIP = 5071
BADHOST = 5082
TOOHOST = 5081


class SysmonitorException(Exception):

  def __init__(self, message, errorcode):
    Exception.__init__(self, message)
    self._message = message
    self._errorcode = errorcode

  @property
  def message(self):
    return self._message.encode('ascii', 'xmlcharrefreplace')
 
  @property
  def errorcode(self):
    return self._errorcode
 