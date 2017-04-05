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
from threading import Thread
import threading
import tornado.web
from tornado.websocket import WebSocketHandler
import urlparse

import paths


logger = logging.getLogger(__name__)

WEBSOCKET_PORT = 54201

# Error codes in nem_exceptions
NO_ERROR = 0
MAX_NOTIFICATIONS = 10
DATE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
RES_TRANSLATION = {'Wireless': 'wifistatus',
                   'Ethernet': 'ethstatus',
                   'Hosts': 'hoststatus',
                   'CPU': 'cpustatus',
                   'RAM': 'ramstatus'}


class DummyGuiServer(object):
    def start(self):
        pass

    def stop(self, timeout=None):
        pass

    def nem_start(self, version, log_dir):
        pass

    def notification(self, error_code, message=''):
        pass

    def speed(self, value):
        pass

    def profilation(self, done=False):
        pass

    def sys_res(self, res, status, info):
       pass

    def wait(self, seconds, message):
        pass

    def result(self, test_type, result=None, spurious=None, error=None):
        pass

    def test(self, test_type, n_tests, n_tot, retry):
        pass

    def measure(self, test_type, bw=None):
        pass


class Communicator(Thread):
    """ Thread di esecuzione del websocket server.
        Invia status alla gui.
    """
    def __init__(self, serial, version):
        Thread.__init__(self)
        self.application = tornado.web.Application([(r'/ws', GuiWebSocket)])
        self.ioLoop = tornado.ioloop.IOLoop.current()
        self.ioLoop.make_current()
        self._last_status = None
        self._lock = threading.Lock()
        self._serial = serial
        global start_msg
        start_msg = GuiMessage(GuiMessage.START,
                               {'version': str(version),
                                'logdir': paths.LOG_DIR}
                               ).dict()

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

    def stop(self, timeout=None):
        logger.info("stopping ioloop")
        self.ioLoop.stop()
        logger.info("joining thread")
        Thread.join(self, timeout)

    def nem_start(self, version, log_dir):
        '''messaggio iniziale con informazioni su Nemesys'''
        msg = GuiMessage(GuiMessage.START, {'version': str(version),
                                            'logdir': str(log_dir)})
        self.sendstatus(msg)

    def notification(self, error_code, message=''):
        '''For errors and notifications'''
        dt = datetime.datetime.now()
        msg = GuiMessage(GuiMessage.NOTIFICATION,
                         {'datetime': dt.strftime(DATE_TIME_FORMAT),
                          'error_code': error_code,
                          'message': message})
        self.sendstatus(msg)

    def speed(self, value):
        msg = GuiMessage(GuiMessage.TACHOMETER,
                         {'value': value})
        self.sendstatus(msg)

    def profilation(self, done=False):
        '''Start or end of system profilation'''
        msg = GuiMessage(GuiMessage.PROFILATION,
                         {'done': done})
        self.sendstatus(msg)

    def sys_res(self, res, status, info):
        '''messaggio per informazione su una risorsa durante la profilazione'''
        msg = GuiMessage(GuiMessage.SYS_RESOURCE,
                         {'resource': RES_TRANSLATION[res],
                          'state': status,
                          'info': info})
        self.sendstatus(msg)

    def wait(self, seconds, message):
        '''Nemesys is pausing for <seconds> seconds'''
        msg = GuiMessage(GuiMessage.WAIT,
                         {'seconds': seconds,
                          'message': message})
        self.sendstatus(msg)

    def result(self, test_type, result=None, spurious=None, error=None):
        contents = {}
        if error is not None:
            contents.update({'test_type': test_type, 'error': error})
        else:
            contents.update({'test_type': test_type, 'result': result})
            if spurious is not None:
                contents.update({'spurious': spurious})
        msg = GuiMessage(GuiMessage.RESULT, content=contents)
        self.sendstatus(msg)

    def test(self, test_type, n_tests, n_tot, retry):
        '''Signals the start of a test'''
        msg = GuiMessage(GuiMessage.TEST,
                         {'test_type': test_type,
                          'n_test': n_tests,
                          'n_tot': n_tot,
                          'retry': retry})
        self.sendstatus(msg)

    def measure(self, test_type, bw=None):
        '''Signals the start of a measurement'''
        if bw is not None:
            msg = GuiMessage(GuiMessage.MEASURE,
                             {'test_type': test_type,
                              'bw': bw})
        else:
            msg = GuiMessage(GuiMessage.MEASURE,
                             {'test_type': test_type})
        self.sendstatus(msg)

    def sendstatus(self, status):
        logger.info("Sending status [%s]" % status)
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

    START = 'start'
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
        return "%s, message: %s" % (self.message_type, self.content)


handler_lock = threading.Lock()
handlers = []
start_msg = None
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
        # Strip port number if present from netloc
        cleaned_netloc = parsed_origin.netloc.split(':')[0]
        if (cleaned_netloc == '127.0.0.1') or (cleaned_netloc == 'localhost'):
            return True
        if ((cleaned_netloc == 'misurainternet.it') or
                (cleaned_netloc.endswith('.misurainternet.it')) or
                (cleaned_netloc.endswith('.fub.it'))):
            return True
        return False

    def open(self):
        with handler_lock:
            handlers.append(self)
            logger.info("server open connection")

    def send_msg(self, msg):
        try:
            jsonString = json.dumps(msg)
            self.write_message(jsonString)
        except Exception as e:
            logger.error("Could not send message [%s] to GUI: %s" % (msg, e))

    def on_message(self, message):
        msg_dict = json.loads(message)
        logger.info("Got message %s", (msg_dict))
        if (msg_dict['request'] == 'currentstatus'):
            if start_msg is not None:
                self.send_msg(start_msg)
            if last_status is not None:
                self.send_msg(last_status)
            for status in list(last_notifications):
                self.send_msg(status)

    def on_close(self):
        with handler_lock:
            handlers.remove(self)
            logger.info("server close connection")
