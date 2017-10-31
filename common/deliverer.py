# deliverer.py
# -*- coding: utf-8 -*-

# Copyright (c) 2010-2016 Fondazione Ugo Bordoni.
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
import logging
import os
import re
import shutil
import zipfile
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from httplib import HTTPException
from ssl import SSLError
from string import join
from urlparse import urlparse
from xml.dom import Node
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError

import pem

from common import httputils
from common import ntptime

logger = logging.getLogger(__name__)


class Deliverer(object):
    def __init__(self, url, certificate, timeout=60):
        self._url = url
        self._certificate = certificate
        self._signer = None
        try:
            certs_and_keys = pem.parse_file(certificate)
            for key in certs_and_keys:
                if isinstance(key, pem.Key):
                    private_key = RSA.importKey(str(key))
                    self._signer = PKCS1_v1_5.new(private_key)
                    break
        except Exception:
            pass
        self._timeout = timeout

    def upload(self, filename):
        """
        Effettua l'upload del file. Restituisce la risposta ricevuta dal repository o None se c'è stato un problema.
        """
        response = None
        logger.info('Invio a WEB: %s' % self._url)
        logger.info('Del file ZIP: %s' % filename)
        try:
            with open(filename, 'rb') as file_to_upload:
                body = file_to_upload.read()

            url = urlparse(self._url)
            response = httputils.post_multipart(url,
                                                fields=None,
                                                files=[('file_to_upload', os.path.basename(filename), body)],
                                                certificate=self._certificate,
                                                timeout=self._timeout)

        except HTTPException as e:
            os.remove(filename)
            logger.error('Impossibile effettuare l\'invio del file delle misure. Errore: %s' % e)

        except SSLError as e:
            os.remove(filename)
            logger.error('Errore SSL durante l\'invio del file delle misure: %s' % e)

        return response

    def pack(self, filename):
        """
        Crea un file zip contenente //filename// e la sua firma SHA1.
        Restituisce il nome del file zip creato.
        """
        # Aggiungi la data di invio in fondo al file
        with open(filename, 'a') as file_to_pack:
            timestamp = ntptime.timestamp()
            file_to_pack.write('\n<!-- [packed] %s -->' % datetime.datetime.fromtimestamp(timestamp).isoformat())

        # Creazione del file zip
        zip_file_name = '%s.zip' % filename[0:-4]
        zip_file = zipfile.ZipFile(zip_file_name, 'a', zipfile.ZIP_DEFLATED)
        zip_file.write(file_to_pack.name, os.path.basename(file_to_pack.name))

        # Gestione della firma del file
        if self._signer is not None:
            # Crea il file della firma
            try:
                signature = self.get_signature(filename)
                with open('%s.sign' % filename[0:-4], 'wb') as signature_file:
                    signature_file.write(signature)
                # Sposto la firma nello zip
                zip_file.write(signature_file.name, os.path.basename(signature_file.name))
                os.remove(signature_file.name)
            except Exception:
                logger.error('Impossibile eseguire la firma del file delle misure. '
                             'Creazione dello zip omettendo il .sign')

        # Controllo lo zip
        if zip_file.testzip() is not None:
            zip_file.close()
            logger.error("Lo zip %s è corrotto. Lo elimino." % zip_file_name)
            os.remove(zip_file_name)
            zip_file_name = None
        else:
            zip_file.close()
            logger.debug("File %s compresso correttamente in %s" % (filename, zip_file_name))

        # A questo punto ho un xml e uno zip
        return zip_file_name

    # restituisce la firma del file da inviare
    def get_signature(self, filename):
        """
        Restituisce la stringa contenente la firma del digest SHA1 del
        file da firmare
        """
        digest = SHA.new()
        digest.update(open(filename).read())
        return self._signer.sign(digest)

    def upload_all_and_move(self, directory, to_dir, do_remove=True):
        """
        Cerca di spedire tutti i file di misura che trova nella cartella d'uscita
        """
        file_pattern = 'measure_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].xml'
        for filename in glob.glob(os.path.join(directory, file_pattern)):
            # logger.debug('Trovato il file %s da spedire' % filename)
            self.upload_and_move(filename, to_dir, do_remove)

    def upload_and_move(self, filename, to_dir, do_remove=True):
        """
        Spedisce il filename di misura al repository entro il tempo messo a
        disposizione secondo il parametro httptimeout
        """
        result = False
        zip_file_name = None
        try:
            # Crea il Deliverer che si occuperà della spedizione
            logger.debug('Invio il file %s a %s' % (filename, self._url))
            zip_file_name = self.pack(filename)
            response = self.upload(zip_file_name)

            if response is not None:
                (code, message) = _parserepositorydata(response)
                code = int(code)
                logger.info('Risposta dal server delle misure: [%d] %s' % (code, message))

                # Se tutto è andato bene sposto il file zip nella cartella "sent" e rimuovo l'xml
                # Anche in caso di "duplicate entry", 506
                if code == 0 or code == 506:
                    os.remove(filename)
                    _movefiles(zip_file_name, to_dir)

                    result = True
        except Exception as e:
            logger.error('Errore durante la spedizione del file delle misure %s: %s' % (filename, e))
        finally:
            # Elimino lo zip del file di misura temporaneo
            if os.path.exists(zip_file_name):
                os.remove(zip_file_name)
            # Se non sono una sonda _devo_ cancellare il file di misura
            if do_remove and os.path.exists(filename):
                os.remove(filename)

            return result


def _parserepositorydata(data):
    """
    Valuta l'XML ricevuto dal repository, restituisce il codice e il messaggio ricevuto
    """
    # TODO: use xmltodict instead
    xml = getxml(data)
    if xml is None:
        logger.error('Nessuna risposta ricevuta')
        return None

    nodes = xml.getElementsByTagName('response')
    if len(nodes) < 1:
        logger.error('Nessuna risposta ricevuta nell\'XML:\n%s' % xml.toxml())
        return None

    node = nodes[0]

    code = getvalues(node, 'code')
    message = getvalues(node, 'message')
    return code, message


def _movefiles(filename, to_dir):

    directory = os.path.dirname(filename)
    pattern = os.path.basename(filename)

    try:
        for f in os.listdir(directory):
            # Cercare tutti i file che iniziano per pattern
            if re.search(pattern, f) is not None:
                # Spostarli tutti in self._sent
                old = ('%s/%s' % (directory, f))
                new = ('%s/%s' % (to_dir, f))
                shutil.move(old, new)

    except Exception as e:
        logger.error('Errore durante lo spostamento dei file di misura %s' % e)


def getxml(data):
    if len(data) < 1:
        logger.error('Nessun dato da processare')
        raise Exception('Ricevuto un messaggio vuoto')

    logger.debug('Dati da convertire in XML:\n%s' % data)
    try:
        xml = parseString(data)
    except ExpatError:
        logger.error('Il dato ricevuto non è in formato XML: %s' % data)
        raise Exception('Errore di formattazione del messaggio')

    return xml


def getvalues(node, tag=None):
    if tag is None:
        values = []
        for child in node.childNodes:
            if child.nodeType == Node.TEXT_NODE:
                # logger.debug('Trovato nodo testo.')
                values.append(child.nodeValue)

        # logger.debug('Value found: %s' % join(values).strip())
        return join(values).strip()

    else:
        return getvalues(node.getElementsByTagName(tag)[0])
