# nem_options.py
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
Created on 14/apr/2016

@author: ewedlund
"""

import hashlib
from ConfigParser import ConfigParser, NoOptionError
from optparse import OptionParser
from os import path

from common import client
from mist import paths


class MistOptions(object):
    def __init__(self, options, md5conf):
        self._client = client.getclient(options)
        self._scheduler = options.scheduler
        self._repository = options.repository
        self._tasktimeout = options.tasktimeout
        self._testtimeout = options.testtimeout
        self._httptimeout = options.httptimeout
        self._md5conf = md5conf

    def __str__(self, *args, **kwargs):
        s = ""
        s += "============================================\n"
        options_dict = self.__dict__
        for key in options_dict:
            s += "| %s : %s\n" % (key, options_dict[key])
        s += "============================================\n"
        return s

    @property
    def client(self):
        return self._client

    @property
    def scheduler(self):
        return self._scheduler

    @property
    def repository(self):
        return self._repository

    @property
    def tasktimeout(self):
        return self._tasktimeout

    @property
    def testtimeout(self):
        return self._testtimeout

    @property
    def httptimeout(self):
        return self._httptimeout

    @property
    def md5conf(self):
        return self._md5conf


def check_required(parser, opt):
    response = True
    option = parser.get_option(opt).dest
    # logger.debug(getattr(parser.values, option))
    if getattr(parser.values, option) is None:
        response = False
        parser.error('%s option not supplied' % option)
    return response


def parse(version, description=''):
    """
    Parsing dei parametri da linea di comando
    """

    config = ConfigParser()
    parser = OptionParser(version, description)
    'TODO: remove when fixed'
    parser.add_option("--task-file", dest="task_file",
                      help="read task from file [default: %default]", metavar="FILE")
    # parser.add_option("-t", "--text", dest="text_based", action="store_true",
    # help="Senza interfaccia grafica [default: %default]")
    parser.add_option("--no-profile", dest="no_profile", action="store_true",
                      help="Non profilare il sistema durante la misura [default: %default]")

    if path.exists(paths.CONF_MAIN):
        config.read(paths.CONF_MAIN)
    # logger.info('Caricata configurazione da %s' % paths.CONF_MAIN)

    # Task options
    # --------------------------------------------------------------------------
    section = 'task'
    if not config.has_section(section):
        config.add_section(section)

    option = 'tasktimeout'
    value = '3600'
    try:
        value = config.getint(section, option)
    except (ValueError, NoOptionError):
        config.set(section, option, value)
    parser.add_option('--task-timeout', dest=option, type='int', default=value,
                      help='global timeout (in seconds) for each task [%s]' % value)

    option = 'testtimeout'
    value = '60'
    try:
        value = config.getint(section, option)
    except (ValueError, NoOptionError):
        config.set(section, option, value)
    parser.add_option('--test-timeout', dest=option, type='float', default=value,
                      help='timeout (in seconds as float number) for each test in a task [%s]' % value)

    option = 'httptimeout'
    value = '60'
    try:
        value = config.getint(section, option)
    except (ValueError, NoOptionError):
        config.set(section, option, value)
    parser.add_option('--http-timeout', dest=option, type='int', default=value,
                      help='timeout (in seconds) for http operations [%s]' % value)

    option = 'scheduler'
    value = 'https://speedtest.agcom244.fub.it/Scheduler'
    try:
        value = config.get(section, option)
    except (ValueError, NoOptionError):
        config.set(section, option, value)
    parser.add_option('-s', '--scheduler', dest=option, default=value,
                      help='complete url for schedule download [%s]' % value)

    option = 'repository'
    value = 'https://speedtest.agcom244.fub.it/Upload'
    try:
        value = config.get(section, option)
    except (ValueError, NoOptionError):
        config.set(section, option, value)
    parser.add_option('-r', '--repository', dest=option, default=value,
                      help='upload URL for deliver measures\' files [%s]' % value)

    option = 'progressurl'
    value = 'https://speedtest.agcom244.fub.it/ProgressXML'
    try:
        value = config.get(section, option)
    except (ValueError, NoOptionError):
        config.set(section, option, value)
    parser.add_option('--progress-url', dest=option, default=value,
                      help='complete URL for progress request [%s]' % value)

    # Client options
    # --------------------------------------------------------------------------
    section = 'client'
    if not config.has_section(section):
        config.add_section(section)

    option = 'clientid'
    value = ''
    try:
        value = config.get(section, option)
    except (ValueError, NoOptionError):
        pass
    parser.add_option('-c', '--clientid', dest=option, default=value,
                      help='client identification string [%s]' % value)

    option = 'username'
    value = 'anonymous'
    try:
        value = config.get(section, option)
    except (ValueError, NoOptionError):
        config.set(section, option, value)
    parser.add_option('--username', dest=option, default=value,
                      help='username for FTP login [%s]' % value)

    option = 'password'
    value = '@anonymous'
    try:
        value = config.get(section, option)
    except (ValueError, NoOptionError):
        config.set(section, option, value)
    parser.add_option('--password', dest=option, default=value,
                      help='password for FTP login [%s]' % value)

    # Profile options
    # --------------------------------------------------------------------------
    section = 'profile'
    if not config.has_section(section):
        config.add_section(section)

    option = 'bandwidthup'
    value = 2048
    try:
        value = config.getint(section, option)
    except (ValueError, NoOptionError):
        pass
    parser.add_option('--up', dest=option, default=value, type='int',
                      help='upload bandwidth [%s]' % value)

    option = 'bandwidthdown'
    value = 2048
    try:
        value = config.getint(section, option)
    except (ValueError, NoOptionError):
        pass
    parser.add_option('--down', dest=option, default=value, type='int',
                      help='download bandwidth [%s]' % value)

    # Isp options
    # --------------------------------------------------------------------------
    section = 'isp'
    if not config.has_section(section):
        config.add_section(section)

    option = 'ispid'
    value = 'fub001'
    try:
        value = config.get(section, option)
    except (ValueError, NoOptionError):
        pass
    parser.add_option('--ispid', dest=option, default=value,
                      help='ISP id [%s]' % value)

    with open(paths.CONF_MAIN, 'w') as f:
        config.write(f)

    (options, args) = parser.parse_args()

    # Verifica che le opzioni obbligatorie siano presenti
    # --------------------------------------------------------------------------

    try:

        if not check_required(parser, '--clientid'):
            config.set('client', 'clientid', options.clientid)

        if not check_required(parser, '--up'):
            config.set('profile', 'bandwidthup', options.bandwidthup)

        if not check_required(parser, '--down'):
            config.set('profile', 'bandwidthdown', options.bandwidthdown)

    finally:
        with open(paths.CONF_MAIN, 'w') as f:
            config.write(f)

    with open(paths.CONF_MAIN, 'r') as f:
        md5 = hashlib.md5(f.read()).hexdigest()

    return options, args, md5
