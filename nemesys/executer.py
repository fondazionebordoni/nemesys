# executer.py
# -*- coding: utf-8 -*-

# Copyright (c) 2011-2016 Fondazione Ugo Bordoni.
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

from datetime import datetime
import glob
import logging
import os
from profile import Profile
from random import randint
import re
import shutil
from time import sleep
from urlparse import urlparse

from _generated_version import __version__, FULL_VERSION
from client import Client
from deliverer import Deliverer
import errorcode
import httputils
from isp import Isp
from measure import Measure
import iptools
import nem_options
import communicator
import paths
from progress import Progress
import status
import sysmonitor
from tester import Tester
from timeNtp import timestampNtp
import xmlutils


logger = logging.getLogger(__name__)

CHECK_ALL = 'CHECKALL'
CHECK_MEDIUM = 'CHECKMEDIUM'

# Non eseguire i test del profiler
BYPASS_PROFILER = False
# Numero massimo di misure per ora
MAX_MEASURES_PER_HOUR = 4
# Soglia per il rapporto tra traffico 'spurio' e traffico totale
TH_TRAFFIC = 0.1
# Tempo di attesa tra una misura e la successiva in caso di misura fallita
TIME_LAG = 5
# Enumeration
DOWN = 'down'
UP = 'up'
# Put 1 to enable arping
ARPING = 1


class Executer(object):

    def __init__(self, client, scheduler, repository, progressurl, polling = 300.0, tasktimeout = 60,
                             testtimeout = 30, httptimeout = 60, local = False, isprobe = True, md5conf = None, killonerror = True):

        self._client = client
        self._scheduler = scheduler
        self._repository = repository
        self._polling = polling
        self._tasktimeout = tasktimeout
        self._testtimeout = testtimeout
        self._httptimeout = httptimeout
        self._local = local
        self._isprobe = isprobe
        self._md5conf = md5conf
        self._killonerror = killonerror
        self._progressurl = progressurl

        self._outbox = paths.OUTBOX
        self._sent = paths.SENT
        self._communicator = None
        self._progress = None
        self._deliverer = Deliverer(self._repository, self._client.isp.certificate, self._httptimeout)

        if self._isprobe:
            logger.info('Inizializzato software per sonda.')
        else:
            logger.info('Inizializzato software per misure d\'utente con ISP id = %s' % client.isp.id)

    def test(self, taskfilename = None):

        task = None

        if (taskfilename == None):
            # Test di download di un file di scheduling
            task = self._download_task()
            logger.debug('Test scaricamento task:\n\t%s' % task)
        else:
            with open(taskfilename, 'r') as taskfile:
                task = xmlutils.xml2task(taskfile.read())

        if (task != None):
            logger.debug('Test esecuzione task:')
            self._dotask(task)
        else:
            logger.info('Nessun task da eseguire.')

    def wait(self):

        # Se non è una sonda, ma un client d'utente
        if not self._isprobe:
            # Se ho fatto MAX_MEASURES_PER_HOUR misure in questa ora, aspetto la prossima ora
            now = datetime.fromtimestamp(timestampNtp())
            hour = now.hour
            made = self._progress.howmany(hour)
            if made >= MAX_MEASURES_PER_HOUR:

                # Quanti secondi perché scatti la prossima ora?
                wait_hour = self._polling
                try:
                    delta_hour = now.replace(hour = (hour + 1) % 24, minute = 0, second = 0) - now
                    if delta_hour.days < 0:
                        logger.info('Nuovo giorno: delta_hour %s' % delta_hour)
                    # Aggiungo un random di 5 minuti per evitare chiamate sincrone
                    wait_hour = delta_hour.seconds
                except ValueError as e:
                    logger.warning('Errore nella determinazione della prossima ora: %s.' % e)

                random_sleep = randint(2, self._polling * 15 / MAX_MEASURES_PER_HOUR)
                logger.info('La misura delle %d è completa. Aspetto %d minuti per il prossimo polling.' % (hour, (wait_hour + random_sleep)/60))

                # Aspetto un'ora poi aggiorno lo stato
                sleep(wait_hour)
                self._updatestatus(status.READY)

                # Aspetto un altro po' per evitare di chiedere di fare le misure contemporaneamente agli altri
                sleep(random_sleep)
            elif made >= 1:
                wait_next = max(self._polling * 3, 180)
                # Ritardo la richiesta per le successive: dovrebbe essere maggiore del tempo per effettuare una misura, altrimenti eseguo MAX_MEASURES_PER_HOUR + 1
                logger.info('Ho fatto almento una misura. Aspetto %d minuti per il prossimo polling.' % (wait_next/60))
                sleep(wait_next)
            else:
                # Aspetto prima di richiedere il task
                sleep(self._polling)
        else:
            # Aspetto prima di richiedere il task
            sleep(self._polling)

    def _hourisdone(self):
        now = datetime.fromtimestamp(timestampNtp())
        hour = now.hour
        made = self._progress.howmany(hour)
        if made >= MAX_MEASURES_PER_HOUR:
            return True
        else:
            return False

    def loop(self):

