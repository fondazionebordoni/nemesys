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

from common import ntptime, backend_response
from common import paths
from mist import gui_event

logger = logging.getLogger(__name__)
MAX_SEND_RETRY = 3


def upload_one_file(deliverer, filename):
    upload_ok = False
    zipname = None
    try:
        zipname = deliverer.pack(filename)
        response = deliverer.upload(zipname)

        if response is not None:
            (code, message) = backend_response.parse(response)
            logger.info('Risposta dal server di upload: [%d] %s', code, message)
            upload_ok = code == 0
    except Exception as e:
        logger.error('Errore durante la spedizione del file delle misure %s: %s', filename, e,
                     exc_info=True)
    finally:
        if zipname and os.path.exists(zipname):
            os.remove(zipname)  # Elimino ZIP se esiste
    return upload_ok


def save_and_send_measure(measure, event_dispatcher, deliverer):
    # Salva il file con le misure
    filename = os.path.join(paths.OUTBOX_DIR, 'measure_%s.xml' % measure.id)
    with open(filename, 'w') as f:
        f.write(str(measure))
        # Aggiungi la data di fine in fondo al file
        f.write('\n<!-- [finished] %s -->' % datetime.fromtimestamp(ntptime.timestamp()).isoformat())
    event_dispatcher.postEvent(gui_event.UpdateEvent('Salvataggio delle misure in corso....'))
    logger.info('File di misura %s da spedire.', filename)
    upload_ok = False
    retries = 0
    while not upload_ok and retries < MAX_SEND_RETRY:
        retries += 1
        upload_ok = upload_one_file(deliverer, filename)

        if upload_ok:
            logger.info('File %s spedito con successo.', filename)
            event_dispatcher.postEvent(gui_event.UpdateEvent('Salvataggio completato con successo.',
                                                             gui_event.UpdateEvent.MAJOR_IMPORTANCE))
        else:
            logger.warning('Errore nella spedizione del file %s.', filename)
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
    try:
        os.remove(filename)
    except OSError:
        logger.warning('File %s non rimosso: %s', filename, e)

