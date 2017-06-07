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
import platform
from threading import Event
from time import sleep

from common._generated_version import __version__, FULL_VERSION
from common import client
from common.deliverer import Deliverer
import gui_server
from common import iptools
from measure import Measure
from common.nem_exceptions import SysmonitorException
from common import nem_exceptions
import nem_options
import paths
from common.proof import Proof
from scheduler import Scheduler
from sysmonitor import SysProfiler
from common.tester import Tester
from common.timeNtp import timestampNtp


logger = logging.getLogger(__name__)

TH_TRAFFIC = 0.1
MAX_ERRORS = 3
SLEEP_SECS_AFTER_TASK = 30


class Executer(object):

    def __init__(self, client, scheduler, deliverer, sys_profiler,
                 polling=300.0, tasktimeout=60,
                 testtimeout=30, isprobe=True):

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

        self._time_to_stop = False

        if self._isprobe:
            logger.info('Inizializzato software per sonda.')
            self._gui_server = gui_server.DummyGuiServer()
        else:
            logger.info('Inizializzato software per misure '
                        'd\'utente con ISP id = %s' % client.isp.id)
            logger.info('Con profilo [%s]' % client.profile)
            self._gui_server = gui_server.Communicator(serial=self._client.id,
                                                       version=__version__)
            self._gui_server.start()

    def _do_task(self, task, dev):
        """
        Esegue il complesso di test prescritti dal task
        In presenza di errori ri-tenta per un massimo di 5 volte
        """
        logger.info('Inizio task di misura verso il server %s' % task.server)
        try:
            t = Tester(dev=dev, host=task.server, timeout=self._testtimeout)
            # TODO: Pensare ad un'altra soluzione per la generazione
            # del progressivo di misura
            start = datetime.fromtimestamp(timestampNtp())
            m_id = start.strftime('%y%m%d%H%M')
            m = Measure(m_id, task.server,
                        self._client, __version__,
                        start.isoformat())

            for test_type in ['ping', 'download', 'upload']:
                if test_type == 'ping':
                    n_reps = task.ping
                    self._gui_server.measure(test_type)
                    sleep_secs = 1
                elif test_type == "download":
                    n_reps = task.download
                    if n_reps > 0:
                        self._gui_server.measure(test_type, self._client.profile.download/1000)
                    sleep_secs = 10
                else:
                    n_reps = task.upload
                    if n_reps > 0:
                        self._gui_server.measure(test_type, self._client.profile.upload/1000)
                    sleep_secs = 10
                proofs = self._do_tests(test_type, n_reps, sleep_secs, t)
                m.add_proofs(proofs)
            sec = datetime.fromtimestamp(timestampNtp()).strftime('%S')
            f = open('%s/measure_%s%s.xml' % (self._outbox, m.id, sec), 'w')
            f.write(str(m))
            f.write('\n<!-- [finished] %s -->'
                    % datetime.fromtimestamp(timestampNtp()).isoformat())
            f.close()

            if not self._deliverer.upload_and_move(f.name,
                                                   self._sent,
                                                   (not self._isprobe)):
                msg = ('Misura terminata ma un errore si è '
                       'verificato durante il suo invio.')
                self._gui_server.notification(nem_exceptions.DELIVERY_ERROR,
                                              msg)
            logger.info('Fine task di misura.')

        except Exception as e:
            logger.error('Task interrotto per eccezione durante l\'esecuzione '
                         'di un test: %s' % e.message, exc_info=True)
            error_code = nem_exceptions.errorcode_from_exception(e)
            self._gui_server.notification(error_code, str(e))

    def _do_tests(self, test_type, n_reps, sleep_secs, t):
        proofs = []
        i = 1
        upload_bw = self._client.profile.upload * 1000
        while i <= n_reps:
            n_errors = 0
            while n_errors < MAX_ERRORS:
                if n_errors > 0:
                    logger.info('Misura in ripresa '
                                'dopo sospensione per errore.')
                logger.info("Esecuzione Test %d su %d di %s" % (i, n_reps, test_type))
                self._gui_server.test(test_type, i, n_reps, (n_errors > 0))
                try:
                    if test_type == 'ping':
                        proof = t.testping()
                        logger.info('Ping result: %.3f' % proof.duration)
                        self._gui_server.speed(proof.duration)
                        if i == n_reps:
                            self._gui_server.result(test_type, proof.duration)
                    elif test_type == 'download':
                        proof = t.testhttpdown(self.callback_httptest)
                        self._test_gating(proof)
                        kbps = proof.bytes_tot * 8.0 / proof.duration
                        logger.info('Download result: %.3f kbps' % kbps)
                        result = int(proof.bytes_tot * 8.0 / proof.duration)
                        self._gui_server.result(test_type,
                                                result=result,
                                                spurious=proof.spurious)
                    else:
                        proof = t.testhttpup(self.callback_httptest,
                                             upload_bw)
                        self._test_gating(proof)
                        kbps = proof.bytes_tot * 8.0 / proof.duration
                        logger.info('Upload result: %.3f kbps' % kbps)
                        res = int(proof.bytes_tot * 8.0 / proof.duration)
                        self._gui_server.result(test_type,
                                                result=res,
                                                spurious=proof.spurious)
                    proofs.append(proof)
                    break
                except Exception as e:
                    n_errors += 1
                    if n_errors >= MAX_ERRORS:
                        logger.warn("Il massimo numero di errori è stato "
                                    "raggiunto, sospendo la misura")
                        if self._isprobe:
                            proof = Proof(test_type=test_type,
                                          start_time=datetime.now(),
                                          duration=0,
                                          errorcode=nem_exceptions.errorcode_from_exception(e))
                            proofs.append(proof)
                            break
                        else:
                            raise e
                    else:
                        logger.warning(('Misura sospesa per eccezione {0}, '
                                        'è errore n. {1}').format(e, n_errors),
                                       exc_info=True)
                        self._gui_server.result(test_type, error=str(e))
                sleep(sleep_secs)
            i += 1
        return proofs

    def _get_and_handle_task(self):
        """
            Downloads a task from the scheduler and
            follows the directions found in the task
        """
        task = self._scheduler.download_task()
        if task is None:
            logger.warn("Ricevuto task vuoto")
            return
        logger.info('Trovato task %s' % task)
        if task.now:
            secs_to_next_measurement = 0
        else:
            delta = task.start - datetime.fromtimestamp(timestampNtp())
            secs_to_next_measurement = delta.days * 86400 + delta.seconds
        if task.is_wait or secs_to_next_measurement > self._polling + 30:
            '''Should just sleep and then download task again'''
            if task.is_wait:
                wait_secs = task.delay
            else:
                wait_secs = self._polling
                logger.debug('Prossimo task tra: %s minuti'
                             % (secs_to_next_measurement / 60))
            logger.debug('Faccio una pausa per %s minuti (%s secondi)'
                         % (wait_secs / 60, wait_secs))
            logger.debug("Trovato messaggio: %s" % task.message)
            self._gui_server.wait(wait_secs, task.message)
            self._sleep_and_wait(wait_secs)
        else:
            '''Should execute task after secs_to_next_measurement'''
            if secs_to_next_measurement >= 0:
                if task.download > 0 or task.upload > 0 or task.ping > 0:
                    logger.debug('Impostazione di un nuovo task tra: %s minuti'
                                 % (secs_to_next_measurement / 60))
                    self._sleep_and_wait(secs_to_next_measurement)
                    if self._isprobe:
                        dev = iptools.get_dev(task.server.ip, 80)
                    else:
                        dev = self._profile_system(task.server.ip, 80)
                    if dev:
                        self._do_task(task, dev)
                else:
                    logger.warn('Ricevuto task senza azioni da svolgere')
            else:
                logger.warn('Tempo di attesa prima della misura anomalo: '
                            '%s minuti' % (secs_to_next_measurement / 60))

    def _profile_system(self, server_ip, port):
        self._gui_server.profilation()
        try:
            self._sys_profiler.checkall(self.callback_sys_prof)
            sleep(1)
            self._gui_server.profilation(done=True)
            dev = iptools.get_dev(server_ip, port)
            return dev
        except SysmonitorException as e:
            logger.error('La profilazione del sistema ha rivelato '
                         'un problema: %s' % e)
            sleep(2)
            self._gui_server.profilation(done=True)
