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
from xml.dom import minidom
from datetime import datetime
from time import sleep




class _Controller(threading.Thread, object):
    def __init__(self, object):
        threading.Thread.__init__(self)
        self._running=False
        self._trayicon=object

    def stop(self):
        self._running=False

    def run(self):#controllo sullo stato del demone!
        self._running=True
        sleep(10)
        while self._running:
            try:
                self._trayicon.setstatus(self._trayicon.proxy.getstatus())# TODO:sul server (executer) va implementato il metodo getstatus()
            except Exception: # Catturare l'eccezione dovuta a errore di comunicazione col demone
                self._trayicon.setstatus(status.ERROR)
            sleep(20)#il controllo sulla variazione dello stato lo faccio ogni 20 sec
            


class TrayIcon():        
        def __init__(self, url, status):                
                self._status = status
                self.proxy = xmlrpclib.ServerProxy(url)
                self._menu=None
                self._crea_menu(self)


        def setstatus(self, status):
                self._status = status
                self._updatestatus()

        def _updatestatus(self):#aggiorna l'icona e il messaggio nel system tray, l'aggiornamento viene fatto solo se lo staus è cambiato,
                                #ovvero se è cambiata l'icona o il messaggio. In questo modo evito che l'icona "sfarfalli" se non cambia lo stato
                self._icona=paths.ICON_PATH+paths.DIR_SEP+self._status._icon
                self._stringa=self._status._message
                if((self._vecchiaIcona!=self._icona)or(self._vecchiaStringa!=self._stringa)):
                    self._icon.set_visible(False)
                    self._icon = gtk.status_icon_new_from_file(self._icona)
                    self._icon.set_tooltip(self._stringa)      
                    self._icon.connect('popup-menu',self._callback,self._menu)
                self._vecchiaIcona=self._icona
                self._vecchiaStringa=self._stringa
                

        def statoMisura(self,widget):
                global winAperta
                if(winAperta):
                        self._win.destroy()#così lascio aprire una finestra sola relativa allo stato della misura
                self._win=gtk.Window(gtk.WINDOW_TOPLEVEL)
                self._win.set_title("Stato Misura Nemesys")
                self._win.set_position(gtk.WIN_POS_CENTER)
                self._win.set_default_size(600,300)
                self._win.set_resizable(False)
                self._win.set_icon_from_file(paths.ICON_PATH+paths.DIR_SEP+"icon.png")
                self._win.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#FFF'))
                self._win.set_border_width(20)

                _coloreCelle=dict()#lo uso per associare ad ogni colonna lo stato red o green
                for n in range(24):#inizializzo tutto allo stato rosso
                        _coloreCelle[n]='red'


                _table = gtk.Table(6,24,True)#6 righe, 24 colonne
                self._win.add(_table)


                _ore=dict()
                for n in range(0,24):
                        _hour=str(n)
                        if(n<10):
                                _hour='0'+_hour         
                        _hour="<small>"+_hour+':00'+"</small>"
                        _ore[n]=gtk.Label(_hour)
                        _ore[n].set_use_markup(True)
                        _table.attach(_ore[n],n,n+1,4,5,xpadding=1, ypadding=0)
  
                
                #creo le 24 drawing area               
                _darea_1_1 = gtk.DrawingArea()
                _darea_1_2 = gtk.DrawingArea()
                _darea_1_3 = gtk.DrawingArea()
                _darea_1_4 = gtk.DrawingArea()
                _darea_1_5 = gtk.DrawingArea()
                _darea_1_6 = gtk.DrawingArea()
                _darea_1_7 = gtk.DrawingArea()
                _darea_1_8 = gtk.DrawingArea()
                _darea_1_9 = gtk.DrawingArea()
                _darea_1_10 = gtk.DrawingArea()
                _darea_1_11 = gtk.DrawingArea()
                _darea_1_12 = gtk.DrawingArea()
                _darea_1_13 = gtk.DrawingArea()
                _darea_1_14 = gtk.DrawingArea()
                _darea_1_15 = gtk.DrawingArea()
                _darea_1_16 = gtk.DrawingArea()
                _darea_1_17 = gtk.DrawingArea()
                _darea_1_18 = gtk.DrawingArea()
                _darea_1_19 = gtk.DrawingArea()
                _darea_1_20 = gtk.DrawingArea()
                _darea_1_21 = gtk.DrawingArea()
                _darea_1_22 = gtk.DrawingArea()
                _darea_1_23 = gtk.DrawingArea()
                _darea_1_24 = gtk.DrawingArea()

                
                #riga1 è una lista che contiene in modo ordinato tutte le drawing area
                _riga1=[_darea_1_1,_darea_1_2,_darea_1_3,_darea_1_4,_darea_1_5,_darea_1_6,_darea_1_7,_darea_1_8,_darea_1_9,_darea_1_10,_darea_1_11,_darea_1_12,_darea_1_13,_darea_1_14,_darea_1_15,_darea_1_16,_darea_1_17,_darea_1_18,_darea_1_19,_darea_1_20,_darea_1_21,_darea_1_22,_darea_1_23,_darea_1_24]
        

                #inserisco in tabella le 24 drawing area che ho appena creato e le coloro di rosso
                for i in range(0,24):
                        _table.attach(_riga1[i], i, i+1, 5, 6, xpadding=1, ypadding=0)
                        _riga1[i].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))
                
                
                #il codice di seguito serve per measure.xml                
                _xmldoc=minidom.parse(paths.XML_DIR+paths.DIR_SEP+'measure.xml')
                _start=_xmldoc.documentElement.getElementsByTagName('start')[0].firstChild.data

                #la versione 2.5 di python ha un bug nella funzione strptime che non riesce a leggere i microsecondi (%f) 
                def _str2datetime(s):
                        parts = s.split('.')
                        dt = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
                        return dt.replace(microsecond=int(parts[1]))

                _inizioMisure=_str2datetime(str(_start))#inizioMisure è datetime
                _coloreCelle[_inizioMisure.hour]='green'
                _slots=_xmldoc.documentElement.getElementsByTagName('slot')
                for _slot in _slots:
                        _misura=str(_slot.firstChild.data)
                        _misuraDataTime=_str2datetime(_misura)
                        _delta=_misuraDataTime-_inizioMisure
                        if(_delta.days<3):#ovvero se la misura è valida
                                _coloreCelle[_misuraDataTime.hour]='green'
                                
                _n=0
                for i in range(0,24):
                        _riga1[i].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(_coloreCelle[i]))
                        if(_coloreCelle[i]=='green'):
                                _n=_n+1                     
                                 
                _label1 = gtk.Label("<b><big>Nemesys</big></b>")
                _label2 = gtk.Label("<big>Data inizio misurazioni: "+str(_inizioMisure.day)+"/"+str(_inizioMisure.month)+"/"+str(_inizioMisure.year)+" alle ore "+str(_inizioMisure.hour)+":"+str(_inizioMisure.minute)+":"+str(_inizioMisure.second)+"</big>")
                _label3 = gtk.Label("<big>Si ricorda che la misurazione va completata entro tre giorni dal suo inizio</big>")
                _label4 = gtk.Label("<big>Stato di avanzamento della misura: "+str(_n)+" misure su 24</big>")
                _label1.set_use_markup(True)
                _label2.set_use_markup(True)
                _label3.set_use_markup(True)
                _label4.set_use_markup(True)

                _table.attach(_label1, 0, 24, 0, 1)
                _table.attach(_label2, 0, 24, 1, 2)
                _table.attach(_label3, 0, 24, 2, 3)
                _table.attach(_label4, 0, 24, 3, 4)

                self._win.show_all()
                winAperta=True

                       
        
        def _abilitaDisabilitaPopUp(self,widget):
                global statoPopUp
                self._item2.destroy() 
                if(statoPopUp=="ON"):
                        statoPopUp="OFF"
                        self._item2 = gtk.ImageMenuItem('Abilita Pop-up')
                else:
                        statoPopUp="ON"
                        self._item2 = gtk.ImageMenuItem('Disabilita Pop-up')
                self._img_sm = gtk.image_new_from_stock('gtk-dialog-warning', gtk.ICON_SIZE_MENU)
                self._item2.set_image(self._img_sm)
                self._item2.connect('activate', self._abilitaDisabilitaPopUp)
                self._menu.insert(self._item2,1)



        def _serviziOnline(self,widget):
                webbrowser.open("http://misurainternet.fub.it/login_form.php")
                
        def _info(self,widget):
                global infoAperta
                if infoAperta:#non do all'utente la possibilità di aprire n finestre info
                        self._infoMessage.destroy()
                infoAperta=True
                self._infoMessage=gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Nemesys e' stato realizzato da:\n .. \n .. \n ..")
                self._infoMessage.show()
                self._infoMessage.set_icon_from_file(paths.ICON_PATH+paths.DIR_SEP+"icon.png")
                if self._infoMessage.run()==gtk.RESPONSE_CLOSE:
                        self._infoMessage.destroy()
                        infoAperta=False
               
        def _callback(self,widget, button, time, menu):
                self._menu.popdown()
                self._menu.show_all()
                #self.menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.icon)
                self._menu.popup(None, None, None, button, time, self._icon)#elimina la freccia per visualizzare il menu per intero
                

        def _destroy(self, widget, data=None):#quando esco dal programma
                self._icon.set_visible(False)
                self._menu.destroy()
                if (self._win!=None):
                        self._win.destroy()
                if(self._infoMessage!=None):
                        self._infoMessage.destroy()
                controller.stop()#fermo il thread di controllo
                return gtk.main_quit()


        def _crea_menu(self,widget):
                global statoPopUp
                if(self._menu!=None):
                    self._menu.destroy()
                self._menu = gtk.Menu()
                if(winAperta==False):
                        self._win=None
                if(infoAperta==False):
                        self._infoMessage=None

                self._icona=None
                self._stringa=None
                self._vecchiaIcona=None
                self._vecchiaStringa=None

                self._icona=paths.ICON_PATH+paths.DIR_SEP+self._status._icon
                self._stringa=self._status._message
                
                self._icon = gtk.status_icon_new_from_file(self._icona)
                self._icon.set_tooltip(self._stringa)      
                self._icon.connect('popup-menu',self._callback,self._menu)

                self._item1 = gtk.ImageMenuItem('Stato misurazione')
                self._img_sm = gtk.image_new_from_stock('gtk-execute', gtk.ICON_SIZE_MENU)
                self._item1.set_image(self._img_sm)
                self._item1.connect('activate', self.statoMisura)
                self._menu.append(self._item1)
                
                if(statoPopUp=="ON"):
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
        iniziale = status.PAUSE#parto dallo stato iniziale "bianco"
        trayicon = TrayIcon("http://localhost:21401/", iniziale)
        controller = _Controller(trayicon)
        controller.start()
        trayicon.main()


