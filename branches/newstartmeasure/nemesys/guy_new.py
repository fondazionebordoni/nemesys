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
from progress import Progress, Progress
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

class MyFrame(wx.Frame):
  def __init__(self, *args, **kwds):
    # Base e gestione stato
    setlocale(LC_ALL, '')
    self._status = Status(status.ERROR, "error")
    self.xmldoc = Progress(True)
    
    # Grafica
    kwds["style"] = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.RESIZE_BOX)
    wx.Frame.__init__(self, *args, **kwds)

    # Menu Bar
    self.frame_1_menubar = wx.MenuBar()
    wxglade_tmp_menu = wx.Menu()
    self.frame_1_menubar.Append(wxglade_tmp_menu, "About")
    self.SetMenuBar(self.frame_1_menubar)
    # Menu Bar end
    self.panel_1 = wx.Panel(self, -1)
    self.bitmap_1 = wx.StaticBitmap(self.panel_1, -1, wx.Bitmap("../icons/logo_misurainternet.png", wx.BITMAP_TYPE_ANY))
    self.label_1 = wx.StaticText(self.panel_1, -1, "Ne.me.sys", style=wx.ALIGN_CENTRE)
    self.label_2 = wx.StaticText(self.panel_1, -1, "Inizio test di misura: %s" % self.xmldoc.start().strftime('%c'), style=wx.ALIGN_CENTRE)
    self.helper = wx.StaticText(self.panel_1, -1, "La misurazione va completata entro tre giorni dal suo inizio", style=wx.ALIGN_CENTRE)
    self.label_3 = wx.StaticText(self.panel_1, -1, "Stato di avanzamento: X test su 24", style=wx.ALIGN_CENTRE)
    self.bitmap_2 = wx.StaticBitmap(self.panel_1, -1, wx.Bitmap("../icons/logo_nemesys.png", wx.BITMAP_TYPE_ANY))
    self.message = wx.TextCtrl(self.panel_1, -1, "[%s] Sto contattando il servizio di misura attendere qualche secondo." % getdate().strftime('%c'), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL | wx.TE_RICH | wx.TE_RICH2 | wx.NO_BORDER)
    self.sizer_5_staticbox = wx.StaticBox(self.panel_1, -1, "Dettaglio di stato della misura")

    self.__set_properties()
    self.__do_layout()
    
    self.InitBuffer()
    self.Bind(wx.EVT_PAINT, self.PaintInit)
    self._controller = _Controller(LISTENING_URL, self)
    self._controller.start()

  def InitBuffer(self):
    w, h = self.GetClientSize()
    self.buffer = wx.EmptyBitmap(w, h)
    #dc = wx.BufferedDC(wx.ClientDC(self), self.buffer)
    
  def __set_properties(self):
    # begin wxGlade: MyFrame.__set_properties
    self.SetTitle("Ne.me.sys")
    self.SetSize((600, 300))
    self.label_1.SetFont(wx.Font(26, wx.DEFAULT, wx.NORMAL, wx.BOLD, 0, ""))
    self.message.SetMinSize((580, -1))
    #self.message.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))
    #self.panel_1.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))
    # end wxGlade

  def __do_layout(self):
    # begin wxGlade: MyFrame.__do_layout
    sizer_1 = wx.BoxSizer(wx.VERTICAL)
    sizer_2 = wx.BoxSizer(wx.VERTICAL)
    self.sizer_5_staticbox.Lower()
    sizer_5 = wx.StaticBoxSizer(self.sizer_5_staticbox, wx.HORIZONTAL)
    sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
    sizer_4 = wx.BoxSizer(wx.VERTICAL)

    sizer_3.Add(self.bitmap_1, 0, wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 10)
    sizer_4.Add(self.label_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
    sizer_4.Add(self.label_2, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
    sizer_4.Add(self.helper, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
    sizer_4.Add(self.label_3, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
    sizer_3.Add(sizer_4, 0, wx.TOP | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
    sizer_3.Add(self.bitmap_2, 0, wx.LEFT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 10)
    sizer_2.Add(sizer_3, 1, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)

    self._grid = wx.GridSizer(2, 24, 2, 6)
    for i in range (0, 24):
      label_hour = wx.StaticText(self.panel_1, -1, "%2d" % i)
      self._grid.Add(label_hour, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)

    for i in range (24, 48):    
      bitmap_hour = wx.StaticBitmap(self.panel_1, -1, wx.Bitmap("../icons/red.png", wx.BITMAP_TYPE_ANY))
      self._grid.Add(bitmap_hour, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)

    sizer_2.Add(self._grid, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 8)
    sizer_5.Add(self.message, 1, wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
    sizer_2.Add(sizer_5, 2, wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 10)
    self.panel_1.SetSizer(sizer_2)
    sizer_1.Add(self.panel_1, 1, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
    self.SetSizer(sizer_1)
    
    # Setting up the menu.
    filemenu = wx.Menu()

    # Creating the menubar.
    menuBar = wx.MenuBar()
    menuBar.Append(filemenu, "&Ne.Me.Sys") # Adding the "filemenu" to the MenuBar
    self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
    
    # wx.ID_ABOUT and wx.ID_EXIT are standard ids provided by wxWidgets.
    menuAbout = filemenu.Append(wx.ID_ABOUT, "&About", " Information about this program")
    menuExit = filemenu.Append(wx.ID_EXIT, "E&xit", " Terminate the program")
    self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
    self.Bind(wx.EVT_MENU, self.OnExit, menuExit)

    self.Layout()
    # end wxGlade

  def PaintInit(self, event):
    '''
    Inizializza le casselle ora tutte rosse
    '''

    n = 0
    for hour in range(0, 24):
        color = "red"
        if self.xmldoc.isdone(hour):
            color = "green"
            n = n + 1
        self.PaintHour(hour, color)

    #logger.debug('Aggiorno lo stato di avanzamento')
    if (n != 0):
      self.label_3.SetLabel('Stato di avanzamento: %d test su 24' % n)
    else:
      self.label_3.SetLabel('Stato di avanzamento: nessun test effettuato su 24')

  def setstatus(self, currentstatus):
    '''
    Aggiorna il messaggio nel system tray, l'aggiornamento viene
    fatto solo se lo staus è cambiato, ovvero se è cambiata il
    messaggio.
    '''
    logger.debug('Inizio aggiornamento stato')
    #if (self._status.icon != currentstatus.icon or self._status.message != currentstatus.message):
      
    hour = getdate().hour
    logger.debug('Ora attuale: %d' % hour)
    self.PaintHour(hour, "yellow")
    
    if (bool(re.search(status.PLAY.message, currentstatus.message))):
        self.PaintHour(hour, "yellow")
    elif (bool(re.search('Misura terminata|Misura interrotta', currentstatus.message))):
        self.PaintInit(None)
    elif (bool(re.search(status.FINISHED.message, currentstatus.message))):
        self.helper.SetLabel("Misura completa! Visita la tua area personale sul sito\nwww.misurainternet.it per scaricare il pdf delle misure")
      
    message = self.getformattedmessage(currentstatus.message)
    self.message.AppendText("\n[%s] %s" % (getdate().strftime('%c'), message))
      
    #self.message.Wrap(590)
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
    
  def PaintHour(self, hour, color):
    '''
    Aggiorna la casella allora specificata con il colore specificatio
    '''
    old = self._grid.GetItem(24 + hour).GetWindow()
    bitmap_hour = wx.StaticBitmap(self.panel_1, -1, wx.Bitmap("../icons/%s.png" % color, wx.BITMAP_TYPE_ANY))
    self._grid.Replace(old, bitmap_hour)

  def OnAbout(self, e):
      # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
      dlg = wx.MessageDialog(self, "Copyright (c) 2010-2011 Fondazione Ugo Bordoni \nEmail: info@fub.it", "Ne.Me.Sys. (Network Measurement System) \nHomepage del progetto: www.misurainternet.it", wx.OK)
      dlg.ShowModal() # Show it
      dlg.Destroy() # finally destroy it when finished.

  def OnExit(self, e):
      self._controller.join()
      self.Close(True)  # Close the frame.

def getdate():
  return datetime.fromtimestamp(timestampNtp())

# end of class MyFrame
if __name__ == "__main__":
  app = wx.PySimpleApp(0)
  if platform == 'win32':
    wx.CallLater(200, sleeper)
  wx.InitAllImageHandlers()
  frame_1 = MyFrame(None, -1, "")
  app.SetTopWindow(frame_1)
  frame_1.Show()
  app.MainLoop()
