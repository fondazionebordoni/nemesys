#!/usr/bin/env python
# encoding: utf-8
# Copyright (c) 2011-2016 Fondazione Ugo Bordoni.
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
#
# Originally generated by wxGlade 0.6.3 on Wed Apr 11 17:48:58 2012


import hashlib
import httplib
import logging
import os
import ssl
import urlparse
import wx

from common import iptools
import paths

SWN = 'MisuraInternet Speed Test'

logger = logging.getLogger(__name__)

configurationServer = 'https://speedtest.agcom244.fub.it/Config'
MAXretry = 5  # # numero massimo di tentativi prima di chiudere la finestra ##
provinciaList = sorted(
    ["TO", "VC", "NO", "CN", "AT", "AL", "AO", "IM", "SV", "GE", "SP", "VA", "CO", "SO", "MI", "BG", "BS", "PV", "CR",
     "MN", "BZ", "TN", "VR", "VI", "BL", "TV", "VE", "PD", "RO", "UD", "GO", "TS", "PC", "PR", "RE", "MO", "BO", "FE",
     "RA", "FC", "PU", "AN", "MC", "AP", "MS", "LU", "PT", "FI", "LI", "PI", "AR", "SI", "GR", "PG", "TR", "VT", "RI",
     "RM", "LT", "FR", "CE", "BN", "NA", "AV", "SA", "AQ", "TE", "PE", "CH", "CB", "FG", "BA", "TA", "BR", "LE", "PZ",
     "MT", "CS", "CZ", "RC", "TP", "PA", "ME", "AG", "CL", "EN", "CT", "RG", "SR", "SS", "NU", "CA", "PN", "IS", "OR",
     "BI", "LC", "LO", "RN", "PO", "KR", "VV", "VB", "OT", "OG", "VS", "CI", "MB", "FM", "BT"])

reg_message = '''
Verranno ora richieste le credenziali per l'attivazione.\n
Se NON e' stata effettuata l'iscrizione verra' richiesto di
selezionare la provincia dalla quale si sta effettuando
la misura con %s.\n
Se e' stata effettuata l'iscrizione verra' richiesto di
inserire i codici di accesso (username e password)
utilizzate per accedere all'area riservata su misurainternet.it.
Al momento dell'inserimento si prega di verificare
la correttezza delle credenziali di accesso.\n
Dopo %s tentativi falliti, sara' necessario riavviare
il programma per procedere nuovamente all'inserimento.\n
Al momento dell'inserimento si prega di avere accesso alla rete.''' % (SWN, MAXretry)

RegInfo = {"style": wx.OK | wx.ICON_INFORMATION,
           "title": "Informazioni sulla registrazione",
           "message": reg_message
           }

cred_message = '''
Le credenziali di accesso inserite sono errate.\n
Controllare la loro correttezza accedendo all'area
personale sul sito www.misurainternet.it
'''

ErrorCode = {"style": wx.OK | wx.ICON_ERROR,
             "title": "%s Error" % SWN,
             "message": cred_message
             }

ErrorSave = {"style": wx.OK | wx.ICON_ERROR,
             "title": "%s Error" % SWN,
             "message": "\nErrore nel salvataggio del file di configurazione."
             }

ErrorDownload = {"style": wx.OK | wx.ICON_ERROR,
                 "title": "%s Error" % SWN,
                 "message": "\nErrore nel download del file di configurazione\no credenziali di accesso non corrette."
                 }

conf_err_message = '''
Il download del file di configurazione e' fallito per %s volte.\n
Riavviare il programma dopo aver verificato la correttezza
delle credenziali di accesso e di avere accesso alla rete.
''' % MAXretry

ErrorRetry = {"style": wx.OK | wx.ICON_ERROR,
              "title": "%s Error" % SWN,
              "message": conf_err_message
              }

