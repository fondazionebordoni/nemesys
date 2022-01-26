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
import logging
import os
import re
import shutil
import zipfile
from http.client import HTTPException
from ssl import SSLError
from urllib.parse import urlparse

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

from common import ntptime, backend_response
from common.httputils import post_multipart
from common.nem_exceptions import DeliveryException

logger = logging.getLogger(__name__)


class Deliverer(object):
    def __init__(self, url, certificate, timeout=60):
        self._url = url
        self._timeout = timeout
        self._private_key = None
        if certificate:
            logger.info("Carico certificato da %s", certificate)
            try:
                with open(certificate, "rb") as key_file:
                    self._private_key = serialization.load_pem_private_key(
                        key_file.read(),
                        password=None,
                        backend=default_backend()
                    )
            except Exception as e:
                logger.warning('Impossibile inizializzare chiave privata, i file non verranno firmate: %s', e)
        self._certificate = certificate

    def upload(self, filename):
        """
        Effettua l'upload del file. Restituisce la risposta ricevuta dal repository o None se c'è stato un problema.
        """
        response = None
        logger.info('Invio a WEB: %s', self._url)
        logger.info('Del file ZIP: %s', filename)
        try:
            with open(filename, 'rb') as myfile:
                body = myfile.read()

            url = urlparse(self._url)
            response = post_multipart(url,
                                      fields=None,
                                      files=[('myfile', os.path.basename(filename), body)],
                                      certificate=self._certificate,
                                      timeout=self._timeout)

        except HTTPException as e:
            os.remove(filename)
            logger.error('Impossibile effettuare l\'invio del file delle misure. Errore: %s', e)

        except SSLError as e:
            os.remove(filename)
            logger.error('Errore SSL durante l\'invio del file delle misure: %s', e)

        return response

    def pack(self, filename):
        """
        Crea un file zip contenente //filename// e la sua firma SHA1.
        Restituisce il nome del file zip creato.
        """

        # Aggiungi la data di invio in fondo al file
        with open(filename, 'a') as myfile:
            timestamp = ntptime.timestamp()
            myfile.write('\n<!-- [packed] %s -->' % datetime.datetime.fromtimestamp(timestamp).isoformat())

        # Gestione della firma del file
        signature_file = None
        if self._private_key:
            # Crea il file della firma
            with open(filename, 'rb') as data_file:
                data = data_file.read()
                signature = self._private_key.sign(data,
                                                   padding.PKCS1v15(),
                                                   hashes.SHA1())
            with open('%s.sign' % filename[0:-4], 'wb') as signature_file:
                signature_file.write(signature)

        # Creazione del file zip
        zipname = '%s.zip' % filename[0:-4]
        zip_file = zipfile.ZipFile(zipname, 'a', zipfile.ZIP_DEFLATED)
        zip_file.write(myfile.name, os.path.basename(myfile.name))

        # Sposto la firma nello zip
        if signature_file is not None and os.path.exists(signature_file.name):
            zip_file.write(signature_file.name, os.path.basename(signature_file.name))
            os.remove(signature_file.name)

        # Controllo lo zip
        if zip_file.testzip() is not None:
            zip_file.close()
            logger.error('Lo zip %s è corrotto. Lo elimino.', zipname)
            os.remove(zipname)
            zipname = None
        else:
            zip_file.close()
            logger.debug('File %s compresso correttamente in %s', filename, zipname)

        # A questo punto ho un xml e uno zip
        return zipname

    def uploadall_and_move(self, directory, to_dir, do_remove=True):
        """
        Cerca di spedire tutti i file di misura che trova nella cartella d'uscita
        """
        file_pattern = 'measure_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].xml'
        for filename in glob.glob(os.path.join(directory, file_pattern)):
            try:
                self.upload_and_move(filename, to_dir, do_remove)
                logger.debug('Inviato il file %s', filename)
            except Exception as e:
                logger.warning('Errore inviando il file %s: %s', filename, e)

    def upload_and_move(self, filename, to_dir, do_remove=True):
        """
        Spedisce il filename di misura al repository entro il tempo messo a
        disposizione secondo il parametro httptimeout
        """
        logger.debug('Invio il file %s a %s', filename, self._url)
        zip_file_name = self.pack(filename)
        response = self.upload(zip_file_name)
        # Elimino lo zip del file di misura temporaneo
        if os.path.exists(zip_file_name):
            os.remove(zip_file_name)
        # Se non sono una sonda _devo_ cancellare il file di misura
        if do_remove and os.path.exists(filename):
            os.remove(filename)

        if response is not None:
            (code, message) = backend_response.parse(response)
            code = int(code)
            logger.info('Risposta dal server delle misure: [%d] %s', code, message)
            # TODO se codice è [301] Misura ricevuta ma non salvata sul database
            # dovrebbe specificarlo
            # Se tutto è andato bene sposto il file zip nella cartella "sent" e rimuovo l'xml
            # Anche in caso di "duplicate entry", 506
            if code == 0 or code == 506:
                if os.path.exists(filename):
                    os.remove(filename)
                _movefiles(zip_file_name, to_dir)
            else:
                raise DeliveryException('Messaggio dal server: [%d] %s' % (code, message))
        else:
            raise DeliveryException('Errore durante la spedizione del file delle misure')


def _movefiles(filename, to_dir):
    directory = os.path.dirname(filename)
    pattern = os.path.basename(filename)

    try:
        for f in os.listdir(directory):
            # Cercare tutti i file che iniziano per pattern
            if re.search(pattern, f) is not None:
                # Spostarli tutti in self._sent
                # TODO: use os.path.join e catch per ogni file
                old = ('%s/%s' % (directory, f))
                new = ('%s/%s' % (to_dir, f))
                shutil.move(old, new)
    except Exception as e:
        logger.error('Errore durante lo spostamento dei file di misura %s', e)
