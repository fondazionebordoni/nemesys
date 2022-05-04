# login.py
# -*- coding: utf-8 -*-

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

import tkinter
import hashlib
import logging
import os
import sys
import tkinter.messagebox
import urllib.request, urllib.error, urllib.parse

from common import httputils
from common import utils
from nemesys import log_conf
from common import paths

CANCEL_MESSAGE = '''L'autenticazione non e' andata a buon fine.
Procedere con la disinstallazione e reinstallare nuovamente Ne.Me.Sys. \
dopo aver controllato user-id e password che ti sono state invitate in fase \
di registrazione o a richiedere una nuova licenza dalla tua area privata sul sito misurainternet.it.'''

MAX_ERROR_MESSAGE = '''Le credenziali non sono corrette, il nome del file di installazione \
è stato modificato o la licenza non è più valida.
Procedere con la disinstallazione e reinstallare nuovamente Ne.Me.Sys. \
dopo aver controllato user-id e password che ti sono state invitate in fase \
di registrazione o a richiedere una nuova licenza dalla tua area privata sul sito misurainternet.it.'''

GENERIC_ERROR_MESSAGE = '''Si è verificato un errore. Verifica:

- di avere accesso alla rete,
- di non aver modificato il nome del file di installazione,
- di aver digitato correttamente le credenziali di accesso (se richieste),
- di avere una licenza attiva,
- di non aver ottenuto un certificato con Ne.Me.Sys. meno di 45 giorni antecedenti ad oggi.

Dopo 5 tentativi di accesso falliti, sarà necessario disinstallare \
Ne.Me.Sys e reinstallarlo nuovamente.'''

CONNECTION_ERROR_MESSAGE = '''Connessione fallita.
Verifica di avere accesso alla rete.'''

CODE_ERROR_MESSAGE = '''Autenticazione fallita o licenza non attiva.

Assicurati di non aver modificato il nome del file di installazione. \
Se questo fosse il caso, effettua nuovamente il download.

Se non hai modificato il nome del file di installazione, verifica i dati di accesso e la presenza di una licenza attiva al sito www.misurainternet.it'''

CLIENT_CONFIG = 'client.conf'
BACKEND_URL = {
    None: 'https://finaluser.agcom244.fub.it/Config',
    'PS': 'https://services.pianoscuola.misurainternet.it/config',
}


logger = logging.getLogger(__name__)


class LoginException(Exception):
    def __init__(self, message=''):
        Exception.__init__(self, message)


class LoginAuthenticationException(LoginException):
    pass


class LoginConnectionException(LoginException):
    pass


class LoginCancelledException(LoginException):
    pass


class MaxLoginException(LoginException):
    pass


def read_properties(filename):
    """
    reads a properties file and returns a dict of properties
    """
    with open(filename, "r") as inf:
        properties = {}
        for line in inf:
            line = line.strip()
            if '=' in line:
                name, value = line.split('=')
                properties[name.strip()] = value.strip()
    return properties


def write_properties(filename, properties):
    """
    (over)writes properties to a file
    """
    with open(filename, "w") as inf:
        for key in properties:
            inf.write("\r\n" + key + " = " + properties[key])


def getCode():
    """
    Apre una finestra che chiede il codice licenza. Resituisce il codice licenza e chiude la finestra.
    """
    root = tkinter.Tk()
    if utils.is_windows():
        root.wm_iconbitmap('Nemesys.ico')
    app = LoginGui(master=root)
    app.master.title("Attivazione Ne.Me.Sys")
    app.mainloop()
    serial_code = str(app.result)
    if root:
        root.destroy()

    if serial_code == 'Cancel':
        logger.info('Utente ha premuto Cancel')
        raise LoginCancelledException()

    if serial_code == 'None' or len(serial_code) < 4:
        raise LoginAuthenticationException('Nome utente o password sbagliato')

    return serial_code


def ErrorDialog(message):
    root = tkinter.Tk()
    if utils.is_windows():
        root.wm_iconbitmap('Nemesys.ico')
    root.withdraw()
    title = 'Errore'
    tkinter.messagebox.showerror(title, message, parent=root)
    root.destroy()


