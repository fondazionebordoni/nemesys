# executer.py
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

from ConfigParser import ConfigParser, NoOptionError
from client import Client
from datetime import datetime
from deliverer import Deliverer
from errorcoder import Errorcoder
from isp import Isp
from logger import logging
from measure import Measure
from optparse import OptionParser
from os import path
from profile import Profile
from progress import Progress
from random import randint
from status import Status
from sysmonitorexception import SysmonitorException
from tester import Tester
from threading import Semaphore, Thread, Timer
from time import sleep
from timeNtp import timestampNtp
from urlparse import urlparse
from xmlutils import getvalues, getstarttime, getxml, xml2task
import asyncore
import glob
import hashlib
import httputils
import os
import paths
import re
import shutil
import socket
import status
import sysmonitor
import sysmonitorexception

bandwidth_sem = Semaphore()
status_sem = Semaphore()
logger = logging.getLogger()
errors = Errorcoder(paths.CONF_ERRORS)
current_status = status.LOGO
__version__ = '2.1.5'

# Non eseguire i test del profiler
BYPASS_PROFILER = False
# Numero massimo di misure per ora
MAX_MEASURES_PER_HOUR = 1
# Soglia per il rapporto tra traffico 'spurio' e traffico totale
TH_TRAFFIC = 0.1
TH_TRAFFIC_INV = 0.9
# Soglia per numero di pacchetti persi
TH_PACKETDROP = 0.01
# Tempo di attesa tra una misura e la successiva in caso di misura fallita
TIME_LAG = 5
# Enumeration
DOWN = 'down'
UP = 'up'
# Put 1 to enable arping
ARPING = 1


class _Communicator(Thread):

  def __init__(self):
    Thread.__init__(self)
    self._channel = _Channel(('127.0.0.1', 21401))

  def sendstatus(self):
    self._channel.sendstatus()

  def run(self):
    asyncore.loop(5)
    logger.debug('Nemesys asyncore loop terminated.')

  def join(self, timeout = None):
    self._channel.quit()
    Thread.join(self, timeout)


class _Channel(asyncore.dispatcher):

  def __init__(self, url):
    asyncore.dispatcher.__init__(self)
    self._url = url
    self._sender = None
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.set_reuse_addr()
    self.bind(self._url)
    self.listen(1)

  def sendstatus(self, status = None):
    if self._sender:
      self._sender.write(current_status)
    else:
      pass

  def handle_accept(self):
    (channel, addr) = self.accept()
    self._sender = _Sender(channel)
    self.sendstatus()

  def quit(self):
    if (self._sender != None):
      self._sender.close()
    self.close()


class _Sender(asyncore.dispatcher):

  def readable(self):
    return False # don't have anything to read

  def writable(self):
    #return len(self.buffer) > 0
    return False

  def write(self, status):
    try:
      self.buffer = status.getxml()
    except Exception as e:
      logger.warning('Errore durante invio del messaggio di stato: %s' % e)
      status = Status(status.ERROR, 'Errore di decodifica unicode')
      self.buffer = status.getxml()

    try:
      self.handle_write()
    except Exception as e:
      logger.warning('Impossibile inviare il messaggio di notifica, errore: %s' % e)
      self.close()

  def handle_read(self):
    data = self.recv(2048)
    logger.debug('Received: %s' % data)

  def handle_write(self):
    logger.debug('Sending status "%s"' % self.buffer)
    sent = self.send(self.buffer)
    self.buffer = self.buffer[sent:]

  def handle_close(self):
    self.close()

  def handle_error(self):
    self.handle_close()


class OptionParser(OptionParser):

  def check_required(self, opt):
    option = self.get_option(opt)
    if getattr(self.values, option.dest) is None:
      self.error('%s option not supplied' % option)


