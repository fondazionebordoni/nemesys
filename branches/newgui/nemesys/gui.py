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
from locale import LC_ALL, setlocale
from logger import logging
from progress import Progress
from status import Status
from threading import Event, Thread
from time import sleep
from xmlutils import xml2status
from datetime import datetime
import re
import paths
import socket
import status
from os import path
import wx

filenames = [path.join(paths.ICONS, 'logo_nemesys.png'), path.join(paths.ICONS, 'logo_misurainternet.png')]

LISTENING_URL = ('localhost', 21401)
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
        # TODO Verificare al fattibilità di ricollegamento della gui al demone
        '''
        while self._running:
        loop(1)
        '''
        loop(1)
        logger.debug('GUI asyncore loop terminated.')

    def join(self, timeout=None):
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
        except Exception, e:
            logger.error('Errore durante la decodifica dello stato del sistema di misura: %s' % e)
            current_status = Status(status.ERROR, '%s' % e)

        if current_status == None:
            current_status = Status(status.ERROR, 'Errore di comunicazione con il server.')

        self._trayicon.setstatus(current_status)

class TrayIcon(wx.Frame):

    def __init__(self):
        wx.Frame.__init__ (self, None, -1, "Ne.Me.Sys.", size = (630,420))
        panel = wx.Panel(self, -1)
        self.Bind(wx.EVT_PAINT, self.PaintInit)
        
        setlocale(LC_ALL, '')
        self._status = status.ERROR
        #self.run()

        
        #Create Control
        #Logo 1
        logo1 = wx.Image(filenames[1], wx.BITMAP_TYPE_ANY)
        #logo1 = logo1.Scale(111, 76)
        logo1 = wx.StaticBitmap(panel, -1, wx.BitmapFromImage(logo1), pos = (50,20))
        
        #Misura Internet
        st1 = wx.StaticText(panel, -1,'Ne.Me.Sys.', (165, 15), (300, -1), wx.ALIGN_CENTER)
        st1.SetFont(wx.Font(25, wx.SWISS, wx.NORMAL, wx.BOLD))
        
        #Logo 2
        logo2 = wx.Image(filenames[0], wx.BITMAP_TYPE_ANY)
        #logo2 = logo2.Scale(76,76)
        logo2 = wx.StaticBitmap(panel, -1, wx.BitmapFromImage(logo2), pos = (495, 25))
        
        #Casella Messaggi
        wx.StaticText (panel, -1, "Dettaglio stato Ne.Me.Sys.", (15, 230), (600, -1), wx.ALIGN_CENTER)
        self.message = wx.TextCtrl(panel, -1,"", (15,255), (600,100), wx.TE_READONLY)
        
        #Stato Misura
        wx.StaticText (panel, -1, "Si ricorda che la misurazione va completata entro tre giorni dal suo inizio", (15, 190), (600, -1), wx.ALIGN_CENTER)
                
        self.CreateStatusBar() # A StatusBar in the bottom of the window

        # Setting up the menu.
        filemenu= wx.Menu()


        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&Ne.Me.Sys") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
        
        # wx.ID_ABOUT and wx.ID_EXIT are standard ids provided by wxWidgets.
        menuAbout = filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
        
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
        hour = datetime.now().hour
        n = 0
        if (bool(re.search(status.PLAY.message, currentstatus.message))):
            self.PaintHour(hour, "yellow")
        elif (bool(re.search('Misura terminata', currentstatus.message))):
            self.PaintHour(hour, "green")
            n = n + 1
            wx.StaticText(self, -1,'Stato di Avanzamento: %d test su 24' %n, (165, 75), (300, -1), wx.ALIGN_CENTER)
            
        if (self._status.icon != currentstatus.icon
            or self._status.message != currentstatus.message):
            #if True:
            self._status = currentstatus
            self.message.SetValue ("%s" % currentstatus.message)
            
        
    def PaintInit(self, event):
        '''
        Inizializza le casselle ora tutte rosse
            
        '''
        xmldoc = Progress()
        inizioMisure = xmldoc.start()  # inizioMisure è datetime
        
        wx.StaticText(self, -1, ('Inizio test di misura: %s' % inizioMisure.strftime('%c')), (165, 55), (300, -1), wx.ALIGN_CENTER)
        
        first = 15
        n = 0
        for hour in range(0, 24):
            color = "red"
            if xmldoc.isdone(hour):
                color="green"
                n = n + 1
            self.PaintHour(hour, color)
            wx.StaticText(self, -1, "%s" % hour, ((first + (hour*25)), 130), (25, -1), wx.ALIGN_CENTER)
        wx.StaticText(self, -1,'Stato di Avanzamento: %d test su 24' %n, (165, 75), (300, -1), wx.ALIGN_CENTER)

    
    def PaintHour(self, hour, color):
        '''
        Aggiorna la casella allora specificata con il colore specificatio
        '''
        dc = wx.PaintDC(self)
        dc.SetPen(wx.Pen('#d4d4d4'))
        
        first = 15
        dc.SetBrush(wx.Brush(color))
        dc.DrawRectangle(first + (hour*25), 155, 25, 25)
        
        
    def OnAbout(self,e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog( self, "Copyright (c) 2010 Fondazione Ugo Bordoni \nEmail: info@fub.it", "Ne.Me.Sys. (Network Measurement System) \nHomepage del progetto \nwww.misurainternet.it", wx.OK)
        dlg.ShowModal() # Show it
        dlg.Destroy() # finally destroy it when finished.

    def OnExit(self,e):
        self._controller.join()
        self.Close(True)  # Close the frame.


if __name__ == '__main__':
    app = wx.PySimpleApp ()
    frame = TrayIcon ()
    frame.Show (True)
    app.MainLoop ()