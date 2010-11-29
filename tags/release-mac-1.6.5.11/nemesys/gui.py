# gui.py
# -*- coding: utf-8 -*-

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

from asyncore import dispatcher, loop
from datetime import datetime
from locale import LC_ALL, setlocale
from logger import logging
from os import path
from progress import Progress
from status import Status
from threading import Event, Thread
from time import sleep
from xmlutils import xml2status
import HTMLParser
import paths
import re
import socket
import status
import wx

filenames = [path.join(paths.ICONS, 'logo_nemesys.png'), path.join(paths.ICONS, 'logo_misurainternet.png')]

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

    def join(self, timeout=None):
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
        return False  # don't have anything to write

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
        self._trayicon.setstatus(status.ERROR)
        self.handle_close()
        self._stopevent.wait(WAIT_RECONNECT)
        self._reconnect()

    def handle_close(self):
        self.close()

    def handle_read(self):
        data = self.recv(2048)
        logger.debug('Received: %s' % data)

        # TODO Corregere dialogo su socket
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

class TrayIcon(wx.Frame):

    def __init__(self):
        
        setlocale(LC_ALL, '')
        self._status = Status(status.ERROR, "error")
        wx.Frame.__init__ (self, None, -1, "Ne.Me.Sys.", size=(630, 370), style=(wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.RESIZE_BOX)))
        panel = wx.Panel(self, -1)
        self.Bind(wx.EVT_PAINT, self.PaintInit)
        
        xmldoc = Progress(True)
        inizioMisure = xmldoc.start()  # inizioMisure è datetime
        
        label = 'Inizio test di misura: %s' % inizioMisure.strftime('%c')
        
        #self.run()
        self.iniziomisura = wx.StaticText(panel, -1, label, (165, 55), (300, -1), wx.ALIGN_CENTER)
        self.avanzamento = wx.StaticText(panel, -1, " ", (165, 75), (300, -1), wx.ALIGN_CENTER)

        #Create Control
        #Logo 1
        logo1 = wx.Image(filenames[1], wx.BITMAP_TYPE_ANY)
        #logo1 = logo1.Scale(111, 76)
        logo1 = wx.StaticBitmap(panel, -1, wx.BitmapFromImage(logo1), pos=(50, 20))
        
        #Misura Internet
        st1 = wx.StaticText(panel, -1, 'Ne.Me.Sys.', (165, 15), (300, -1), wx.ALIGN_CENTER)
        st1.SetFont(wx.Font(25, wx.SWISS, wx.NORMAL, wx.BOLD))
        
        #Logo 2
        logo2 = wx.Image(filenames[0], wx.BITMAP_TYPE_ANY)
        #logo2 = logo2.Scale(76,76)
        logo2 = wx.StaticBitmap(panel, -1, wx.BitmapFromImage(logo2), pos=(495, 25))
        
        first = 15
        for i in range (0, 24):
            wx.StaticText(panel, -1, "%s" % i, ((first + (i * 25)), 130), (25, -1), wx.ALIGN_CENTER)
            
        #Casella Messaggi
        #wx.StaticText (panel, -1, "Dettaglio stato Ne.Me.Sys.", (15, 230), (600, -1), wx.ALIGN_CENTER)
        sb = wx.StaticBox(panel, -1, "Dettaglio stato Ne.Me.Sys.", (15, 230), (600, 100))
        box = wx.StaticBoxSizer(sb, wx.VERTICAL)
        self.message = wx.StaticText(panel, -1, "Sto contattando il servizio di misura...\n...attendere qualche secondo.", (20, 247), (590, 80), wx.ST_NO_AUTORESIZE)
        box.Add(self.message, 1, wx.ALL, 5)

        #Stato Misura
        self.helper = wx.StaticText (panel, -1, "Si ricorda che la misurazione va completata entro tre giorni dal suo inizio", (15, 190), (600, -1), wx.ALIGN_CENTER)
                
        # self.CreateStatusBar() # A StatusBar in the bottom of the window

        # Setting up the menu.
        filemenu = wx.Menu()

        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu, "&Ne.Me.Sys") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
        
        # wx.ID_ABOUT and wx.ID_EXIT are standard ids provided by wxWidgets.
        menuAbout = filemenu.Append(wx.ID_ABOUT, "&About", " Information about this program")
        menuExit = filemenu.Append(wx.ID_EXIT, "E&xit", " Terminate the program")
        
        #menuItem = filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        #self.Bind(wx.EVT_MENU, self.OnAbout, menuItem)
        
        # Set events.
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)

        self.Show(True)
        self.Center()
        
        self._controller = _Controller(LISTENING_URL, self)
        self._controller.start()
        
    
    def setstatus(self, currentstatus):
        '''
        Aggiorna il messaggio nel system tray, l'aggiornamento viene
        fatto solo se lo staus è cambiato, ovvero se è cambiata il
        messaggio.
        '''
        logger.debug('Inizio aggiornamento stato')
        if (self._status.icon != currentstatus.icon or self._status.message != currentstatus.message):
          
          hour = datetime.now().hour
          logger.debug('Ora attuale: %d' % hour)
          
          if (bool(re.search(status.PLAY.message, currentstatus.message))):
              self.PaintHour(hour, "yellow")
          elif (bool(re.search('Misura terminata|Misura interrotta', currentstatus.message))):
              self.PaintInit(None)
          elif (bool(re.search(status.FINISHED.message, currentstatus.message))):
              self.helper.SetLabel("Misura completa! Visita la tua area personale sul sito\nwww.misurainternet.it per scaricare il pdf delle misure")
            
          message = self.getformattedmessage(currentstatus.message)
          
          self.message.SetLabel("%s" % message)
          self.message.Wrap(590)
          self._status = currentstatus
        
        
    def getformattedmessage(self, message):
        logger.debug('Instanzio HTMLParser')
        htmlmessage = HTMLParser.HTMLParser()
      
        logger.debug('Messaggio prima di unescape: %s' % message)
        message = htmlmessage.unescape(message)
        logger.debug('Messaggio dopo unescape: %s' % message)
        message = message.replace('(\'', '')
        message = message.replace('\')', '')
        message = message.replace('\', \'', '\n')
        
        logger.debug('Messaggio da stampare a video: %s' % message)
        return message      
    
    def PaintInit(self, event):
        '''
        Inizializza le casselle ora tutte rosse
            
        '''
        xmldoc = Progress()

        n = 0
        for hour in range(0, 24):
            color = "red"
            if xmldoc.isdone(hour):
                color = "green"
                n = n + 1
            self.PaintHour(hour, color)
        logger.debug('Aggiorno lo stato di avanzamento')
        self.avanzamento.SetLabel('Stato di Avanzamento: %d test su 24' % n)

    
    def PaintHour(self, hour, color):
        '''
        Aggiorna la casella allora specificata con il colore specificatio
        '''
        dc = wx.PaintDC(self)
        dc.SetPen(wx.Pen('#d4d4d4'))
        
        first = 15
        dc.SetBrush(wx.Brush(color))
        dc.DrawRectangle(first + (hour * 25), 155, 25, 25)
        
        
    def OnAbout(self, e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog(self, "Copyright (c) 2010 Fondazione Ugo Bordoni \nEmail: info@fub.it", "Ne.Me.Sys. (Network Measurement System) \nHomepage del progetto: www.misurainternet.it", wx.OK)
        dlg.ShowModal() # Show it
        dlg.Destroy() # finally destroy it when finished.

    def OnExit(self, e):
        self._controller.join()
        self.Close(True)  # Close the frame.


if __name__ == '__main__':
    app = wx.PySimpleApp ()
    frame = TrayIcon ()
    frame.Show (True)
    app.MainLoop ()
