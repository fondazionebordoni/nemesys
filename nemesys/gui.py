# gui.py
# -*- coding: utf-8 -*-

# Copyright (c) 2010 Fondazione Ugo Bordoni.
#
# This program is free software: you can greyistribute it and/or modify
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

from asyncore import dispatcher, loop
from datetime import datetime
from logger import logging
from os import path
from progress import Progress
from status import Status
from sys import platform
from threading import Event, Thread
from time import sleep
from timeNtp import timestampNtp
from xmlutils import xml2status
import HTMLParser
import paths
import re
import socket
import status
import wx

LISTENING_URL = ('127.0.0.1', 21401)
NOTIFY_COLORS = ('yellow', 'black')
WAIT_RECONNECT = 15 # secondi
logger = logging.getLogger()

def sleeper():
        sleep(.001)
        return 1 # don't forget this otherwise the timeout will be removed

class _Controller(Thread):

    def __init__(self, url, trayicon):
        Thread.__init__(self)
        self._channel = _Channel(url, trayicon)
        self._trayicon = trayicon
        self._running = True

    def run(self):
        logger.debug('Inizio loop')
        # TODO Verificare al fattibilità di ricollegamento della gui al demone
        '''
        while self._running:
            loop(1)
        '''
        loop(1)
        logger.debug('GUI asyncore loop terminated.')

    def join(self, timeout = None):
        logger.debug('Richiesta di close')
        self._running = False
        self._channel.quit()
        Thread.join(self, timeout)

class _Channel(dispatcher):

    def __init__(self, url, trayicon):
        dispatcher.__init__(self)
        self._trayicon = trayicon
        self._url = url
        self._stopevent = Event()
        self._reconnect()

    def handle_connect(self):
        pass

    def writable(self):
        return False    # don't have anything to write

    def quit(self):
        logger.debug('Quitting channel.')
        self._stopevent.set()
        self.close()

    def _reconnect(self):
        if not self._stopevent.isSet():
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connect(self._url)

    def handle_error(self):
        logger.debug('Error. Closing client socket.')
        try:
            wx.CallAfter(self._trayicon.setstatus, status.ERROR)
        except Exception as e:
            logger.error('Errore durante l\'aggiornamento dello stato %s' % e)

        self.handle_close()
        self._stopevent.wait(WAIT_RECONNECT)
        self._reconnect()

    def handle_close(self):
        self.close()

    def handle_read(self):
        data = self.recv(2048)
        logger.debug('Received: %s' % data)

        # TODO Correggere dialogo su socket
        try:
                start = max(data.rfind('<?xml'), 0)
                current_status = xml2status(data[start:])
        except Exception as e:
                logger.error('Errore durante la decodifica dello stato del sistema di misura: %s' % e)
                current_status = Status(status.ERROR, '%s' % e)

        if current_status == None:
                current_status = Status(status.ERROR, 'Errore di comunicazione con il server.')

        logger.debug('Metto l\'aggiornamento dello stato nella coda grafica')
        try:
            wx.CallAfter(self._trayicon.setstatus, current_status)
        except Exception as e:
            logger.error('Errore durante l\'aggiornamento dello stato %s' % e)

