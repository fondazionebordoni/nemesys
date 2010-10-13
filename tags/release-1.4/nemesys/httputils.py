# httputils.py
# -*- coding: utf8 -*-

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
#
# This code is derived from: recipe-146306-1.py by Wade Leftwich
# Licensed under the Python Software Foundation License
# Original version by Wade Leftwich:
#   -> http://code.activestate.com/recipes/146306-http-client-to-post-using-multipartform-data/

import httplib, mimetypes

def post_multipart(url, fields, files, certificate=None, timeout=60):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return the server's response page.
    """
    content_type, body = encode_multipart_formdata(fields, files)

    # TODO Aggiungere verifica certificato server
    if (url.scheme != 'https'):
      h = httplib.HTTPConnection(host=url.hostname, timeout=timeout) 
    elif (certificate != None):
      h = httplib.HTTPSConnection(host=url.hostname, key_file=certificate, cert_file=certificate, timeout=timeout)
    else:
      h = httplib.HTTPSConnection(host=url.hostname, timeout=timeout)

    h.putrequest('POST', url.path)
    h.putheader('content-type', content_type)
    h.putheader('content-length', str(len(body)))
    h.endheaders()
    h.send(body)
    #errcode, errmsg, headers = h.getreply()
    #return h.file.read()
    return h.getresponse().read()

def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []

    if fields != None:
      for (key, value) in fields:
          L.append('--' + BOUNDARY)
          L.append('Content-Disposition: form-data; name="%s"' % key)
          L.append('')
          L.append(value)

    if files != None:
      for (key, filename, value) in files:
          L.append('--' + BOUNDARY)
          L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
          L.append('Content-Type: %s' % get_content_type(filename))
          L.append('')
          L.append(value)

    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
