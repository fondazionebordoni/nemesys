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
from gobject import idle_add, timeout_add
from locale import LC_ALL, setlocale
from logger import logging
from os import path
from popup import NotificationStack
from progress import Progress
from status import Status
from sys import platform
from threading import Event, Thread
from time import sleep
from xmlutils import xml2status
import pango, cairo, pangocairo, atk, gio
import gtk
import paths
import pygtk
import socket
import status
import webbrowser
pygtk.require('2.0')

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
    while self._running:
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

    try:
      current_status = xml2status(data)
    except Exception, e:
      logger.error('Errore durante la decodifica dello stato del sistema di misura: %s' % e)
      current_status = Status(status.ERROR, '%s' % e)
      self.handle_error()

    if current_status == None:
      current_status = Status(status.ERROR, 'Errore di comunicazione con il server.')

    idle_add(self._trayicon.setstatus, current_status)

class TrayIcon():

  def __init__(self):
    setlocale(LC_ALL, '')
    self._status = status.ERROR
    self._popupenabled = True
    self._menu = None
    self._progress_dialog = None
    self._about_dialog = None
    self._crea_menu()
    self._notifier = NotificationStack()
    self._controller = _Controller(LISTENING_URL, self)
    self._controller.start()
    self.run()

  def setstatus(self, currentstatus):
    '''
    Aggiorna l'icona e il messaggio nel system tray, l'aggiornamento viene
    fatto solo se lo staus è cambiato, ovvero se è cambiata l'icona o il
    messaggio. In questo modo evito che l'icona "sfarfalli" se non cambia
    lo stato.
    '''

    if (self._status.icon != currentstatus.icon
        or self._status.message != currentstatus.message):
    #if True:
      self._status = currentstatus
      self._trayicon.set_visible(False)
      self._trayicon = gtk.status_icon_new_from_file(self._status.icon)
      self._trayicon.set_tooltip(self._status.message)
      self._trayicon.connect('popup-menu', self._callback, self._menu)
      if self._popupenabled:
        self._popupstato(None)

  def _popupstato(self, widget):
    self._notifier.bg_color = gtk.gdk.Color(NOTIFY_COLORS[0])
    self._notifier.fg_color = gtk.gdk.Color(NOTIFY_COLORS[1])
    self._notifier.new_popup(title="Ne.Me.Sys.", message=self._status.message, image=self._status.icon)

  def _statomisura(self, widget):

    if self._progress_dialog != None:
      self._progress_dialog.destroy()  # così lascio aprire una finestra sola relativa allo stato della misura

    self._progress_dialog = gtk.Window(gtk.WINDOW_TOPLEVEL)
    self._progress_dialog.set_title('Stato Misura Ne.Me.Sys.')
    self._progress_dialog.set_position(gtk.WIN_POS_CENTER)
    self._progress_dialog.set_default_size(600, 270)
    self._progress_dialog.set_resizable(False)
    self._progress_dialog.set_icon_from_file(status.LOGO.icon)
    self._progress_dialog.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#FFF'))
    self._progress_dialog.set_border_width(20)

    coloreCelle = dict() # lo uso per associare ad ogni colonna lo stato red o green
    for n in range(24): # inizializzo tutto allo stato rosso
      coloreCelle[n] = 'red'

    table = gtk.Table(6, 24, True)  # 7 righe, 24 colonne
    table.set_size_request(600, 180)
    self._progress_dialog.add(table)

    ore = dict()
    for n in range(0, 24):
      hour = '<small>%d</small>' % n
      ore[n] = gtk.Label(hour)
      ore[n].set_use_markup(True)
      table.attach(ore[n], n, n + 1, 3, 4, xpadding=1, ypadding=0)

    # creo le 24 drawing area
    darea_1_1 = gtk.DrawingArea()
    darea_1_2 = gtk.DrawingArea()
    darea_1_3 = gtk.DrawingArea()
    darea_1_4 = gtk.DrawingArea()
    darea_1_5 = gtk.DrawingArea()
    darea_1_6 = gtk.DrawingArea()
    darea_1_7 = gtk.DrawingArea()
    darea_1_8 = gtk.DrawingArea()
    darea_1_9 = gtk.DrawingArea()
    darea_1_10 = gtk.DrawingArea()
    darea_1_11 = gtk.DrawingArea()
    darea_1_12 = gtk.DrawingArea()
    darea_1_13 = gtk.DrawingArea()
    darea_1_14 = gtk.DrawingArea()
    darea_1_15 = gtk.DrawingArea()
    darea_1_16 = gtk.DrawingArea()
    darea_1_17 = gtk.DrawingArea()
    darea_1_18 = gtk.DrawingArea()
    darea_1_19 = gtk.DrawingArea()
    darea_1_20 = gtk.DrawingArea()
    darea_1_21 = gtk.DrawingArea()
    darea_1_22 = gtk.DrawingArea()
    darea_1_23 = gtk.DrawingArea()
    darea_1_24 = gtk.DrawingArea()

    # riga1 è una lista che contiene in modo ordinato tutte le drawing area
    riga1 = [darea_1_1, darea_1_2, darea_1_3, darea_1_4, darea_1_5, darea_1_6,
      darea_1_7, darea_1_8, darea_1_9, darea_1_10, darea_1_11, darea_1_12,
      darea_1_13, darea_1_14, darea_1_15, darea_1_16, darea_1_17, darea_1_18,
      darea_1_19, darea_1_20, darea_1_21, darea_1_22, darea_1_23, darea_1_24]

    # inserisco in tabella le 24 drawing area che ho appena creato e le coloro di rosso
    for i in range(0, 24):
      table.attach(riga1[i], i, i + 1, 4, 5, xpadding=1, ypadding=1)
      riga1[i].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('red'))

    # il codice di seguito serve per measure.xml
    if not path.exists(paths.MEASURE_STATUS):
      return

    xmldoc = Progress()
    inizioMisure = xmldoc.start()  # inizioMisure è datetime

    n = 0
    for i in range(0, 24):
      if xmldoc.isdone(i):
        riga1[i].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('green'))
        n = n + 1

    logo1 = gtk.Image()
    pixbuf = gtk.gdk.pixbuf_new_from_file(status.LOGOSTATOMISURA1.icon)
    scaled_buf = pixbuf.scale_simple(75, 75, gtk.gdk.INTERP_BILINEAR)
    logo1.set_from_pixbuf(scaled_buf)

    logo2 = gtk.Image()
    pixbuf = gtk.gdk.pixbuf_new_from_file(status.LOGOSTATOMISURA2.icon)
    scaled_buf = pixbuf.scale_simple(95, 65, gtk.gdk.INTERP_BILINEAR)
    logo2.set_from_pixbuf(scaled_buf)

    label1 = gtk.Label("<b><big><big>Ne.Me.Sys.</big></big></b>")
    label2 = gtk.Label("<big>Inizio test di misura: %s</big>" % inizioMisure.strftime('%c'))
    label3 = gtk.Label("<big>Stato di avanzamento: %s test su 24</big>" % str(n))
    label4 = gtk.Label("Si ricorda che la misurazione va completata entro tre giorni dal suo inizio")
    label5 = gtk.Label("Misura completa! Visita la tua area personale sul sito\n<i>www.misurainternet.it</i> per scaricare il pdf delle misure")

    label1.set_use_markup(True)
    label2.set_use_markup(True)
    label3.set_use_markup(True)
    label4.set_use_markup(True)
    label5.set_use_markup(True)

    label1.set_justify(gtk.JUSTIFY_CENTER)
    label2.set_justify(gtk.JUSTIFY_CENTER)
    label3.set_justify(gtk.JUSTIFY_CENTER)
    label4.set_justify(gtk.JUSTIFY_CENTER)
    label5.set_justify(gtk.JUSTIFY_CENTER)

    table.attach(logo1, 0, 6, 0, 3)
    table.attach(logo2, 18, 24, 0, 3)
    table.attach(label1, 8, 16, 0, 1)
    table.attach(label2, 0, 24, 1, 2)
    table.attach(label3, 0, 24, 2, 3)
    if n < 24:
      table.attach(label4, 0, 24, 5, 6)
    else:
      table.attach(label5, 0, 24, 5, 6)

    self._progress_dialog.show_all()

  def _togglepopup(self, widget):
    self._popupenabled = widget.get_active()
    logger.debug("Popup abilitato: %s" % self._popupenabled)

  def _serviziOnline(self, widget):
    webbrowser.open('http://www.misurainternet.it/login_form.php')

  def _about(self, widget):
    if self._about_dialog != None:
      self._about_dialog.destroy()

    # TODO Inserire controllo per nuove versioni del software: viene einserito nel messaggio di about un avviso: "scaricare la nuova versione" 
    self._about_dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE,
                                          '''
Ne.Me.Sys. (Network Measurement System)
Copyright (c) 2010 Fondazione Ugo Bordoni <info@fub.it>
Homepage del progetto su www.misurainternet.it''')
    self._about_dialog.show()
    self._about_dialog.set_icon_from_file(status.LOGO.icon)
    if self._about_dialog.run() == gtk.RESPONSE_CLOSE:
      self._about_dialog.destroy()

  def _callback(self, widget, button, time, menu):
    self._menu.popdown()
    self._menu.show_all()
    # self.menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.icon)
    # elimina la freccia per visualizzare il menu per intero
    self._menu.popup(None, None, None, button, time, self._trayicon)

  def _quit(self, widget, data=None):  # quando esco dal programma

    self._trayicon.set_visible(False)

    self._controller.join()

    if self._menu != None:
      self._menu.destroy()

    if (self._progress_dialog != None):
      self._progress_dialog.destroy()

    if (self._about_dialog != None):
      self._about_dialog.destroy()

    return gtk.main_quit()

  def _on_event(self, widget, event):
    logger.debug('Event: %s' % event.type)

  def _closemenu(self, widget):
    self._menu.popdown()

  def _crea_menu(self):
    if self._menu:
      self._menu.destroy()

    self._menu = gtk.Menu()

    icona = self._status.icon
    stringa = self._status.message

    self._trayicon = gtk.status_icon_new_from_file(icona)
    self._trayicon.set_tooltip(stringa)
    self._trayicon.connect('popup-menu', self._callback, self._menu)

    item = gtk.ImageMenuItem('Stato della _misura')
    icon = gtk.image_new_from_stock('gtk-index', gtk.ICON_SIZE_MENU)
    item.set_image(icon)
    item.connect('activate', self._statomisura)
    self._menu.append(item)

    item = gtk.ImageMenuItem('Stato di Ne.Me.Sys.')
    icon = gtk.image_new_from_stock('gtk-info', gtk.ICON_SIZE_MENU)
    item.set_image(icon)
    item.connect('activate', self._popupstato)
    self._menu.append(item)

    item = gtk.CheckMenuItem('Visualizza _popup')
    item.set_active(self._popupenabled)
    item.connect('activate', self._togglepopup)
    self._menu.append(item)

    item = gtk.ImageMenuItem('Servizi _online')
    icon = gtk.image_new_from_stock('gtk-network', gtk.ICON_SIZE_MENU)
    item.set_image(icon)
    item.connect('activate', self._serviziOnline)
    self._menu.append(item)

    item = gtk.ImageMenuItem(stock_id=gtk.STOCK_ABOUT)
    item.connect('activate', self._about)
    self._menu.append(item)

    item = gtk.ImageMenuItem(stock_id=gtk.STOCK_CLOSE)
    item.connect('activate', self._closemenu)
    self._menu.append(item)

    self._menu.append(gtk.SeparatorMenuItem())

    item = gtk.ImageMenuItem(stock_id=gtk.STOCK_QUIT)
    item.connect('activate', self._quit)
    self._menu.append(item)

  def run(self):
    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()
    gtk.main()
    gtk.gdk.threads_leave()

if __name__ == '__main__':
  if platform == 'win32':
    timeout_add(400, sleeper)
  trayicon = TrayIcon()
