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

import Tkinter
import hashlib
import logging
import os
import sys
import tkMessageBox

from common import utils
from nemesys import log_conf
from nemesys import paths
from nemesys.getconf import getconf

logger = logging.getLogger(__name__)

_clientConfigurationFile = 'client.conf'
_configurationServer = 'https://finaluser.agcom244.fub.it/Config'


class LoginException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


class LoginAuthenticationException(LoginException):
    def __init__(self, message):
        Exception.__init__(self, message)


class LoginConnectionException(LoginException):
    def __init__(self, message):
        Exception.__init__(self, message)


class LoginCancelledException(LoginException):
    def __init__(self, message=""):
        Exception.__init__(self, message)


class MaxLoginException(LoginException):
    def __init__(self, message=""):
        Exception.__init__(self, message)


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


### Activation code ###
def getCode():
    """
    Apre una finestra che chiede il codice licenza. Resituisce il codice licenza e chiude la finestra.
    """
    root = Tkinter.Tk()
    if utils.is_windows():
        root.wm_iconbitmap('Nemesys.ico')
    app = LoginGui(master=root)
    app.master.title("Attivazione Ne.Me.Sys")
    app.mainloop()
    appresult = str(app.result)
    logger.info(appresult)

    if appresult == 'Cancel':
        logger.info("User pressed Cancel button, exiting")
        raise LoginCancelledException()

    if appresult == '' or len(appresult) < 4:
        logger.error('Wrong activation code')
        # CodeError()
        raise LoginAuthenticationException('Wrong username/password')

    if root:
        root.destroy()
    return appresult


def CodeError():
    """
    Errore in caso di credenziali errate
    """
    message = '''Autenticazione fallita o licenza non attiva.

Controllare i dati di accesso e la presenza di una licenza attiva al sito www.misurainternet.it'''
    ErrorDialog(message)


def ConnectionError():
    """
    Errore in caso di connessione fallita
    """
    message = '''Connessione fallita.
Controllare di avere accesso alla rete.'''
    ErrorDialog(message)


def GenericError():
    """
    Errore in caso di tentativo di download non andato a buon fine
    """
    message = '''Si è verificato un errore. Controllare:

- di avere accesso alla rete,
- di aver digitato correttamente le credenziali di accesso,
- di avere una licenza attiva,
- di non aver ottenuto un certificato con Ne.Me.Sys. meno di 45 giorni antecedenti ad oggi.

Dopo 5 tentativi di accesso falliti, sarà necessario disinstallare Ne.Me.Sys e reinstallarlo nuovamente.'''
    ErrorDialog(message)


def MaxError():
    """
    Errore in caso di quinto inserimento errato di credenziali
    """
    message = '''Le credenziali non sono corrette o la licenza non è più valida.
Procedere con la disinstallazione e reinstallare nuovamente Ne.Me.Sys. \
dopo aver controllato user-id e password che ti sono state invitate in fase \
di registrazione o a richiedere una nuova licenza dalla tua area privata sul sito misurainternet.it.'''
    ErrorDialog(message)


def CancelError():
    """
    Utente e' uscito
    """
    message = '''L'autenticazione non e' andata a buon fine.
Procedere con la disinstallazione e reinstallare nuovamente Ne.Me.Sys. \
dopo aver controllato user-id e password che ti sono state invitate in fase \
di registrazione o a richiedere una nuova licenza dalla tua area privata sul sito misurainternet.it.'''
    ErrorDialog(message)
    sys.exit()


def ErrorDialog(message):
    root = Tkinter.Tk()
    if utils.is_windows():
        root.wm_iconbitmap('Nemesys.ico')
    root.withdraw()
    title = 'Errore'
    tkMessageBox.showerror(title, message, parent=root)
    root.destroy()


def OkDialog():
    root = Tkinter.Tk()
    if utils.is_windows():
        root.wm_iconbitmap('Nemesys.ico')
    root.withdraw()
    title = 'Ne.Me.Sys autenticazione corretta'
    message = 'Username e password corrette e verificate'
    tkMessageBox.showinfo(title, message, parent=root)
    root.destroy()


### Function to Download Configuration File ###
def getActivationFile(appresult, path, config_path):
    """
      Scarica il file di configurazione. Ritorna True se tutto è andato bene
    """
    logger.info('getActivationFile function')
    ac = appresult
    logger.info('Codici ricevuti: %s' % ac)

    try:
        download = getconf(ac, path, _clientConfigurationFile, _configurationServer)
        logger.info('download = %s' % str(download))
    except IOError as e:
        logger.error('Cannot write to the configuration file: %s' % str(e))
        raise
    except Exception as e:
        logger.error('Cannot download the configuration file: %s' % str(e))
        raise LoginConnectionException(str(e))
    if download is not True:
        logger.info('Received error from server, wrong credentials or license not active')
        raise LoginAuthenticationException("")
    else:
        logger.info('Configuration file successfully downloaded')
        # myProp.writeProps(config_path, '\nregistered', 'ok')
        OkDialog()
        # return True