ErrorRegistration = {"style": wx.OK | wx.ICON_ERROR,
                     "title": "%s Registration Error" % SWN,
                     "message": "\nQuesta copia di %s non risulta correttamente registrata." % SWN
                     }


class Dialog(wx.Dialog):
    def __init__(self, parent, title, default, caption):
        wx.Dialog.__init__(self, None, -1, title)
        window_panel = wx.Panel(self)

        label_info_provincia = wx.StaticText(window_panel, -1, "\nSe NON e' stata effettuata l'iscrizione inserire"
                                                               "\nla provincia in cui si sta effettuando"
                                                               "\nla misura con MisuraInternet Speed Test."
                                                               "\n", style=wx.ALIGN_CENTRE)
        label_provincia = wx.StaticText(window_panel, -1, "Provincia:", style=wx.ALIGN_RIGHT)
        self.text_provincia = wx.ComboBox(window_panel, choices=provinciaList, style=wx.CB_READONLY)
        label_info_login = wx.StaticText(window_panel, -1, "\nSe e' stata effettuata l'iscrizione inserire"
                                                           "\ni codici di accesso (username e password)"
                                                           "\nutilizzati per accedere all'area personale."
                                                           "\n", style=wx.ALIGN_CENTRE)
        label_username = wx.StaticText(window_panel, -1, "Username:", style=wx.ALIGN_RIGHT)
        self.text_username = wx.TextCtrl(window_panel, -1, default)
        label_password = wx.StaticText(window_panel, -1, "Password:", style=wx.ALIGN_RIGHT)
        self.text_password = wx.TextCtrl(window_panel, -1, "", style=wx.TE_PASSWORD)
        button_login = wx.Button(window_panel, caption, "Accedi")

        self.text_provincia.SetMinSize((80, 26))
        self.text_username.SetMinSize((180, 26))
        self.text_password.SetMinSize((180, 26))
        button_login.SetMinSize((80, 26))

        (pw_width, _) = label_password.GetSize().Get()
        (username_width, _) = label_username.GetSize().Get()
        if pw_width > username_width:
            label_username.SetMinSize((pw_width, -1))
        else:
            label_password.SetMinSize((username_width, -1))

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_input_username = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input_password = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input_provincia = wx.BoxSizer(wx.HORIZONTAL)

        sizer_input_provincia.Add(label_provincia, flag=wx.LEFT | wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, border=2)
        sizer_input_provincia.Add(self.text_provincia, flag=wx.LEFT | wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, border=2)

        sizer_input_username.Add(label_username, flag=wx.LEFT | wx.RIGHT | wx.ALIGN_RIGHT, border=2)
        sizer_input_username.Add(self.text_username, flag=wx.LEFT | wx.RIGHT | wx.ALIGN_RIGHT, border=2)

        sizer_input_password.Add(label_password, flag=wx.LEFT | wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, border=2)
        sizer_input_password.Add(self.text_password, flag=wx.LEFT | wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, border=2)

        sizer_main.Add(label_info_provincia, flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_BOTTOM | wx.ALL, border=8)
        sizer_main.Add(sizer_input_provincia, flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, border=2)
        sizer_main.Add(label_info_login, flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_BOTTOM | wx.ALL, border=2)
        sizer_main.Add(sizer_input_username, flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, border=2)
        sizer_main.Add(sizer_input_password, flag=wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, border=2)
        sizer_main.Add(button_login, flag=wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL,
                       border=8)

        window_panel.SetSizerAndFit(sizer_main)
        sizer_main.Fit(self)
        self.Layout()

        self.Bind(wx.EVT_BUTTON, self.button_pressed, button_login)
        self.text_password.Bind(wx.EVT_TEXT_PASTE, _on_pw_paste)

    def get_value(self):
        username = self.text_username.GetValue()
        password = self.text_password.GetValue()
        provincia = self.text_provincia.GetValue()
        if len(username) > 2:
            return "%s|%s" % (username, hashlib.sha1(password).hexdigest())
        else:
            if len(provincia) == 2:
                mac = iptools.get_mac_address()
                return "%s|%s" % (provincia, mac)
            else:
                return None

    def button_pressed(self, event):  # wxGlade: MyDialog.<event_handler>
        self.EndModal(event.GetId())