class MyFrame (wx.Frame):

    def __init__(self):

        # Base e gestione stato
        self._status = Status(status.ERROR, "error")
        xmldoc = Progress(True)
        #da qui modifico la dimensione della finestra FRAME
        wx.Frame.__init__ (self, None, id = wx.ID_ANY, title = 'Nemesys', pos = wx.DefaultPosition, size = wx.Size(750, 500), style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.RESIZE_BOX))
        self.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        bSizer2 = wx.BoxSizer(wx.VERTICAL)

        bSizer3 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_bitmap1 = wx.StaticBitmap(self, wx.ID_ANY, wx.Bitmap(path.join(paths.ICONS, u"logo_misurainternet.png"), wx.BITMAP_TYPE_ANY), wx.DefaultPosition, wx.DefaultSize, 0)
        bSizer3.Add(self.m_bitmap1, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        bSizer4 = wx.BoxSizer(wx.VERTICAL)

        self.label_nemesys = wx.StaticText(self, wx.ID_ANY, u"Nemesys", wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTRE)
        self.label_nemesys.Wrap(-1)
        self.label_nemesys.SetFont(wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD, False))
        bSizer4.Add(self.label_nemesys, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 2)

        self.label_startmeasures = wx.StaticText(self, wx.ID_ANY, u"Inizio test di misura: %s" % xmldoc.start().strftime('%c'), wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTRE)
        self.label_startmeasures.Wrap(-1)
        bSizer4.Add(self.label_startmeasures, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 2)

        label = u"La misurazione va completata entro tre giorni dal suo inizio\n"
        if platform == 'darwin':
            label = "%s\n" % label
        self.label_helper = wx.StaticText(self, wx.ID_ANY, label, wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTRE)
        self.label_helper.Wrap(-1)
        bSizer4.Add(self.label_helper, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 2)

        self.label_avanzamento = wx.StaticText(self, wx.ID_ANY, u"Stato di avanzamento: 0 test su 24", wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTRE)
        self.label_avanzamento.Wrap(-1)
        bSizer4.Add(self.label_avanzamento, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 2)

        self.label_fasce = wx.StaticText(self, wx.ID_ANY, u"Dettaglio misure per fasce orarie:", wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTRE)
        self.label_fasce.Wrap(-1)
        bSizer4.Add(self.label_fasce, 0, wx.TOP | wx.ALIGN_CENTER_HORIZONTAL, 2)

        bSizer3.Add(bSizer4, 1, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND, 5)

        self.m_bitmap2 = wx.StaticBitmap(self, wx.ID_ANY, wx.Bitmap(path.join(paths.ICONS, u"logo_nemesys.png"), wx.BITMAP_TYPE_ANY), wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_CENTRE)
        bSizer3.Add(self.m_bitmap2, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        bSizer2.Add(bSizer3, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND, 5)

        self._grid = wx.GridSizer(2, 24, 0, 0)

        for i in range(0, 24):
            self.m_staticText5 = wx.StaticText(self, wx.ID_ANY, u"%s" % i, wx.DefaultPosition, wx.DefaultSize, 0)
            self.m_staticText5.Wrap(-1)
            self._grid.Add(self.m_staticText5, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)

        for i in range (0, 24):
            self.m_bitmap17 = wx.StaticBitmap(self, wx.ID_ANY, wx.Bitmap(path.join(paths.ICONS, "grey.png"), wx.BITMAP_TYPE_ANY), wx.DefaultPosition, wx.DefaultSize, 0)
            self._grid.Add(self.m_bitmap17, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)

        bSizer2.Add(self._grid, 0, wx.ALIGN_CENTER_HORIZONTAL, 2)
        ##############
        #INSERIRE QUI LA PROGRESS BAR
        self.label_teststatus = wx.StaticText(self, wx.ID_ANY, "Avanzamento della misura in corso", wx.DefaultPosition, wx.DefaultSize, 0)
        self.label_teststatus.Wrap(-1)
        bSizer2.Add(self.label_teststatus, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)

        #bSizer5 = wx.BoxSizer(wx.HORIZONTAL)
        #self.fillspace1 = wx.StaticText(self, wx.ID_ANY, " ", wx.DefaultPosition, wx.DefaultSize, 0)
        #self.fillspace1.Wrap(-1)
        #bSizer5.Add(self.fillspace1, 0, wx.ALL | wx.ALIGN_LEFT, 15)
        #self.gauge = wx.Gauge(self, -1, 100, wx.DefaultPosition, wx.DefaultSize, wx.GA_HORIZONTAL)
        self.gauge = wx.Gauge(self, -1, 100, wx.DefaultPosition, wx.Size(660, 25), wx.GA_HORIZONTAL)
        bSizer2.Add(self.gauge, 0, wx.ALIGN_CENTER_HORIZONTAL, 10)
        #bSizer5.Add(self.gauge, 1, wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND, 10)
        self.fillspace2 = wx.StaticText(self, wx.ID_ANY, " ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.fillspace2.Wrap(-1)
        bSizer2.Add(self.fillspace2, 0, wx.EXPAND, 5)

        #bSizer2.Add(bSizer5, 0 , wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND, 5)
        self.gauge.SetValue(0)
        ##############
        sbSizer1 = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, u"Dettaglio di stato di Nemesys"), wx.VERTICAL)

        date = '%s' % getdate().strftime('%c')
        self.messages_area = wx.TextCtrl(self, wx.ID_ANY, "%s Sto contattando il servizio di misura attendere qualche secondo." % date, wx.DefaultPosition, wx.DefaultSize, wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH | wx.TE_RICH2 | wx.TE_WORDWRAP | wx.NO_BORDER | wx.VSCROLL)
        sbSizer1.Add(self.messages_area, 1, wx.ALL | wx.EXPAND, 5)
        self.messages_area.SetStyle(0, len(date), wx.TextAttr(status.PAUSE.color))

        bSizer2.Add(sbSizer1, 1, wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND, 5)

        self.SetSizer(bSizer2)
        self.m_menubar1 = wx.MenuBar()
        self.menu = wx.Menu()

        menu_info = wx.MenuItem(self.menu, wx.ID_ABOUT, u"&Info", u"Informazioni sul programma", wx.ITEM_NORMAL)
        self.menu.AppendItem(menu_info)

        menu_exit = wx.MenuItem(self.menu, wx.ID_EXIT, u"&Exit", u"Chiudi il programma", wx.ITEM_NORMAL)
        self.menu.AppendItem(menu_exit)

        self.m_menubar1.Append(self.menu, u"Menu")

        self.SetMenuBar(self.m_menubar1)

        self.Centre(wx.BOTH)
        self.Layout()

        # Connect Events
        self.Bind(wx.EVT_MENU, self.menu_info, menu_info)
        self.Bind(wx.EVT_MENU, self.menu_exit, menu_exit)
        self.PaintInit(None)

        self._controller = _Controller(LISTENING_URL, self)
        self._controller.start()


    def menu_exit(self, event):
        self._controller.join()
        self.Close(True)

    def menu_info(self, event):
        dlg = wx.MessageDialog(self, "Nemesys (Network Measurement System)\nHomepage del progetto: www.misurainternet.it\nCopyright (c) 2010-2011 Fondazione Ugo Bordoni \nEmail: info@fub.it", "Info", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def PaintInit(self, event):

        xmldoc = Progress(True)

        n = 0
        for hour in range(0, 24):
                color = "grey"
                if xmldoc.isdone(hour):
                        color = "green"
                        n = n + 1
                self.PaintHour(hour, color)

        #logger.debug('Aggiorno lo stato di avanzamento')
        if (n != 0):
            self.label_avanzamento.SetLabel('Stato di avanzamento: %d test su 24' % n)
        else:
            self.label_avanzamento.SetLabel('Stato di avanzamento: nessun test effettuato su 24')

    def setstatus(self, currentstatus):
        '''
        Aggiorna il messaggio nel system tray, l'aggiornamento viene
        fatto solo se lo staus è cambiato, ovvero se è cambiata il
        messaggio.
        '''
        logger.debug('Inizio aggiornamento stato')
        if (self._status.message != currentstatus.message):

            hour = getdate().hour
            logger.debug('Ora attuale: %d' % hour)

            if (bool(re.search(status.PLAY.color, currentstatus.color)) or bool(re.search('Misura in esecuzione', currentstatus.message))):
                self.PaintInit(None)
                self.PaintHour(hour, "yellow")
            if (bool(re.search('Misura sospesa', currentstatus.message))):
                self.PaintInit(None)
                self.PaintHour(hour, "red")
            elif (bool(re.search('Misura terminata|Misura interrotta', currentstatus.message))):
                self.PaintInit(None)
                self.gauge.SetValue(0)
                self.label_teststatus.SetLabel("Avanzamento della misura in corso")
            elif (bool(re.search('Avviso', currentstatus.message))):
                self.label_helper.SetForegroundColour(currentstatus.color)
                self.label_helper.SetLabel("Hai ricevuto un avviso dal server centrale!\nLeggi il messaggio nella finestra del dettaglio di stato di Nemesys")
            elif (bool(re.search(status.FINISHED.message, currentstatus.message))):
                self.label_helper.SetForegroundColour(currentstatus.color)
                self.label_helper.SetLabel("Misura completa! Visita la tua area personale sul sito\nwww.misurainternet.it per scaricare il certificato di misura.")
            #aggiornamento del GAUGE
            elif (bool(re.search('Esecuzione Test', currentstatus.message))):
                    try:
                            msg = str(currentstatus.message)
                            elem = msg.split()
                            now = int(elem[2])
                            ntot = int(elem[4])
                            perc = round((now * 100) / ntot)
                            self.gauge.SetValue(perc)
                            self.label_teststatus.SetLabel("Avanzamento della misura in corso: %d%%" % perc)
                    except Exception as e:
                            logger.error('Errore nello status corrente di aggiornamento Gauge: %s' % e)

            message = self.getformattedmessage(currentstatus.message)
            date = '\n%s' % getdate().strftime('%c')
            self.messages_area.AppendText("%s %s" % (date, message))
            end = self.messages_area.GetLastPosition() - len(message)
            start = end - len(date)
            self.messages_area.SetStyle(start, end, wx.TextAttr(currentstatus.color))

            self._status = currentstatus
            self.Layout()

    def getformattedmessage(self, message):
        logger.debug('Instanzio HTMLParser')
        htmlmessage = HTMLParser.HTMLParser()

        logger.debug('Messaggio prima di unescape: %s' % message)
        message = htmlmessage.unescape(message)
        logger.debug('Messaggio dopo unescape: %s' % message)
        message = message.replace('(\'', '')
        message = message.replace('\')', '')
        message = message.replace('\n', ' ')
        message = message.replace('\', \'', '')

        logger.debug('Messaggio da stampare a video: %s' % message)
        return message

    def PaintHour(self, hour, color):
        '''
        Aggiorna la casella allora specificata con il colore specificatio
        '''
        #logger.debug('PaintHour: %d, %s' % (hour, color))
        old = self._grid.GetItem(24 + hour).GetWindow()
        bmp = wx.StaticBitmap(self, wx.ID_ANY, wx.Bitmap(path.join(paths.ICONS, "%s.png" % color), wx.BITMAP_TYPE_ANY), wx.DefaultPosition, wx.DefaultSize, 0)
        self._grid.Replace(old, bmp)
        old.Destroy()
        self.Layout()

def getdate():
    return datetime.fromtimestamp(timestampNtp())

if __name__ == '__main__':
    app = wx.App(False)
    if platform == 'win32':
        wx.CallLater(200, sleeper)
    frame = MyFrame()
    frame.Show()
    app.MainLoop()
