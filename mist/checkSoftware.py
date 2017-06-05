#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import re
import webbrowser
import wx
from urlparse import urlparse

import httputils
from optionParser import OptionParser
from registration import registration

## OPTIONAL ##
# from usbkey import check_usb, move_on_key

SWN = 'MisuraInternet Speed Test'

logger = logging.getLogger(__name__)

#Data di scadenza
dead_date = 22221111

url_version = "https://speedtest.agcom244.fub.it/Version"
area_privata = "https://www.misurainternet.it"        # /login_form.php"


class CheckSoftware():

    def __init__(self, version):
        
        parser = OptionParser(version = version, description = '')
        (options, args, md5conf) = parser.parse()
        self._httptimeout = options.httptimeout
        self._clientid = options.clientid
        self._thisVersion = version
        self._lastVersion = version
        self._stillDay = "unknown"
        
        
    def _showDialog(self, dialog):
        msgBox = wx.MessageDialog(None, dialog['message'], dialog['title'], dialog['style'])
        res = msgBox.ShowModal()
        msgBox.Destroy()
        return res
    
         
    def _softwareVersion(self):
        versionOK = True
        deadlineOK = True
        
        url = urlparse(url_version)
        connection = httputils.getverifiedconnection(url = url, certificate = None, timeout = self._httptimeout)
        try:
            connection.request('GET', '%s?speedtest=true&version=%s' % (url.path, self._thisVersion))
            data = connection.getresponse().read()
            #data = "1.1.1:8"        # FAKE REPLY #
            #logger.debug(data)
            
            if (re.search('(\.?\d+)+:', data) is None):
                logger.warning("Non e' stato possibile controllare la versione per risposta errata del server.")
                return True
            
            data = data.split(":")
            
            #### VERSION ####
            version = re.search('(\.?\d+)+',data[0])
            '''
            una stringa di uno o piu' numeri                                        \d+
            ozionalmente preceduta da un punto                                    \.?
            che si ripeta piu' volte                                                        (\.?\d+)+
            '''
            if (version is not None):
                self._lastVersion = version.string
                logger.info("L'ultima versione sul server e' la %s" % self._lastVersion)
                if (self._thisVersion != self._lastVersion):
                    logger.info("Nuova versione disponbile. [ this:%s | last:%s ]" % (self._thisVersion, self._lastVersion))
                    newVersion = \
                    { \
                    "style":wx.YES|wx.NO|wx.ICON_INFORMATION, \
                    "title":"%s %s" % (SWN, self._thisVersion), \
                    "message": \
                    '''
                    E' disponibile una nuova versione:
                    %s %s

                    E' possibile effetuare il download dalla relativa sezione
                    nell'area privata del sito www.misurainternet.it

                    Vuoi scaricare ora la nuova versione?
                    ''' % (SWN, self._lastVersion)
                    }
                    res = self._showDialog(newVersion)
                    if res == wx.ID_YES:
                        versionOK = False
                        logger.info("Si e' scelto di scaricare la nuova versione del software.")
                        webbrowser.open(area_privata, new=2, autoraise=True)
                        return versionOK
                    else:
                        logger.info("Si e' scelto di continuare ad utilizzare la vecchia versione del software.")
                        versionOK = True
                else:
                    versionOK = True
                    logger.info("E' in esecuzione l'ultima versione del software.")
            else:
                versionOK = True
                logger.error("Errore nella verifica della presenza di una nuova versione.")
                
            #### DEADLINE ####
            deadline = re.search('(-?\d+)(?!.)',data[1])
            '''
            una stringa di uno o piu' numeri                                        \d+
            ozionalmente preceduta da un segno meno                         -?
            ma che non abbia alcun carattere dopo                             (?!.) 
            '''
            if (deadline is not None):
                self._stillDay = deadline.string
                logger.info("Giorni rimasti comunicati dal server: %s" % self._stillDay)
                if (int(self._stillDay)>=0):
                    deadlineOK = True
                    logger.info("L'attuale versione %s scade fra %s giorni." % (self._thisVersion, self._stillDay))
                    beforeDeadline = \
                    { \
                    "style":wx.OK|wx.ICON_EXCLAMATION, \
                    "title":"%s %s" % (SWN, self._thisVersion), \
                    "message": \
                    '''
                    Questa versione di %s
                    potra' essere utilizzata ancora per %s giorni.
                    ''' % (SWN, self._stillDay)
                    }
                    res = self._showDialog(beforeDeadline)
                else:
                    deadlineOK = False
                    self._stillDay = -(int(self._stillDay))
                    logger.info("L'attuale versione %s e' scaduta da %s giorni." % (self._thisVersion, self._stillDay))
                    afterDeadline = \
                    { \
                    "style":wx.OK|wx.ICON_EXCLAMATION, \
                    "title":"%s %s" % (SWN, self._thisVersion), \
                    "message": \
                    '''
                    Questa versione di %s
                    e' scaduta da %s giorni e pertanto
                    non potra' piu' essere utilizzata.
                    ''' % (SWN, self._stillDay)
                    }
                    res = self._showDialog(afterDeadline)
            else:
                deadlineOK = True
                logger.info("Questa versione del software non ha ancora scadenza.")
                
        except Exception as e:
            logger.error("Impossibile controllare se ci sono nuove versioni. Errore: %s." % e)
            
        return (versionOK and deadlineOK)
        
        
    def _isRegistered(self):
        regOK = registration(self._clientid)
        return regOK
        
        
    def _check_usbkey(self):
        check = True
        # if (not check_usb()):
            # self._cycle.clear()
            # logger.info('Verifica della presenza della chiave USB fallita')
            # wx.CallAfter(self._gui._update_messages, "Per l'utilizzo di questo software occorre disporre della opportuna chiave USB. Inserire la chiave nel computer e riavviare il programma.", 'red')
        return check
        
        
    def checkIT(self):
        checkOK = False
        check_list = {1:self._softwareVersion,2:self._isRegistered}
        for check in check_list:
            checkOK = check_list[check]()
            if not checkOK:
                break
        return checkOK




if __name__ == '__main__':
    import log_conf
    log_conf.init_log()
    app = wx.App(False)
    checker = CheckSoftware("1.1.2")
    checker.checkIT()
