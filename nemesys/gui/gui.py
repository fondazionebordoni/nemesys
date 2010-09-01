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

from xml.dom import minidom

from datetime import datetime

from time import sleep




class TrayIcon:
        
        def __init__(self):
                self.crea_menu(self)

        def statoMisura(self,widget):
                global winAperta
                if(winAperta):
                        self.win.destroy()#così lascio aprire una finestra sola relativa allo stato della misura
                self.win=gtk.Window(gtk.WINDOW_TOPLEVEL)
                self.win.set_title("Stato Misura Nemesys")
                self.win.set_position(gtk.WIN_POS_CENTER)
                self.win.set_default_size(600,300)
                self.win.set_resizable(False)
                self.win.set_icon_from_file(paths.ICON_PATH+paths.DIR_SEP+"icon.png")
                color=gtk.gdk.color_parse('#FFF')
                self.win.modify_bg(gtk.STATE_NORMAL, color)
                self.win.set_border_width(20)

                coloreCelle=dict()#lo uso per associare ad ogni colonna lo stato red o green
                for n in range(24):#inizializzo tutto allo stato rosso
                        coloreCelle[n]='red'


                table = gtk.Table(6,24,True)#6 righe, 24 colonne
                self.win.add(table)


                ore=dict()
                for n in range(0,24):
                        hour=str(n)
                        nexthour=str(n+1)
                        if(n<10):
                                hour='0'+hour
                                
                        hour="<small>"+hour+':00'+"</small>"
                        #ore[n]=gtk.Label("<small>"+hour+':00 - '+nexthour+':00'+"</small>")
                        ore[n]=gtk.Label(hour)
                        ore[n].set_use_markup(True)
                        table.attach(ore[n],n,n+1,4,5,xpadding=1, ypadding=0)
  
                
                #creo le 24 drawing area della prima riga                
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

                
                #riga1 è una lista che contiene in modo ordinato tutte le drawing area della prima riga
                riga1=[darea_1_1,darea_1_2,darea_1_3,darea_1_4,darea_1_5,darea_1_6,darea_1_7,darea_1_8,darea_1_9,darea_1_10,darea_1_11,darea_1_12,darea_1_13,darea_1_14,darea_1_15,darea_1_16,darea_1_17,darea_1_18,darea_1_19,darea_1_20,darea_1_21,darea_1_22,darea_1_23,darea_1_24]
        

                #inserisco in tabella le 48 drawing area che ho appena creato e le coloro di rosso
                for i in range(0,24):
                        table.attach(riga1[i], i, i+1, 5, 6, xpadding=1, ypadding=0)
                        riga1[i].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))
                
                
                #il codice di seguito serve per measure.xml                
                xmldoc=minidom.parse(paths.XML_DIR+paths.DIR_SEP+'measure.xml')
                start=xmldoc.documentElement.getElementsByTagName('start')[0].firstChild.data

                #la versione 2.5 di python ha un bug nella funzione strptime che non riesce a leggere i microsecondi (%f) 
                def str2datetime(s):
                        parts = s.split('.')
                        dt = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
                        return dt.replace(microsecond=int(parts[1]))

                inizioMisure=str2datetime(str(start))#inizioMisure è datetime
                coloreCelle[inizioMisure.hour]='green'
                slots=xmldoc.documentElement.getElementsByTagName('slot')
                for slot in slots:
                        misura=str(slot.firstChild.data)
                        misuraDataTime=str2datetime(misura)
                        delta=misuraDataTime-inizioMisure
                        if(delta.days<3):#ovvero se la misura è valida
                                coloreCelle[misuraDataTime.hour]='green'
                                
                n=0
                for i in range(0,24):
                        riga1[i].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(coloreCelle[i]))
                        if(coloreCelle[i]=='green'):
                                n=n+1                     
                                 
                label1 = gtk.Label("<b><big>Nemesys</big></b>")
                label2 = gtk.Label("<big>Data inizio misurazioni: "+str(inizioMisure.day)+"/"+str(inizioMisure.month)+"/"+str(inizioMisure.year)+" alle ore "+str(inizioMisure.hour)+":"+str(inizioMisure.minute)+":"+str(inizioMisure.second)+"</big>")
                label3 = gtk.Label("<big>Si ricorda che la misurazione va completata entro tre giorni dal suo inizio</big>")
                label4 = gtk.Label("<big>Stato di avanzamento della misura: "+str(n)+" misure su 24</big>")
                label1.set_use_markup(True)
                label2.set_use_markup(True)
                label3.set_use_markup(True)
                label4.set_use_markup(True)

                table.attach(label1, 0, 24, 0, 1)
                table.attach(label2, 0, 24, 1, 2)
                table.attach(label3, 0, 24, 2, 3)
                table.attach(label4, 0, 24, 3, 4)

                self.win.show_all()
                winAperta=True

                
                
        
        def abilitaDisabilitaPopUp(self,widget):
                global statoPopUp
                global winAperta
                global infoAperta
                if(self.win==None):
                        winAperta=False
                else:
                        winAperta=True
                if(self.message==None):
                        infoAperta=False
                else:
                        infoAperta=True
                if(statoPopUp=="ON"):
                        statoPopUp="OFF"
                else:
                        statoPopUp="ON"
                
                print "statoPopUp= "+statoPopUp

                #DISTRUGGO L'ICONA E IL MENU E POI LI RICREO AGGIORNATI IN BASE ALLA SCELTA DELL'UTENTE
                self.icon.set_visible(False)
                self.item.destroy()
                self.img_sm.destroy()
                self.menu.destroy()
                self.crea_menu(self)


        def serviziOnline(self,widget):
                webbrowser.open("http://misurainternet.fub.it/login_form.php")
                
        def info(self,widget):
                global infoAperta
                if infoAperta:#non do all'utente la possibilità di aprire n finestre info
                        self.message.destroy()
                infoAperta=True
                self.message=gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Nemesys e' stato realizzato da:\n .. \n .. \n ..")
                self.message.show()
                self.message.set_icon_from_file(paths.ICON_PATH+paths.DIR_SEP+"icon.png")
                resp=self.message.run()
                if resp==gtk.RESPONSE_CLOSE:
                        self.message.destroy()
                        infoAperta=False
               
        def callback(self,widget, button, time, menu):
                menu.show_all()
                menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.icon)

        def destroy(self, widget, data=None):
                self.icon.set_visible(False)
                self.item.destroy()
                self.img_sm.destroy()
                self.menu.destroy()
                if (self.win!=None):
                        self.win.destroy()
                if(self.message!=None):
                        self.message.destroy()
                return gtk.main_quit()


        def crea_menu(self,widget):
                global stato
                global statoPopUp
                global statoDemone
                
                self.menu = gtk.Menu()
                if(winAperta==False):
                        self.win=None
                if(infoAperta==False):
                        self.message=None

                icona=None
                stringa=None
                
                if stato=="v":
                        icona=paths.ICON_PATH+paths.DIR_SEP+"icon_verde.png"
                        stringa="NeMeSys sta effettuando una misura..."
                elif stato=="a":
                        icona=paths.ICON_PATH+paths.DIR_SEP+"icon_arancio.png"
                        stringa="NeMeSys effettuera' una misura nella prossima ora"
                elif stato=="b":
                        icona=paths.ICON_PATH+paths.DIR_SEP+"icon_bianca.png"
                        stringa="NeMeSys non effettuera' una misura nella prossima ora"
                elif stato=="r":
                        icona=paths.ICON_PATH+paths.DIR_SEP+"icon_rossa.png"
                        stringa="NeMeSys non risponde alle richieste, riavviare manualmente"
                elif stato=="c":
                        icona=paths.ICON_PATH+paths.DIR_SEP+"icon_blu.png"
                        stringa="NeMeSys ha terminato le misurazioni"

                self.icon = gtk.status_icon_new_from_file(icona)
                self.icon.set_tooltip(stringa)      
                self.icon.connect('popup-menu',self.callback,self.menu)

                self.item = gtk.ImageMenuItem('Stato misurazione')
                self.img_sm = gtk.image_new_from_stock('gtk-execute', gtk.ICON_SIZE_MENU)
                self.item.set_image(self.img_sm)
                self.item.connect('activate', self.statoMisura)
                self.menu.append(self.item)
                
                if(statoPopUp=="ON"):
                        self.item = gtk.ImageMenuItem('Disabilita Pop-up')
                else:
                        self.item = gtk.ImageMenuItem('Abilita Pop-up')
                self.img_sm = gtk.image_new_from_stock('gtk-dialog-warning', gtk.ICON_SIZE_MENU)
                self.item.set_image(self.img_sm)
                self.item.connect('activate', self.abilitaDisabilitaPopUp)
                self.menu.append(self.item)

                self.item = gtk.ImageMenuItem('Servizi online')
                self.img_sm = gtk.image_new_from_stock('gtk-network', gtk.ICON_SIZE_MENU)
                self.item.set_image(self.img_sm)
                self.item.connect('activate', self.serviziOnline)
                self.menu.append(self.item)

                self.item = gtk.ImageMenuItem('Info')
                self.img_sm = gtk.image_new_from_stock('gtk-about', gtk.ICON_SIZE_MENU)
                self.item.set_image(self.img_sm)
                self.item.connect('activate', self.info)
                self.menu.append(self.item)

                self.item = gtk.SeparatorMenuItem()
                self.menu.append(self.item)
                self.item = gtk.ImageMenuItem(stock_id=gtk.STOCK_QUIT)
                self.item.connect('activate', self.destroy)
                self.menu.append(self.item)
                
        def main(self):
                gtk.main()
                

if __name__ == "__main__":
        stato="v"#stato mi dice se sto misurando: v=verde, a=arancio, b=bianca, r=rosso, c=blu qui decido con che stato partire
        statoPopUp="ON"#per discriminare fra abilita e disabilita popup
        statoDemone="ON"
        winAperta=False
        infoAperta=False
        trayicon = TrayIcon()
        trayicon.main()
