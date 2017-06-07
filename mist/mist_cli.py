# encoding: utf-8
# Copyright (c) 2016 Fondazione Ugo Bordoni.
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
"""
mist.mist_cli -- CLI version of Speedtest

mist.mist_cli is a network speed test


@author:     ewedlund

@copyright:  2015-2016 Fondazione Ugo Bordoni. All rights reserved.

@license:    GNU General Public License

@contact:    helpdesk@misurainternet.it
"""
import logging
import os
import platform
import signal
import sys
import thread
from threading import Event, Thread

import gui_event
import mist_messages
import test_type
from common._generated_version import __version__

logger = logging.getLogger(__name__)

DEFAULT_WIDTH = 80
DEFAULT_HEIGHT = 24


class bcolors(object):
    """
    Add some color to the output,
    disable for Windows
    """
    if not platform.system().lower().startswith('win'):
        PINK = '\033[95m'
        BLUE = '\033[94m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        ENDC = '\033[0m'
    else:
        PINK = ''
        BLUE = ''
        GREEN = ''
        YELLOW = ''
        RED = ''
        ENDC = ''


class MistCli(Thread):
    def __init__(self, event_dispatcher):
        Thread.__init__(self)
        self._event_dispatcher = event_dispatcher
        self._event_dispatcher.bind(gui_event.myEVT_UPDATE, self._on_update)
        self._event_dispatcher.bind(gui_event.myEVT_PROGRESS, self._on_progress)
        self._event_dispatcher.bind(gui_event.myEVT_RESULT, self._on_result)
        self._event_dispatcher.bind(gui_event.myEVT_ERROR, self._on_error)
        self._event_dispatcher.bind(gui_event.myEVT_RESOURCE, self._on_resource)
        self._event_dispatcher.bind(gui_event.myEVT_STOP, self._on_stop)
        self._event_dispatcher.bind(gui_event.myEVT_AFTER_CHECK, self._on_after_check)
        self._is_busy = False
        self._listener = None
        self._idle = Event()
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signal, frame):
        print 'Ctrl-C, exiting...'
        sys.exit(0)

    def set_listener(self, listener):
        self._listener = listener

    def run(self):
        self._print_greeting()
        self._idle.set()
        #         self._ask_for_input()
        self._do_loop()

    def _get_height_width(self):
        try:
            (height, width) = os.popen('stty size', 'r').read().split()
        except Exception:
            height = DEFAULT_HEIGHT
            width = DEFAULT_WIDTH
        return int(height), int(width)

    def _format_string(self, string, centered=True, frame='', color=None):
        (_, width) = self._get_height_width()
        if '\n' in string:
            raise Exception("Just one row at a time, please!")
        try:
            str_length = len(string)
        except Exception:
            print 'Could not get length!'
            return string
        if color is not None:
            string = color + string + bcolors.ENDC
        if (str_length + 4) > width:
            'TODO: split to several rows'
            pass
        else:
            if len(frame) > 0:
                space_to_fill = width - str_length - (len(frame) + 1) * 2
                frame_before = frame + " "
                frame_after = " " + frame
            else:
                space_to_fill = width - str_length
                frame_before = ''
                frame_after = ''
            if centered:
                num_spaces_before = space_to_fill / 2
                num_spaces_after = int(round(space_to_fill / 2.0))
            else:
                num_spaces_before = 0
                num_spaces_after = space_to_fill
            string = frame_before + ' ' * num_spaces_before + string + ' ' * num_spaces_after + frame_after
        return string

    def _on_update(self, update_event):
        if update_event.getImportance() == gui_event.UpdateEvent.MAJOR_IMPORTANCE:
            color = bcolors.BLUE
        else:
            color = None
        self._update_messages(update_event.getMessage(), color=color)

    def _on_progress(self, gui_event):
        pass

    def _on_resource(self, resource_event):
        if resource_event.getMessageFlag():
            try:
                info_string = str(resource_event.getValue().info)
                status = resource_event.getValue().status
                if status is not None:
                    color = None
                    info_string = '\t' + info_string
                elif status is True:
                    color = bcolors.GREEN
                    info_string = '[OK]\t' + info_string
                else:
                    color = bcolors.RED
                    info_string = '[WARN]\t' + info_string
                self._update_messages(info_string, color=color)
            except Exception:
                logger.error("Impossibile ottenere info dalla risorsa %s" % str(resource_event.getValue()))

    def _update_messages(self, message, color=None, font=None):
        logger.info('Messaggio all\'utente: "%s"' % message)
        if color:
            print color + message + bcolors.ENDC
        else:
            print message

    def _on_result(self, result_event):
        result_test_type = result_event.getType()
        result_value = result_event.getValue()
        color = bcolors.GREEN
        if result_test_type == test_type.PING:
            message = mist_messages.PING_RESULT % result_value
        elif result_test_type == test_type.FTP_DOWN:
            message = mist_messages.FTP_DOWN_RESULT % result_value
        elif result_test_type == test_type.FTP_UP:
            message = mist_messages.FTP_UP_RESULT % result_value
        elif test_type.is_http_down(result_test_type):
            message = "Download (HTTP): %.0f kbps" % result_value
        elif test_type.is_http_up(result_test_type):
            message = "Upload (HTTP): %.0f kbps" % result_value
        else:
            logger.error("Unknown result %s: %s" % (result_test_type, result_value))
            message = ""
        self._update_messages(message, color)

    def _on_error(self, error_event):
        self._update_messages(error_event.getMessage(), bcolors.RED)

    def _on_stop(self, stop_event):
        if stop_event.isOneShot():
            self._update_messages(">> MISURA TERMINATA <<\nPer la versione completa iscriviti su misurainternet.it",
                                  color=bcolors.GREEN)
            self._update_messages('''Per effettuare altre misure e conservare i tuoi risultati \
            nell'area riservata effettua l'iscrizione su misurainternet.it
            ''')
        else:
            self._update_messages(">> MISURA TERMINATA <<", color=bcolors.GREEN)
            self._update_messages("Sistema pronto per una nuova misura")
        self.set_busy(False)

    def _on_check(self):
        #         self._reset_info()
        self._update_messages(mist_messages.PROFILING)
        try:
            self._listener.check()
        except AttributeError:
            logger.error("Nessun listener adatto configurato, impossibile procedere")

    def _on_after_check(self, gui_event):
        pass

    def _on_play(self):
        try:
            self._listener.play()
        except AttributeError:
            logger.error("Nessun listener adatto configurato, impossibile procedere", exc_info=True)

    def _print_greeting(self):
        (height, width) = self._get_height_width()
        frame_row = '+' + ('-' * (width - 2)) + '+'
        print frame_row
        frame = '|'
        print self._format_string('', frame=frame)
        print self._format_string('Benvenuto in %s versione %s' % (mist_messages.SWN, __version__), frame=frame,
                                  color=bcolors.BLUE)
        print self._format_string('', frame=frame)
        print self._format_string('Premendo il tasto C avvierai la profilazione della macchina per la misura.',
                                  frame=frame, color=bcolors.YELLOW)
        print self._format_string('', frame=frame)
        print self._format_string('Premendo il tasto M avvierai una profilazione e il test di misura completo.',
                                  frame=frame, color=bcolors.GREEN)
        print self._format_string('', frame=frame)
        print self._format_string('Per uscire premere il tasto Q.', frame=frame, color=bcolors.RED)
        print self._format_string('', frame=frame)
        print frame_row

    def set_busy(self, busy=False):
        if busy:
            self._idle.clear()
        else:
            self._idle.set()

    def _do_loop(self):
        while True:
            try:
                self._idle.wait()
                line = raw_input('C(heck)/M(isura)/Q(uit)> ').lower()
            except KeyboardInterrupt:
                print "Keyboard Interrupt"
                thread.interrupt_main()
                break
            except EOFError:
                print ''
                break
            if 'q' in line:
                if self._listener:
                    self._listener.exit()
                break
            elif 'c' in line:
                self._on_check()
            elif 'm' in line:
                self._on_play()
