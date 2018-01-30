# backend_response.py
# -*- coding: utf8 -*-
# Copyright (c) 2018 Fondazione Ugo Bordoni.
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

import logging

import xmltodict

logger = logging.getLogger(__name__)


def parse(data):
    """
    Valuta l'XML ricevuto dal backend, restituisce il codice e il messaggio ricevuto
    """
    try:
        xml_dict = xmltodict.parse(data)
        response_dict = xml_dict['response']
        message = response_dict.get('message') or ''
        code = response_dict.get('code') or 999
    except Exception:
        logger.error('Ricevuto risposta non XML dal server: %s', data)
        code = 999
        message = ''
    return int(code), message