def OkDialog():
    root = tkinter.Tk()
    if utils.is_windows():
        root.wm_iconbitmap('Nemesys.ico')
    root.withdraw()
    title = 'Ne.Me.Sys autenticazione corretta'
    message = 'Username e password corrette e verificate'
    tkinter.messagebox.showinfo(title, message, parent=root)
    root.destroy()


def getActivationFile(client_type, token, path):
    """
      Scarica il file di configurazione.
    """
    logger.info(f'Codici ricevuti: {client_type}, {token}')

    try:
        url = '%s?clientid=%s' % (BACKEND_URL[client_type], token)
        resp = httputils.do_get(url)
        data = resp.read().decode('utf-8')
    except KeyError:
        logger.error(f"Tipo client {client_type} non riconosciuto")
        raise LoginAuthenticationException('')
    except Exception as e:
        logger.error('impossibile scaricare il file di configurazione: %s', e)
        raise LoginConnectionException(str(e))

    if 'clientid' in str(data):
        try:
            with open('%s/%s' % (path, CLIENT_CONFIG), 'w') as myfile:
                myfile.write(data)
                logger.info('File di configurazione scaricato con successo')
                if client_type is None:
                    OkDialog()
        except IOError as e:
            logger.error('Impossible scrivere il file di configurazione: %s', e)
            raise LoginException('Impossibile scrivere il file di configurazione: %s' % e)
    elif 'non valido' in str(data):
        logger.info('Ricevuto errore dal server, credenziali errati o licenza non attiva.')
        raise LoginAuthenticationException('')
    else:
        raise Exception('Errore nel file di configurazione')


class LoginGui(tkinter.Frame):
    """
    finestra di codice licenza
    """

    def sendMsg(self):
        inserted_username = self.username.get()
        inserted_password = self.password.get()
        if inserted_username and inserted_password:
            self.result = "{}|{}".format(
                self.username.get(),
                hashlib.sha1(self.password.get().encode('utf-8')).hexdigest()
            )
        self.quit()

    def cancel(self):
        self.result = 'Cancel'
        self.quit()

    def createWidgets(self):
        self.Title = tkinter.Label(self, padx=20, pady=8)
        self.Title["text"] = """
Se sei registrato sul sito misurainternet.it con SPID
inserisci codice fiscale e codice Ne.Me.Sys dell'utenza
(visibile nell'area personale).

Ma se ancora non hai migrato il tuo utente a SPID,
usa i vecchi codici di autenticazione, email e password,
che usi per accedere all'area personale.
"""
        self.Title.grid(column=0, row=0, columnspan=2)

        username_label = tkinter.Label(self, text="Cod. fiscale (o email):")
        username_label.grid(column=0, row=1)

        self.username = tkinter.Entry(self, width=20)
        self.username.grid(column=1, row=1)

        password_label = tkinter.Label(self, text="Cod. Ne.Me.Sys (o password):")
        password_label.grid(column=0, row=2)

        self.password = tkinter.Entry(self, width=20)
        self.password["show"] = "*"
        self.password.grid(column=1, row=2)

        self.button_frame = tkinter.Frame(self)
        self.button_frame.grid(column=0, row=3, columnspan=2, pady=8)

        self.invio = tkinter.Button(self.button_frame)
        self.invio["text"] = "Accedi",
        self.invio["command"] = self.sendMsg
        self.invio.grid(column=0, row=0, padx=4)

        self.cancl = tkinter.Button(self.button_frame)
        self.cancl["text"] = "Annulla",
        self.cancl["command"] = self.cancel
        self.cancl.grid(column=1, row=0, padx=4)

    def __init__(self, master=None):
        tkinter.Frame.__init__(self, master)
        self.config(width="800")
        if utils.is_windows():
            self.master.wm_iconbitmap('Nemesys.ico')
        self.pack()
        self.createWidgets()
        self.result = None


