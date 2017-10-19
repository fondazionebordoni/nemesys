# result_sender.py
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


import logging
import os
import re
import time
from datetime import datetime

import xmltodict

from common import ntptime
from mist import gui_event
from mist import paths

logger = logging.getLogger(__name__)
MAX_SEND_RETRY = 3


def parse_response(data):
    """
    Valuta l'XML ricevuto dal repository, restituisce il codice e il messaggio ricevuto
    """
    code = 99
    message = ''
    try:
        xml_dict = xmltodict.parse(data)
        response_dict = xml_dict['response']
        message = response_dict.get('message') or ''
        code = response_dict.get('code') or 99
    except Exception:
        logger.error('Ricevuto risposta non XML dal server: %s', data)
    return int(code), message


def upload_one_file(deliverer, filename):
    upload_ok = False
    zipname = None
    try:
        zipname = deliverer.pack(filename)
        response = deliverer.upload(zipname)

        if response is not None:
            (code, message) = parse_response(response)
            logger.info('Risposta dal server di upload: [%d] %s', code, message)
            upload_ok = code == 0
    except Exception as e:
        logger.error('Errore durante la spedizione del file delle misure %s: %s', filename, e,
                     exc_info=True)
    finally:
        if os.path.exists(filename) and upload_ok:
            os.remove(filename)  # Elimino XML se esiste
        if zipname and os.path.exists(zipname):
            os.remove(zipname)  # Elimino ZIP se esiste
    return upload_ok


def upload(event_dispatcher, deliverer, fname=None):
    """
    Cerca di spedire al repository entro il tempo messo a disposizione secondo il parametro httptimeout
    uno o tutti i filename di misura che si trovano nella cartella d'uscita
    """
    if fname is not None:
        filenames = [fname]
    else:
        filenames = []
        for root, _, files in os.walk(paths.OUTBOX_DIR):
            for xmlfile in files:
                if re.search('measure_[0-9]{14}.xml', xmlfile):
                    filenames.append(os.path.join(root, xmlfile))
    len_filenames = len(filenames)
    num_sent_files = 0
    if len_filenames > 0:
        event_dispatcher.postEvent(gui_event.UpdateEvent('Salvataggio delle misure in corso....'))
        logger.info('Trovati %s file di misura da spedire.', len_filenames)
        for filename in filenames:
            if not os.path.exists(filename):
                logger.warn('File %s non esiste, passo al prossimo', filename)
                continue
            upload_ok = False
            retries = 0
            while not upload_ok and retries < MAX_SEND_RETRY:
                retries += 1
                upload_ok = upload_one_file(deliverer, filename)

                if upload_ok:
                    logger.info('File %s spedito con successo.', filename)
                    num_sent_files += 1
                else:
                    logger.info('Errore nella spedizione del file %s.', filename)
                    event_dispatcher.postEvent(gui_event.ErrorEvent(
                        'Tentativo di salvataggio numero {} di {} fallito.'.format(retries, MAX_SEND_RETRY)))
                    if retries >= MAX_SEND_RETRY:
                        event_dispatcher.postEvent(gui_event.ErrorEvent('Impossibile salvare le misure.'))
                        break
                    else:
                        sleep_time = 5 * retries
                        event_dispatcher.postEvent(gui_event.ErrorEvent(
                            'Nuovo tentativo fra {} secondi.'.format(sleep_time)))
                        time.sleep(sleep_time)

        for filename in filenames:
            if os.path.exists(filename):
                os.remove(filename)
        if num_sent_files == len_filenames:
            event_dispatcher.postEvent(gui_event.UpdateEvent('Salvataggio completato con successo.',
                                                             gui_event.UpdateEvent.MAJOR_IMPORTANCE))
        else:
            logger.warn('Num sent files (%d) less than num files (%d)', num_sent_files, len_filenames)
    else:
        logger.info('Nessun file di misura da spedire.')
    return num_sent_files


def save_and_send_measure(measure, event_dispatcher, deliverer):
    # Salva il file con le misure
    f = open(os.path.join(paths.OUTBOX_DAY_DIR, 'measure_%s.xml' % measure.id), 'w')
    f.write(str(measure))
    # Aggiungi la data di fine in fondo al file
    f.write('\n<!-- [finished] %s -->' % datetime.fromtimestamp(ntptime.timestamp()).isoformat())
    f.close()
    return upload(event_dispatcher, deliverer)
