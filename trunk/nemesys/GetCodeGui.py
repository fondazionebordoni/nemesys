# GetCodeGui.py
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

from Tkinter import *
import tkFont
from threading import Thread
import time
import tkMessageBox

class GetCodeGui(Frame):
    
    def sendMsg(self):
        self.result=self.code.get()
        self.quit()

    def createWidgets(self):
        self.Title = Label(self)
        self.Title["text"] = "\nInserire codice di licenza per NeMeSys.\nIl codice licenza e' riportato nella propria area privata sul sito www.misurainternet.it,\nnella sezione Licenze e PDF misure.\n"
        self.Title.pack({"side": "top"})

        self.invio = Button(self)
        self.invio["text"] = "invio",
        self.invio["command"] = self.sendMsg
        self.invio.pack({"side": "bottom"})        

        self.code = Entry(self)
        self.code.pack({"side": "bottom"})

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack(side = BOTTOM)
        self.createWidgets()

class Errore (Thread):
    def __init__(self,error):
        Thread.__init__(self)
        self.error = error
    
    def run(self):
        if self.error=='ace':
            ACEmain()
        elif self.error=='download':
            Downloadmain()
        elif self.error =='code':
            CodeError()

def GCGmain():
    rootGCG = Tk()
    rootGCG.wm_iconbitmap('..\\nemesys.ico')
    appGCG = GetCodeGui(master=rootGCG)
    appGCG.master.title("Codice licenza Nemesys")
    appGCG.mainloop()
    appresult = str(appGCG.result)
    rootGCG.destroy()
    return appresult

def ACEmain():
    rootACE = Tk()
    rootACE.withdraw()
    title='Nemesys Error'
    message="Errore nella lettura del codice di attivazione.\nControllare il file di configurazione cfg.properties."
    tkMessageBox.showerror(title,message,parent=rootACE)
    rootACE.destroy()

def Downloadmain():
    rootDown = Tk()
    rootDown.withdraw()
    title='Nemesys Error'
    message="Impossibile installare il servizio NeMeSys, errore nel download del file di configurazione.\nNon avviare il servizio NeMeSys deselezionando l'opzione:\n\n\t\t'Avvia il servizio NeMeSys'.\t\n\nPer rimuovere tutti i componenti di NeMeSys dal computer, eseguire la procedura di disinstallazione.\n"
    tkMessageBox.showerror(title,message,parent=rootDown)
    rootDown.destroy()

def CodeError():
    rootCode = Tk()
    rootCode.withdraw()
    title='Nemesys Error'
    message="Codice di attivazione non inserito: impossibile procedere con l'installazione di NeMeSys.\nPer rimuovere tutti i componenti di NeMeSys dal computer, eseguire la procedura di disinstallazione.\n"
    tkMessageBox.showerror(title,message,parent=rootCode)
    rootCode.destroy()    

if __name__ == '__main__':
    print GCGmain()