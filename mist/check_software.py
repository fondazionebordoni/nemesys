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
from urlparse import urlparse

from common import httputils
import mist_options
from registration import registration

SWN = 'MisuraInternet Speed Test'

logger = logging.getLogger(__name__)

# Data di scadenza
dead_date = 22221111

url_version = "https://speedtest.agcom244.fub.it/Version"
area_privata = "https://www.misurainternet.it"  # /login_form.php"


class CheckSoftware(object):
    def __init__(self, version):
        (options, args, md5conf) = mist_options.parse(version=version, description='')
        self._httptimeout = options.httptimeout
        self._clientid = options.clientid
        self._thisVersion = version
        self._lastVersion = version
        self._stillDay = "unknown"

    def _showDialog(self, dialog):
        msgBox = wx.MessageDialog(None, dialog['message'], dialog['title'], dialog['style'])
        res = msgBox.ShowModal()
        msgBox.Destroy()
        return res

    def _softwareVersion(self):
        version_ok = True
        deadline_ok = True

        url = urlparse(url_version)
        connection = httputils.get_verified_connection(url=url, certificate=None, timeout=self._httptimeout)
        try:
            connection.request('GET', '%s?speedtest=true&version=%s' % (url.path, self._thisVersion))
            data = connection.getresponse().read()
            # data = "1.1.1beta:8"        # example
            if re.search('(\.?\d+)+?.\S+:', data) is None:
                logger.warning("Non e' stato possibile controllare la versione per risposta errata del server.")
                return True

            data = data.split(":")

            version = re.search('(\.?\d+)+', data[0])
            '''
            una stringa di uno o piu' numeri      \d+
            opzionalmente preceduta da un punto   \.?
            che si ripeta piu' volte              (\.?\d+)+
            '''
            if version is not None:
                self._lastVersion = version.string
                logger.info("L'ultima versione sul server e' la %s" % self._lastVersion)
                if self._thisVersion != self._lastVersion:
                    logger.info("Nuova versione disponbile. [ this:{} | last:{} ]"
                                .format(self._thisVersion, self._lastVersion))
                    new_version = \
                        {
                            "style": wx.YES | wx.NO | wx.ICON_INFORMATION,
                            "title": "%s %s" % (SWN, self._thisVersion),
                            "message": '''
                            E' disponibile una nuova versione:
                            %s %s

                            E' possibile effettuare il download dalla relativa sezione
                            nell'area privata del sito www.misurainternet.it

                            Vuoi scaricare ora la nuova versione?
                            ''' % (SWN, self._lastVersion)
                        }
                    res = self._showDialog(new_version)
                    if res == wx.ID_YES:
                        version_ok = False
                        logger.info("Si e' scelto di scaricare la nuova versione del software.")
                        webbrowser.open(area_privata, new=2, autoraise=True)
                        return version_ok
                    else:
                        logger.info("Si e' scelto di continuare ad utilizzare la vecchia versione del software.")
                        version_ok = True
                else:
                    version_ok = True
                    logger.info("E' in esecuzione l'ultima versione del software.")
            else:
                version_ok = True
                logger.error("Errore nella verifica della presenza di una nuova versione.")

            # DEADLINE
            deadline = re.search('(-?\d+)(?!.)', data[1])
            '''
            una stringa di uno o piu' numeri            \d+
            ozionalmente preceduta da un segno meno     -?
            ma che non abbia alcun carattere dopo       (?!.)
            '''
            if deadline is not None:
                self._stillDay = deadline.string
                logger.info("Giorni rimasti comunicati dal server: %s" % self._stillDay)
                if int(self._stillDay) >= 0:
                    deadline_ok = True
                    logger.info("L'attuale versione %s scade fra %s giorni." % (self._thisVersion, self._stillDay))
                    before_deadline = \
                        {
                            "style": wx.OK | wx.ICON_EXCLAMATION,
                            "title": "%s %s" % (SWN, self._thisVersion),
                            "message": '''
                            Questa versione di %s
                            potra' essere utilizzata ancora per %s giorni.
                            ''' % (SWN, self._stillDay)
                        }
                    self._showDialog(before_deadline)
                else:
                    deadline_ok = False
                    self._stillDay = -(int(self._stillDay))
                    logger.info("L'attuale versione %s e' scaduta da %s giorni." % (self._thisVersion, self._stillDay))
                    after_deadline = \
                        {
                            "style": wx.OK | wx.ICON_EXCLAMATION,
                            "title": "%s %s" % (SWN, self._thisVersion),
                            "message": '''
                            Questa versione di %s
                            e' scaduta da %s giorni e pertanto
                            non potra' piu' essere utilizzata.
                            ''' % (SWN, self._stillDay)
                        }
                    self._showDialog(after_deadline)
            else:
                deadline_ok = True
                logger.info("Questa versione del software non ha ancora scadenza.")

        except Exception as e:
            logger.error("Impossibile controllare se ci sono nuove versioni. Errore: %s." % e)

        return version_ok and deadline_ok

    def _is_registered(self):
        return registration(self._clientid)

    def check_it(self):
        check_ok = False
        check_list = {1: self._softwareVersion, 2: self._is_registered}
        for check in check_list:
            check_ok = check_list[check]()
            if not check_ok:
                break
        return check_ok


if __name__ == '__main__':
    import log_conf

    log_conf.init_log()
    app = wx.App(False)
    checker = CheckSoftware("1.1.2")
    checker.check_it()
