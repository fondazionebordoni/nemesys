# gui.py
# -*- coding: utf8 -*-

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

import pygtk
pygtk.require('2.0')
import gtk
import webbrowser
import datetime
import time
import paths
import threading
import xmlrpclib
import status
from logger import logging
from xml.dom import minidom
from datetime import datetime
from time import sleep
from xmlutils import xml2status

logger = logging.getLogger()

class _Controller(threading.Thread):
    
    def __init__(self, object, url):
        threading.Thread.__init__(self)
        self._proxy = xmlrpclib.ServerProxy(url)
        self._running = False
        self._trayicon = object

    def stop(self):
        self._running = False

    def run(self):
        '''
        Controllo sullo stato del demone!
        '''
        self._running = True
        while self._running:
            try:
                self._trayicon.setstatus(xml2status(self._proxy.getstatus()))
            except Exception as e:
                # Catturare l'eccezione dovuta a errore di comunicazione col demone
                error = 'Errore durante la decodifica dello stato del demone: %s' % e
                logger.error(error)
                current_status = status.ERROR
                current_status.message = error
                self._trayicon.setstatus(current_status)
                
            #il controllo sulla variazione dello stato lo faccio ogni 20 sec
            sleep(20)
            
class TrayIcon():        

    def __init__(self, status=status.LOGO):                
        self._status = status
        self._menu = None
        self._crea_menu(self)

    def setstatus(self, status):
        '''
        Aggiorna l'icona e il messaggio nel system tray, l'aggiornamento viene
        fatto solo se lo staus è cambiato, ovvero se è cambiata l'icona o il
        messaggio. In questo modo evito che l'icona "sfarfalli" se non cambia
        lo stato.
        '''
        #logger.debug('Nuovo stato: %s, vecchio: %s' % (status, self._status))
        if (self._status.icon != status.icon or self._status.message != status.message):
            self._status = status
            self._icon.set_visible(False)
            self._icon = gtk.status_icon_new_from_file(self._status.icon)
            self._icon.set_tooltip(self._status.message)      
            self._icon.connect('popup-menu', self._callback, self._menu)
                
    #la versione 2.5 di python ha un bug nella funzione strptime che non riesce a leggere i microsecondi (%f) 
    def _str2datetime(s):
        parts = s.split('.')
        dt = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
        return dt.replace(microsecond=int(parts[1]))

    def statoMisura(self, widget):
        global winAperta
        if(winAperta):
            self._win.destroy()#così lascio aprire una finestra sola relativa allo stato della misura
        self._win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self._win.set_title("Stato Misura Nemesys")
        self._win.set_position(gtk.WIN_POS_CENTER)
        self._win.set_default_size(600, 300)
        self._win.set_resizable(False)
        self._win.set_icon_from_file(paths.ICONS + paths.DIR_SEP + status.LOGO.icon)
        self._win.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#FFF'))
        self._win.set_border_width(20)
        
        coloreCelle = dict()#lo uso per associare ad ogni colonna lo stato red o green
        for n in range(24):#inizializzo tutto allo stato rosso
            coloreCelle[n] = 'red'
        
        
        table = gtk.Table(6, 24, True)#6 righe, 24 colonne
        self._win.add(table)


        ore = dict()
        for n in range(0, 24):
            hour = str(n)
            
            if(n < 10):
                hour = '0' + hour         
            
            hour = "<small>" + hour + ':00' + "</small>"
            ore[n] = gtk.Label(hour)
            ore[n].set_use_markup(True)
            table.attach(ore[n], n, n + 1, 4, 5, xpadding=1, ypadding=0)
         
        #creo le 24 drawing area               
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
        
        #riga1 è una lista che contiene in modo ordinato tutte le drawing area
        riga1 = [darea_1_1, darea_1_2, darea_1_3, darea_1_4, darea_1_5, darea_1_6, darea_1_7, darea_1_8, darea_1_9, darea_1_10, darea_1_11, darea_1_12, darea_1_13, darea_1_14, darea_1_15, darea_1_16, darea_1_17, darea_1_18, darea_1_19, darea_1_20, darea_1_21, darea_1_22, darea_1_23, darea_1_24]
        
        #inserisco in tabella le 24 drawing area che ho appena creato e le coloro di rosso
        for i in range(0, 24):
            table.attach(riga1[i], i, i + 1, 5, 6, xpadding=1, ypadding=0)
            riga1[i].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))
        
        #il codice di seguito serve per measure.xml                
        xmldoc = minidom.parse(paths.MEASURE_STATUS)
        start = xmldoc.documentElement.getElementsByTagName('start')[0].firstChild.data

        inizioMisure = self._str2datetime(str(start))#inizioMisure è datetime
        coloreCelle[inizioMisure.hour] = 'green'
        slots = xmldoc.documentElement.getElementsByTagName('slot')
        for slot in slots:
            misura = str(slot.firstChild.data)
            misuraDataTime = self._str2datetime(misura)
            delta = misuraDataTime - inizioMisure
            if(delta.days < 3):#ovvero se la misura è valida
                coloreCelle[misuraDataTime.hour] = 'green'
                        
        n = 0
        for i in range(0, 24):
            riga1[i].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(coloreCelle[i]))
            if(coloreCelle[i] == 'green'):
                n = n + 1                     
                         
        label1 = gtk.Label("<b><big>Nemesys</big></b>")
        label2 = gtk.Label("<big>Data inizio misurazioni: " + str(inizioMisure.day) + "/" + str(inizioMisure.month) + "/" + str(inizioMisure.year) + " alle ore " + str(inizioMisure.hour) + ":" + str(inizioMisure.minute) + ":" + str(inizioMisure.second) + "</big>")
        
        label3 = gtk.Label("<big>Si ricorda che la misurazione va completata entro tre giorni dal suo inizio</big>")
        label4 = gtk.Label("<big>Stato di avanzamento della misura: " + str(n) + " misure su 24</big>")
        label1.set_use_markup(True)
        label2.set_use_markup(True)
        label3.set_use_markup(True)
        label4.set_use_markup(True)
        
        table.attach(label1, 0, 24, 0, 1)
        table.attach(label2, 0, 24, 1, 2)
        table.attach(label3, 0, 24, 2, 3)
        table.attach(label4, 0, 24, 3, 4)
        
        self._win.show_all()
        winAperta = True

    def _abilitaDisabilitaPopUp(self, widget):
        global statoPopUp
        self._item2.destroy() 
        if(statoPopUp == "ON"):
                statoPopUp = "OFF"
                self._item2 = gtk.ImageMenuItem('Abilita Pop-up')
        else:
                statoPopUp = "ON"
                self._item2 = gtk.ImageMenuItem('Disabilita Pop-up')
        self._img_sm = gtk.image_new_from_stock('gtk-dialog-warning', gtk.ICON_SIZE_MENU)
        self._item2.set_image(self._img_sm)
        self._item2.connect('activate', self._abilitaDisabilitaPopUp)
        self._menu.insert(self._item2, 1)

    def _serviziOnline(self, widget):
        webbrowser.open("http://misurainternet.fub.it/login_form.php")
        
    def _info(self, widget):
        global infoAperta
        if infoAperta:#non do all'utente la possibilità di aprire n finestre info
                self._infoMessage.destroy()
        infoAperta = True
        self._infoMessage = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Nemesys e' stato realizzato da:\n .. \n .. \n ..")
        self._infoMessage.show()
        self._infoMessage.set_icon_from_file(paths.ICONS + paths.DIR_SEP + "icon.png")
        if self._infoMessage.run() == gtk.RESPONSE_CLOSE:
                self._infoMessage.destroy()
                infoAperta = False
       
    def _callback(self, widget, button, time, menu):
        self._menu.popdown()
        self._menu.show_all()
        #self.menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.icon)
        self._menu.popup(None, None, None, button, time, self._icon)#elimina la freccia per visualizzare il menu per intero
    
    def _destroy(self, widget, data=None):#quando esco dal programma
        self._icon.set_visible(False)
        self._menu.destroy()
        if (self._win != None):
                self._win.destroy()
        if(self._infoMessage != None):
                self._infoMessage.destroy()
        controller.stop()#fermo il thread di controllo
        return gtk.main_quit()
    
    def _crea_menu(self, widget):
        global statoPopUp
        if(self._menu != None):
            self._menu.destroy()
        self._menu = gtk.Menu()
        if(winAperta == False):
            self._win = None
        if(infoAperta == False):
            self._infoMessage = None
    
        self._icona = None
        self._stringa = None
        self._vecchiaIcona = None
        self._vecchiaStringa = None
    
        self._icona = paths.ICONS + paths.DIR_SEP + self._status.icon
        self._stringa = self._status._message
        
        self._icon = gtk.status_icon_new_from_file(self._icona)
        self._icon.set_tooltip(self._stringa)      
        self._icon.connect('popup-menu', self._callback, self._menu)
    
        self._item1 = gtk.ImageMenuItem('Stato misurazione')
        self._img_sm = gtk.image_new_from_stock('gtk-execute', gtk.ICON_SIZE_MENU)
        self._item1.set_image(self._img_sm)
        self._item1.connect('activate', self.statoMisura)
        self._menu.append(self._item1)
        
        if(statoPopUp == "ON"):
            self._item2 = gtk.ImageMenuItem('Disabilita Pop-up')
        else:
            self._item2 = gtk.ImageMenuItem('Abilita Pop-up')

        self._img_sm = gtk.image_new_from_stock('gtk-dialog-warning', gtk.ICON_SIZE_MENU)
        self._item2.set_image(self._img_sm)
        self._item2.connect('activate', self._abilitaDisabilitaPopUp)
        self._menu.append(self._item2)
    
        self._item3 = gtk.ImageMenuItem('Servizi online')
        self._img_sm = gtk.image_new_from_stock('gtk-network', gtk.ICON_SIZE_MENU)
        self._item3.set_image(self._img_sm)
        self._item3.connect('activate', self._serviziOnline)
        self._menu.append(self._item3)
    
        self._item4 = gtk.ImageMenuItem('Info')
        self._img_sm = gtk.image_new_from_stock('gtk-about', gtk.ICON_SIZE_MENU)
        self._item4.set_image(self._img_sm)
        self._item4.connect('activate', self._info)
        self._menu.append(self._item4)
    
        self._item5 = gtk.SeparatorMenuItem()
        self._item5 = gtk.ImageMenuItem(stock_id=gtk.STOCK_QUIT)
        self._item5.connect('activate', self._destroy)
        self._menu.append(self._item5)
            
    def main(self):
        gtk.gdk.threads_init()
        gtk.gdk.threads_enter()
        gtk.main()
        gtk.gdk.threads_leave()

if __name__ == "__main__":
    statoPopUp = "ON"#per discriminare fra abilita e disabilita popup
    winAperta = False#indica se è aperta o meno la finestra contenente l'andamento della misura
    infoAperta = False#indica se è aperta o meno la finestra contenente le info su nemesys
    trayicon = TrayIcon()
    controller = _Controller(trayicon, 'http://localhost:21401')
    controller.start()
    trayicon.main()