class LoginGui(Tkinter.Frame):
    """
    finestra di codice licenza
    """

    def sendMsg(self):
        inserted_username = self.username.get()
        inserted_password = self.password.get()
        if (inserted_username and inserted_password):
            self.result = "%s|%s" % (self.username.get(), hashlib.sha1(self.password.get()).hexdigest())
        self.quit()

    def cancel(self):
        self.result = 'Cancel'
        self.quit()

    def createWidgets(self):
        self.Title = Tkinter.Label(self, padx=60, pady=8)
        self.Title["text"] = '''Inserisci i codici di accesso (username e password)
        che hai usato per accedere all'area personale'''
        self.Title.grid(column=0, row=0, columnspan=2)

        username_label = Tkinter.Label(self, text="username:")
        username_label.grid(column=0, row=1)

        self.username = Tkinter.Entry(self, width=30)
        self.username.grid(column=1, row=1)

        password_label = Tkinter.Label(self, text="password:")
        password_label.grid(column=0, row=2)

        self.password = Tkinter.Entry(self, width=30)
        self.password["show"] = "*"
        self.password.grid(column=1, row=2)

        self.button_frame = Tkinter.Frame(self)
        self.button_frame.grid(column=1, row=3, columnspan=2, pady=8)

        self.invio = Tkinter.Button(self.button_frame)
        self.invio["text"] = "Accedi",
        self.invio["command"] = self.sendMsg
        self.invio.grid(column=0, row=0, padx=4)

        self.cancl = Tkinter.Button(self.button_frame)
        self.cancl["text"] = "Cancel",
        self.cancl["command"] = self.cancel
        self.cancl.grid(column=1, row=0, padx=4)

    def __init__(self, master=None):
        Tkinter.Frame.__init__(self, master)
        self.config(width="800")
        if utils.is_windows():
            self.master.wm_iconbitmap('Nemesys.ico')
        self.pack()
        self.createWidgets()
        self.result = None


def try_to_activate(config_path):
    activated = False
    j = 0
    # Al massimo faccio fare 5 tentativi di inserimento codice di licenza
    while not activated:
        # Prendo un codice licenza valido sintatticamente
        errorfunc = None
        try:
            appresult = getCode()
            activated = getActivationFile(appresult, paths._CONF_DIR, config_path)
            return appresult
        except LoginAuthenticationException:
            logger.warning("Authentication failure n. %d" % j)
            errorfunc = CodeError
        except LoginConnectionException as e:
            logger.warning("Authentication connection problem: %s", e)
            errorfunc = ConnectionError
        except LoginCancelledException:
            raise
        except Exception as e:
            logger.error("Caught exception while downloading configuration file: %s", e)
            errorfunc = GenericError
        if j < 4:
            errorfunc()
            j += 1
        else:
            raise MaxLoginException()
    return activated


def main():
    ###  DISCOVERING PATH  ###
    try:
        _PATH = os.path.dirname(sys.argv[0])
        if _PATH == '':
            _PATH = "." + os.sep
        if _PATH[len(_PATH) - 1] != os.sep:
            _PATH = _PATH + os.sep
    except Exception as e:
        _PATH = "." + os.sep

    ###  READING PROPERTIES  ###
    config_dir = os.path.join(_PATH, 'cfg')
    if not os.path.exists(config_dir):
        os.mkdir(config_dir)
    config_file = os.path.join(config_dir, 'cfg.properties')
    if os.path.exists(config_file):
        try:
            _prop = read_properties(config_file)
        except Exception as e:
            logger.error("Could not read configuration file from %s" % config_file, e)
            ErrorDialog("File di configurazione non trovata in {}, impossibile procedere con l'installazione".format(
                config_file))
            sys.exit(1)
    else:
        _prop = []

    if 'registered' in _prop:
        # Ho tentato almeno una volta il download
        logger.debug('Registered in _prop')
        status = str(_prop['registered'])
        if status == 'ok':
            # Allora posso continuare lo start del servizio
            logger.debug('Status of registered is Ok')
            logger.info('Configuration file already downloaded')
        else:
            # Il servizio non può partire
            logger.error('Login previously failed. ')
            # Dialog to unistall and retry
            MaxError()
    else:
        try:
            code = try_to_activate(config_file)
            logger.info('License file successfully downloaded')
        except LoginCancelledException:
            CancelError()
            sys.exit(0)
        except MaxLoginException:
            MaxError()
            logger.warning('MaxError occurred at attempt number 5')
            write_properties(config_file, {'registered': 'nok'})
            sys.exit(1)
        write_properties(config_file, {'code': code, 'registered': 'ok'})


if __name__ == '__main__':
    log_conf.init_log()
    main()
