# gui_server.py
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

import collections
import datetime
import json
import logging
import os
import subprocess
from threading import Thread
import threading
import tornado.web
from tornado.websocket import WebSocketHandler
import urlparse

import utils
import paths


logger = logging.getLogger(__name__)

WEBSOCKET_PORT = 54201

#Error codes in nem_exceptions
NO_ERROR = 0
MAX_NOTIFICATIONS = 10
DATE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

class Communicator(Thread):
    """ Thread di esecuzione del websocket server.
        Invia status alla gui.
    """
    def __init__(self, serial):
        Thread.__init__(self)
        self.application = tornado.web.Application([(r'/ws', GuiWebSocket)])
        self.ioLoop = tornado.ioloop.IOLoop.current()
        self.ioLoop.make_current()
        self._last_status = None
        self._lock = threading.Lock()
        self._serial = serial

    def run(self):
        try:
            self.application.listen(WEBSOCKET_PORT)
            self.ioLoop.start()
            # close() viene eseguito solo dopo che start esce dal loop,
            # ovvero dopo che riceve il comando stop(). Rilascia le risorse.
            self.ioLoop.close(all_fds=True)
            logger.info('closed ioLoop')
        except Exception as e:
            logger.error("Could not open websocket: %s" % (e))

    #TODO: Questo non viene mai chiamato - verificare chiusura Nemesys
    def join(self, timeout=None):
        logger.info("stopping ioloop")
        self.ioLoop.stop()
        logger.info("joining thread")
        Thread.join(self, timeout)

    def sendstatus(self, status):
        with self._lock:
            status_dict = status.dict()
            status_dict['serial'] = self._serial
            if status.is_notification:
                global last_notifications
                last_notifications.append(status_dict)
                if len(last_notifications) > MAX_NOTIFICATIONS:
                    last_notifications.popleft()
            else:
                global last_status
                last_status = status_dict
            global handler_lock
            with handler_lock:
                for handler in handlers:
                    try:
                        handler.send_msg(status_dict)
                    except Exception as e:
                        logger.warn("Could not send message to GUI: %s" % (e))

class GuiMessage(object):

    SYS_RESOURCE = 'sys_resource'
    PROFILATION = 'profilation'
    MEASURE = 'measure'
    TEST = 'test'
    NOTIFICATION = 'notification'
    WAIT = 'wait'
    TACHOMETER = 'tachometer'
    RESULT = 'result'

    def __init__(self, message_type, content=None):
        self.message_type = message_type
        self.content = content

    @property
    def is_notification(self):
        return self.message_type == self.NOTIFICATION

    def dict(self):
        return {'type': self.message_type, 'content': self.content}

    def __str__(self):
        return "Type: %s, message: %s" % (self.message_type, self.content)

def gen_sys_resource_message(res, status, info=''):
    '''messaggio per informazione su una risorsa durante la profilazione'''
    res_translation = {'Wireless': 'wifistatus',\
                      'Ethernet': 'ethstatus',\
                      'Hosts': 'hoststatus',\
                      'CPU': 'cpustatus',\
                      'RAM': 'ramstatus'}
    return GuiMessage(GuiMessage.SYS_RESOURCE, {'resource': res_translation[res], 'state': status, 'info': info})

def gen_profilation_message(done=False):
    '''Start of system profilation'''
    return GuiMessage(GuiMessage.PROFILATION, {'done': done})

def gen_wait_message(seconds, message=''):
    '''Nemesys is pausing for <seconds> seconds'''
    return GuiMessage(GuiMessage.WAIT, {'seconds': seconds, 'message': message})

def gen_notification_message(error_code=NO_ERROR, message=''):
    '''For errors and notifications'''
    dt = datetime.datetime.now()
    return GuiMessage(GuiMessage.NOTIFICATION, {'datetime': dt.strftime(DATE_TIME_FORMAT), 'error_code': error_code, 'message': message})

def gen_measure_message(test_type, bw=None):
    '''Signals the start of a measurement'''
    if bw != None:
        return GuiMessage(GuiMessage.MEASURE, {'test_type': test_type, 'bw': bw})
    else:
        return GuiMessage(GuiMessage.MEASURE, {'test_type': test_type})

def gen_test_message(test_type, n_test=0, n_tot=0, retry=False):
    '''Signals the start of a test'''
    return GuiMessage(GuiMessage.TEST, {'test_type': test_type, 'n_test': n_test, 'n_tot': n_tot, 'retry': retry})

def gen_tachometer_message(value):
    return GuiMessage(GuiMessage.TACHOMETER, {'value': value})

def gen_result_message(test_type, result = None, spurious=None, error=None):
    contents = {}
    if error != None:
        contents.update({'test_type': test_type, 'error': error})
    else:
        contents.update({'test_type': test_type, 'result':result})
        if spurious != None:
            contents.update({'spurious': spurious})
    return GuiMessage(GuiMessage.RESULT, content=contents)


handler_lock = threading.Lock()
handlers = []
last_status = None
last_notifications = collections.deque()

class GuiWebSocket(WebSocketHandler):
    """ Handler per una connessione.
        gestisce le richieste e le risposte.
    """

    def check_origin(self, origin):
        logger.info("GUI connecting from: %s" % (origin))
        if not origin:
            return True
        parsed_origin = urlparse.urlparse(origin)
        if (not parsed_origin.netloc) or (parsed_origin.scheme == 'file'):
            return True
        if (parsed_origin.netloc == '127.0.0.1') or (parsed_origin.netloc == 'localhost'):
            return True
        if parsed_origin.netloc.endswith('.misurainternet.it') or parsed_origin.netloc.endswith('.fub.it'):
            return True
        return False

    def open(self):
        with handler_lock:
            handlers.append(self)  # si aggiunge alla lista degli handler attivi,
            logger.info("server open connection")  # a cui inviare aggiornamenti

    def send_msg(self, msg):
        jsonString = json.dumps(msg)
        logger.info("Sending string %s" % jsonString)
        self.write_message(jsonString)

    def on_message(self, message):
        # TODO: wake up executer? When?
        msg_dict = json.loads(message)
        logger.info("Got message %s", (msg_dict))
#         if (msg_dict['request'] == 'log'):
#             self.openLogFolder()
#         elif (msg_dict['request'] == 'stop'):  # per ora chiude unicamente la websocket
#             self.close(code=1000)  # TODO gestire chiusura applicazione Ne.Me.Sys.
        if (msg_dict['request'] == 'currentstatus'):
            if last_status != None:
                self.send_msg(last_status)
            for status in list(last_notifications):
                self.send_msg(status)


    def openLogFolder(self):
#         if hasattr(sys, 'frozen'):
#             # trova il path del file in esecuzione.
#             # commentati i "+ sep + '..'" perche portavano nella cartella superiore.
#             d = path.dirname(sys.executable)   # + sep + '..'
#         else:
#             d = path.abspath(path.dirname(__file__))  # + sep + '..'
#
#         d = path.normpath(d)
        d = paths.LOG_DIR
        logger.info("Opening log file: %s" % (d))
        if utils.is_windows():
            os.startfile(d)
        elif utils.is_darwin():
            subprocess.Popen(['open', d])
        elif utils.is_linux():
            subprocess.Popen(['xdg-open', d])

    def on_close(self):
        with handler_lock:
            handlers.remove(self) # si rimuove dalla lista degli handler attivi
            logger.info("server close connection")