def _on_pw_paste(event):
    logger.debug("Ignoring password paste")


def show_dialog(dialog, message=None):
    if message is None:
        msg_box = wx.MessageDialog(None, dialog['message'], dialog['title'], dialog['style'], pos=(200, 200))
    else:
        msg_box = wx.MessageDialog(None, message, dialog['title'], dialog['style'], pos=(200, 200))
    msg_box.ShowModal()
    msg_box.Destroy()


def getconf(code, filepath, url_string):
    # # Scarica il file di configurazione dalla url (HTTPS) specificata, salvandolo nel file specificato. ##
    # # Solleva eccezioni in caso di problemi o file ricevuto non corretto. ##

    url = urlparse.urlparse(url_string)
    try:
        # TODO: This does not do any verification of the server's certificate. #
        try:
            '''python >= 2.7.9'''
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            connection = httplib.HTTPSConnection(host=url.hostname, context=context)
        except AttributeError:
            '''python < 2.7.9'''
            connection = httplib.HTTPSConnection(host=url.hostname)

        connection.request('GET', '%s?clientid=%s' % (url.path, code))
        logger.debug("Dati inviati: %s" % code)

        data = connection.getresponse().read()
    except:
        raise Exception("Impossibile contattare il server, verificare la connessione a Internet")
    logger.debug("Dati ricevuti:\n%s" % data)

    # Controllo se nel file di configurazione e' presente il codice di attivazione. #
    if data.find(code) != -1 or data.find("username") != -1:
        data2file = open(filepath, 'w')
        data2file.write(data)
    else:
        raise Exception(data.replace(";", ""))

    return os.path.exists(filepath)


def registration(code):
    if (len(code) < 4) or '|' in code:
        reg_ok = False
        logger.info("ClientID assente o di errata lunghezza, login richiesto")
        show_dialog(RegInfo)
        for retry in range(MAXretry):
            # # Prendo un codice licenza valido sintatticamente    ##
            logger.info('Tentativo di registrazione %s di %s' % (retry + 1, MAXretry))
            title = "Tentativo %s di %s" % (retry + 1, MAXretry)
            default = ""
            dlg = Dialog(None, title, default, wx.ID_OK)
            res = dlg.ShowModal()
            code = dlg.get_value()
            dlg.Destroy()
            logger.info("Codici di accesso inseriti dall'utente: %s" % code)
            if res != wx.ID_OK:
                logger.warning('Registration aborted at attempt number %d' % (retry + 1))
                break

            filepath = paths.CONF_MAIN
            try:
                if code is not None and len(code) > 4:
                    # Prendo il file di configurazione. #
                    reg_ok = getconf(code, filepath, configurationServer)
                    if reg_ok is True:
                        logger.info('Configuration file successfully downloaded and saved')
                        break
                    else:
                        logger.error('Configuration file not correctly saved')
                        show_dialog(ErrorSave)
                else:
                    logger.error('Wrong username/password')
                    show_dialog(ErrorCode)
            except Exception as error:
                logger.error('Configuration file not downloaded or incorrect: %s' % error)
                show_dialog(ErrorDownload, str(error))

            if not (retry + 1 < MAXretry):
                show_dialog(ErrorRetry)

        if not reg_ok:
            logger.info('Verifica della registrazione del software fallita')
            show_dialog(ErrorRegistration)

    else:
        reg_ok = True

    return reg_ok


if __name__ == '__main__':
    import log_conf
    log_conf.init_log()
    app = wx.App(False)
    registration("456")
    # getconf('ab0cd1ef2gh3ij4kl5mn6op7qr8st9uv', './../config/client.conf', 'https://finaluser.agcom244.fub.it/Config')
