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
'''
Created on 12/ott/2015

@author: ewedlund
'''

import logging
import os
import threading
import wx
from collections import deque
from datetime import datetime

from common import paths
from mist import gui_event
from mist import mist_messages
from mist import test_type
from mist.system_resource import SystemResource, RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_HOSTS, RES_TRAFFIC

TOTAL_STEPS = 1000
MY_BLUE = (0x13, 0x45, 0x8f)

logger = logging.getLogger(__name__)


class mistGUI(wx.Frame):
    def __init__(self, *args, **kwds):

        wx.Frame.__init__(self, *args, **kwds)
        self._busy = False
        self._can_measure = True
        self._writer_lock = threading.Lock()

    def make_left_header_panel(self, panel_header):
        dc = wx.ScreenDC()
        result_font = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        dc.SetFont(result_font)
        w, h = dc.GetTextExtent('X')
        panel_header_left = wx.Panel(panel_header, -1)
        panel_header_left.SetBackgroundColour((0x13, 0x45, 0x8f))
        bitmap_header_left = wx.StaticBitmap(panel_header_left, -1,
                                             wx.Bitmap(os.path.join(paths.ICONS, u"logo_mist.png"), wx.BITMAP_TYPE_ANY),
                                             style=wx.NO_BORDER)
        label_ping = wx.StaticText(panel_header_left, -1, "Ping", style=wx.ALIGN_LEFT)
        label_ping.SetMinSize((w * 8, h))
        label_ping.SetForegroundColour('white')
        label_ping.SetBackgroundColour(MY_BLUE)
        label_http_down = wx.StaticText(panel_header_left, -1, "Download", style=wx.ALIGN_LEFT)
        label_http_down.SetForegroundColour('white')
        label_http_down.SetBackgroundColour(MY_BLUE)
        label_http_down.SetMinSize((w * 10, h))
        label_http_up = wx.StaticText(panel_header_left, -1, "Upload", style=wx.ALIGN_LEFT)
        label_http_up.SetForegroundColour('white')
        label_http_up.SetBackgroundColour(MY_BLUE)
        label_http_up.SetMinSize((w * 10, h))
        self.label_ping_res = wx.StaticText(panel_header_left, -1, "- - - -", style=wx.ALIGN_LEFT)
        self.label_ping_res.SetForegroundColour('white')
        self.label_ping_res.SetFont(result_font)
        self.label_http_down_res = wx.StaticText(panel_header_left, -1, "- - - -", style=wx.ALIGN_LEFT)
        self.label_http_down_res.SetForegroundColour('white')
        self.label_http_down_res.SetFont(result_font)
        self.label_http_up_res = wx.StaticText(panel_header_left, -1, "- - - -", style=wx.ALIGN_LEFT)
        self.label_http_up_res.SetForegroundColour('white')
        self.label_http_up_res.SetFont(result_font)
        grid_sizer_results = wx.FlexGridSizer(2, 3, 0, 0)
        grid_sizer_results.Add(label_ping, 0, wx.TOP | wx.LEFT | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND, 20)
        grid_sizer_results.Add(label_http_down, 0, wx.TOP | wx.LEFT | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND, 20)
        grid_sizer_results.Add(label_http_up, 0, wx.TOP | wx.LEFT | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND, 20)
        grid_sizer_results.Add(self.label_ping_res, 0, wx.TOP | wx.LEFT | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND, 20)
        grid_sizer_results.Add(self.label_http_down_res, 0, wx.TOP | wx.LEFT | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND,
                               20)
        grid_sizer_results.Add(self.label_http_up_res, 0, wx.TOP | wx.LEFT | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND, 20)
        grid_sizer_results.SetMinSize((300, 122))
        sizer_header_left = wx.BoxSizer(wx.HORIZONTAL)
        sizer_header_left.Add(bitmap_header_left, 0, wx.LEFT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL,
                              30)
        sizer_header_left.Add(grid_sizer_results, 0, wx.ALIGN_CENTER_HORIZONTAL, 0)
        panel_header_left.SetSizerAndFit(sizer_header_left)
        return panel_header_left

    def make_right_header_panel(self, panel_header):
        panel_header_right = wx.Panel(panel_header, -1)
        panel_header_right.SetBackgroundColour('white')
        bitmap_header_right = wx.StaticBitmap(panel_header_right, -1,
                                              wx.Bitmap(os.path.join(paths.ICONS, u"logo_mist_end.png"),
                                                        wx.BITMAP_TYPE_ANY))
        self.button_play = wx.Button(panel_header_right, -1, label="TEST")
        self.button_check = wx.Button(panel_header_right, -1, label="CHECK")
        self.button_play.SetToolTip(wx.ToolTip("Avvia la profilazione e una misura completa"))
        self.button_check.SetToolTip(wx.ToolTip("Avvia la profilazione della macchina"))
        box_sizer_buttons = wx.BoxSizer(wx.VERTICAL)
        box_sizer_buttons.Add(self.button_check, 0,
                              wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        box_sizer_buttons.Add(self.button_play, 0,
                              wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer_header_right = wx.BoxSizer(wx.HORIZONTAL)
        sizer_header_right.Add(bitmap_header_right, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL)
        sizer_header_right.Add(box_sizer_buttons, 0, wx.RIGHT | wx.ALIGN_CENTER, 10)
        sizer_header_right.SetMinSize((-1, 45))
        panel_header_right.SetSizerAndFit(sizer_header_right)
        return panel_header_right

    def make_main_panel(self, window_panel):
        'TODO: this is from the old layout, should rewrite'
        panel_main = wx.Panel(window_panel)
        panel_main.SetBackgroundColour("white")
        self.gauge = wx.Gauge(panel_main, -1, TOTAL_STEPS, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.bitmap_cpu = wx.StaticBitmap(panel_main, -1,
                                          wx.Bitmap(os.path.join(paths.ICONS, u"%s_gray.png" % RES_CPU.lower()),
                                                    wx.BITMAP_TYPE_ANY))
        self.bitmap_ram = wx.StaticBitmap(panel_main, -1,
                                          wx.Bitmap(os.path.join(paths.ICONS, u"%s_gray.png" % RES_RAM.lower()),
                                                    wx.BITMAP_TYPE_ANY))
        self.bitmap_eth = wx.StaticBitmap(panel_main, -1,
                                          wx.Bitmap(os.path.join(paths.ICONS, u"%s_gray.png" % RES_ETH.lower()),
                                                    wx.BITMAP_TYPE_ANY))
        self.bitmap_wifi = wx.StaticBitmap(panel_main, -1,
                                           wx.Bitmap(os.path.join(paths.ICONS, u"%s_gray.png" % RES_WIFI.lower()),
                                                     wx.BITMAP_TYPE_ANY))
        self.bitmap_hosts = wx.StaticBitmap(panel_main, -1,
                                            wx.Bitmap(os.path.join(paths.ICONS, u"%s_gray.png" % RES_HOSTS.lower()),
                                                      wx.BITMAP_TYPE_ANY))
        self.bitmap_traffic = wx.StaticBitmap(panel_main, -1,
                                              wx.Bitmap(os.path.join(paths.ICONS, u"%s_gray.png" % RES_TRAFFIC.lower()),
                                                        wx.BITMAP_TYPE_ANY))
        self.label_cpu = wx.StaticText(panel_main, -1, "%s\n- - - -" % RES_CPU, style=wx.ALIGN_CENTRE)
        self.label_ram = wx.StaticText(panel_main, -1, "%s\n- - - -" % RES_RAM, style=wx.ALIGN_CENTRE)
        self.label_eth = wx.StaticText(panel_main, -1, "%s\n- - - -" % RES_ETH, style=wx.ALIGN_CENTRE)
        self.label_wifi = wx.StaticText(panel_main, -1, "%s\n- - - -" % RES_WIFI, style=wx.ALIGN_CENTRE)
        self.label_hosts = wx.StaticText(panel_main, -1, "%s\n- - - -" % RES_HOSTS, style=wx.ALIGN_CENTRE)
        self.label_traffic = wx.StaticText(panel_main, -1, "%s\n- - - -" % RES_TRAFFIC, style=wx.ALIGN_CENTRE)
        grid_sizer_system_indicators = wx.FlexGridSizer(2, 6, 0, 0)
        grid_sizer_system_indicators.Add(self.bitmap_cpu, 0,
                                         wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 24)
        grid_sizer_system_indicators.Add(self.bitmap_ram, 0,
                                         wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 24)
        grid_sizer_system_indicators.Add(self.bitmap_eth, 0,
                                         wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 24)
        grid_sizer_system_indicators.Add(self.bitmap_wifi, 0,
                                         wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 24)
        grid_sizer_system_indicators.Add(self.bitmap_hosts, 0,
                                         wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 24)
        grid_sizer_system_indicators.Add(self.bitmap_traffic, 0,
                                         wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 24)
        grid_sizer_system_indicators.Add(self.label_cpu, 0,
                                         wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 24)
        grid_sizer_system_indicators.Add(self.label_ram, 0,
                                         wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 24)
        grid_sizer_system_indicators.Add(self.label_eth, 0,
                                         wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 24)
        grid_sizer_system_indicators.Add(self.label_wifi, 0,
                                         wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 24)
        grid_sizer_system_indicators.Add(self.label_hosts, 0,
                                         wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 24)
        grid_sizer_system_indicators.Add(self.label_traffic, 0,
                                         wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 24)
        self.messages_text = wx.TextCtrl(panel_main, -1, "",
                                         style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
                                         | wx.TE_BESTWRAP | wx.BORDER_NONE)
        sizer_main_window = wx.BoxSizer(wx.VERTICAL)
        sizer_messages_area = wx.StaticBoxSizer(wx.StaticBox(panel_main, -1, "Messaggi"), wx.VERTICAL)
        sizer_system_status = wx.BoxSizer(wx.VERTICAL)
        sizer_messages_area.Add(self.messages_text, 90, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND, 4)
        sizer_system_status.Add(grid_sizer_system_indicators, 0,
                                wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 8)
        sizer_main_window.Add(self.gauge, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND,
                              2)
        sizer_main_window.Add(sizer_messages_area, 90,
                              wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND, 4)
        sizer_main_window.Add(sizer_system_status, 0,
                              wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL | wx.EXPAND, 4)
        panel_main.SetSizer(sizer_main_window)
        return panel_main

    def init_frame(self, version, event_dispatcher):
        self._version = version
        self._event_dispatcher = event_dispatcher
        self._tester = None
        self._stream = deque([], maxlen=800)

        window_panel = wx.Panel(self)
        window_panel.SetBackgroundColour('white')

        panel_header = wx.Panel(window_panel, -1)
        panel_header_left = self.make_left_header_panel(panel_header)
        panel_header_right = self.make_right_header_panel(panel_header)

        sizer_header = wx.BoxSizer(wx.HORIZONTAL)
        sizer_header.Add(panel_header_left, 80, wx.TOP, 1)
        sizer_header.Add(panel_header_right, 20, wx.TOP, 1)
        panel_header.SetSizerAndFit(sizer_header)

        panel_main = self.make_main_panel(window_panel)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel_header, 0, wx.EXPAND)
        sizer.Add(panel_main, 90, wx.EXPAND)

        window_panel.SetSizerAndFit(sizer)
        # TODO: find out why sizer_main_window ends up being 808 pixels wide
        self.SetSize((810, 460))

        self.SetTitle("%s - versione %s" % (mist_messages.SWN, self._version))
        self.messages_text_style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_BESTWRAP | wx.BORDER_NONE

        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_BUTTON, self._on_play, self.button_play)
        self.Bind(wx.EVT_BUTTON, self._on_check, self.button_check)

        self.Bind(gui_event.EVT_UPDATE, self._on_update)
        self.Bind(gui_event.EVT_PROGRESS, self._on_progress)
        self.Bind(gui_event.EVT_RESULT, self._on_result)
        self.Bind(gui_event.EVT_ERROR, self._on_error)
        self.Bind(gui_event.EVT_RESOURCE, self._on_resource)
        self.Bind(gui_event.EVT_STOP, self._on_stop)

        self._initial_message()
        self.Layout()

    def _on_close(self, event):
        # TODO: handle in controller?
        logger.info("Richiesta di close")
        if self._busy:
            dlg = wx.MessageDialog(self, "\nVuoi davvero chiudere %s?" % mist_messages.SWN, mist_messages.SWN,
                                   wx.OK | wx.CANCEL | wx.ICON_QUESTION)
            res = dlg.ShowModal()
            dlg.Destroy()
            if res != wx.ID_OK:
                return
            if self._listener:
                self._listener.kill_test()
            self.Unbind(gui_event.EVT_UPDATE)
            self.Unbind(gui_event.EVT_PROGRESS)
            self.Unbind(gui_event.EVT_RESULT)
            self.Unbind(gui_event.EVT_ERROR)
            self.Unbind(gui_event.EVT_RESOURCE)
            self.Unbind(gui_event.EVT_STOP)
        if self._listener:
            self._listener.exit()
        self.Destroy()

    def _on_play(self, gui_event):
        self._reset_info()
        try:
            self._listener.play()
        except AttributeError:
            logger.error("Nessun listener adatto configurato, impossibile procedere", exc_info=True)

    def _on_check(self, gui_event):
        self._reset_info()
        self._update_messages(mist_messages.PROFILING, 'black', font=(12, 93, 92, 1))
        try:
            self._listener.check()
        except AttributeError:
            logger.error("Nessun listener adatto configurato, impossibile procedere")

    def _update_http_down(self, downwidth):
        self.label_http_down_res.SetLabel("%.0f kbps" % downwidth)
        self.Layout()

    def _update_http_up(self, upwidth):
        self.label_http_up_res.SetLabel("%.0f kbps" % upwidth)
        self.Layout()

    def _update_ping(self, rtt):
        self.label_ping_res.SetLabel("%.1f ms" % rtt)
        self.Layout()

    def _reset_info(self):
        checkable_set = {RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_HOSTS, RES_TRAFFIC}

        for resource in checkable_set:
            self._set_resource_info(resource, SystemResource(None, None, None, None))

        self.label_http_up_res.SetLabel("- - - -")
        self.label_http_down_res.SetLabel("- - - -")
        self.label_ping_res.SetLabel("- - - -")

        self.messages_text.Clear()
        self._update_gauge(0)
        self.Layout()

    def _on_progress(self, gui_event):
        try:
            self._update_gauge(gui_event.getValue())
        except:
            pass

    def _update_gauge(self, value_in_percent):
        '''Update absolute value in percent'''
        gauge_len = self.gauge.GetRange()
        real_value = int(value_in_percent * gauge_len) + 1
        if real_value > gauge_len:
            real_value = gauge_len
        self.gauge.SetValue(real_value)

    def _increment_gauge(self, value_in_percent):
        '''Increment with value in percent'''
        gauge_len = self.gauge.GetRange()
        current_val = self.gauge.GetValue()
        increment = int(value_in_percent * gauge_len) + 1
        new_val = current_val + increment
        if new_val > gauge_len:
            new_val = gauge_len
        self.gauge.SetValue(new_val)

    def _on_resource(self, resource_event):
        self._set_resource_info(resource_event.getResource(), resource_event.getValue(),
                                resource_event.getMessageFlag())

    def _set_resource_info(self, resource, info, message_flag=True):
        res_bitmap = None
        res_label = None
        try:
            if info.status is None:
                colour = 'gray'
            elif info.status is True:
                colour = 'green'
            else:
                colour = 'red'
        except AttributeError:
            logger.critical("res %s" % info, exc_info=True)
            colour = 'gray'
        if resource == RES_CPU:
            res_bitmap = self.bitmap_cpu
            res_label = self.label_cpu
        elif resource == RES_RAM:
            res_bitmap = self.bitmap_ram
            res_label = self.label_ram
        elif resource == RES_ETH:
            res_bitmap = self.bitmap_eth
            res_label = self.label_eth
        elif resource == RES_WIFI:
            res_bitmap = self.bitmap_wifi
            res_label = self.label_wifi
        elif resource == RES_HOSTS:
            res_bitmap = self.bitmap_hosts
            res_label = self.label_hosts
        elif resource == RES_TRAFFIC:
            res_bitmap = self.bitmap_traffic
            res_label = self.label_traffic

        if (res_bitmap is not None):
            res_bitmap.SetBitmap(wx.Bitmap(os.path.join(paths.ICONS, u"%s_%s.png" % (resource.lower(), colour))))

        if (res_label is not None):
            if (info.value is not None):
                if resource == RES_ETH or resource == RES_WIFI:
                    status = {-1: "Not Present", 0: "Off Line", 1: "On Line"}
                    res_label.SetLabel("%s\n%s" % (resource, status[info.value]))
                elif resource == RES_CPU or resource == RES_RAM:
                    res_label.SetLabel("%s\n%.1f%%" % (resource, float(info.value)))
                else:
                    res_label.SetLabel("%s\n%s" % (resource, info.value))
            else:
                res_label.SetLabel("%s\n- - - -" % resource)

        if message_flag:
            if info.info is not None:
                self._update_messages(info.info, colour)

        self.Layout()

    def _on_update(self, update_event):
        if update_event.getImportance() == gui_event.UpdateEvent.MAJOR_IMPORTANCE:
            font = (12, 93, 92, 1)
        else:
            font = None
        self._update_messages(update_event.getMessage(), font=font)

    def _update_messages(self, message, colour='black', font=None, fill=False):
        logger.info('Messaggio all\'utente: "%s"' % message)
        self._stream.append((str(message), colour, font, fill))
        #            if (system().lower().startswith('win')):
        #                writer = Thread(target = self._writer)
        #                writer.start()
        #            else:
        self._writer()

    def _on_result(self, result_event):
        result_test_type = result_event.getType()
        result_value = result_event.getValue()
        if result_event.isIntermediate():
            self._handle_intermediate_result(result_test_type, result_value)
        else:
            font = (12, 93, 92, 1)
            color = 'green'
            if result_test_type == test_type.PING:
                message = mist_messages.PING_RESULT % result_value
                update_method = self._update_ping
            elif test_type.is_http_down(result_test_type):
                message = "Download (HTTP): %.0f kbps" % result_value
                update_method = self._update_http_down
            elif test_type.is_http_up(result_test_type):
                message = "Upload (HTTP): %.0f kbps" % result_value
                update_method = self._update_http_up
            else:
                logger.error("Unknown result %s: %s" % (result_test_type, result_value))
                message = ''
            self._update_messages(message, color, font)
            update_method(result_value)

    def _handle_intermediate_result(self, res_test_type, value):
        if test_type.is_http_down(res_test_type):
            self._update_http_down(value)
        elif test_type.is_http_up(res_test_type):
            self._update_http_up(value)
        elif test_type.is_ping(res_test_type):
            self._update_ping(value)

    def _on_error(self, error_event):
        logger.info("Got error gui_event")
        self._update_messages(error_event.getMessage(), 'red')

    def _on_stop(self, stop_event):
        if self._busy:
            if self._listener:
                self._listener.kill_test()
            self._update_messages("Misura terminata\n", 'medium forest green', (12, 93, 92, 1), True)
            if (stop_event.isOneShot()):
                self._update_messages(
                    "Per effettuare altre misure e conservare i tuoi risultati nell'area riservata "
                    "effettua l'iscrizione su misurainternet.it\n",
                    'black', (12, 90, 92, 0), True)
            else:
                self._update_messages("Sistema pronto per una nuova misura", 'black', (12, 90, 92, 0), True)
            self.set_busy(False, stop_event.isOneShot())
            self._update_gauge(1)

    # TODO: simplify
    def _writer(self):
        with self._writer_lock:
            while (len(self._stream) > 0):
                basic_font = wx.Font(pointSize=10,
                                     family=wx.FONTFAMILY_DEFAULT,
                                     style=wx.NORMAL,
                                     weight=wx.NORMAL,
                                     underline=0,
                                     face="")
                words = {}
                (message, colour, font, fill) = self._stream.popleft()
                date = datetime.today().strftime('%a %d/%m/%Y %H:%M:%S')
                last_pos = self.messages_text.GetLastPosition()
                self.messages_text.SetWindowStyleFlag(self.messages_text_style)
                date += "    "
                text = "" + date
                words[date] = (colour, wx.NullColour, basic_font)
                text = text + message
                if fill:
                    textcolour = colour
                else:
                    textcolour = 'black'
                words[message] = (textcolour, wx.NullColour, basic_font)
                self.messages_text.AppendText(text + '\n')
                self.messages_text.SetInsertionPoint(last_pos + 1)
                self.messages_text.ScrollLines(-1)

    def _initial_message(self):

        message = ('''Benvenuto in {} versione {}

            Premendo il tasto CHECK avvierai la profilazione della macchina per la misura.

            Premendo il tasto TEST avvierai una profilazione e il test di misura completo.'''
                   .format(mist_messages.SWN, self._version))

        self.messages_text.SetWindowStyleFlag(self.messages_text_style + wx.TE_CENTER)

        self.messages_text.AppendText(message)
        self.messages_text.ScrollLines(-1)

        font1 = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_BOLD)
        font2 = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, 1, "")
        word1 = "Benvenuto in %s versione %s" % (mist_messages.SWN, self._version)
        words = {word1: (wx.NullColour, wx.NullColour, font1), 'CHECK': (MY_BLUE, wx.NullColour, font2),
                 'TEST': ('green', wx.NullColour, font2)}

        self._set_style(message, words)

        self.Layout()

    def _set_style(self, message, words, offset=0):
        for word in words:
            start = message.find(word) + offset
            end = start + len(word)
            style = words[word]
            self.messages_text.SetStyle(start, end, wx.TextAttr(*style))

    def set_listener(self, listener):
        self._listener = listener

    def set_busy(self, is_busy, is_oneshot=False):
        if is_busy:
            self.button_play.Disable()
            self.button_check.Disable()
            self._busy = True
        else:
            self.button_check.Enable()
            if self._can_measure:
                if is_oneshot:
                    self._can_measure = False
                else:
                    self.button_play.Enable()
            self._busy = False
