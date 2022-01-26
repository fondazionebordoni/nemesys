#!/usr/bin/env python
# -*- coding: utf-8 -*-
# checkSoftware.py
# -*- coding: utf-8 -*-
# Copyright (c) 2016 Fondazione Ugo Bordoni.
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
import re
import webbrowser
import wx
from urllib.parse import urlparse

from common import httputils

MSG_SCADUTO = '''
Questa versione di %s
e' scaduta da %s giorni e pertanto
non potra' piu' essere utilizzata.
'''

MSG_NUOVA_VERSIONE_ = '''
E' disponibile una nuova versione:
%s %s

E' possibile effettuare il download
nella pagina di download del sito
www.misurainternet.it

Vuoi scaricare ora la nuova versione?
'''

SWN = 'MisuraInternet Speed Test'

logger = logging.getLogger(__name__)

URL_VERSION = 'https://speedtest.agcom244.fub.it/Version'
URL_MISURAINTERNET = 'https://www.misurainternet.it'  # /login_form.php'


def show_dialog(dialog):
    """
    Creates a dialog window with message, title and style as in the
    dict passed
    """
    message_dialog = wx.MessageDialog(None, dialog['message'], dialog['title'], dialog['style'])
    res = message_dialog.ShowModal()
    message_dialog.Destroy()
    return res


def get_version(version):
    url = urlparse(URL_VERSION)
    connection = httputils.get_verified_connection(url=url, certificate=None)
    connection.request('GET', '%s?speedtest=true&version=%s' % (url.path, version))
    data = connection.getresponse().read()
    # Esempio di risposta: '1.1.1beta:8'
    if re.search(r'(\.?\d+)+?.\S+:', data) is None:
        logger.warning("Non e' stato possibile controllare la versione per risposta errata del server.")
        return True

    data = data.split(':')

    # una stringa di uno o piu' numeri      \d+
    # opzionalmente preceduta da un punto   \.?
    # che si ripeta piu' volte              (\.?\d+)+
    remote_version_regex = re.search(r'(\.?\d+)+', data[0])
    if not remote_version_regex:
        raise Exception('Ricevuto stringa anomala per la versione dal server: %s', data)

    # DEADLINE
    # una stringa di uno o piu' numeri            \d+
    # opzionalmente preceduta da un segno meno     -?
    # ma che non abbia alcun carattere dopo       (?!.)
    days_left = re.search(r'(-?\d+)(?!.)', data[1])
    if not days_left:
        return remote_version_regex.string, None
    else:
        return remote_version_regex.string, days_left.string


def get_new_version(version, remote_version):
    new_version_dialog = \
        {
            'style': wx.YES | wx.NO | wx.ICON_INFORMATION,
            'title': '%s %s' % (SWN, version),
            'message': MSG_NUOVA_VERSIONE_ % (SWN, remote_version)
        }
    result = show_dialog(new_version_dialog)
    if result == wx.ID_YES:
        logger.info("Si e' scelto di scaricare la nuova versione del software.")
        webbrowser.open(URL_MISURAINTERNET, new=2, autoraise=True)
        # Torna False per fermare Speedtest
        return True


def warn_version_not_valid(days_left, version):
    still_day = -(int(days_left))
    logger.info("L'attuale versione %s e' scaduta da %s giorni.", version, still_day)
    after_deadline = \
        {
            'style': wx.OK | wx.ICON_EXCLAMATION,
            'title': '%s %s' % (SWN, version),
            'message': MSG_SCADUTO % (SWN, still_day)
        }
    show_dialog(after_deadline)


def do_check(version):
    """
    Check if the running version is the most recent
    If not, ask user to download the latest
    """
    try:
        (remote_version, days_left) = get_version(version)
    except Exception:
        # This should not stop Speedtest
        return True

    logger.info("L'ultima versione sul server e' la %s", remote_version)

    if version == remote_version:
        logger.info("E' in esecuzione l'ultima versione del software.")
        return True

    logger.info("Nuova versione disponibile [ this:%s | last:%s ]", version, remote_version)
    if get_new_version(version, remote_version):
        # Stop Speedtest
        return False

    logger.info("Si e' scelto di continuare ad utilizzare la vecchia versione del software.")

    logger.info("Giorni rimasti comunicati dal server: %s", days_left)
    if not days_left or int(days_left) >= 0:
        logger.info("L'attuale versione %s scade fra %s giorni.", version, days_left)
        return True

    warn_version_not_valid(days_left, version)
    return False


if __name__ == '__main__':
    from . import log_conf

    log_conf.init_log()
    app = wx.App(False)
    print(do_check('1.1.2'))
