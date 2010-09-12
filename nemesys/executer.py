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
from client import Client
from datetime import datetime
from deliverer import Deliverer
from httplib import HTTPSConnection
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
from socket import gaierror
import status
from status import Status
from tester import Tester
from threading import Semaphore
from threading import Thread
from threading import Timer
from urlparse import urlparse
from xmlutils import getvalues
from xmlutils import getxml
from xmlutils import xml2task

bandwidth = Semaphore()
logger = logging.getLogger()


class _Communicator(Thread):

  def __init__(self):
    Thread.__init__(self)
    self.running = False
    self._channel = _Channel(('localhost', 21401))

  def sendstatus(self, status):
    self._channel.sendstatus(status)

  def stop(self):
    self.running = False

  def run(self):
    self.running = True
    asyncore.loop()


class _Sender(asyncore.dispatcher):

  # def readable(self):
  #    return False # don't have anything to read

  def writable(self):
    return len(self.buffer) > 0

  def write(self, status):
    try:
      self.buffer = status.getxml()
    except UnicodeEncodeError:
      self.buffer = Status(Status.ERROR, 'Errore di decodifica unicode').getxml()

    self.handle_write()

  def handle_read(self):
    data = self.recv(2048)
    logger.debug('Received: %s' % data)

  def handle_write(self):
    logger.debug('Sending status "%s"' % self.buffer)
    sent = self.send(self.buffer)
    self.buffer = self.buffer[sent:]

  def handle_close(self):
    self.close()


class _Channel(asyncore.dispatcher):

  def __init__(self, url):
    asyncore.dispatcher.__init__(self)
    self._url = url
    self._sender = None
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.set_reuse_addr()
    self.bind(self._url)
    self.listen(1)

  def sendstatus(self, status):
    if self._sender:
      self._sender.write(status)
    else:
      pass

  def handle_accept(self):
    (channel, addr) = self.accept()
    self._sender = _Sender(channel)
    self._sender.write(status.LOGO)


class OptionParser(OptionParser):

  def check_required(self, opt):
    option = self.get_option(opt)
    if getattr(self.values, option.dest) is None:
      self.error('%s option not supplied' % option)


