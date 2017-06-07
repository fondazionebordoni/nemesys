#!/usr/bin/env python
# -*- coding: utf-8 -*-
# nem_options.py
#
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

import ctypes
import logging
import os
import platform
import sys
import wx
from optparse import OptionParser
from time import sleep

from common._generated_version import __version__, FULL_VERSION, __updated__
import gui_event
import mist_cli
import mist_gui
import mist_options
import paths
import sysmonitor
from check_software import CheckSoftware
from mist_controller import MistController

logger = logging.getLogger(__name__)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    '''Command line options.'''
    program_name = os.path.basename(sys.argv[0])
    program_version = __version__
    program_build_date = "%s" % __updated__
    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)
    program_longdesc = ''''''

    # TODO: Needs fixing, mixup with optionParser.OptionParser
    # , description=program_license)
    parser = OptionParser(version=program_version_string, epilog=program_longdesc)
    parser.add_option("-t", "--text", dest="text_based", action="store_true",
                      help="Senza interfaccia grafica [default: %default]")
    parser.set_defaults(text_based=False)
    (args_opts, _) = parser.parse_args(argv)

    ''' Check for sudo on linux and Administrator on Windows'''
    current_os = platform.system().lower()
    if current_os.startswith('lin') or current_os.startswith('darwin'):
        if (os.getenv('SUDO_USER') is None) and (os.getenv('USER') != 'root'):
            is_admin = False
        else:
            is_admin = True
    else:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    # TODO: Avoid need for admin for creation of log files etc.
    # So we can move this check to later
    if not is_admin:
        sys.stderr.write('Speedtest avviato senza permessi di amministratore - chiusura tester\n')
        if not args_opts.text_based:
            # Display window with message
            app = wx.App(False)
            msgBox = wx.MessageDialog(None,
                                      "\nSpeedtest e' stato avviato senza i permessi di amministratore.\n\n"
                                      "Su sistemi Linux e MacOS va avviato da linea di comando con 'sudo'",
                                      "Attenzione: Speedtest non puo' essere avviato",
                                      style=wx.OK)
            msgBox.ShowModal()
            msgBox.Destroy()
        sys.exit()

    try:
        paths.check_paths()
        import log_conf
        log_conf.init_log()
    except IOError:
        print ("Impossibile inizializzare il logging, assicurarsi che il programma stia girando con "
               "i permessi di amministratore.")
        sys.exit()

    try:
        sysmonitor.SysMonitor().log_interfaces()
    except Exception as e:
        logger.error("Impossibile trovare interfaccia attiva: %s" % e)
        if args_opts.text_based:
            print "Impossibile trovare un interfaccia di rete attiva, verificare la connessione alla rete."
        else:
            app = wx.App(False)
            msgBox = wx.MessageDialog(None,
                                      "\nImpossibile trovare un interfaccia di rete attiva, "
                                      "verificare la connessione alla rete.",
                                      style=wx.OK)
            msgBox.ShowModal()
            msgBox.Destroy()
        sys.exit()

    try:
        SWN = 'MisuraInternet Speed Test'
        logger.info('Starting %s v.%s' % (SWN, FULL_VERSION))
        #         mist(args_opts.text_based, file_opts, md5conf)
        version = __version__
        if not args_opts.text_based:
            app = wx.App(False)

            # Check if this is the last version
            version_ok = CheckSoftware(version).check_it()

            if not version_ok:
                return
        (file_opts, _, md5conf) = mist_options.parse(version)
        mist_opts = mist_options.MistOptions(file_opts, md5conf)
        if args_opts.text_based:
            event_dispatcher = gui_event.CliEventDispatcher()
            GUI = mist_cli.MistCli(event_dispatcher)
            controller = MistController(GUI, version, event_dispatcher, mist_opts)
            GUI.set_listener(controller)
            GUI.start()
        else:
            if platform.system().lower().startswith('win'):
                wx.CallLater(200, sleeper)
            GUI = mist_gui.mistGUI(None, -1, "",
                                   style=wx.DEFAULT_FRAME_STYLE)
            event_dispatcher = gui_event.WxGuiEventDispatcher(GUI)
            controller = MistController(GUI, version, event_dispatcher, mist_opts)
            GUI.init_frame(version, event_dispatcher)
            GUI.set_listener(controller)
            app.SetTopWindow(GUI)
            GUI.Show()
            app.MainLoop()
    except Exception, e:
        logging.critical("Impossibile avviare il programma", exc_info=True)
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        return 2


def sleeper():
    sleep(.001)
    return 1  # don't forget this otherwise the timeout will be removed


if __name__ == "__main__":
    main()