#         t = None

        # Open socket for GUI dialog
        if not self._isprobe:
            self._communicator = communicator.Communicator()
            self._communicator.start()

        # Prepare Progress file
        self._progress = Progress(clientid=self._client.id, progressurl=self._progressurl)

        # Controllo se 
        # - non sono trascorsi 3 giorni dall'inizio delle misure
        # - non ho finito le misure
        # - sono una sonda
        task = None
        while self._isprobe or (not self._progress.doneall() and not self._progress.expired()): #TODO: check for pre-release of certificate

            if self._isprobe or (not self._hourisdone()):

                self._updatestatus(status.READY)
                if self._isprobe:
                    self._uploadall()
                try:
                    new_task = self._download_task()
                    task = new_task
                except Exception as e:
                    logger.error('Errore durante la ricezione del task per le misure: %s' % e)
                    self._updatestatus(status.Status(status.ERROR, 'Errore durante la ricezione del task per le misure: %s' % e))

                # Se ho scaricato un task imposto l'allarme
                if (task != None):
                    logger.debug('Trovato task %s' % task)

                    if (task.message != None and len(task.message) > 0):
                        logger.debug("Trovato messaggio: %s" % task.message)
                        self._updatestatus(status.Status(status.MESSAGE, task.message))

                    if (task.now):
                        # Task immediato
                        alarm = 5.00
                    else:
                        delta = task.start - datetime.fromtimestamp(timestampNtp())
                        alarm = delta.days * 86400 + delta.seconds

                    if alarm > self._polling + 30:
                        # More than self._polling plus 30 seconds to next task, go to sleep
                        logger.debug('Prossimo task tra: %s minuti, faccio una pausa per %s minuti' % (alarm/60, self._polling/60))
                    elif alarm > 0 and (task.download > 0 or task.upload > 0 or task.ping > 0):
                        logger.debug('Impostazione di un nuovo task tra: %s minuti' % (alarm/60))
                        self._updatestatus(status.Status(status.READY, 'Inizio misura tra pochi secondi...'))
                        # Aspettare alarm secondi, e poi esseguire il task
                        sleep(alarm)
                        self._dotask(task)
                    else:
                        logger.warn('Alarm anomalo: %s minuti' % (alarm/60))
            else:
                self._updatestatus(status.PAUSE)
            # Attendi il prossimo polling
            self.wait()

        while True:
            self._updatestatus(status.FINISHED)
            sleep(float(self._polling * 3))

    def _download_task(self):
        '''
        Download task from scheduler
        '''
        url = urlparse(self._scheduler)
        certificate = self._client.isp.certificate
        connection = httputils.getverifiedconnection(url = url, certificate = certificate, timeout = self._httptimeout)

        try:
            connection.request('GET', '%s?clientid=%s&version=%s&confid=%s' % (url.path, self._client.id, __version__, self._md5conf))
            data = connection.getresponse().read()
        except Exception as e:
            logger.error('Impossibile scaricare lo scheduling. Errore: %s.' % e)
            self._updatestatus(status.Status(status.ERROR, 'Impossibile dialogare con lo scheduler delle misure.'))
            return None

        return xmlutils.xml2task(data)

    def _test_gating(self, test, testtype):
        '''
        Check that spurious traffic is not too high
        '''
        logger.debug('Percentuale di traffico spurio: %.2f%%' % (test.spurious * 100))
        if not self._isprobe:
            if test.spurious < 0:
                raise Exception('Errore durante la verifica del traffico di misura: impossibile salvare i dati.')
            if test.spurious >= TH_TRAFFIC:
                raise Exception('Eccessiva presenza di traffico internet non legato alla misura: percentuali %d%%.' % (round(test.spurious * 100)))


    def _profile_system(self, checktype = CHECK_ALL):
        '''
        Profile system and return an exception or an errorcode whether the system is not suitable for measuring. 
        '''
        error = 0
        if not (self._isprobe or BYPASS_PROFILER):

            try:
                if (checktype == CHECK_ALL):
                    sysmonitor.checkall(self._client.profile.upload, self._client.profile.download, self._client.isp.id, ARPING)
                elif (checktype == CHECK_MEDIUM):
                    sysmonitor.mediumcheck()
                else:
                    logger.warning("Unknown check type: %s" % str(checktype))
                    sysmonitor.mediumcheck()

            except Exception as e:
                logger.error('Errore durante la verifica dello stato del sistema: %s' % e)

                if self._killonerror:
                    raise e
                else:
                    self._updatestatus(status.Status(status.ERROR, 'Misura in esecuzione ma non corretta. %s Proseguo a misurare.' % e))
                    error = errorcode.from_exception(e)
        return error

    def _dotask(self, task):
        '''
        Esegue il complesso di test prescritti dal task entro il tempo messo a
        disposizione secondo il parametro tasktimeout (non implementato)
        '''
        if not self._isprobe and self._progress != None:
            made = self._progress.howmany(datetime.fromtimestamp(timestampNtp()).hour)
            if made >= MAX_MEASURES_PER_HOUR:
                logger.debug('Gia eseguiti %d misure in questa ora' % MAX_MEASURES_PER_HOUR)
                self._updatestatus(status.PAUSE)
                return

        logger.info('Inizio task di misura verso il server %s' % task.server)

        # TODO: Inserire il timeout complessivo di task (da posticipare)
        try:

            self._updatestatus(status.PLAY)

            # Profilazione iniziale del sistema
            # ------------------------
            base_error = 0
            if self._profile_system() != 0:
                base_error = 50000

            dev = iptools.get_dev(task.server.ip, 80)
            t = Tester(dev = dev, host = task.server, timeout = self._testtimeout,
                                 username = self._client.username, password = self._client.password)

            # TODO: Pensare ad un'altra soluzione per la generazione del progressivo di misura
            start = datetime.fromtimestamp(timestampNtp())
            m_id = start.strftime('%y%m%d%H%M')
            m = Measure(m_id, task.server, self._client, __version__, start.isoformat())

            # Set task timeout alarm
            # signal.alarm(self._tasktimeout)

            # Testa i ping
            i = 1
            while (i <= task.ping):
                self._updatestatus(status.Status(status.PLAY, "Esecuzione Test %d su %d" % (i + task.download + task.upload, task.download + task.upload + task.ping)))
                try:
                    error = self._profile_system(CHECK_MEDIUM);
                    logger.debug('Starting ping test [%d]' % i)
                    test = t.testping()
                    if error > 0 or base_error > 0:
                        test.seterrorcode(error + base_error)
                    logger.debug('Ping result: %.3f' % test.duration)
                    logger.debug('Ping error: %d, %d, %d' % (base_error, error, test.errorcode))
                    m.savetest(test)
                    i = i + 1
                    if ((i - 1) % task.nicmp == 0):
                        sleep(task.delay)
                except Exception as e:
                    if not datetime.fromtimestamp(timestampNtp()).hour == start.hour:
                        raise e
                    else:
                        logger.warning('Misura sospesa per eccezione %s' % e, exc_info=True)
                        self._updatestatus(status.Status(status.ERROR, 'Misura sospesa per errore: %s Aspetto 10 secondi prima di proseguire la misura.' % e))
                        sleep(10)
                        logger.info('Misura in ripresa dopo sospensione. Test ping %d di %d' % (i, task.ping))
                        self._updatestatus(status.Status(status.PLAY, 'Proseguo la misura. Misura in esecuzione'))

            # Testa gli http down
            # ------------------------
            i = 1;
            while (i <= task.download):
                self._updatestatus(status.Status(status.PLAY, "Esecuzione Test %d su %d" % (i, task.download + task.upload + task.ping)))
                try:
                    # Profilazione del sistema
                    error = self._profile_system(CHECK_ALL);
                    logger.info('Starting http download test [%d]' % i)
                    test = t.testhttpdown(callback_update_speed=None)
                    if error > 0 or base_error > 0:
                        test.seterrorcode(error + base_error)
                    self._test_gating(test, DOWN)
                    logger.debug('Download result: %.3f' % test.duration)
                    logger.debug('Download error: %d, %d, %d' % (base_error, error, test.errorcode))
                    m.savetest(test)
                    i = i + 1
                    sleep(1)
                except Exception as e:
                    if not datetime.fromtimestamp(timestampNtp()).hour == start.hour:
                        raise e
                    else:
                        logger.warning('Misura sospesa per eccezione %s' % e)
                        self._updatestatus(status.Status(status.ERROR, 'Misura sospesa per errore: %s Aspetto %d minuti prima di proseguire la misura.' % (e, TIME_LAG/60)))
                        sleep(TIME_LAG)
                        logger.info('Misura in ripresa dopo sospensione. Test download %d di %d' % (i, task.download))
                        self._updatestatus(status.Status(status.PLAY, 'Proseguo la misura. Misura in esecuzione'))

            # Testa gli http up
            i = 1;
            while (i <= task.upload):
                self._updatestatus(status.Status(status.PLAY, "Esecuzione Test %d su %d" % (i + task.download, task.download + task.upload + task.ping)))
                try:
                    error = self._profile_system(CHECK_ALL);
                    logger.debug('Starting http upload test [%d]' % i)
                    test = t.testhttpup(callback_update_speed=None, bw=self._client.profile.upload)
                    if error > 0 or base_error > 0:
                        test.seterrorcode(error + base_error)
                    self._test_gating(test, UP)
                    logger.debug('Upload result: %.3f' % (test.bytes_tot/test.duration/1000.0))
                    logger.debug('Upload error: %d, %d, %d' % (base_error, error, test.errorcode))
                    m.savetest(test)
                    i = i + 1
                    sleep(1)
                except Exception as e:
                    if not datetime.fromtimestamp(timestampNtp()).hour == start.hour:
                        raise e
                    else:
                        logger.warning('Misura sospesa per eccezione %s' % e, exc_info=True)
                        self._updatestatus(status.Status(status.ERROR, 'Misura sospesa per errore: %s Aspetto %d minuti prima di proseguire la misura.' % (e, TIME_LAG/60)))
                        sleep(TIME_LAG)
                        logger.info('Misura in ripresa dopo sospensione. Test upload %d di %d' % (i, task.upload))
                        self._updatestatus(status.Status(status.PLAY, 'Proseguo la misura. Misura in esecuzione'))

            # Unset task timeout alarm
            # signal.alarm(0)

            sec = datetime.fromtimestamp(timestampNtp()).strftime('%S')
            f = open('%s/measure_%s%s.xml' % (self._outbox, m.id, sec), 'w')
            f.write(str(m))
            f.write('\n<!-- [finished] %s -->' % datetime.fromtimestamp(timestampNtp()).isoformat())
            f.close()

            if (not self._local):
                upload = self._upload(f.name)
                if upload:
                    self._updatestatus(status.Status(status.OK, 'Misura terminata con successo.'))
                else:
                    self._updatestatus(status.Status(status.ERROR, 'Misura terminata ma un errore si è verificato durante il suo invio.'))
            else:
                self._updatestatus(status.Status(status.OK, 'Misura terminata.'))

            logger.info('Fine task di misura.')

        except RuntimeWarning:
            self._updatestatus(status.Status(status.ERROR, 'Misura interrotta per timeout.'))
            logger.warning('Timeout during task execution. Time elapsed > %1f seconds ' % self._tasktimeout)

        except Exception as e:
            logger.error('Task interrotto per eccezione durante l\'esecuzione di un test: %s' % e)
            self._updatestatus(status.Status(status.ERROR, 'Misura interrotta. %s Attendo %d minuti' % (e, self._polling/60)))


    def _uploadall(self):
        '''
        Cerca di spedire tutti i file di misura che trova nella cartella d'uscita
        '''
        for filename in glob.glob(os.path.join(self._outbox, 'measure_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].xml')):
            #logger.debug('Trovato il file %s da spedire' % filename)
            self._upload(filename)

    def _upload(self, filename):
        '''
        Spedisce il filename di misura al repository entro il tempo messo a
        disposizione secondo il parametro httptimeout
        '''
        response = None
        result = False

        try:
            # Crea il Deliverer che si occuperà della spedizione
            #logger.debug('Invio il file %s a %s' % (filename, self._repository))
            zipname = self._deliverer.pack(filename)
            response = self._deliverer.upload(zipname)

            if (response != None):
                (code, message) = self._parserepositorydata(response)
                code = int(code)
                logger.info('Risposta dal server di upload: [%d] %s' % (code, message))

                # Se tutto è andato bene sposto il file zip nella cartella "sent" e rimuovo l'xml
                if (code == 0):
                    time = xmlutils.getstarttime(filename)
                    os.remove(filename)
                    self._movefiles(zipname)
                    self._progress.putstamp(time)

                    result = True

        except Exception as e:
            logger.error('Errore durante la spedizione del file delle misure %s: %s' % (filename, e))

        finally:
            # Elimino lo zip del file di misura temporaneo
            if os.path.exists(zipname):
                os.remove(zipname)
            # Se non sono una sonda _devo_ cancellare il file di misura 
            if not self._isprobe and os.path.exists(filename):
                os.remove(filename)

            return result

    def _updatestatus(self, current_status):

        logger.debug('Aggiornamento stato: %s' % current_status.message)

        if (self._communicator != None):
            self._communicator.sendstatus(current_status)

    def _movefiles(self, filename):

        directory = os.path.dirname(filename)
        #pattern = path.basename(filename)[0:-4]
        pattern = os.path.basename(filename)

        try:
            for f in os.listdir(directory):
                # Cercare tutti i file che iniziano per pattern
                if (re.search(pattern, f) != None):
                    # Spostarli tutti in self._sent
                    old = ('%s/%s' % (directory, f))
                    new = ('%s/%s' % (self._sent, f))
                    shutil.move(old, new)

        except Exception as e:
            logger.error('Errore durante lo spostamento dei file di misura %s' % e)

    def _parserepositorydata(self, data):
        '''
        Valuta l'XML ricevuto dal repository, restituisce il codice e il messaggio ricevuto
        '''

        xml = xmlutils.getxml(data)
        if (xml == None):
            logger.error('Nessuna risposta ricevuta')
            return None

        nodes = xml.getElementsByTagName('response')
        if (len(nodes) < 1):
            logger.error('Nessuna risposta ricevuta nell\'XML:\n%s' % xml.toxml())
            return None

        node = nodes[0]

        code = xmlutils.getvalues(node, 'code')
        message = xmlutils.getvalues(node, 'message')
        return (code, message)

