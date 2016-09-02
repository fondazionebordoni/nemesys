# httpclient.py
# -*- coding: utf-8 -*-
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
Minimal httpclient so that we can set
TCP window size
"""

import logging
import socket
import threading
import urlparse


END_STRING = '_ThisIsTheEnd_'

logger = logging.getLogger(__name__)


class HttpException(Exception):

    def __init__(self, message):
        Exception.__init__(self, message)
        self._message = message.decode('utf-8')

    @property
    def message(self):
        return self._message


class HttpClient():

    def __init__(self):
        self._http_response = None

    def post(self, url, headers=None, tcp_window_size=None,
             data_source=None, timeout=18):
        self._response_received = False
        self._read_timeout = False
        url_res = urlparse.urlparse(url)
        server = url_res.hostname
        port = url_res.port
        if not port:
            port = 80
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if (tcp_window_size is not None) and (tcp_window_size > 0):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, tcp_window_size)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, tcp_window_size)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        try:
            s.connect((server, port))
        except:
            raise HttpException("Impossibile connettersi al server %s sulla porta %d" % (server, port))
        post_request = "POST /misurainternet.txt HTTP/1.0\r\n"
        if (tcp_window_size is not None) and (tcp_window_size > 0):
            post_request = "%s%s:%s\r\n" % (post_request,
                                            "X-Tcp-Window-Size",
                                            tcp_window_size)
        for header in headers.items():
            post_request = "%s%s:%s\r\n" % (post_request, header[0], header[1])
        post_request = "%s\r\n" % post_request
        s.send(post_request)
        receive_thread = threading.Thread(target=self._read_response,
                                          args=(s,))
        receive_thread.start()
        timeout_timer = threading.Timer(float(timeout), self._timeout)
        timeout_timer.start()
        bytes_sent = 0
        if data_source is not None:
            for data_chunk in data_source:
                if self._response_received or self._read_timeout:
                    logger.debug("Received response or timeout, stop sending")
                    try:
                        if not self._read_timeout:
                            s.send(END_STRING*2)
                        s.shutdown(socket.SHUT_RDWR)
                        s.close()
                    except socket.error:
                        pass
                    break
                if not data_chunk:
                    try:
                        s.send("0\r\n")
                        s.send("\r\n")
                    except socket.error:
                        pass
                    break
                try:
                    chunk_size = len(data_chunk)
                    bytes_sent += s.send("%s\r\n" % hex(chunk_size)[2:])
                    bytes_sent += s.send("%s\r\n" % data_chunk)
                except:
                    pass
        logger.debug("sent %d bytes" % bytes_sent)
        receive_thread.join()
        timeout_timer.cancel()
        return self._http_response

    def _timeout(self):
        self._read_timeout = True

    def _read_response(self, sock):
        all_data = ""
        start_body_found = False
        sock.settimeout(2.0)

        while not self._read_timeout:
                try:
                    data = sock.recv(1)
                    if data is not None:
                        all_data = "%s%s" % (all_data, data)
                    if '[' in data:
                        start_body_found = True
                    if ']' in data and start_body_found:
                        self._response_received = True
                        break
                except socket.timeout:
                    pass
                except:
                    break
        if all_data and '\n' in all_data:
            lines = all_data.split('\n')
            try:
                response = lines[0].strip().split()
                response_code = int(response[1])
                response_cause = ' '.join(response[2:])
            except:
                logger.error("Could not parse response %s" % all_data)
                response_code = 999
                response_cause = "Risposta dal server non HTTP"
            i = 1
            # Find an empty line, the content is what comes after
            content = ""
            while i < len(lines):
                if lines[i].strip() == "":
                    content = lines[i + 1:][0]
                    break
                i += 1
        else:
            response_code = 999
            response_cause = "Nessuna risposta dal server"
            content = ""
        self._http_response = HttpResponse(response_code,
                                           response_cause,
                                           content)


class HttpResponse(object):
    '''Read from socket and parse something like this

    HTTP/1.1 200 OK
    Content-Type: text/plain;charset=ISO-8859-1
    Content-Length: 81
    Server: Jetty(8.1.16.v20140903)

    [11758564,11691628,11771232,11656120,11534992,11603564,11724892,11764052,11781776]
    '''
    def __init__(self, response_code, response_cause, content):
        self._response_code = response_code
        self._response_cause = response_cause
        self._content = content

    def __str__(self, *args, **kwargs):
        my_str = "Response code: %d\n" % self._response_code
        my_str += "Response cause: %s\n" % self._response_cause
        my_str += "Response content: %s\n" % self._content
        return my_str
        return object.__str__(self, *args, **kwargs)

    @property
    def status_code(self):
        return self._response_code

    @property
    def status(self):
        return self._response_cause

    @property
    def content(self):
        return self._content

    def close(self):
            pass