class Executer:

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
    current_status = status.LOGO
    self._communicator = None
    self._progress = None
    self._deliverer = Deliverer(self._repository, self._client.isp.certificate, self._httptimeout)

    if self._isprobe:
      logger.info('Inizializzato software per sonda.')
    else:
      logger.info('Inizializzato software per misure d\'utente')

  def test(self, taskfile = None):

    task = None

    if (taskfile == None):
      # Test di download di un file di scheduling
      task = self._download()
      logger.debug('Test scaricamento task:\n\t%s' % task)
    else:
      with open(taskfile, 'r') as file:
        task = xml2task(file.read())

    if (task != None):
      logger.debug('Test esecuzione task:')
      self._dotask(task)
    else:
      logger.info('Nessun task da eseguire.')

  def wait(self):

    # Se non è una sonda, ma un client d'utente
    if not self._isprobe:
      # Se ho fatto 2 misure in questa ora, aspetto la prossima ora
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
        logger.info('La misura delle %d è completa. Aspetto %d secondi per il prossimo polling.' % (hour, wait_hour + random_sleep))

        # Aspetto un'ora poi aggiorno lo stato
        sleep(wait_hour)
        self._updatestatus(status.READY)

        # Aspetto un altro po' per evitare di chiedere di fare le misure contemporaneamente agli altri
        sleep(random_sleep)
      elif made >= 1:
        wait_next = max(self._polling * 3, 180)
        # Ritardo la richiesta per le successive: dovrebbe essere maggiore del tempo per effettuare una misura, altrimenti eseguo MAX_MEASURES_PER_HOUR + 1
        logger.info('Ho fatto almento una misura. Aspetto %d secondi per il prossimo polling.' % wait_next)
        sleep(wait_next)
      else:
        # Aspetto prima di richiedere il task
        sleep(self._polling)
    else:
      # Aspetto prima di richiedere il task
      sleep(self._polling)

  def _hourisdone(self):
    if not self._isprobe:
      now = datetime.fromtimestamp(timestampNtp())
      hour = now.hour
      made = self._progress.howmany(hour)
      if made >= MAX_MEASURES_PER_HOUR:
        return True
      else:
        return False
    else:
      return False

  def loop(self):

    # signal.signal(signal.SIGALRM, runtimewarning)
    t = None

    # Open socket for GUI dialog
    self._communicator = _Communicator()
    self._communicator.start()

    # Prepare Progress file
    progressurl = self._progressurl
    clientid = self._client.id
    self._progress = Progress(clientid = clientid, progressurl = progressurl)

    # Controllo se 
    # - non sono trascorsi 3 giorni dall'inizio delle misure
    # - non ho finito le misure
    # - sono una sonda
    while self._isprobe or (not self._progress.doneall() and self._progress.onair()):

      bandwidth_sem.acquire() # Richiedi accesso esclusivo alla banda

      if not self._hourisdone():

        self._updatestatus(status.READY)
        task = None

        # Solo se sono una sonda invio i file di misura nella cartella da spedire
        if self._isprobe:
          # Controllo se ho dei file da mandare prima di prendermi il compito di fare altre misure
          self._uploadall()

        try:
          task = self._download()
        except Exception as e:
          logger.error('Errore durante la ricezione del task per le misure: %s' % e)
          self._updatestatus(Status(status.ERROR, 'Errore durante la ricezione del task per le misure: %s' % e))

        # Se ho scaricato un task imposto l'allarme
        if (task != None):
          logger.debug('Trovato task %s' % task)

          if (task.message != None and len(task.message) > 0):
            logger.debug("Trovato messaggio: %s" % task.message)
            self._updatestatus(Status(status.MESSAGE, task.message))

          if (task.now):
            # Task immediato
            alarm = 5.00
          else:
            delta = task.start - datetime.fromtimestamp(timestampNtp())
            alarm = delta.days * 86400 + delta.seconds

          if alarm > 0 and (task.download > 0 or task.upload > 0 or task.ping > 0):
            logger.debug('Impostazione di un nuovo task tra: %s secondi' % alarm)
            self._updatestatus(Status(status.READY, 'Inizio misura tra pochi secondi...'))
            # Imposta l'allarme che eseguirà i test quando richiesto dal task

            # Prima cancella il vecchio allarme
            try:
              if (t != None):
                t.cancel()
            except NameError:
              pass
            except AttributeError:
              pass

            # Imposta il nuovo allarme
            t = Timer(alarm, self._dotask, [task])
            t.start()
      else:
        self._updatestatus(status.PAUSE)

      bandwidth_sem.release() # Rilascia l'accesso esclusivo alla banda

      # Attendi il prossimo polling
      self.wait()

    while True:
      self._updatestatus(status.FINISHED)
      sleep(float(self._polling * 3))

  # Scarica il prossimo task dallo scheduler
  def _download(self):
    #logger.debug('Reading resource %s for client %s' % (self._scheduler, self._client))

    url = urlparse(self._scheduler)
    certificate = self._client.isp.certificate
    connection = httputils.getverifiedconnection(url = url, certificate = certificate, timeout = self._httptimeout)

    try:
      connection.request('GET', '%s?clientid=%s&version=%s&confid=%s' % (url.path, self._client.id, __version__, self._md5conf))
      data = connection.getresponse().read()
    except Exception as e:
      logger.error('Impossibile scaricare lo scheduling. Errore: %s.' % e)
      self._updatestatus(Status(status.ERROR, 'Impossibile dialogare con lo scheduler delle misure.'))
      return None

    return xml2task(data)

  def _evaluate_exception(self, e):
    if isinstance (e, SysmonitorException):
      # Inserire nel test tutte le eccezioni da bypassare
      if e.alert_type == sysmonitorexception.WARNCONN.alert_type or e.alert_type == sysmonitorexception.WARNPROC.alert_type:
        logger.warning('Misura in esecuzione con warning: %s' % e)
      else:
        raise e
    else:
      raise e

  def _test_gating(self, test, testtype):
    '''
    Funzione per l'analisi del contabit ed eventuale gating dei risultati del test
    '''
    stats = test.counter_stats
    logger.debug('Valori di test: %s' % stats)

    logger.debug('Analisi della percentuale dei pacchetti persi')
    packet_drop = stats.packet_drop
    packet_tot = stats.packet_tot_all
    if (packet_tot > 0):
      packet_ratio = float(packet_drop) / float(packet_tot)
      logger.debug('Percentuale di pacchetti persi: %.2f%%' % (packet_ratio * 100))
      if (packet_tot > 0 and packet_ratio > TH_PACKETDROP):
        raise Exception('Eccessiva presenza di traffico di rete, impossibile analizzare i dati di test')
    else:
      raise Exception('Errore durante la misura, impossibile analizzare i dati di test')

