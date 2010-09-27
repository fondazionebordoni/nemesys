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

from ssl import SSLError
from time import sleep

from ConfigParser import ConfigParser
from ConfigParser import NoOptionError
import asyncore
from datetime import datetime
from client import Client
from deliverer import Deliverer
from httplib import HTTPSConnection
from httplib import HTTPConnection
from isp import Isp
from logger import logging
from measure import Measure
from optparse import OptionParser
import os
from os import path
import paths
from profile import Profile
import re
import shutil
import socket
import status
import sysmonitor
from status import Status
from tester import Tester
from threading import Semaphore
from threading import Thread
from threading import Timer
from urlparse import urlparse
from xmlutils import getvalues
from xmlutils import getxml
from progress import Progress
from xmlutils import xml2task
from random import randint
import glob

bandwidth = Semaphore()
logger = logging.getLogger()
current_status = status.LOGO
VERSION = '1.2'

# Numero massimo di misure per ora
MAX_MEASURES_PER_HOUR = 2

class _Communicator(Thread):

  def __init__(self):
    Thread.__init__(self)
    self._channel = _Channel(('localhost', 21401))

  def sendstatus(self):
    self._channel.sendstatus()

  def run(self):
    asyncore.loop(5)
    logger.debug('Nemesys asyncore loop terminated.')

  def join(self, timeout=None):
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

  def sendstatus(self, status=None):
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
    return len(self.buffer) > 0

  def write(self, status):
    try:
      self.buffer = status.getxml()
    except UnicodeEncodeError:
      self.buffer = Status(status.ERROR, 'Errore di decodifica unicode').getxml()

    try:
      self.handle_write()
    except Exception as e:
      logger.debug('Impossibile inviare il messaggio di notifica, errore: %s' % e)
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

  def __init__(self, client, scheduler, repository, polling=300.0, tasktimeout=60,
               testtimeout=30, httptimeout=60, local=False, isprobe=True):

    self._client = client
    self._scheduler = scheduler
    self._repository = repository
    self._polling = polling
    self._tasktimeout = tasktimeout
    self._testtimeout = testtimeout
    self._httptimeout = httptimeout
    self._local = local
    self._isprobe = isprobe
    self._outbox = paths.OUTBOX
    self._sent = paths.SENT
    current_status = status.LOGO
    self._communicator = None
    self._progress = None
    if self._isprobe:
      logger.debug('Inizializzato demone per sonda.')
    else:
      logger.debug('Inizializzato demone per misure d\'utente')

  def test(self, taskfile=None):

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

  def loop(self):
    # signal.signal(signal.SIGALRM, runtimewarning)
    t = None

    # Open socket for GUI dialog
    self._communicator = _Communicator()
    self._communicator.start()

    self._progress = Progress(create=True)

    # Controllo se non sono trascorsi 3 giorni dall'inizio delle misure
    while self._progress.onair() or self._isprobe:

      # Se non è una sonda, ma un client d'utente
      if not self._isprobe:
        # Se ho fatto 2 misure in questa ora, aspetto la prossima ora
        now = datetime.now()
        hour = now.hour
        made = self._progress.howmany(hour)
        if made >= MAX_MEASURES_PER_HOUR:
          # Quanti secondi perché scatti la prossima ora?
          delta_hour = now - now.replace(hour=hour + 1)
          # Aggiungo un random di 5 minuti per evitare chiamate sincrone
          wait_hour = delta_hour.seconds + randint(5, 300)
          logger.debug('La misura delle %d è completa. Aspetto %d secondi per il prossimo polling.' % (hour, wait_hour))
          sleep(wait_hour)
        elif made >= 1:
          # Ritardo la richiesta per le successive
          logger.debug('Ho fatto almento una misura. Aspetto %d secondi per il prossimo polling.' % self._polling * 3)
          sleep(self._polling * 3)
        else:
          # Aspetto prima di richiedere il task
          sleep(self._polling)
      else:
        # Aspetto prima di richiedere il task
        sleep(self._polling)

      if not self._isprobe and self._progress.doneall():
        self._updatestatus(status.FINISHED)

      bandwidth.acquire() # Richiedi accesso esclusivo alla banda
      # Controllo se ho dei file da mandare prima di prendermi il compito di fare altre misure
      self._uploadall()
      task = self._download()
      bandwidth.release() # Rilascia l'accesso esclusivo alla banda

      if (task != None):
        # logger.debug('Trovato task %s' % task)

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
        if (task.now):
          # Task immediato: inizio tra 5 secondi
          alarm = 5.00
        else:
          delta = task.start - datetime.now()
          alarm = delta.days * 86400 + delta.seconds

        if alarm > 0:
          logger.debug('Impostazione di un nuovo task tra: %s secondi' % alarm)
          t = Timer(alarm, self._dotask, [task])
          t.start()
      else:
        self._updatestatus(Status(status.ERROR, 'Errore durante la ricezione del task per le misure.'))

    while True:
      self._updatestatus(status.FINISHED)
      sleep(float(self._polling))

  # Scarica il prossimo task dallo scheduler
  def _download(self):
    logger.debug('Reading resource %s for client %s' % (self._scheduler, self._client))

    url = urlparse(self._scheduler)
    clientid = self._client.id
    certificate = self._client.isp.certificate

    # TODO Aggiugnere verifica certificato server
    if (url.scheme != 'https'):
      connection = HTTPConnection(host=url.hostname, timeout=self._httptimeout)
    elif (certificate != None and path.exists(certificate)):
      connection = HTTPSConnection(host=url.hostname, key_file=certificate, cert_file=certificate, timeout=self._httptimeout)
    else:
      connection = HTTPSConnection(host=url.hostname, timeout=self._httptimeout)

    try:
      connection.request('GET', '%s?clientid=%s&version=%s' % (url.path, clientid, VERSION))

    except SSLError as e:
      logger.error('Impossibile scaricare lo scheduling. Errore SSL: %s.' % e)
      self._updatestatus(Status(status.ERROR, 'Impossibile dialogare con lo scheduler delle misure.'))
      return None

    except socket.gaierror as e:
      logger.error('Impossibile scaricare lo scheduling. Errore socket: %s' % e)
      return None

    except socket.error as e:
      logger.error('Impossibile scaricare lo scheduling. Errore socket: %s' % e)
      return None

    except Exception as e:
      logger.error('Impossibile scaricare lo scheduling. Errore: %s' % e)
      return None

    try:
      data = connection.getresponse().read()

    except AttributeError as e:
      logger.error('Impossibile scaricare lo scheduling. Errore httplib: %s' % e)
      return None

    return xml2task(data)

  def _dotask(self, task):
    '''
    Esegue il complesso di test prescritti dal task entro il tempo messo a
    disposizione secondo il parametro tasktimeout
    '''

    bandwidth.acquire()  # Acquisisci la risorsa condivisa: la banda

    # Area riservata per l'esecuzione dei test
    # --------------------------------------------------------------------------

    # TODO Inserire il timeout complessivo di task (da posticipare)

    try:
      if not sysmonitor.checkall():
        raise Exception('Condizioni per effettuare la misura non verificate.')

      self._updatestatus(status.PLAY)

      t = Tester(host=task.server, timeout=self._testtimeout,
                 username=self._client.username, password=self._client.password)

      # TODO Pensare ad un'altra soluzione per la generazione del progressivo di misura
      id = datetime.now().strftime('%y%m%d%H%M')
      m = Measure(id, task.server, self._client)

      # Set task timeout alarm
      # signal.alarm(self._tasktimeout)

      # Testa gli ftp down
      for i in range(1, task.download + 1):

        if not sysmonitor.mediumcheck():
          raise Exception('Condizioni per effettuare la misura non verificate.')
        logger.debug('Starting ftp download test (%s) [%d]' % (task.ftpdownpath, i))
        test = t.testftpdown(task.ftpdownpath)
        logger.debug('Download result: %.3f' % test.value)
        m.savetest(test)

      # Testa gli ftp down
      for i in range(1, task.upload + 1):

        if not sysmonitor.mediumcheck():
          raise Exception('Condizioni per effettuare la misura non verificate.')

        logger.debug('Starting ftp upload test (%s) [%d]' % (task.ftpuppath, i))
        test = t.testftpup(self._client.profile.upload * task.multiplier * 1024 / 8, task.ftpuppath)
        logger.debug('Upload result: %.3f' % test.value)
        m.savetest(test)

      # Testa i ping
      for i in range(1, task.ping + 1):

        if not sysmonitor.mediumcheck():
          raise Exception('Condizioni per effettuare la misura non verificate.')

        logger.debug('Starting ping test [%d]' % i)
        test = t.testping()
        logger.debug('Ping result: %.3f' % test.value)
        if (i % task.nicmp == 0):
          sleep(task.delay)
        m.savetest(test)

      # Unset task timeout alarm
      # signal.alarm(0)

      if not sysmonitor.checkall():
        raise Exception('Condizioni per effettuare la misura non verificate.')

      # Spedisci il file al repository delle misure
      sec = datetime.now().strftime('%S')
      f = open('%s/measure_%s%s.xml' % (self._outbox, m.id, sec), 'w')
      f.write(str(m))
      f.close()

      if (not self._local):
        # TODO Testare correttezza nuovo sistema di upload delle misure
        self._upload(f)

      self._updatestatus(status.READY)

    except RuntimeWarning:
      self._updatestatus(status.Status(status.ERROR, 'Misura interrotta per timeout.'))
      logger.warning('Timeout during task execution. Time elapsed > %1f seconds ' % self._tasktimeout)

    except Exception as e:
      self._updatestatus(status.Status(status.ERROR, 'Misura interrotta: %s' % e))
      logger.error('Task interrotto per eccezione durante l\'esecuzione di un test: %s' % e)

    bandwidth.release() # Rilascia la risorsa condivisa: la banda

  def _uploadall(self):
    '''
    Cerca di spedire tutti i file di misura che trova nella cartella d'uscita
    '''
    for filename in glob.glob(os.path.join(self._outbox, 'measure_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].xml')):
      self._upload(filename)

  def _upload(self, filename):
    '''
    Spedisce il filename di misura al repository entro il tempo messo a
    disposizione secondo il parametro httptimeout
    '''
    try:

      # Crea il Deliverer che si occuperà della spedizione
      d = Deliverer(self._repository, self._client.isp.certificate, self._httptimeout)
      logger.debug('Invio il file %s a %s' % (filename, self._repository))
      response = d.upload(filename)

    except Exception as e:
      logger.error('Errore durante la spedizione del filename delle misure %s: %s' % (filename, e))

    try:
      if (response != None):
        (code, message) = self._parserepositorydata(response)
        code = int(code)
        logger.debug('Risposta dal server di upload: [%d] %s' % (code, message))

        # Se tutto è andato bene sposto il file nella cartella "sent"
        if (code == 0):
          self._movefiles(filename)
          self._progress.putstamp()

    except TypeError as e:
      logger.error('Errore durante il parsing della risposta del repository: %s' % e)

    except Exception as e:
      logger.error('Errore durante il parsing della risposta del repository: %s' % e)

  def _updatestatus(self, new):
    global current_status

    logger.debug('Aggiornamento stato: %s' % new.message)
    current_status = new

    if (self._communicator != None):
      self._communicator.sendstatus()

  def _movefiles(self, filename):

    dir = path.dirname(filename)
    pattern = path.basename(filename)[0:-4]

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
  paths.check_paths()
  (options, args) = parse()

  client = getclient(options)
  isprobe = (client.isp.certificate != None)
  e = Executer(client=client, scheduler=options.scheduler,
               repository=options.repository, polling=options.polling,
               tasktimeout=options.tasktimeout, testtimeout=options.testtimeout,
               httptimeout=options.httptimeout, local=options.local, isprobe=isprobe)
  logger.debug("%s, %s, %s" % (client, client.isp, client.profile))

  if (options.test):
    # Se è presente il flag T segui il test ed esci
    e.test(options.task)
  else:
    # Altrimenti viene eseguito come demone: entra nel loop infinito
    e.loop()


