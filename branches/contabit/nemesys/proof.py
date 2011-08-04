# proof.py
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

# TODO Estendere Proof per la memorizzazione dei dati di contabit

from datetime import datetime

class Proof:

  def __init__(self, type, start, value, bytes, counter_bytes=0, counter_payload=0, errorcode=0):
    self._type = type
    self._start = start
    self._value = value
    self._bytes = bytes
    self._counter_bytes = counter_bytes
    self._counter_payload = counter_payload
    self._errorcode = errorcode

  @property
  def type(self):
    return self._type

  @property
  def start(self):
    return self._start

  @property
  def value(self):
    '''
    Values must be saved in milliseconds.
    '''
    return self._value

  @property
  def bytes(self):
    return self._bytes

  @property
  def counter_bytes(self):
      return self._counter_bytes

  @property
  def counter_payload(self):
      return self._counter_payload

  @property
  def errorcode(self):
    return self._errorcode

  def seterrorcode(self, errorcode):
    if errorcode > 99999 or errorcode < 0:
      # Faccio rimanere nelle ultime 4 cifre l'errore del test
      errorcode = (errorcode - 90000) % 99999
    self._errorcode = errorcode

  def __str__(self):
    return 'type: %s; start: %s; value: %1.3f; bytes: %d; counter_bytes: %d; counter_payload: %d; errorcode: %d' % (self.type, self.start.isoformat(), self.value * 1000, self.bytes, self.counter_bytes, self.counter_payload, self.errorcode)

if __name__ == '__main__':
  t = Proof('download', datetime.now(), 20, 100000, 140000, 100000, 101)
  print t
  t = Proof('ping', datetime.now(), 10000, 999)
  print t
