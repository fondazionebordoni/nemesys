# deliverer.py
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

import datetime
import hashlib
from httplib import HTTPException
from httputils import post_multipart
from logger import logging
from os import path
from urlparse import urlparse
import zipfile
from ssl import SSLError

logger = logging.getLogger()

class Deliverer:
  
  def __init__(self, url, certificate, timeout=60):
    self._url = url
    self._certificate = certificate
    self._timeout = timeout

  def upload(self, filename):
    '''
    Effettua l'upload del file .xml contenente la misura zippato. Restituisce la risposta ricevuta dal repository o None se c'è stato un problema.
    '''
     
    zip = self.pack(filename)

    # Controllo esito procedura compressione e firma
    if zip != None:

      logger.debug('Invio del file %s' % zip)

      try:
        file = open(zip, 'r')
        body = file.read()
        file.close()
        url = urlparse(self._url)
        response = post_multipart(url, fields=None, files=[('myfile', path.basename(zip), body)], certificate=self._certificate, timeout=self._timeout)
        
      except HTTPException as e:
        logger.error('Impossibile effettuare l\'invio del file delle misure. Errore: %s' % e)
        return None

      except SSLError as e:
        logger.error('Errore SSL durante l\'invio del file delle misure: %s' % e)
        return None

      return response
     
    else:
      logger.error("Impossibile inviare il file contenente le misure al Server Repository")
      return None
   

  def pack(self, filename):
    '''
    Crea un file zip contenente //filename// e la sua firma SHA1. Restituisce il nome del file zip creato.
    '''

    # Aggiungi la data in fondo al file
    file = open(filename, 'a')
    file.write('\n<!-- %s -->' % datetime.datetime.now().isoformat())
    file.close()

    sign = None
    if self._certificate != None and path.exists(self._certificate):
      # Crea il file della firma
      signature = self.sign(filename)
      if signature == None:
        logger.error('Impossibile eseguire la firma del file delle misure. Creazione dello zip omettendo il .sign')
      else:
        sign = open('%s.sign' % filename[0:-4], 'w')
        sign.write(signature)
        sign.close()

    # Crea il file zip
    zipname = '%s.zip' % filename[0:-4]
    zip = zipfile.ZipFile(zipname, 'a', zipfile.ZIP_DEFLATED)
    zip.write(file.name, path.basename(file.name))

    if sign != None and path.exists(sign.name):
        zip.write(sign.name, path.basename(sign.name))
      
    if zip.testzip() != None:
      logger.error("Lo zip del file %s è corrotto" % zip.testzip())
      return None
    else:
      zip.close()
      return zipname
   
  #restituisce la firma del file da inviare
  def sign(self, filename):
    '''
    Restituisce la stringa contenente la firma del digest SHA1 del
    file da firmare
    '''
    try:
      from M2Crypto import RSA
    except Exception:
      logger.debug('Impossibile importare il modulo M2Crypto')
      return None

    data = open(filename, 'r').read()
    digest = hashlib.sha1(data).digest()

    rsa = RSA.load_key(self._certificate)

    signature = rsa.sign(digest)
    if rsa.verify(digest, signature):
      return signature
    else:
      return None

if __name__ == '__main__':
  d = Deliverer('https://repository.agcom244.fub.it/Upload', 'fub000.pem')
  #d = Deliverer('https://dataserver.fub.it/Upload', 'fub000.pem')
  #d = Deliverer('http://platone.fub.it/', 'fub000.pem')
  print ('%s' % d.upload("outbox/measure.xml"))
  