def try_to_activate(credentials):
    j = 0
    max_retries = 5 if credentials is None else 1
    # Al massimo faccio fare 5 tentativi di inserimento manuale codice di licenza
    while j < max_retries:
        # Prendo un codice licenza valido sintatticamente
        try:
            if credentials is None:
                client_type = None
                serial_code = getCode()
                token = serial_code
            else:
                client_type, token = credentials
                serial_code = "@".join(credentials)
            getActivationFile(client_type, token, paths._CONF_DIR)
            return serial_code
        except LoginAuthenticationException:
            logger.warning('Errore di autenticazione n. %d', j)
            message = CODE_ERROR_MESSAGE
        except LoginConnectionException as e:
            logger.warning('Problema di connessione al server per l\'autenticazione: %s', e)
            message = CONNECTION_ERROR_MESSAGE
        except LoginCancelledException:
            raise
        except LoginException as e:
            logger.warning('Si e\' riscontrato un problema nel login: %s', e)
            message = str(e)
        except Exception as e:
            logger.error('Si e\' riscontrato un problema scaricando il file di configurazione: %s', e)
            message = GENERIC_ERROR_MESSAGE
        ErrorDialog(message)
        j += 1
    raise MaxLoginException()


def extract_autoconf_credentials():
    """
    Return autoconf credentials, if they are part of the filename

    Filename may have the following format:
    Nemesys_VERSION@CLIENT_TYPE@TOKEN.exe

    In that case return client_type, token
    Otherwise, return None
    """
    logger.info(f'Linea di comando: {" ".join(sys.argv)}')
    if len(sys.argv) != 2:
        logger.info('login.exe eseguito con un numero incorretto di parametri')
        logger.info('Fallback in modalità di configurazione manuale')
        return None
    file_path = sys.argv[1]
    logger.info(f'Percorso del file: {file_path}')
    _, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)
    components = name.split('@')
    if len(components) != 3 and len(components) != 4:
        logger.info('Pacchetto non autoconfigurante')
        return None
    nemesys, client_type, token = components[:3]
    logger.info(f'Pacchetto autoconfigurante: tipo client {client_type}, token {token}')
    return client_type, token


def main():
    logger.info('Avvio del processo di autenticazione')
    #  READING PROPERTIES (if exist)
    app_dir = os.path.dirname(sys.argv[0])
    credentials = extract_autoconf_credentials()
    config_dir = os.path.join(app_dir, 'cfg')
    if not os.path.exists(config_dir):
        os.mkdir(config_dir)
    config_file = os.path.join(config_dir, 'cfg.properties')
    if os.path.exists(config_file):
        try:
            _prop = read_properties(config_file)
        except Exception as e:
            logger.error('Impossibile leggere il file di configurazione da %s: %s', config_file, e)
            try:
                # If config file exists, remove it!
                if os.path.exists(paths.CONF_MAIN):
                    logger.info('Rimuovo: %s', paths.CONF_MAIN)
                    os.remove(paths.CONF_MAIN)
                logger.info('Rimuovo: %s', config_file)
                os.remove(config_file)
                _prop = []
            except IOError:
                ErrorDialog('File di configurazione danneggiato, '
                            'impossibile procedere con l\'installazione'.format(config_file))
                sys.exit(1)
    else:
        _prop = []

    if 'registered' in _prop:
        # Ho tentato almeno una volta il download
        status = str(_prop['registered'])
        if status == 'ok':
            logger.info('File di configurazione gia\' scaricato precedentemente')
        else:
            logger.error('Login fallito precedentemente, bisogna reinstallare Nemesys')
            # Dialog to uninstall and retry
            ErrorDialog(MAX_ERROR_MESSAGE)
    else:
        try:
            code = try_to_activate(credentials)
            logger.info('Autenticazione completato con successo')
            write_properties(config_file, {'code': code, 'registered': 'ok'})
        except LoginCancelledException:
            ErrorDialog(CANCEL_MESSAGE)
        except MaxLoginException:
            logger.warning('Il massimo numero di tentativi di autenticazione raggiunto')
            write_properties(config_file, {'registered': 'nok'})
            ErrorDialog(MAX_ERROR_MESSAGE)


if __name__ == '__main__':
    log_conf.init_log()
    main()
