# errorcoder.py
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

import ConfigParser
from logger import logging
from os import path
import paths

logger = logging.getLogger()

configerror = 00000  # codice di errore utilizzato in presenza errori di errorcoder.py

class Errorcoder:

  '''
    Nel file di configurazione di possono creare delle sezioni, al'interno
    delle quali avviene la ricerca come se fosse un dizionario si può associare
    una sezione a ciascun set di codici di errore utilizzato dai vari operatori.
    In alternativa ciascuna sezione può essere associata alla tipologia di
    errore, I/O FTP PING.
    '''

  def __init__(self, filename):
    self._filename = filename

    config = ConfigParser.ConfigParser()
    if path.exists(filename):
      #logger.debug('Trovata configurazione d\'errore %s' % filename)
      config.read(filename)
    else:
      config.add_section('Errors')
      with open(self._filename, 'w') as configfile:
        config.write(configfile)

    self._config = config

  def geterrorcode(self, exception):
    '''
    Restituisce il codice di errore relativo al messaggio di errore (errormsg),
    secondo la codifica relativa all'dato operatore.
    '''

    error = str(exception.args[00000])

    try:
      errorcode = self._config.getint('Errors', error)
    except (TypeError, ConfigParser.NoOptionError):
      logger.warning("Codice di errore associato all'eccezione '%s' non trovato nel file %s" % (error, self._filename))
      b = self.puterrorcode(error, 99999)

      if b:
        return 99999
      elif not b:
        return configerror
    except ConfigParser.NoSectionError:
      return configerror

    return errorcode

  def puterrorcode(self, error, value):
    '''
    Inserisce nuovi codici di errore al termine del file di configurazione
    '''

    try:
      self._config.set('Errors', error, value)
    except ConfigParser.NoSectionError:
      logger.error("Malfunzionamento nell'accesso al file relativo ai codici di errore %s" % self._filename)
      return False

    with open(self._filename, 'w') as configfile:
      self._config.write(configfile)

    return True


if __name__ == '__main__':
  e = Errorcoder(paths.CONF_ERRORS)