def main():
    logger.info('Starting Nemesys v.%s' % FULL_VERSION)
    paths.check_paths()
    (options, _, md5conf) = nem_options.parse_args(__version__)

    client = getclient(options)
    isprobe = (client.isp.certificate != None)
    e = Executer(client = client, scheduler = options.scheduler,
                             repository = options.repository, progressurl = options.progressurl, polling = options.polling,
                             tasktimeout = options.tasktimeout, testtimeout = options.testtimeout,
                             httptimeout = options.httptimeout, local = options.local,
                             isprobe = isprobe, md5conf = md5conf, killonerror = options.killonerror)
    #logger.debug("%s, %s, %s" % (client, client.isp, client.profile))

    if (options.test):
        # Se è presente il flag T segui il test ed esci
        e.test(options.task)
    else:
        # Altrimenti viene eseguito come processo residente: entra nel loop infinito
        logger.debug('Inizio il loop.')
        e.loop()

def getclient(options):

    profile = Profile(profile_id = options.profileid, upload = options.bandwidthup,
                                        download = options.bandwidthdown)
    isp = Isp(isp_id = options.ispid, certificate = options.certificate)
    return Client(client_id = options.clientid, profile = profile, isp = isp,
                                geocode = options.geocode, username = options.username,
                                password = options.password)


if __name__ == '__main__':
    import log_conf
    log_conf.init_log()
    main()