#     if (testtype == DOWN):
      byte_nem = stats.payload_nem_net
      byte_all = stats.payload_tot
#       packet_nem_inv = stats.packet_up_nem_net
#       packet_all_inv = packet_nem_inv + stats.packet_up_oth_net
#     else:
#       byte_nem = stats.payload_up_nem_net
#       byte_all = byte_nem + stats.byte_up_oth_net
#       packet_nem_inv = stats.packet_down_nem_net
#       packet_all_inv = packet_nem_inv + stats.packet_down_oth_net

    logger.debug('Analisi dei rapporti di traffico')
#     if byte_all > 0 and packet_all_inv > 0:
    if byte_all > 0:
      traffic_ratio = float(byte_all - byte_nem) / float(byte_all)
#       packet_ratio_inv = float(packet_all_inv - packet_nem_inv) / float(packet_all_inv)
#       logger.info('kbyte_nem: %.1f; kbyte_all %.1f; packet_nem_inv: %d; packet_all_inv: %d' % (byte_nem / 1024.0, byte_all / 1024.0, packet_nem_inv, packet_all_inv))
      logger.info('kbyte_nem: %.1f; kbyte_all %.1f' % (byte_nem / 1024.0, byte_all / 1024.0))
      logger.debug('Percentuale di traffico spurio: %.2f%%/%.2f%%' % (traffic_ratio * 100, packet_ratio_inv * 100))
      if traffic_ratio < 0:
        raise Exception('Errore durante la verifica del traffico di misura: impossibile salvare i dati.')
