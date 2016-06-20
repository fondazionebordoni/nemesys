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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import datetime
import glob
import hashlib
from httplib import HTTPException
import logging
import os
import re
import shutil
from ssl import SSLError
from string import join
from urlparse import urlparse
from xml.dom import Node
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError
import zipfile

from httputils import post_multipart
from timeNtp import timestampNtp


logger = logging.getLogger(__name__)

class Deliverer(object):

    def __init__(self, url, certificate, timeout=60):
        self._url = url
        self._certificate = certificate
        self._timeout = timeout

    def upload(self, filename):
        '''
        Effettua l'upload del file. Restituisce la risposta ricevuta dal repository o None se c'è stato un problema.
        '''
        response = None
        logger.info('Invio a WEB: %s' % self._url)
        logger.info('Del file ZIP: %s' % filename)
        try:
            with open(filename, 'rb') as myfile:
                body = myfile.read()
            
            url = urlparse(self._url)
            response = post_multipart(url, fields=None, files=[('myfile', os.path.basename(filename), body)], certificate=self._certificate, timeout=self._timeout)

        except HTTPException as e:
            os.remove(filename)
            logger.error('Impossibile effettuare l\'invio del file delle misure. Errore: %s' % e)

        except SSLError as e:
            os.remove(filename)
            logger.error('Errore SSL durante l\'invio del file delle misure: %s' % e)

        return response

    def pack(self, filename):
        '''
        Crea un file zip contenente //filename// e la sua firma SHA1.
        Restituisce il nome del file zip creato.
        '''

        # Aggiungi la data di invio in fondo al file
        with open(filename, 'a') as myfile:
            myfile.write('\n<!-- [packed] %s -->' % datetime.datetime.fromtimestamp(timestampNtp()).isoformat())            

        # Gestione della firma del file
        sign = None
        if self._certificate != None and os.path.exists(self._certificate):
            # Crea il file della firma
            signature = self.sign(filename)
            if signature == None:
                logger.error('Impossibile eseguire la firma del file delle misure. Creazione dello zip omettendo il .sign')
            else:
                with open('%s.sign' % filename[0:-4], 'wb') as sign:
                    sign.write(signature)

        # Creazione del file zip
        zipname = '%s.zip' % filename[0:-4]
        zip_file = zipfile.ZipFile(zipname, 'a', zipfile.ZIP_DEFLATED)
        zip_file.write(myfile.name, os.path.basename(myfile.name))

        # Sposto la firma nello zip
        if sign != None and os.path.exists(sign.name):
                zip_file.write(sign.name, os.path.basename(sign.name))
                os.remove(sign.name)

        # Controllo lo zip
        if zip_file.testzip() != None:
            zip_file.close()
            logger.error("Lo zip %s è corrotto. Lo elimino." % zipname)
            os.remove(zipname)
            zipname = None
        else:
            zip_file.close()
            logger.debug("File %s compresso correttamente in %s" % (filename, zipname))

        # A questo punto ho un xml e uno zip
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

        data = open(filename, 'rb').read()
        digest = hashlib.sha1(data).digest()

        rsa = RSA.load_key(self._certificate)

        signature = rsa.sign(digest)
        if rsa.verify(digest, signature):
            return signature
        else:
            return None


    def uploadall_and_move(self, directory, to_dir, do_remove=True):
        '''
        Cerca di spedire tutti i file di misura che trova nella cartella d'uscita
        '''
        for filename in glob.glob(os.path.join(directory, 'measure_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].xml')):
            #logger.debug('Trovato il file %s da spedire' % filename)
            self.upload_and_move(filename, to_dir, do_remove)

    def upload_and_move(self, filename, to_dir, do_remove=True):
        '''
        Spedisce il filename di misura al repository entro il tempo messo a
        disposizione secondo il parametro httptimeout
        '''
        response = None
        result = False

        try:
            # Crea il Deliverer che si occuperà della spedizione
            #logger.debug('Invio il file %s a %s' % (filename, self._repository))
            zipname = self.pack(filename)
            response = self.upload(zipname)

            if (response != None):
                (code, message) = self._parserepositorydata(response)
                code = int(code)
                logger.info('Risposta dal server di upload: [%d] %s' % (code, message))

                # Se tutto è andato bene sposto il file zip nella cartella "sent" e rimuovo l'xml
                if (code == 0):
                    os.remove(filename)
                    self._movefiles(zipname, to_dir)

                    result = True

        except Exception as e:
            logger.error('Errore durante la spedizione del file delle misure %s: %s' % (filename, e))

        finally:
            # Elimino lo zip del file di misura temporaneo
            if os.path.exists(zipname):
                os.remove(zipname)
            # Se non sono una sonda _devo_ cancellare il file di misura 
            if do_remove and os.path.exists(filename):
                os.remove(filename)

            return result
        
        
    def _parserepositorydata(self, data):
        '''
        Valuta l'XML ricevuto dal repository, restituisce il codice e il messaggio ricevuto
        '''
        #TODO: use xmltodict instead
        xml = getxml(data)
        if (xml == None):
            logger.error('Nessuna risposta ricevuta')
            return None

        nodes = xml.getElementsByTagName('response')
        if (len(nodes) < 1):
            logger.error('Nessuna risposta ricevuta nell\'XML:\n%s' % xml.toxml())
            return None

        node = nodes[0]

        code = getvalues(node, 'code')
        message = getvalues(node, 'message')
        return (code, message)



    def _movefiles(self, filename, to_dir):

        directory = os.path.dirname(filename)
        #pattern = path.basename(filename)[0:-4]
        pattern = os.path.basename(filename)

        try:
            for f in os.listdir(directory):
                # Cercare tutti i file che iniziano per pattern
                if (re.search(pattern, f) != None):
                    # Spostarli tutti in self._sent
                    old = ('%s/%s' % (directory, f))
                    new = ('%s/%s' % (to_dir, f))
                    shutil.move(old, new)

        except Exception as e:
            logger.error('Errore durante lo spostamento dei file di misura %s' % e)

def getxml(data):
    
    if (len(data) < 1):
        logger.error('Nessun dato da processare')
        raise Exception('Ricevuto un messaggio vuoto');

    logger.debug('Dati da convertire in XML:\n%s' % data)
    try:
        xml = parseString(data)
    except ExpatError:
        logger.error('Il dato ricevuto non è in formato XML: %s' % data)
        raise Exception('Errore di formattazione del messaggio');

    return xml



def getvalues(node, tag=None):

    if (tag == None):
        values = []
        for child in node.childNodes:
            if child.nodeType == Node.TEXT_NODE:
                #logger.debug('Trovato nodo testo.')
                values.append(child.nodeValue)

        #logger.debug('Value found: %s' % join(values).strip())
        return join(values).strip()

    else:
        return getvalues(node.getElementsByTagName(tag)[0])



if __name__ == '__main__':
    import log_conf
    log_conf.init_log()
    d = Deliverer('https://repository.agcom244.fub.it/Upload', 'fub000.pem')
    print ('%s' % d.upload(d.pack("outbox/measure.xml")))