class Executer:

  def __init__(self, client, scheduler, repository, polling=20.0, tasktimeout=60,
               testtimeout=30, httptimeout=60, local=False):

    self._client = client
    self._scheduler = scheduler
    self._repository = repository
    self._polling = polling
    self._tasktimeout = tasktimeout
    self._testtimeout = testtimeout
    self._httptimeout = httptimeout
    self._local = local
    self._outbox = paths.OUTBOX
    self._sent = paths.SENT
    self._communicator = _Communicator()
    self._communicator.start()

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

    while True:

      # TODO Controllare se occorre ancora effettuare le misure

      bandwidth.acquire() # Richiedi accesso esclusivo alla banda
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
        # TODO Se su task ho 'immediate' inizio tra un secondo
        delta = task.start - datetime.now()
        alarm = delta.days * 86400 + delta.seconds

        if alarm > 0:
          logger.debug('Impostazione di un nuovo task tra: %s secondi (%s)' % (alarm, delta))
          t = Timer(alarm, self._dotask, [task])
          t.start()

      # Aspetta 20 secondi
      sleep(float(self._polling))

  # Scarica il prossimo task dallo scheduler
  def _download(self):
    # logger.debug('Reading resource %s for client %s' % (self._scheduler, self._client))

    url = urlparse(self._scheduler)
    clientid = self._client.id
    certificate = self._client.isp.certificate

    connection = HTTPSConnection(url.hostname, key_file=certificate, cert_file=certificate, timeout=self._httptimeout)

    try:
      connection.request('GET', '%s?clientid=%s' % (url.path, clientid))

    except SSLError as e:
      logger.error('Impossibile scaricare lo scheduling. Errore SSL: %s.' % e)
      self._communicator.sendstatus(Status(status.ERROR, 'Impossibile dialogare con lo scheduler delle misure.'))
      return None

    except gaierror as e:
      logger.error('Impossibile scaricare lo scheduling. Errore socket: %s' % e)
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
    # logger.debug(task)

    # TODO Inserire il timeout complessivo di task
    # TODO Inserire controllo lungo per lo stato del PC dell'utente

    self._communicator.sendstatus(status.PLAY)

    t = Tester(host=task.server, timeout=self._testtimeout,
               username=self._client.username, password=self._client.password)

    # TODO Pensare ad un'altra soluzione per la generazione del progressivo di misura
    id = datetime.now().strftime('%y%m%d%H%M')
    m = Measure(id, task.server, self._client)

    # Set task timeout alarm
    # signal.alarm(self._tasktimeout)

    try:
      # Testa gli ftp down
      for i in range(1, task.download + 1):
        # TODO Inserire controllo breve per lo stato del PC dell'utente, nel caso sollevare un'eccezione
        logger.debug('Starting ftp download test (%s) [%d]' % (task.ftpdownpath, i))
        test = t.testftpdown(task.ftpdownpath)
        logger.debug('Download result: %.3f' % test.value)
        m.savetest(test)

      # TODO Inserire controllo medio per lo stato del PC dell'utente, nel caso sollevare un'eccezione

      # Testa gli ftp down
      for i in range(1, task.upload + 1):
        # TODO Inserire controllo breve per lo stato del PC dell'utente, nel caso sollevare un'eccezione
        logger.debug('Starting ftp upload test (%s) [%d]' % (task.ftpuppath, i))
        test = t.testftpup(self._client.profile.upload * task.multiplier * 1024 / 8, task.ftpuppath)
        logger.debug('Upload result: %.3f' % test.value)
        m.savetest(test)

      # TODO Inserire controllo medio per lo stato del PC dell'utente, nel caso sollevare un'eccezione

      # Testa i ping
      for i in range(1, task.ping + 1):
        logger.debug('Starting ping test [%d]' % i)
        test = t.testping()
        logger.debug('Ping result: %.3f' % test.value)
        if (i % task.nicmp == 0):
          sleep(task.delay)
        m.savetest(test)

      # Unset task timeout alarm
      # signal.alarm(0)

      # Spedisci il file al repository delle misure
      sec = datetime.now().strftime('%S')
      f = open('%s/measure_%s%s.xml' % (self._outbox, m.id, sec), 'w')
      f.write(str(m))
      f.close()

      # TODO Valutare se lasciare questa chiamata all'interno della regione critica per la banda
      if (not self._local):
        self._upload(f)

    except RuntimeWarning:
      logger.warning('Timeout during task execution. Time elapsed > %1f seconds ' % self._tasktimeout)

    except Exception as e:
      logger.error('Task interrotto per eccezione durante l\'esecuzione di un test: %s' % e)
      pass

    self._communicator.sendstatus(status.READY)
    bandwidth.release() # Rilascia la risorsa condivisa: la banda

  def _upload(self, file):
    '''
    Spedisce il file di misura al repository entro il tempo messo a
    disposizione secondo il parametro httptimeout
    '''
    try:

      # Crea il Deliverer che si occuperà della spedizione
      d = Deliverer(self._repository, self._client.isp.certificate, self._httptimeout)
      logger.debug('Invio il file %s a %s' % (file.name, self._repository))
      response = d.upload(file.name)

    except Exception as e:
      logger.error('Errore durante la spedizione del file delle misure %s: %s' % (file.name, e))

    try:
      if (response != None):
        (code, message) = self._parserepositorydata(response)
        code = int(code)
        logger.debug('Risposta dal server di upload: [%d] %s' % (code, message))

        # Se tutto è andato bene spostare tutti i file che iniziano per file.name nella cartella "sent"
        if (code == 0):
          self._movefiles(file.name)
          # TODO Inserire timbro su file paths.MEASURE_STATUS

    except TypeError as e:
      logger.error('Errore durante il parsing della risposta del repository: %s' % e)

    except Exception as e:
      logger.error('Errore durante il parsing della risposta del repository: %s' % e)

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

# TODO Creare dei task per l'upload dei file rimasti nella outbox

def main():
  paths.check_paths()
  (options, args) = parse()

  client = getclient(options)
  e = Executer(client=client, scheduler=options.scheduler,
               repository=options.repository, polling=options.polling,
               tasktimeout=options.tasktimeout, testtimeout=options.testtimeout,
               httptimeout=options.httptimeout, local=options.local)

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

  # TODO inserire automaticamente il numero di revisione
  parser = OptionParser(version='1.0.dev250', description='')
  parser.add_option('-T', '--test', dest='test', action='store_true',
                    help='test client functionality by executing a single task')
  parser.add_option('-L', '--local', dest='local', action='store_true',
                    help='perform tests without sending measure files to repository')
  parser.add_option('--task', dest='task',
                    help='path of an xml file with a task to execute (valid only if -T option is enabled)')

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
  value = 'https://scheduling.agcom244.fub.it/'
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
  value = '20'
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
  except NoOptionError:
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

    parser.check_required('--geocode')
    config.set('client', 'geocode', options.geocode)

    parser.check_required('--up')
    config.set('profile', 'bandwidthup', options.bandwidthup)

    parser.check_required('--down')
    config.set('profile', 'bandwidthdown', options.bandwidthdown)

    parser.check_required('--profileid')
    config.set('profile', 'profileid', options.profileid)

    if (options.ispid == None):
      options.ispid = options.clientid[0:6]
      config.set('isp', 'ispid', options.ispid)

    if (options.certificate == None):
      options.certificate = options.clientid[0:6] + '.pem'
      config.set('isp', 'certificate', options.certificate)

  finally:
    with open(paths.CONF_MAIN, 'w') as file:
      config.write(file)

  return (options, args)


def runtimewarning(signum, frame):
  raise RuntimeWarning()

if __name__ == '__main__':
  main()