def getclient(options):

  profile = Profile(id=options.profileid, upload=options.bandwidthup,
                    download=options.bandwidthdown)
  isp = Isp(id=options.ispid, certificate=options.certificate)
  return Client(id=options.clientid, profile=profile, isp=isp,
                geocode=options.geocode, username=options.username,
                password=options.password)

def parse():
  '''
  Parsing dei parametri da linea di comando
  '''

  config = ConfigParser()

  if (path.exists(paths.CONF_MAIN)):
    logger.debug('Trovata configurazione in %s' % paths.CONF_MAIN)
    config.read(paths.CONF_MAIN)

  parser = OptionParser(version=VERSION, description='')
  parser.add_option('-T', '--test', dest='test', action='store_true',
                    help='test client functionality by executing a single task')
  parser.add_option('--task', dest='task',
                    help='path of an xml file with a task to execute (valid only if -T option is enabled)')

  # System options
  # --------------------------------------------------------------------------
  section = 'options'
  if (not config.has_section(section)):
    config.add_section(section)

  option = 'local'
  value = False
  try:
    value = config.getboolean(section, option)
  except NoOptionError:
    config.set(section, option, value)
  parser.add_option('-L', '--local', dest='local', action='store_true', default=value,
                    help='perform tests without sending measure files to repository')

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
  except NoOptionError:
    config.set(section, option, value)
  parser.add_option('--task-timeout', dest=option, type='int', default=value,
                    help='global timeout (in seconds) for each task [%s]' % value)

  option = 'testtimeout'
  value = '60'
  try:
    value = config.getint(section, option)
  except NoOptionError:
    config.set(section, option, value)
  parser.add_option('--test-timeout', dest=option, type='float', default=value,
                    help='timeout (in seconds as float number) for each test in a task [%s]' % value)

  option = 'repository'
  value = 'https://repository.agcom244.fub.it/Upload'
  try:
    value = config.get(section, option)
  except NoOptionError:
    config.set(section, option, value)
  parser.add_option('-r', '--repository', dest=option, default=value,
                    help='upload URL for deliver measures\' files [%s]' % value)

  option = 'scheduler'
  value = 'https://scheduler.agcom244.fub.it/'
  try:
    value = config.get(section, option)
  except NoOptionError:
    config.set(section, option, value)
  parser.add_option('-s', '--scheduler', dest=option, default=value,
                    help='complete url for schedule download [%s]' % value)

  option = 'httptimeout'
  value = '60'
  try:
    value = config.getint(section, option)
  except NoOptionError:
    config.set(section, option, value)
  parser.add_option('--http-timeout', dest=option, type='int', default=value,
                    help='timeout (in seconds) for http operations [%s]' % value)

  option = 'polling'
  value = '300'
  try:
    value = config.getint(section, option)
  except NoOptionError:
    config.set(section, option, value)
  parser.add_option('--polling-time', dest=option, type='int', default=value,
                    help='polling time in seconds between two scheduling requests [%s]' % value)

  # Client options
  # --------------------------------------------------------------------------
  section = 'client'
  if (not config.has_section(section)):
    config.add_section(section)

  option = 'clientid'
  value = None
  try:
    value = config.get(section, option)
  except NoOptionError:
    pass
  parser.add_option('-c', '--clientid', dest=option, default=value,
                    help='client identification string [%s]' % value)

  option = 'geocode'
  value = None
  try:
    value = config.get(section, option)
  except NoOptionError:
    logger.warning('Nessuna specifica geocode inserita.')
    pass
  parser.add_option('-g', '--geocode', dest=option, default=value,
                    help='geocode identification string [%s]' % value)

  option = 'username'
  value = 'anonymous'
  try:
    value = config.get(section, option)
  except NoOptionError:
    config.set(section, option, value)
  parser.add_option('--username', dest=option, default=value,
                    help='username for FTP login [%s]' % value)

  option = 'password'
  value = '@anonymous'
  try:
    value = config.get(section, option)
  except NoOptionError:
    config.set(section, option, value)
  parser.add_option('--password', dest=option, default=value,
                    help='password for FTP login [%s]' % value)

  # Profile options
  # --------------------------------------------------------------------------
  section = 'profile'
  if (not config.has_section(section)):
    config.add_section(section)

  option = 'profileid'
  value = None
  try:
    value = config.get(section, option)
  except NoOptionError:
    pass
  parser.add_option('-p', '--profileid', dest=option, default=value,
                    help='profile identification string [%s]' % value)

  option = 'bandwidthup'
  value = None
  try:
    value = config.getint(section, option)
  except NoOptionError:
    pass
  parser.add_option('--up', dest=option, default=value, type='int',
                    help='upload bandwidth [%s]' % value)

  option = 'bandwidthdown'
  value = None
  try:
    value = config.getint(section, option)
  except NoOptionError:
    pass
  parser.add_option('--down', dest=option, default=value, type='int',
                    help='download bandwidth [%s]' % value)

  # Isp options
  # --------------------------------------------------------------------------
  section = 'isp'
  if (not config.has_section(section)):
    config.add_section(section)

  option = 'ispid'
  value = None
  try:
    value = config.get(section, option)
  except NoOptionError:
    pass
  parser.add_option('--ispid', dest=option, default=value,
                    help='isp identification string [%s]' % value)

  option = 'certificate'
  value = None
  try:
    value = config.get(section, option)
    if not path.exists(value):
      config.remove_option(section, option)
      logger.warning('Trovata configurazione di certificato non esistente su disco. Cambiata configurazione')
      value = None
  except NoOptionError:
    logger.warning('Nessun certificato client specificato.')
    pass
  parser.add_option('--certificate', dest=option, default=value,
                    help='client certificate for schedule downloading and measure file signing [%s]' % value)

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

  return (options, args)


def runtimewarning(signum, frame):
  raise RuntimeWarning()

if __name__ == '__main__':
  main()
