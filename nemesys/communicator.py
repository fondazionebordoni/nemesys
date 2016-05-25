'''
Created on 13/mag/2016

@author: ewedlund
'''
import asyncore
import logging
import socket
from threading import Thread
import threading


logger = logging.getLogger(__name__)


class Communicator(Thread):

    def __init__(self):
        Thread.__init__(self)
        self._channel = _Channel(('127.0.0.1', 21401))

    def sendstatus(self, current_status):
        self._channel.sendstatus(current_status)

    def run(self):
        asyncore.loop(5)
        logger.debug('Nemesys asyncore loop terminated.')

    def join(self, timeout = None):
        self._channel.quit()
        Thread.join(self, timeout)


class _Channel(asyncore.dispatcher):

    def __init__(self, url):
        asyncore.dispatcher.__init__(self)
        self._last_status = None
        self._lock = threading.Lock()
        self._url = url
        self._sender = None
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(self._url)
        self.listen(1)

    def sendstatus(self, current_status):
        with self._lock:
            if self._sender:
                self._sender.write(current_status)
            else:
                #TODO: save status in queue to send later
                self._last_status = current_status

    def handle_accept(self):
        (channel, _) = self.accept()
        self._sender = _Sender(channel)
        if self._last_status != None:
            self.sendstatus(self._last_status)

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
            status = status.Status(status.ERROR, 'Errore di decodifica unicode')
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


