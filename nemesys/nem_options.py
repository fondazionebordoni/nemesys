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
Created on 13/mag/2016

@author: ewedlund
"""

import hashlib
import logging
import os
from ConfigParser import ConfigParser, NoOptionError
from optparse import OptionParser

from nemesys import paths

logger = logging.getLogger(__name__)


def check_required(parser, opt):
    option = parser.get_option(opt)
    if getattr(parser.values, option.dest) is None:
        parser.error('%s option not supplied' % option)


def parse_args(version):
    """
    Parsing dei parametri da linea di comando
    """

    config = ConfigParser()

    if os.path.exists(paths.CONF_MAIN):
        config.read(paths.CONF_MAIN)
        logger.info('Caricata configurazione da %s' % paths.CONF_MAIN)

    parser = OptionParser(version=version, description='')
    parser.add_option('--task', dest='task',
                      help='path of an xml file with a task to execute (valid only if -T option is enabled)')

    # System options
    # --------------------------------------------------------------------------
    section = 'options'
    if not config.has_section(section):
        config.add_section(section)

    # System options
    # --------------------------------------------------------------------------
    section = 'system'
    if not config.has_section(section):
        config.add_section(section)

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

    option = 'repository'
    value = 'https://finaluser.agcom244.fub.it/Upload'
    try:
        value = config.get(section, option)
    except (ValueError, NoOptionError):
        config.set(section, option, value)
    parser.add_option('-r', '--repository', dest=option, default=value,
                      help='upload URL for deliver measures\' files [%s]' % value)

    option = 'scheduler'
    value = 'https://finaluser.agcom244.fub.it/Scheduler'
    try:
        value = config.get(section, option)
    except (ValueError, NoOptionError):
        config.set(section, option, value)
    parser.add_option('-s', '--scheduler', dest=option, default=value,
                      help='complete url for schedule download [%s]' % value)

    option = 'httptimeout'
    value = '60'
    try:
        value = config.getint(section, option)
    except (ValueError, NoOptionError):
        config.set(section, option, value)
    parser.add_option('--http-timeout', dest=option, type='int', default=value,
                      help='timeout (in seconds) for http operations [%s]' % value)

    option = 'polling'
    value = '300'
    try:
        value = config.getint(section, option)
    except (ValueError, NoOptionError):
        config.set(section, option, value)
    parser.add_option('--polling-time', dest=option, type='int', default=value,
                      help='polling time in seconds between two scheduling requests [%s]' % value)

    # Client options
    # --------------------------------------------------------------------------
    section = 'client'
    if not config.has_section(section):
        config.add_section(section)

    option = 'clientid'
    value = None
    try:
        value = config.get(section, option)
    except (ValueError, NoOptionError):
        pass
    parser.add_option('-c', '--clientid', dest=option, default=value,
                      help='client identification string [%s]' % value)

    option = 'geocode'
    value = None
    try:
        value = config.get(section, option)
    except (ValueError, NoOptionError):
        logger.warning('Nessuna specifica geocode inserita.')
        pass
    parser.add_option('-g', '--geocode', dest=option, default=value,
                      help='geocode identification string [%s]' % value)

    # Profile options
    # --------------------------------------------------------------------------
    section = 'profile'
    if not config.has_section(section):
        config.add_section(section)

    option = 'profileid'
    value = None
    try:
        value = config.get(section, option)
    except (ValueError, NoOptionError):
        pass
    parser.add_option('-p', '--profileid', dest=option, default=value,
                      help='profile identification string [%s]' % value)

    option = 'bandwidthup'
    value = None
    try:
        value = config.getint(section, option)
    except (ValueError, NoOptionError):
        pass
    parser.add_option('--up', dest=option, default=value, type='int',
                      help='upload bandwidth [%s]' % value)

    option = 'bandwidthdown'
    value = None
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
    value = None
    try:
        value = config.get(section, option)
    except (ValueError, NoOptionError):
        pass
    parser.add_option('--ispid', dest=option, default=value,
                      help='isp identification string [%s]' % value)

    option = 'certificate'
    value = None
    try:
        value = config.get(section, option)
        if not os.path.exists(value):
            config.remove_option(section, option)
            logger.warning('Trovata configurazione di certificato non esistente su disco. Cambiata configurazione')
            value = None
    except (ValueError, NoOptionError):
        logger.warning('Nessun certificato client specificato.')
        pass
    parser.add_option('--certificate', dest=option, default=value,
                      help='client certificate for schedule downloading and measure file signing [%s]' % value)

    with open(paths.CONF_MAIN, 'w') as f:
        config.write(f)

    (options, args) = parser.parse_args()

    # Verifica che le opzioni obbligatorie siano presenti
    # --------------------------------------------------------------------------

    try:

        check_required(parser, '--clientid')
        config.set('client', 'clientid', options.clientid)

        check_required(parser, '--up')
        config.set('profile', 'bandwidthup', options.bandwidthup)

        check_required(parser, '--down')
        config.set('profile', 'bandwidthdown', options.bandwidthdown)

        check_required(parser, '--profileid')
        config.set('profile', 'profileid', options.profileid)

        check_required(parser, '--ispid')
        config.set('isp', 'ispid', options.ispid)

    finally:
        with open(paths.CONF_MAIN, 'w') as f:
            config.write(f)

    with open(paths.CONF_MAIN, 'r') as f:
        md5 = hashlib.md5(f.read()).hexdigest()

    return options, args, md5
