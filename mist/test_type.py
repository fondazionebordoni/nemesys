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
Created on 08/ott/2015

@author: ewedlund
"""

'''Global test types'''
PING = 1
FTP_UP = 2
FTP_DOWN = 3
HTTP_UP = 4
HTTP_DOWN = 5

STRING_TYPES = {PING: "ping",
                #                 FTP_UP: "ftp upload",
                #                 FTP_DOWN: "ftp download",
                HTTP_UP: "http upload",
                HTTP_DOWN: "http download"
                }
STRING_TYPES_SHORT = {PING: "ping",
                      #                 FTP_UP: "ftp up",
                      #                 FTP_DOWN: "ftp down",
                      HTTP_UP: "http up",
                      HTTP_DOWN: "http down"
                      }


def get_string_type(from_type):
    if from_type in STRING_TYPES:
        return STRING_TYPES[from_type]
    else:
        return "Tipo di misura sconosciuta"


def get_string_type_short(from_type):
    if from_type in STRING_TYPES_SHORT:
        return STRING_TYPES_SHORT[from_type]
    else:
        return "sconosciuta"


def get_xml_string(from_type):
    if is_http_up(from_type):
        return "upload_http"
    elif is_http_down(from_type):
        return "download_http"
    elif is_ftp_up(from_type):
        return "upload"
    elif is_ftp_down(from_type):
        return "download"
    elif is_ping(from_type):
        return "ping"
    else:
        return "unknown"


def is_http(from_type):
    if "http" in get_string_type_short(from_type):
        return True
    return False


def is_http_up(from_type):
    if "http up" in get_string_type_short(from_type):
        return True
    return False


def is_http_down(from_type):
    if "http down" in get_string_type_short(from_type):
        return True
    return False


def is_ftp_up(from_type):
    if "ftp up" in get_string_type_short(from_type):
        return True
    return False


def is_ftp_down(from_type):
    if "ftp down" in get_string_type_short(from_type):
        return True
    return False


def is_ping(from_type):
    if "ping" in get_string_type_short(from_type):
        return True
    return False