#       if traffic_ratio < TH_TRAFFIC and packet_ratio_inv < TH_TRAFFIC_INV:
      if traffic_ratio < TH_TRAFFIC:
        # Dato da salvare sulla misura
        test.bytes = byte_all
      else:
        raise Exception('Eccessiva presenza di traffico internet non legato alla misura: percentuali %d%%/%d%%.' % (round(traffic_ratio * 100), round(packet_ratio_inv * 100)))
    else:
      raise Exception('Errore durante la misura, impossibile analizzare i dati di test')

  def _profile_system(self, checktype = sysmonitor.CHECK_ALL):
    '''
    Profile system and return an exception or an errorcode whether the system is not suitable for measuring. 
    '''
    errorcode = 0
    if not (self._isprobe or BYPASS_PROFILER):

      try:
        if (checktype == sysmonitor.CHECK_ALL):
          test = sysmonitor.checkall(self._client.profile.upload, self._client.profile.download, self._client.isp.id, ARPING)
        elif (checktype == sysmonitor.CHECK_MEDIUM):
          test = sysmonitor.mediumcheck()
        else:
          test = sysmonitor.fastcheck()

        if test != True:
          raise Exception('Condizioni per effettuare la misura non verificate.')

      except Exception as e:
        logger.error('Errore durante la verifica dello stato del sistema: %s' % e)

        if self._killonerror:
          self._evaluate_exception(e)
        else:
          self._updatestatus(status.Status(status.ERROR, 'Misura in esecuzione ma non corretta. %s Proseguo a misurare.' % e))
          errorcode = errors.geterrorcode(e)

    return errorcode

  def _dotask(self, task):
    '''
    Esegue il complesso di test prescritti dal task entro il tempo messo a
    disposizione secondo il parametro tasktimeout
    '''
    # TODO Mischiare i test: down, up, ping, down, up, ping, ecc...

    if not self._isprobe and self._progress != None:
      made = self._progress.howmany(datetime.fromtimestamp(timestampNtp()).hour)
      if made >= MAX_MEASURES_PER_HOUR:
        self._updatestatus(status.PAUSE)
        return

    bandwidth_sem.acquire()  # Acquisisci la risorsa condivisa: la banda

    logger.info('Inizio task di misura verso il server %s' % task.server)

    # Area riservata per l'esecuzione della misura
    # --------------------------------------------------------------------------

    # TODO Inserire il timeout complessivo di task (da posticipare)
    try:

      self._updatestatus(status.PLAY)

      # Profilazione iniziale del sistema
      # ------------------------
      base_error = 0
      if self._profile_system() != 0:
        base_error = 50000

