#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010-2016 Fondazione Ugo Bordoni.
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

# TODO fix use of parameter _running

import logging
from datetime import datetime
from threading import Thread
from time import sleep
from urlparse import urlparse

import gui_event
import paths
import result_sender
import system_resource
import task
import test_type
from best_test import BestTest
from common import iptools
from common import server
from common.deliverer import Deliverer
from common.nem_exceptions import MeasurementException
from common.tester import Tester
from common.timeNtp import timestampNtp
from measure import Measure

logger = logging.getLogger(__name__)

TH_TRAFFIC = 0.1  # Soglia per il rapporto tra traffico 'spurio' e traffico totale #
TIME_LAG = 5  # Tempo di attesa tra una misura e la successiva in caso di misura fallita #
MAX_TEST_RETRY = 3


class SpeedTester(Thread):
    def __init__(self, version, event_dispatcher, system_profiler, mist_options):
        Thread.__init__(self)

        self._version = version
        self._event_dispatcher = event_dispatcher
        self._profiler = system_profiler
        self._client = mist_options.client
        self._scheduler = mist_options.scheduler
        # TODO: serve?         self._tasktimeout = mist_options.tasktimeout
        self._httptimeout = mist_options.httptimeout
        self._testtimeout = mist_options.testtimeout
        self._md5conf = mist_options.md5conf
        self._deliverer = Deliverer(mist_options.repository, self._client.isp.certificate, self._httptimeout)
        self._running = False
        self._progress = 0.01

    def is_oneshot(self):
        return self._client.is_oneshot()

    def stop(self):
        self._running = False
        logger.info("Chiusura del tester")

    def is_running(self):
        return self._running

    def callback_server(self, message):
        self._event_dispatcher.postEvent(gui_event.UpdateEvent(message))

    def receive_partial_results_up(self, **args):
        """Intermediate results from tester"""
        speed = args['speed']
        logger.info("Got partial result: %f", speed)
        self._event_dispatcher.postEvent(gui_event.ResultEvent(test_type.HTTP_UP, speed, is_intermediate=True))

    def receive_partial_results_down(self, **args):
        """Intermediate results from tester"""
        speed = args['speed']
        logger.info("Got partial result: %f", speed)
        self._event_dispatcher.postEvent(gui_event.ResultEvent(test_type.HTTP_DOWN, speed, is_intermediate=True))

    def _do_test(self, tester, t_type, my_task, previous_profiler_result):
        test_done = 0
        test_good = 0
        retry = 0
        best_ping_value = 4444
        best_bw_value = -1

        if t_type == test_type.PING:
            test_todo = my_task.ping
        elif test_type.is_http_down(t_type):
            test_todo = my_task.http_download
        elif test_type.is_http_up(t_type):
            test_todo = my_task.http_upload
        else:
            logger.warn("Tipo di test da effettuare non definito: %s" % test_type.get_string_type(t_type))
            test_todo = 0

        while (test_good < test_todo) and self._running:
            self._progress += self._progress_step
            self._event_dispatcher.postEvent(gui_event.ProgressEvent(self._progress))

            profiler_result = self._profiler.profile_once(
                {system_resource.RES_CPU, system_resource.RES_RAM, system_resource.RES_ETH, system_resource.RES_WIFI})
            sleep(1)

            self._event_dispatcher.postEvent(gui_event.UpdateEvent(
                "Test %d di %d di %s" % (test_good + 1, test_todo, test_type.get_string_type(t_type).upper())))
            try:
                test_done += 1
                message = ("Tentativo numero %s con %s riusciti su %s da collezionare"
                           % (test_done, test_good, test_todo))

                short_string = test_type.get_string_type_short(t_type).upper()
                logger.info("[%s] %s [%s]" % (short_string, message, short_string))
                if t_type == test_type.PING:
                    proof = tester.testping()
                    logger.info("[ Ping: %s ] [ Actual Best: %s ]" % (proof.duration, best_ping_value))
                    self._event_dispatcher.postEvent(
                        gui_event.ResultEvent(test_type.PING, proof.duration, is_intermediate=True))
                    self._event_dispatcher.postEvent(gui_event.UpdateEvent("Risultato %s (%s di %s): %.1f ms" %
                                                                           (test_type.get_string_type(t_type).upper(),
                                                                            test_good + 1, test_todo,
                                                                            proof.duration)))
                    if proof.duration < best_ping_value:
                        best_ping_value = proof.duration
                        best_testres = proof
                        best_testres_profiler = profiler_result
                else:
                    if test_type.is_http_down(t_type):
                        proof = tester.testhttpdown(self.receive_partial_results_down)
                    elif test_type.is_http_up(t_type):
                        proof = tester.testhttpup(self.receive_partial_results_up,
                                                  bw=self._client.profile.upload * 1000)
                    bandwidth = proof.bytes_tot * 8 / float(proof.duration)
                    self._event_dispatcher.postEvent(gui_event.ResultEvent(t_type, bandwidth, is_intermediate=True))
                    self._event_dispatcher.postEvent(gui_event.UpdateEvent("Risultato %s (%s di %s): %s" %
                                                                           (test_type.get_string_type(t_type).upper(),
                                                                            test_good + 1, test_todo,
                                                                            int(bandwidth))))
                    spurious_percent = "%.2f%%" % (proof.spurious * 100)
                    if proof.spurious < 0:
                        info = ('Traffico totale risulta minore del traffico di misura: percentuale %s'
                                % spurious_percent)
                        self._event_dispatcher.postEvent(gui_event.ResourceEvent(system_resource.RES_TRAFFIC,
                                                                                 system_resource.SystemResource(
                                                                                     status=False, info=info,
                                                                                     value=spurious_percent), True))
                        raise Exception("traffico spurio negativo.")
                    if proof.spurious > TH_TRAFFIC:
                        info = ('Eccessiva presenza di traffico internet non legato alla misura: percentuale %s'
                                % spurious_percent)
                        self._event_dispatcher.postEvent(gui_event.ResourceEvent(system_resource.RES_TRAFFIC,
                                                                                 system_resource.SystemResource(
                                                                                     status=False, info=info,
                                                                                     value=spurious_percent), True))
                        raise Exception("superata la soglia di traffico spurio.")
                    else:
                        info = 'Traffico internet non legato alla misura: percentuale %s' % spurious_percent
                        self._event_dispatcher.postEvent(gui_event.ResourceEvent(system_resource.RES_TRAFFIC,
                                                                                 system_resource.SystemResource(
                                                                                     status=True, info=info,
                                                                                     value=spurious_percent), False))

                    logger.info("[ Bandwidth in %s : %s ] [ Actual Best: %s ]" % (t_type, bandwidth, best_ping_value))
                    if bandwidth > best_bw_value:
                        best_bw_value = bandwidth
                        best_testres = proof
                        best_testres_profiler = profiler_result
                test_good += 1
                self._progress += self._progress_step
                self._event_dispatcher.postEvent(gui_event.ProgressEvent(self._progress))

            except Exception as e:
                logger.error("Errore durante l'esecuzione di un test", exc_info=True)
                self._event_dispatcher.postEvent(gui_event.ErrorEvent("Errore durante l'esecuzione di un test: %s" % e))
                retry += 1
                if retry < MAX_TEST_RETRY:
                    self._event_dispatcher.postEvent(
                        gui_event.UpdateEvent("Ripresa del test tra %d secondi" % TIME_LAG))
                    sleep(TIME_LAG)
                else:
                    raise Exception("Superato il numero massimo di errori possibili durante una misura.")
        previous_profiler_result.update(best_testres_profiler)
        return BestTest(proof=best_testres, profiler_info=previous_profiler_result, n_tests_done=test_done)

    def run(self):
        self._running = True
        self._event_dispatcher.postEvent(
            gui_event.UpdateEvent("Inizio dei test di misura", gui_event.UpdateEvent.MAJOR_IMPORTANCE))
        self._event_dispatcher.postEvent(gui_event.ProgressEvent(self._progress))
        try:
            ip = iptools.getipaddr()
            dev = iptools.get_dev(ip=ip)
            mac = iptools.get_mac_address(dev)
        except Exception as e:
            logger.error(e, exc_info=True)
            self._event_dispatcher.postEvent(gui_event.ErrorEvent("Impossibile ottenere il dettaglio dell\'interfaccia "
                                                                  "di rete. Assicurarsi di essere connesso alla rete."))
            self._event_dispatcher.postEvent(gui_event.StopEvent(is_oneshot=self.is_oneshot()))
            self._running = False
            return

        os = self._profiler.get_os()
        self._profiler.profile_in_background(
            {system_resource.RES_CPU, system_resource.RES_RAM, system_resource.RES_ETH, system_resource.RES_WIFI})
        self._progress += 0.01
        self._event_dispatcher.postEvent(gui_event.ProgressEvent(self._progress))
        if self.is_oneshot():
            self._event_dispatcher.postEvent(gui_event.UpdateEvent("Scelta del server di misura "
                                                                   "in corso, attendere..."))
            try:
                chosen_server = server.get_server(self._event_dispatcher)
                self._event_dispatcher.postEvent(
                    gui_event.UpdateEvent("Scelto il server di misura %s" % chosen_server.name,
                                          gui_event.UpdateEvent.MAJOR_IMPORTANCE))

            except Exception as e:
                self._event_dispatcher.postEvent(gui_event.ErrorEvent(e.message))
                self._event_dispatcher.postEvent(gui_event.StopEvent(is_oneshot=self.is_oneshot()))
                self._running = False
                return
        else:
            chosen_server = None
        my_task = task.download_task(url=urlparse(self._scheduler),
                                     client_id=self._client.id,
                                     certificate=self._client.isp.certificate,
                                     version=self._version,
                                     md5conf=self._md5conf,
                                     timeout=self._httptimeout,
                                     server=chosen_server)

        if my_task is None:
            self._event_dispatcher.postEvent(
                gui_event.ErrorEvent("Impossibile eseguire ora i test di misura. Riprovare tra qualche secondo."))
        else:
            self._progress += 0.01
            self._event_dispatcher.postEvent(gui_event.ProgressEvent(self._progress))
            try:
                test_types = [test_type.PING, test_type.HTTP_DOWN, test_type.HTTP_UP]
                total_num_tasks = 0
                for _ in test_types:
                    total_num_tasks += 4
                total_num_tasks *= 2  # Multiply by 2 to make two progress per task
                total_num_tasks += 3  # Two profilations and save test
                self._progress_step = (1.0 - self._progress) / total_num_tasks

                if my_task.server.location is not None:
                    self._event_dispatcher.postEvent(
                        gui_event.UpdateEvent("Selezionato il server di misura di %s" % my_task.server.location,
                                              gui_event.UpdateEvent.MAJOR_IMPORTANCE))

                start_time = datetime.fromtimestamp(timestampNtp())

                tester = Tester(dev=dev, host=my_task.server, timeout=self._testtimeout)

                measure = Measure(self._client, start_time, my_task.server, ip, os, mac, self._version)

                profiler_result = self._profiler.profile_once({system_resource.RES_HOSTS, system_resource.RES_TRAFFIC})
                self._progress += self._progress_step
                self._event_dispatcher.postEvent(gui_event.ProgressEvent(self._progress))
                sleep(1)

                for t_type in test_types:
                    if not self._running:
                        # Has been interrupted
                        self._profiler.stop_background_profiling()
                        return
                    try:
                        sleep(1)
                        best_test = self._do_test(tester, t_type, my_task, profiler_result)
                        measure.savetest(best_test)  # Saves test in XML file
                        self._event_dispatcher.postEvent(gui_event.UpdateEvent("Elaborazione dei dati"))
                        if t_type == test_type.PING:
                            self._event_dispatcher.postEvent(gui_event.ResultEvent(t_type, best_test.proof.duration))
                        elif test_type.is_http(t_type):
                            self._event_dispatcher.postEvent(gui_event.ResultEvent(t_type,
                                                                                   (best_test.proof.bytes_tot * 8 /
                                                                                    float(best_test.proof.duration))))
                    except MeasurementException as e:
                        self._event_dispatcher.postEvent(gui_event.ErrorEvent("Errore durante il test: %s" % e.message))

                stop_time = datetime.fromtimestamp(timestampNtp())
                measure.savetime(start_time, stop_time)
                logger.debug(measure)

                # # Salvataggio della misura ##
                self._progress += self._progress_step
                self._event_dispatcher.postEvent(gui_event.ProgressEvent(self._progress))
                num_sent_files = result_sender.save_and_send_measure(measure, self._event_dispatcher, self._deliverer)
                if (num_sent_files > 0) and self._client.is_oneshot():
                    os.remove(paths.CONF_MAIN)
                self._event_dispatcher.postEvent(gui_event.ProgressEvent(1))
                # # Fine Salvataggio ##

            except Exception as e:
                logger.warning('Misura sospesa per eccezione: %s.' % e, exc_info=True)
                self._event_dispatcher.postEvent(gui_event.ErrorEvent('Misura sospesa per errore: %s' % e))

        self._profiler.stop_background_profiling()
        self._event_dispatcher.postEvent(gui_event.StopEvent(is_oneshot=self.is_oneshot()))
        self._running = False
