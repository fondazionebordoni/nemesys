# getconf.py
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

import httplib
import urlparse
import os

def getconf(serial, dir, filename, url):
   '''
   Scarica il file di configurazione dalla url (HTTPS) specificata, salvandolo nel file specificato.
   Solleva eccezioni in caso di problemi o file ricevuto non corretto.
   '''
   url = urlparse.urlparse(url)
   connection = httplib.HTTPSConnection(host=url.hostname)
   # Warning This does not do any verification of the server’s certificate.

   connection.request('GET', '%s?clientid=%s' % (url.path, serial))
   data = connection.getresponse().read()
   print "Got response: %s" % str(data)
   # Controllo stupido sul contenuto del file
   if ("clientid" in str(data)):
      with open('%s/%s' % (dir, filename), 'w') as file:
         file.write(data)
   elif ("non valido" in str(data)):
       return False
   else:
      raise Exception('Error in configuration file')

   return os.path.exists(file.name)

if __name__ == '__main__':
   filetmp = 'client.conf'
   service = 'https://finaluser.agcom244.fub.it/Config'
   
   if (os.path.exists(filetmp)):
      os.remove(filetmp)
      
   try:
      getconf('fub00000000001', '.', filetmp, service)
      assert False
   except:
      assert True
      
   if (os.path.exists(filetmp)):
      os.remove(filetmp)
      
   try:
      getconf('', '.', filetmp, service)
      assert False
   except:
      assert True
      
   exit
      
   if (os.path.exists(filetmp)):
      os.remove(filetmp)

   try:
      getconf('test@example.com|notaverystrongpassword', '.', filetmp, service)
      assert False
   except:
      assert True

   if (os.path.exists(filetmp)):
      os.remove(filetmp)