#       ip = sysmonitor.getIp(task.server.ip, 21)
      dev = sysmonitor.getDev(task.server.ip, 21)
      t = Tester(if_ip = ip, host = task.server, timeout = self._testtimeout,
                 username = self._client.username, password = self._client.password)

      # TODO Pensare ad un'altra soluzione per la generazione del progressivo di misura
      start = datetime.fromtimestamp(timestampNtp())
      id = start.strftime('%y%m%d%H%M')
      m = Measure(id, task.server, self._client, __version__, start.isoformat())

      # Set task timeout alarm
      # signal.alarm(self._tasktimeout)

      # Testa gli ftp down
      # ------------------------
      i = 1;
      while (i <= task.download):
        self._updatestatus(status.Status(status.PLAY, "Esecuzione Test %d su %d" % (i, task.download + task.upload + task.ping)))
        try:
          # Profilazione del sistema
          error = self._profile_system(sysmonitor.CHECK_ALL);

          # Esecuzione del test
          logger.info('Starting ftp download test (%s) [%d]' % (task.ftpdownpath, i))
          test = t.testftpdown(task.ftpdownpath)

          # Gestione degli errori nel test
          if error > 0 or base_error > 0:
            test.seterrorcode(error + base_error)

          # Analisi da contabit
          self._test_gating(test, DOWN)

          # Salvataggio della misura
          logger.debug('Download result: %.3f' % test.value)
          logger.debug('Download error: %d, %d, %d' % (base_error, error, test.errorcode))
          m.savetest(test)
          i = i + 1

          # Prequalifica della linea
          if (test.value > 0):
            bandwidth = int(round(test.bytes * 8 / test.value))
            logger.debug('Banda ipotizzata in download: %d' % bandwidth)
            task.update_ftpdownpath(bandwidth)

          sleep(1)

        # Cattura delle eccezioni durante la misura
        except Exception as e:
          if not datetime.fromtimestamp(timestampNtp()).hour == start.hour:
            raise e
          else:
            logger.warning('Misura sospesa per eccezione %s' % e)
            self._updatestatus(status.Status(status.ERROR, 'Misura sospesa per errore: %s Aspetto %d secondi prima di proseguire la misura.' % (e, TIME_LAG)))
            sleep(TIME_LAG)
            logger.info('Misura in ripresa dopo sospensione. Test download %d di %d' % (i, task.download))
            self._updatestatus(status.Status(status.PLAY, 'Proseguo la misura. Misura in esecuzione'))

      # Testa gli ftp up
      i = 1;
      while (i <= task.upload):
        self._updatestatus(status.Status(status.PLAY, "Esecuzione Test %d su %d" % (i + task.download, task.download + task.upload + task.ping)))
        try:
          # Profilazione del sistema
          error = self._profile_system(sysmonitor.CHECK_ALL);

          # Esecuzione del test
          logger.debug('Starting ftp upload test (%s) [%d]' % (task.ftpuppath, i))
          test = t.testftpup(self._client.profile.upload * task.multiplier * 1000 / 8, task.ftpuppath)

          # Gestione degli errori nel test
          if error > 0 or base_error > 0:
            test.seterrorcode(error + base_error)

          # Analisi da contabit
          self._test_gating(test, UP)

          # Salvataggio del test nella misura
          logger.debug('Upload result: %.3f' % test.value)
          logger.debug('Upload error: %d, %d, %d' % (base_error, error, test.errorcode))
          m.savetest(test)
          i = i + 1

          # Prequalifica della linea
          if (test.value > 0):
            bandwidth = int(round(test.bytes * 8 / test.value))
            logger.debug('Banda ipotizzata in upload: %d' % bandwidth)
            self._client.profile.upload = bandwidth

          sleep(1)

        # Cattura delle eccezioni durante la misura
        except Exception as e:
          if not datetime.fromtimestamp(timestampNtp()).hour == start.hour:
            raise e
          else:
            logger.warning('Misura sospesa per eccezione %s' % e)
            self._updatestatus(status.Status(status.ERROR, 'Misura sospesa per errore: %s Aspetto %d secondi prima di proseguire la misura.' % (e, TIME_LAG)))
            sleep(TIME_LAG)
            logger.info('Misura in ripresa dopo sospensione. Test upload %d di %d' % (i, task.upload))
            self._updatestatus(status.Status(status.PLAY, 'Proseguo la misura. Misura in esecuzione'))

      # Testa i ping
      i = 1
      while (i <= task.ping):
        self._updatestatus(status.Status(status.PLAY, "Esecuzione Test %d su %d" % (i + task.download + task.upload, task.download + task.upload + task.ping)))
        try:
          # Profilazione del sistema
          error = self._profile_system(sysmonitor.CHECK_MEDIUM);

          # Esecuzione del test
          logger.debug('Starting ping test [%d]' % i)
          test = t.testping()

          # Gestione degli errori nel test
          if error > 0 or base_error > 0:
            test.seterrorcode(error + base_error)

          # Salvataggio del test nella misura
          logger.debug('Ping result: %.3f' % test.value)
          logger.debug('Ping error: %d, %d, %d' % (base_error, error, test.errorcode))
          m.savetest(test)
          i = i + 1

          if ((i - 1) % task.nicmp == 0):
            sleep(task.delay)

        # Cattura delle eccezioni durante la misura
        except Exception as e:
          if not datetime.fromtimestamp(timestampNtp()).hour == start.hour:
            raise e
          else:
            logger.warning('Misura sospesa per eccezione %s' % e)
            self._updatestatus(status.Status(status.ERROR, 'Misura sospesa per errore: %s Aspetto 10 secondi prima di proseguire la misura.' % e))
            sleep(10)
            logger.info('Misura in ripresa dopo sospensione. Test ping %d di %d' % (i, task.ping))
            self._updatestatus(status.Status(status.PLAY, 'Proseguo la misura. Misura in esecuzione'))

      # Unset task timeout alarm
      # signal.alarm(0)

      # Spedisci il file al repository delle misure
      sec = datetime.fromtimestamp(timestampNtp()).strftime('%S')
      f = open('%s/measure_%s%s.xml' % (self._outbox, m.id, sec), 'w')
      f.write(str(m))

      # Aggiungi la data di fine in fondo al file
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
      self._updatestatus(status.Status(status.ERROR, 'Misura interrotta. %s Attendo %d secondi' % (e, self._polling)))

    bandwidth_sem.release() # Rilascia la risorsa condivisa: la banda

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
          time = getstarttime(filename)
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

  def _updatestatus(self, new):
    global current_status, status_sem

    status_sem.acquire()
    logger.debug('Aggiornamento stato: %s' % new.message)
    current_status = new

    if (self._communicator != None):
      self._communicator.sendstatus()
    status_sem.release()

  def _movefiles(self, filename):

    dir = path.dirname(filename)
    #pattern = path.basename(filename)[0:-4]
    pattern = path.basename(filename)

    try:
      for file in os.listdir(dir):
        # Cercare tutti i file che iniziano per pattern
        if (re.search(pattern, file) != None):
          # Spostarli tutti in self._sent
          old = ('%s/%s' % (dir, file))
          new = ('%s/%s' % (self._sent, file))
          shutil.move(old, new)

    except Exception as e:
      logger.error('Errore durante lo spostamento dei file di misura %s' % e)

  def _parserepositorydata(self, data):
    '''
    Valuta l'XML ricevuto dal repository, restituisce il codice e il messaggio ricevuto
    '''

    xml = getxml(data)
    if (xml == None):
      logger.error('Nessuna risposta ricevuta')
      return None

    nodes = xml.getElementsByTagName('response')
    if (len(nodes) < 1):
      logger.error('Nessuna risposta ricevuta nell\'XML:\n%s' % xml.toxml())
      return None

    node = nodes[0]

    code = getvalues(node, 'code')
    message = getvalues(node, 'message')
    return (code, message)

