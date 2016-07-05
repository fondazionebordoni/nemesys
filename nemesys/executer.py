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
import logging
from threading import Event
from time import sleep

from _generated_version import __version__, FULL_VERSION
import client
from deliverer import Deliverer
import gui_server
import iptools
from measure import Measure
from nem_exceptions import SysmonitorException
import nem_exceptions
import nem_options
import paths
from scheduler import Scheduler
from sysmonitor import SysProfiler
from tester import Tester
from timeNtp import timestampNtp


logger = logging.getLogger(__name__)

TH_TRAFFIC = 0.1
MAX_ERRORS = 3
SLEEP_SECS_AFTER_TASK = 30

class Executer(object):

    def __init__(self, client, scheduler, deliverer, sys_profiler, polling = 300.0, tasktimeout = 60,
                             testtimeout = 30, isprobe = True):

        self._client = client
        self._scheduler = scheduler
        self._deliverer = deliverer
        self._sys_profiler = sys_profiler
        self._polling = polling
        self._tasktimeout = tasktimeout
        self._testtimeout = testtimeout
        self._isprobe = isprobe

        self._outbox = paths.OUTBOX
        self._sent = paths.SENT
        self._wakeup_event = Event()

        if self._isprobe:
            self._communicator = None
            logger.info('Inizializzato software per sonda.')
        else:
            logger.info('Inizializzato software per misure d\'utente con ISP id = %s' % client.isp.id)
            self._communicator = gui_server.Communicator(serial=self._client.id)
            self._communicator.start()

    def stop(self):
        self._time_to_stop = True


    def loop(self):
        # Open socket for GUI dialog
        self._time_to_stop = False
        while not self._time_to_stop:
            if self._isprobe:
                '''Try to send any unsent measures (only probe)'''
                self._deliverer.uploadall_and_move(self._outbox, self._sent, do_remove=(not self._isprobe))

            try:
                task = self._scheduler.download_task()
                logger.debug('Trovato task %s' % task)
                # If task contains wait instructions
                if task.now:
                    secs_to_next_measurement = 0
                else:
                    delta = task.start - datetime.fromtimestamp(timestampNtp())
                    secs_to_next_measurement = delta.days * 86400 + delta.seconds

                if task.is_wait or secs_to_next_measurement > self._polling + 30:
                    '''Should just sleep and then download task again'''
                    if task.is_wait:
                        wait_secs = task.delay
                        logger.debug('Faccio una pausa per %s minuti (%s secondi)' % (wait_secs/60, wait_secs))
                    else:
                        wait_secs = self._polling
                        logger.debug('Prossimo task tra: %s minuti, faccio una pausa per %s minuti' % (secs_to_next_measurement/60, self._polling/60))

                    # Check for message and update GUI
                    logger.debug("Trovato messaggio: %s" % task.message)
                    self._updatestatus(gui_server.gen_wait_message(wait_secs, task.message))
                    # Sleep for wait_secs seconds, unless woken up by event
                    self._sleep_and_wait(wait_secs)
                else:
                    '''Should execute task after secs_to_next_measurement'''
                    if secs_to_next_measurement >= 0:
                        if task.download > 0 or task.upload > 0 or task.ping > 0:
                            logger.debug('Impostazione di un nuovo task tra: %s minuti' % (secs_to_next_measurement/60))
                            self._sleep_and_wait(secs_to_next_measurement)
                            try:
                                self._updatestatus(gui_server.gen_profilation_message())
                                self._sys_profiler.checkall(self._client.profile.upload, self._client.profile.download, self._client.isp.id, arping=True, callback=self.sys_prof_callback)
                                dev = iptools.get_dev(task.server.ip, 80)
                                sleep(1)
                                self._updatestatus(gui_server.gen_profilation_message(done=True))
                                self._dotask(task, dev)
                            except SysmonitorException as e:
                                logger.error('La profilazione del sistema ha rivelato un problema: %s' % e)
                                sleep(2)
                                self._updatestatus(gui_server.gen_profilation_message(done=True))
                                self._updatestatus(gui_server.gen_notification_message(error_code=nem_exceptions.errorcode_from_exception(e), message=str(e)))
                        else:
                            #TODO: aggiornare GUI?
                            logger.warn('Ricevuto task senza azioni da svolgere')
                    else:
                        logger.warn('Tempo di attesa prima della misura anomalo: %s minuti' % (secs_to_next_measurement/60))
            except Exception as e:
                logger.error('Errore durante la gestione del task per le misure: %s' % e, exc_info=True)
                self._updatestatus(gui_server.gen_notification_message(error_code=nem_exceptions.TASK_ERROR, message=str(e)))
            finally:
                #TODO: check if this is how it is supposed to be
                self._updatestatus(gui_server.gen_wait_message(SLEEP_SECS_AFTER_TASK, "Aspetto %d secondi prima di continuare" % SLEEP_SECS_AFTER_TASK))
                sleep(SLEEP_SECS_AFTER_TASK)



    def _sleep_and_wait(self, seconds):
        event_status = self._wakeup_event.wait(seconds)
        if event_status == True:
            logger.debug("Woken up while sleeping")
            self._wakeup_event.clear()


    def _test_gating(self, test):
        '''
        Check that spurious traffic is not too high
        '''
        logger.debug('Percentuale di traffico spurio: %.2f%%' % (test.spurious * 100))
        if not self._isprobe:
            if test.spurious < 0:
                raise Exception('Errore durante la verifica del traffico di misura: impossibile salvare i dati.')
            if test.spurious >= TH_TRAFFIC:
                raise Exception('Eccessiva presenza di traffico internet non legato alla misura: percentuali %d%%.' % (round(test.spurious * 100)))


    def _dotask(self, task, dev):
        '''
        Esegue il complesso di test prescritti dal task
        In presenza di errori ri-tenta per un massimo di 5 volte
        '''
        logger.info('Inizio task di misura verso il server %s' % task.server)

        try:
            t = Tester(dev = dev, host = task.server, timeout = self._testtimeout,
                                 username = self._client.username, password = self._client.password)

            # TODO: Pensare ad un'altra soluzione per la generazione del progressivo di misura
            start = datetime.fromtimestamp(timestampNtp())
            m_id = start.strftime('%y%m%d%H%M')
            m = Measure(m_id, task.server, self._client, __version__, start.isoformat())

            for test_type in ['ping', 'download', 'upload']:
                if test_type == 'ping':
                    n_reps = task.ping
                    self._updatestatus(gui_server.gen_measure_message(test_type))
                    sleep_secs = 1
                elif test_type == "down":
                    n_reps = task.download
                    if n_reps > 0:
                        self._updatestatus(gui_server.gen_measure_message(test_type, bw=self._client.profile.download/1000.0))
                    sleep_secs = 10
                else:
                    n_reps = task.upload
                    if n_reps > 0:
                        self._updatestatus(gui_server.gen_measure_message(test_type, bw=self._client.profile.upload/1000.0))
                    sleep_secs = 10
                i = 1
                while i <= n_reps:
                    n_errors = 0
                    error_has_occured = False
                    done = False
                    while n_errors < MAX_ERRORS and not done:
                        if error_has_occured:
                            logger.info('Misura in ripresa dopo sospensione per errore.')

                        logger.info("Esecuzione Test %d su %d" % (i, n_reps))
                        try:
                            logger.debug('Starting %s test [%d]' % (test_type, i))
                            self._updatestatus(gui_server.gen_test_message(test_type, i, n_reps, error_has_occured))

                            if test_type == 'ping':
                                test = t.testping()
                                logger.debug('Ping result: %.3f' % test.duration)
                                self._updatestatus(gui_server.gen_tachometer_message(test.duration))
                                #TODO: just showing last value, should omit?
                                if i == n_reps:
                                    self._updatestatus(gui_server.gen_result_message(test_type, test.duration))
                            elif test_type == 'download':
                                test = t.testhttpdown(callback_update_speed=self.http_test_callback)
                                self._test_gating(test)
                                logger.debug('Download result: %.3f kbps' % (test.bytes_tot*8.0/test.duration))
                                self._updatestatus(gui_server.gen_result_message(test_type, result=int(test.bytes_tot*8.0/test.duration), spurious=test.spurious))
                            else:
                                test = t.testhttpup(callback_update_speed=self.http_test_callback, bw=self._client.profile.upload*1000)
                                self._test_gating(test)
                                logger.debug('Upload result: %.3f kbps' % (test.bytes_tot*8.0/test.duration))
                                self._updatestatus(gui_server.gen_result_message(test_type, result=int(test.bytes_tot*8.0/test.duration), spurious=test.spurious))

                            m.savetest(test)
                            done = True
                            error_has_occured = False
                        except Exception as e:
                            n_errors += 1
                            if n_errors >= MAX_ERRORS:
                                logger.warn("Il massimo numero di errori è stato raggiunto, sospendo la misura")
                                raise e
                            else:
                                logger.warning('Misura sospesa per eccezione %s, è errore n. %d' % (e, n_errors), exc_info=True)
                                error_has_occured = True
                                self._updatestatus(gui_server.gen_result_message(test_type, error=str(e)))
                        sleep(sleep_secs)
                    i += 1
            sec = datetime.fromtimestamp(timestampNtp()).strftime('%S')
            f = open('%s/measure_%s%s.xml' % (self._outbox, m.id, sec), 'w')
            f.write(str(m))
            f.write('\n<!-- [finished] %s -->' % datetime.fromtimestamp(timestampNtp()).isoformat())
            f.close()

            if not self._deliverer.upload_and_move(f.name, self._sent, do_remove=(not self._isprobe)):
                self._updatestatus(gui_server.gen_notification_message(error_code=nem_exceptions.DELIVERY_ERROR,
                                                                       message='Misura terminata ma un errore si è verificato durante il suo invio.'))
            logger.info('Fine task di misura.')

        except Exception as e:
            logger.error('Task interrotto per eccezione durante l\'esecuzione di un test: %s' % e.message, exc_info=True)
            self._updatestatus(gui_server.gen_notification_message(error_code=nem_exceptions.errorcode_from_exception(e), message=str(e)))


    def _updatestatus(self, current_status):
        logger.info("Status update: %s", current_status)
        if (self._communicator != None):
            self._communicator.sendstatus(current_status)

    def sys_prof_callback(self, resource, status, info=""):
        '''Is called by sysmonitor for each resource'''
        if status == True:
            status = 'ok'
        else:
            status = 'error'
        logger.info("Callback from system profiler: %s, %s, %s" %(resource, status, info))
        self._updatestatus(gui_server.gen_sys_resource_message(resource, status, info))

    def http_test_callback(self, second, speed):
        '''Is called by the tester each second.
        speed is in kbps'''
        logger.info("Callback from tester: %s, %s" %(second, speed))
        self._updatestatus(gui_server.gen_tachometer_message(speed/1000))



def main():
    #TODO: separate between probe and not probe
    import log_conf
    log_conf.init_log()

    logger.info('Starting Nemesys v.%s' % FULL_VERSION)
    paths.check_paths()
    (options, _, md5conf) = nem_options.parse_args(__version__)

    c = client.getclient(options)
    isprobe = (c.isp.certificate != None)
    e = Executer(client=c,
                 scheduler=Scheduler(options.scheduler, c, md5conf, __version__, options.httptimeout),
                 deliverer=Deliverer(options.repository, c.isp.certificate, options.httptimeout),
                 sys_profiler = SysProfiler(bypass=False),
                 polling=options.polling,
                 tasktimeout=options.tasktimeout,
                 testtimeout=options.testtimeout,
                 isprobe=isprobe)
    #logger.debug("%s, %s, %s" % (client, client.isp, client.profile))

    logger.debug('Inizio il loop.')
    e.loop()

if __name__ == '__main__':
    main()
