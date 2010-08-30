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


from time import sleep

import pygtk
pygtk.require('2.0')
import gtk
import webbrowser
import xmlrpclib
import status

from xml.dom import minidom

class TrayIcon:
    def __init__(self, url, status):
        self._status = status
        self._proxy = xmlrpclib.ServerProxy(url)
        print 'Creo menu'
        self.crea_menu(self)

    def _loop(self):
        print 'Loop'
        while (True):
            try:
                self._setstatus(self._proxy.getstatus())
            except Exception: # Catturare l'eccezione dovita a errore di comunicazione col demone
                self._setstatus(status.ERROR)

            sleep(30)
            

    def _setstatus(self, status):
        self._status = status
        self._updatestatus()

    def _updatestatus(self):
        '''
        Cambia l'icona nel vassoio di sistema e visualizza il messaggio nel popup
        '''
        self.icon.set_visible(False)
        self.item.destroy()
        self.img_sm.destroy()
        self.menu.destroy()
        self.crea_menu(self)

    def statoMisura(self, widget):   #al momento stampo staticamente i quadrati colorati e il numero di misura, in realtà questa funzione ne chiamerà una
        #che mi restituisce o una tabella o il modo di crearmene una leggendo lo stato dall'XML salvato in locale
        win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        win.set_title("Stato Misura Ne.Me.Sys.")
        win.set_position(gtk.WIN_POS_CENTER)
        win.set_default_size(700, 400)
        win.set_icon_from_file("icon.png")
        color = gtk.gdk.color_parse('#FFF')
        win.modify_bg(gtk.STATE_NORMAL, color)
        win.set_border_width(20)

        coloreCelle = dict()#lo uso per associare ad ogni colonna lo stato red o green, userò poi il dizionario per fare "l'or" nella quarta riga
        for n in range(49):#inizializzo tutto allo stato rosso
            coloreCelle[n] = 'red'

 
        label1 = gtk.Label("<b><big>Ne.Me.Sys</big></b>")
        label2 = gtk.Label("<big>Stato di avanzamento della misura</big>")
        label1.set_use_markup(True)
        label2.set_use_markup(True)

        table = gtk.Table(7, 48, False)#7 righe, 48 colonne
        win.add(table)

        table.attach(label1, 0, 48, 0, 1)
        table.attach(label2, 0, 48, 1, 2)


        #qui di seguito c'è la creazione delle varie drawingarea, il loro posizionamento in tabella e l'assegnamento del colore rosso
        #successivamente viene letto l'xml e colorate di verde le celle opportune
     
                
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
        darea_1_25 = gtk.DrawingArea()
        darea_1_26 = gtk.DrawingArea()
        darea_1_27 = gtk.DrawingArea()
        darea_1_28 = gtk.DrawingArea()
        darea_1_29 = gtk.DrawingArea()
        darea_1_30 = gtk.DrawingArea()
        darea_1_31 = gtk.DrawingArea()
        darea_1_32 = gtk.DrawingArea()
        darea_1_33 = gtk.DrawingArea()
        darea_1_34 = gtk.DrawingArea()
        darea_1_35 = gtk.DrawingArea()
        darea_1_36 = gtk.DrawingArea()
        darea_1_37 = gtk.DrawingArea()
        darea_1_38 = gtk.DrawingArea()
        darea_1_39 = gtk.DrawingArea()
        darea_1_40 = gtk.DrawingArea()
        darea_1_41 = gtk.DrawingArea()
        darea_1_42 = gtk.DrawingArea()
        darea_1_43 = gtk.DrawingArea()
        darea_1_44 = gtk.DrawingArea()
        darea_1_45 = gtk.DrawingArea()
        darea_1_46 = gtk.DrawingArea()
        darea_1_47 = gtk.DrawingArea()
        darea_1_48 = gtk.DrawingArea()
                
        #riga1 è una lista che contiene in modo ordinato tutte le drawing area della prima riga
        riga1 = [darea_1_1, darea_1_2, darea_1_3, darea_1_4, darea_1_5, darea_1_6, darea_1_7, darea_1_8, darea_1_9, darea_1_10, darea_1_11, darea_1_12, darea_1_13, darea_1_14, darea_1_15, darea_1_16, darea_1_17, darea_1_18, darea_1_19, darea_1_20, darea_1_21, darea_1_22, darea_1_23, darea_1_24, darea_1_25, darea_1_26, darea_1_27, darea_1_28, darea_1_29, darea_1_30, darea_1_31, darea_1_32, darea_1_33, darea_1_34, darea_1_35, darea_1_36, darea_1_37, darea_1_38, darea_1_39, darea_1_40, darea_1_41, darea_1_42, darea_1_43, darea_1_44, darea_1_45, darea_1_46, darea_1_47, darea_1_48]
        

        #inserisco in tabella le 48 drawing area che ho appena creato e le coloro di rosso
        for i in range(0, 48):
            table.attach(riga1[i], i, i + 1, 2, 3, xpadding=1, ypadding=10)
            riga1[i].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))
                


        #creo le 48 drawing area della seconda riga
        darea_2_1 = gtk.DrawingArea()
        darea_2_2 = gtk.DrawingArea()
        darea_2_3 = gtk.DrawingArea()
        darea_2_4 = gtk.DrawingArea()
        darea_2_5 = gtk.DrawingArea()
        darea_2_6 = gtk.DrawingArea()
        darea_2_7 = gtk.DrawingArea()
        darea_2_8 = gtk.DrawingArea()
        darea_2_9 = gtk.DrawingArea()
        darea_2_10 = gtk.DrawingArea()
        darea_2_11 = gtk.DrawingArea()
        darea_2_12 = gtk.DrawingArea()
        darea_2_13 = gtk.DrawingArea()
        darea_2_14 = gtk.DrawingArea()
        darea_2_15 = gtk.DrawingArea()
        darea_2_16 = gtk.DrawingArea()
        darea_2_17 = gtk.DrawingArea()
        darea_2_18 = gtk.DrawingArea()
        darea_2_19 = gtk.DrawingArea()
        darea_2_20 = gtk.DrawingArea()
        darea_2_21 = gtk.DrawingArea()
        darea_2_22 = gtk.DrawingArea()
        darea_2_23 = gtk.DrawingArea()
        darea_2_24 = gtk.DrawingArea()
        darea_2_25 = gtk.DrawingArea()
        darea_2_26 = gtk.DrawingArea()
        darea_2_27 = gtk.DrawingArea()
        darea_2_28 = gtk.DrawingArea()
        darea_2_29 = gtk.DrawingArea()
        darea_2_30 = gtk.DrawingArea()
        darea_2_31 = gtk.DrawingArea()
        darea_2_32 = gtk.DrawingArea()
        darea_2_33 = gtk.DrawingArea()
        darea_2_34 = gtk.DrawingArea()
        darea_2_35 = gtk.DrawingArea()
        darea_2_36 = gtk.DrawingArea()
        darea_2_37 = gtk.DrawingArea()
        darea_2_38 = gtk.DrawingArea()
        darea_2_39 = gtk.DrawingArea()
        darea_2_40 = gtk.DrawingArea()
        darea_2_41 = gtk.DrawingArea()
        darea_2_42 = gtk.DrawingArea()
        darea_2_43 = gtk.DrawingArea()
        darea_2_44 = gtk.DrawingArea()
        darea_2_45 = gtk.DrawingArea()
        darea_2_46 = gtk.DrawingArea()
        darea_2_47 = gtk.DrawingArea()
        darea_2_48 = gtk.DrawingArea()

        #riga2 è una lista che contiene in modo ordinato tutte le drawing area della seconda riga
        riga2 = [darea_2_1, darea_2_2, darea_2_3, darea_2_4, darea_2_5, darea_2_6, darea_2_7, darea_2_8, darea_2_9, darea_2_10, darea_2_11, darea_2_12, darea_2_13, darea_2_14, darea_2_15, darea_2_16, darea_2_17, darea_2_18, darea_2_19, darea_2_20, darea_2_21, darea_2_22, darea_2_23, darea_2_24, darea_2_25, darea_2_26, darea_2_27, darea_2_28, darea_2_29, darea_2_30, darea_2_31, darea_2_32, darea_2_33, darea_2_34, darea_2_35, darea_2_36, darea_2_37, darea_2_38, darea_2_39, darea_2_40, darea_2_41, darea_2_42, darea_2_43, darea_2_44, darea_2_45, darea_2_46, darea_2_47, darea_2_48]

        #inserisco in tabella le 48 drawing area che ho appena creato e le coloro di rosso
        for i in range(0, 48):
            table.attach(riga2[i], i, i + 1, 3, 4, xpadding=1, ypadding=10)
            riga2[i].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))
                     

        #creo le 48 drawing area della terza riga
        darea_3_1 = gtk.DrawingArea()
        darea_3_2 = gtk.DrawingArea()
        darea_3_3 = gtk.DrawingArea()
        darea_3_4 = gtk.DrawingArea()
        darea_3_5 = gtk.DrawingArea()
        darea_3_6 = gtk.DrawingArea()
        darea_3_7 = gtk.DrawingArea()
        darea_3_8 = gtk.DrawingArea()
        darea_3_9 = gtk.DrawingArea()
        darea_3_10 = gtk.DrawingArea()
        darea_3_11 = gtk.DrawingArea()
        darea_3_12 = gtk.DrawingArea()
        darea_3_13 = gtk.DrawingArea()
        darea_3_14 = gtk.DrawingArea()
        darea_3_15 = gtk.DrawingArea()
        darea_3_16 = gtk.DrawingArea()
        darea_3_17 = gtk.DrawingArea()
        darea_3_18 = gtk.DrawingArea()
        darea_3_19 = gtk.DrawingArea()
        darea_3_20 = gtk.DrawingArea()
        darea_3_21 = gtk.DrawingArea()
        darea_3_22 = gtk.DrawingArea()
        darea_3_23 = gtk.DrawingArea()
        darea_3_24 = gtk.DrawingArea()
        darea_3_25 = gtk.DrawingArea()
        darea_3_26 = gtk.DrawingArea()
        darea_3_27 = gtk.DrawingArea()
        darea_3_28 = gtk.DrawingArea()
        darea_3_29 = gtk.DrawingArea()
        darea_3_30 = gtk.DrawingArea()
        darea_3_31 = gtk.DrawingArea()
        darea_3_32 = gtk.DrawingArea()
        darea_3_33 = gtk.DrawingArea()
        darea_3_34 = gtk.DrawingArea()
        darea_3_35 = gtk.DrawingArea()
        darea_3_36 = gtk.DrawingArea()
        darea_3_37 = gtk.DrawingArea()
        darea_3_38 = gtk.DrawingArea()
        darea_3_39 = gtk.DrawingArea()
        darea_3_40 = gtk.DrawingArea()
        darea_3_41 = gtk.DrawingArea()
        darea_3_42 = gtk.DrawingArea()
        darea_3_43 = gtk.DrawingArea()
        darea_3_44 = gtk.DrawingArea()
        darea_3_45 = gtk.DrawingArea()
        darea_3_46 = gtk.DrawingArea()
        darea_3_47 = gtk.DrawingArea()
        darea_3_48 = gtk.DrawingArea()

        #riga3 è una lista che contiene in modo ordinato tutte le drawing area della terza riga
        riga3 = [darea_3_1, darea_3_2, darea_3_3, darea_3_4, darea_3_5, darea_3_6, darea_3_7, darea_3_8, darea_3_9, darea_3_10, darea_3_11, darea_3_12, darea_3_13, darea_3_14, darea_3_15, darea_3_16, darea_3_17, darea_3_18, darea_3_19, darea_3_20, darea_3_21, darea_3_22, darea_3_23, darea_3_24, darea_3_25, darea_3_26, darea_3_27, darea_3_28, darea_3_29, darea_3_30, darea_3_31, darea_3_32, darea_3_33, darea_3_34, darea_3_35, darea_3_36, darea_3_37, darea_3_38, darea_3_39, darea_3_40, darea_3_41, darea_3_42, darea_3_43, darea_3_44, darea_3_45, darea_3_46, darea_3_47, darea_3_48]

        #inserisco in tabella le 48 drawing area che ho appena creato e le coloro di rosso
        for i in range(0, 48):
            table.attach(riga3[i], i, i + 1, 4, 5, xpadding=1, ypadding=10)
            riga3[i].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))
 

        #ultima riga matrice, i colori li metto in base al dizionario, in questo modo ottengo l'or automaticamente
        darea_4_1 = gtk.DrawingArea()
        darea_4_2 = gtk.DrawingArea()
        darea_4_3 = gtk.DrawingArea()
        darea_4_4 = gtk.DrawingArea()
        darea_4_5 = gtk.DrawingArea()
        darea_4_6 = gtk.DrawingArea()
        darea_4_7 = gtk.DrawingArea()
        darea_4_8 = gtk.DrawingArea()
        darea_4_9 = gtk.DrawingArea()
        darea_4_10 = gtk.DrawingArea()
        darea_4_11 = gtk.DrawingArea()
        darea_4_12 = gtk.DrawingArea()
        darea_4_13 = gtk.DrawingArea()
        darea_4_14 = gtk.DrawingArea()
        darea_4_15 = gtk.DrawingArea()
        darea_4_16 = gtk.DrawingArea()
        darea_4_17 = gtk.DrawingArea()
        darea_4_18 = gtk.DrawingArea()
        darea_4_19 = gtk.DrawingArea()
        darea_4_20 = gtk.DrawingArea()
        darea_4_21 = gtk.DrawingArea()
        darea_4_22 = gtk.DrawingArea()
        darea_4_23 = gtk.DrawingArea()
        darea_4_24 = gtk.DrawingArea()
        darea_4_25 = gtk.DrawingArea()
        darea_4_26 = gtk.DrawingArea()
        darea_4_27 = gtk.DrawingArea()
        darea_4_28 = gtk.DrawingArea()
        darea_4_29 = gtk.DrawingArea()
        darea_4_30 = gtk.DrawingArea()
        darea_4_31 = gtk.DrawingArea()
        darea_4_32 = gtk.DrawingArea()
        darea_4_33 = gtk.DrawingArea()
        darea_4_34 = gtk.DrawingArea()
        darea_4_35 = gtk.DrawingArea()
        darea_4_36 = gtk.DrawingArea()
        darea_4_37 = gtk.DrawingArea()
        darea_4_38 = gtk.DrawingArea()
        darea_4_39 = gtk.DrawingArea()
        darea_4_40 = gtk.DrawingArea()
        darea_4_41 = gtk.DrawingArea()
        darea_4_42 = gtk.DrawingArea()
        darea_4_43 = gtk.DrawingArea()
        darea_4_44 = gtk.DrawingArea()
        darea_4_45 = gtk.DrawingArea()
        darea_4_46 = gtk.DrawingArea()
        darea_4_47 = gtk.DrawingArea()
        darea_4_48 = gtk.DrawingArea()
                
        #riga4 è una lista che contiene in modo ordinato tutte le drawing area della quarta riga
        riga4 = [darea_4_1, darea_4_2, darea_4_3, darea_4_4, darea_4_5, darea_4_6, darea_4_7, darea_4_8, darea_4_9, darea_4_10, darea_4_11, darea_4_12, darea_4_13, darea_4_14, darea_4_15, darea_4_16, darea_4_17, darea_4_18, darea_4_19, darea_4_20, darea_4_21, darea_4_22, darea_4_23, darea_4_24, darea_4_25, darea_4_26, darea_4_27, darea_4_28, darea_4_29, darea_4_30, darea_4_31, darea_4_32, darea_4_33, darea_4_34, darea_4_35, darea_4_36, darea_4_37, darea_4_38, darea_4_39, darea_4_40, darea_4_41, darea_4_42, darea_4_43, darea_4_44, darea_4_45, darea_4_46, darea_4_47, darea_4_48]

        #inserisco in tabella le 48 drawing area che ho appena creato e le coloro di rosso
        for i in range(0, 48):
            table.attach(riga4[i], i, i + 1, 6, 7, xpadding=1, ypadding=10)
            riga4[i].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))

                
        #il codice di seguito serve per esempio2.xml
        xmldoc = minidom.parse('esempio2.xml')
        days = xmldoc.documentElement.getElementsByTagName('day')
        for day in days:
            slots = day.getElementsByTagName('slot')
            giorno = int(day.attributes['id'].nodeValue)
            for slot in slots:
                slotVerde = int(slot.attributes['id'].nodeValue)
                if giorno == 1:
                    riga1[slotVerde-1].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("green"))
                    coloreCelle[slotVerde-1] = 'green'
                elif giorno == 2:
                    riga2[slotVerde-1].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("green"))
                    coloreCelle[slotVerde-1] = 'green'
                elif giorno == 3:
                    riga3[slotVerde-1].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("green"))
                    coloreCelle[slotVerde-1] = 'green'
                        

        #qui creo la stringa che mi indica a che passo sono arrivato
        numero = 0
        for n in range(49):
            if coloreCelle[n] == 'green':
                numero = numero + 1
        numeroStep = str(numero)
        stringa = "<big>Sono state effettuate " + numeroStep + " misure su 48</big>"
        label3 = gtk.Label(stringa)
        label3.set_use_markup(True)
        table.attach(label3, 0, 48, 5, 6, xpadding=1, ypadding=1)

        for i in range(0, 48):
            riga4[i].modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(coloreCelle[i]))

        #grammarNode = xmldoc.firstChild
        #print grammarNode.childNodes[0].toxml()
        #print grammarNode.childNodes[1].toxml()
        #print grammarNode.childNodes[2].toxml()
        #print grammarNode.childNodes[3].toxml()
                
        #il codice qui commentato mi legge tutti i nodi del file xml secondo l'identazione di pantanetti
        '''
                xmldoc = minidom.parse('C:\Users\Valerio\Desktop\prove python\prova2_nemesys\esempio.xml')
                days=xmldoc.documentElement.getElementsByTagName('day')
                for day in days:
                        print 'Day: '+day.attributes['id'].nodeValue
                        hours=xmldoc.documentElement.getElementsByTagName('hour')
                        for hour in hours:
                                print 'Hour: '+hour.attributes['id'].nodeValue
                                print hour.childNodes[0].nodeValue
                
                '''
                
        win.show_all()
             
                
        
    def abilitaDisabilitaPopUp(self, widget):
        global statoPopUp
        if(statoPopUp == "ON"):
            statoPopUp = "OFF"
        else:
            statoPopUp = "ON"
                
        print "statoPopUp= " + statoPopUp

        self._updatestatus()

    def abilitaDisabilitaDemone(self, widget):
        global statoDemone
        if(statoDemone == "ON"):
            statoDemone = "OFF"
            #QUI VA MESSO IL CODICE PER SPEGNERE IL DEMONE
        else:
            statoDemone = "ON"
            #QUI VA MESSO IL CODICE PER ACCENDERE IL DEMONE
        print "statoDemone= " + statoDemone

        self._updatestatus()

    def serviziOnline(self, widget):
        webbrowser.open("http://misurainternet.fub.it/login_form.php")
                
    def info(self, widget):
        message = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE, "Ne.Me.Sys e' stato realizzato da:\n .. \n .. \n ..")
        message.show()
        message.set_icon_from_file("icon.png")
        resp = message.run()
        if resp == gtk.RESPONSE_CLOSE:
            message.destroy()
               
    def callback(self, widget, button, time, menu):
        menu.show_all()
        menu.popup(None, None, gtk.status_icon_position_menu, button, time, self.icon)

    def destroy(self, widget, data=None):
        self.icon.set_visible(False)
        self.item.destroy()
        self.img_sm.destroy()
        self.menu.destroy()
        return gtk.main_quit()

    def crea_menu(self, widget):
        stato = self._status
        global statoPopUp
        global statoDemone
                
        self.menu = gtk.Menu()

        icona = None
        stringa = None
                
        if stato == "v":
            icona = "icon_verde.png"
            stringa = "NeMeSys sta effettuando una misura..."
        elif stato == "a":
            icona = "icon_arancio.png"
            stringa = "NeMeSys effettuera' una misura nella prossima ora"
        elif stato == status.PAUSE:
            icona = "icon_bianca.png"
            stringa = "NeMeSys non effettuera' una misura nella prossima ora"
        elif stato == status.ERROR:
            icona = "icon_rossa.png"
            stringa = "NeMeSys non risponde alle richieste, riavviare manualmente"
        else:
            icona = "icon_blu.png"
            stringa = "NeMeSys ha terminato le misurazioni"

        self.icon = gtk.status_icon_new_from_file(icona)
        self.icon.set_tooltip(stringa)
        self.icon.connect('popup-menu', self.callback, self.menu)

        self.item = gtk.ImageMenuItem('Stato misurazione')
        self.img_sm = gtk.image_new_from_stock('gtk-execute', gtk.ICON_SIZE_MENU)
        self.item.set_image(self.img_sm)
        self.item.connect('activate', self.statoMisura)
        self.menu.append(self.item)

        if(statoDemone == "ON"):
            self.item = gtk.ImageMenuItem('Stop misure')
            self.img_sm = gtk.image_new_from_stock('gtk-disconnect', gtk.ICON_SIZE_MENU)
        else:
            self.item = gtk.ImageMenuItem('Start misure')
            self.img_sm = gtk.image_new_from_stock('gtk-connect', gtk.ICON_SIZE_MENU)
        self.item.set_image(self.img_sm)
        self.item.connect('activate', self.abilitaDisabilitaDemone)
        self.menu.append(self.item)
                
        if(statoPopUp == "ON"):
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
        print 'Main'
        gtk.main()
        # TODO Implementare il controllo dello stato del server su un thread differente -> questo modifica l'icona nel vassoio
        self._loop()

if __name__ == "__main__":
    # TODO
    statoPopUp = "ON" # Per discriminare fra abilita e disabilita popup
    statoDemone = "ON"
    trayicon = TrayIcon("https://localhost:21401", status.ERROR)
    trayicon.main()