def main():
  logger.info('Starting Nemesys v.%s' % __version__)
  paths.check_paths()
  (options, args, md5conf) = parse()

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

  profile = Profile(id = options.profileid, upload = options.bandwidthup,
                    download = options.bandwidthdown)
  isp = Isp(id = options.ispid, certificate = options.certificate)
  return Client(id = options.clientid, profile = profile, isp = isp,
                geocode = options.geocode, username = options.username,
                password = options.password)

def parse():
  '''
  Parsing dei parametri da linea di comando
  '''

  config = ConfigParser()

  if (path.exists(paths.CONF_MAIN)):
    config.read(paths.CONF_MAIN)
    logger.info('Caricata configurazione da %s' % paths.CONF_MAIN)

  parser = OptionParser(version = __version__, description = '')
  parser.add_option('-T', '--test', dest = 'test', action = 'store_true',
                    help = 'test client functionality by executing a single task')
  parser.add_option('--task', dest = 'task',
                    help = 'path of an xml file with a task to execute (valid only if -T option is enabled)')

  # System options
  # --------------------------------------------------------------------------
  section = 'options'
  if (not config.has_section(section)):
    config.add_section(section)

  option = 'local'
  value = False
  try:
    value = config.getboolean(section, option)
  except (ValueError, NoOptionError):
    config.set(section, option, value)
  parser.add_option('-L', '--local', dest = option, action = 'store_true', default = value,
                    help = 'perform tests without sending measure files to repository')

  option = 'killonerror'
  value = True
  try:
    value = config.getboolean(section, option)
  except (ValueError, NoOptionError):
    config.set(section, option, value)
  parser.add_option('-K', '--killonerror', dest = option, action = 'store_true', default = value,
                    help = 'kill tests if an exception is raised during check')

  # System options
  # --------------------------------------------------------------------------
  section = 'system'
  if (not config.has_section(section)):
    config.add_section(section)

  # Task options
  # --------------------------------------------------------------------------
  section = 'task'
  if (not config.has_section(section)):
    config.add_section(section)

  option = 'tasktimeout'
  value = '3600'
  try:
    value = config.getint(section, option)
  except (ValueError, NoOptionError):
    config.set(section, option, value)
  parser.add_option('--task-timeout', dest = option, type = 'int', default = value,
                    help = 'global timeout (in seconds) for each task [%s]' % value)

  option = 'testtimeout'
  value = '60'
  try:
    value = config.getint(section, option)
  except (ValueError, NoOptionError):
    config.set(section, option, value)
  parser.add_option('--test-timeout', dest = option, type = 'float', default = value,
                    help = 'timeout (in seconds as float number) for each test in a task [%s]' % value)

  option = 'repository'
  value = 'https://finaluser.agcom244.fub.it/Upload'
  try:
    value = config.get(section, option)
  except (ValueError, NoOptionError):
    config.set(section, option, value)
  parser.add_option('-r', '--repository', dest = option, default = value,
                    help = 'upload URL for deliver measures\' files [%s]' % value)

  option = 'progressurl'
  value = 'https://finaluser.agcom244.fub.it/ProgressXML'
  try:
    value = config.get(section, option)
  except (ValueError, NoOptionError):
    config.set(section, option, value)
  parser.add_option('--progress-url', dest = option, default = value,
                    help = 'complete URL for progress request [%s]' % value)

  option = 'scheduler'
  value = 'https://finaluser.agcom244.fub.it/Scheduler'
  try:
    value = config.get(section, option)
  except (ValueError, NoOptionError):
    config.set(section, option, value)
  parser.add_option('-s', '--scheduler', dest = option, default = value,
                    help = 'complete url for schedule download [%s]' % value)

  option = 'httptimeout'
  value = '60'
  try:
    value = config.getint(section, option)
  except (ValueError, NoOptionError):
    config.set(section, option, value)
  parser.add_option('--http-timeout', dest = option, type = 'int', default = value,
                    help = 'timeout (in seconds) for http operations [%s]' % value)

  option = 'polling'
  value = '300'
  try:
    value = config.getint(section, option)
  except (ValueError, NoOptionError):
    config.set(section, option, value)
  parser.add_option('--polling-time', dest = option, type = 'int', default = value,
                    help = 'polling time in seconds between two scheduling requests [%s]' % value)

  # Client options
  # --------------------------------------------------------------------------
  section = 'client'
  if (not config.has_section(section)):
    config.add_section(section)

  option = 'clientid'
  value = None
  try:
    value = config.get(section, option)
  except (ValueError, NoOptionError):
    pass
  parser.add_option('-c', '--clientid', dest = option, default = value,
                    help = 'client identification string [%s]' % value)

  option = 'geocode'
  value = None
  try:
    value = config.get(section, option)
  except (ValueError, NoOptionError):
    logger.warning('Nessuna specifica geocode inserita.')
    pass
  parser.add_option('-g', '--geocode', dest = option, default = value,
                    help = 'geocode identification string [%s]' % value)

  option = 'username'
  value = 'anonymous'
  try:
    value = config.get(section, option)
  except (ValueError, NoOptionError):
    config.set(section, option, value)
  parser.add_option('--username', dest = option, default = value,
                    help = 'username for FTP login [%s]' % value)

  option = 'password'
  value = '@anonymous'
  try:
    value = config.get(section, option)
  except (ValueError, NoOptionError):
    config.set(section, option, value)
  parser.add_option('--password', dest = option, default = value,
                    help = 'password for FTP login [%s]' % value)

  # Profile options
  # --------------------------------------------------------------------------
  section = 'profile'
  if (not config.has_section(section)):
    config.add_section(section)

  option = 'profileid'
  value = None
  try:
    value = config.get(section, option)
  except (ValueError, NoOptionError):
    pass
  parser.add_option('-p', '--profileid', dest = option, default = value,
                    help = 'profile identification string [%s]' % value)

  option = 'bandwidthup'
  value = None
  try:
    value = config.getint(section, option)
  except (ValueError, NoOptionError):
    pass
  parser.add_option('--up', dest = option, default = value, type = 'int',
                    help = 'upload bandwidth [%s]' % value)

  option = 'bandwidthdown'
  value = None
  try:
    value = config.getint(section, option)
  except (ValueError, NoOptionError):
    pass
  parser.add_option('--down', dest = option, default = value, type = 'int',
                    help = 'download bandwidth [%s]' % value)

  # Isp options
  # --------------------------------------------------------------------------
  section = 'isp'
  if (not config.has_section(section)):
    config.add_section(section)

  option = 'ispid'
  value = None
  try:
    value = config.get(section, option)
  except (ValueError, NoOptionError):
    pass
  parser.add_option('--ispid', dest = option, default = value,
                    help = 'isp identification string [%s]' % value)

  option = 'certificate'
  value = None
  try:
    value = config.get(section, option)
    if not path.exists(value):
      config.remove_option(section, option)
      logger.warning('Trovata configurazione di certificato non esistente su disco. Cambiata configurazione')
      value = None
  except (ValueError, NoOptionError):
    logger.warning('Nessun certificato client specificato.')
    pass
  parser.add_option('--certificate', dest = option, default = value,
                    help = 'client certificate for schedule downloading and measure file signing [%s]' % value)

  with open(paths.CONF_MAIN, 'w') as file:
    config.write(file)

  (options, args) = parser.parse_args()

  # Verifica che le opzioni obbligatorie siano presenti
  # --------------------------------------------------------------------------

  try:

    parser.check_required('--clientid')
    config.set('client', 'clientid', options.clientid)

    parser.check_required('--up')
    config.set('profile', 'bandwidthup', options.bandwidthup)

    parser.check_required('--down')
    config.set('profile', 'bandwidthdown', options.bandwidthdown)

    parser.check_required('--profileid')
    config.set('profile', 'profileid', options.profileid)

    parser.check_required('--ispid')
    config.set('isp', 'ispid', options.ispid)

  finally:
    with open(paths.CONF_MAIN, 'w') as file:
      config.write(file)

  with open(paths.CONF_MAIN, 'r') as file:
    md5 = hashlib.md5(file.read()).hexdigest()

  return (options, args, md5)

def runtimewarning(signum, frame):
  raise RuntimeWarning()

if __name__ == '__main__':
  main()