#             error_code = nem_exceptions.errorcode_from_exception(e)
#             self._gui_server.notification(error_code, message=str(e))
            return None

    def _sleep_and_wait(self, seconds):
        event_status = self._wakeup_event.wait(seconds)
        if event_status is True:
            logger.debug("Woken up while sleeping")
            self._wakeup_event.clear()

    def _test_gating(self, test):
        """
        Check that spurious traffic is not too high
        """
        logger.debug('Percentuale di traffico spurio: %.2f%%'
                     % (test.spurious * 100))
        if not self._isprobe:
            if test.spurious < 0:
                raise Exception('Errore durante la verifica del traffico di '
                                'misura: impossibile salvare i dati.')
            if test.spurious >= TH_TRAFFIC:
                raise Exception('Eccessiva presenza di traffico internet non '
                                'legato alla misura: percentuali %d%%.'
                                % (round(test.spurious * 100)))

    def callback_sys_prof(self, resource, status, info="", errorcode=0):
        """Is called by sysmonitor for each resource"""
        if status is True:
            status = 'ok'
        else:
            status = 'error'
        logger.debug("Callback from system profiler: %s, %s, %s"
                     % (resource, status, info))
        self._gui_server.sys_res(resource, status, info)
        if status is 'error':
            self._gui_server.notification(errorcode, message=info)

    def callback_httptest(self, second, speed):
        """Is called by the tester each second.
        speed is in kbps"""
        logger.debug("Callback from tester: %s, %s" % (second, speed))
        self._gui_server.speed(speed / 1000.0)

    def loop(self):
        try:
            self._sys_profiler.log_interfaces()
        except Exception as e:
            msg = "Impossibile rilevare le schede di rete: %s" % e
            logger.error(msg, exc_info=True)
            self._gui_server.notification(nem_exceptions.FAILPROF,
                                          message=msg)
        while not self._time_to_stop:
            logger.debug("Starting main loop")
            if self._isprobe:
                '''Try to send any unsent measures (only probe)'''
                self._deliverer.uploadall_and_move(self._outbox,
                                                   self._sent,
                                                   do_remove=False)

            try:
                self._get_and_handle_task()
            except Exception as e:
                logger.error('Errore durante la gestione del task per le '
                             'misure: %s' % e, exc_info=True)
                self._gui_server.notification(nem_exceptions.TASK_ERROR,
                                              message=str(e))
            finally:
                # TODO: check if this is how it is supposed to be
                self._gui_server.wait(SLEEP_SECS_AFTER_TASK,
                                      "Aspetto %d secondi prima di continuare"
                                      % SLEEP_SECS_AFTER_TASK)
                sleep(SLEEP_SECS_AFTER_TASK)
        logger.info("Exiting main loop")
        if self._gui_server:
            self._gui_server.stop(5.0)

    def stop(self):
        self._time_to_stop = True


def main():
    import log_conf
    log_conf.init_log()

    logger.info('Starting Nemesys v.%s on %s %s'
                % (FULL_VERSION, platform.system(), platform.release()))
    paths.check_paths()
    (options, _, md5conf) = nem_options.parse_args(__version__)

    c = client.getclient(options)
    isprobe = (c.isp.certificate is not None)
    sys_profiler = SysProfiler(c.profile.upload,
                               c.profile.download,
                               c.isp.id)

    e = Executer(client=c,
                 scheduler=Scheduler(options.scheduler,
                                     c,
                                     md5conf,
                                     __version__,
                                     options.httptimeout),
                 deliverer=Deliverer(options.repository,
                                     c.isp.certificate,
                                     options.httptimeout),
                 sys_profiler=sys_profiler,
                 polling=options.polling,
                 tasktimeout=options.tasktimeout,
                 testtimeout=options.testtimeout,
                 isprobe=isprobe)

    logger.debug('Inizio il loop.')
    e.loop()


if __name__ == '__main__':
    main()
