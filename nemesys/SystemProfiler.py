__author__ = "Hewlett-Packard Italiana s.r.l."
__copyright__ = "Copyright 2010, Hewlett-Packard Italiana"
__credits__ = ["HP-Italia"]
__license__ = "Commercial"
__version__ = "$Revision: 1.00.00 $"
"""
    XDSLMeter Auth
 
"""
import platform
import os
import sys
import OSMetrics
import psutil
import time
import logging
import prop
from xml.dom.minidom import Document
from Tkinter import *
from GetCodeGui import GetCodeGui


###  DEFINE CONSTANTS  ###
_win="win32"
_mac="darwin"
_linux="linux2"
_not_available="not available"
_unknown_parameter="unknown parameter"
_PATH = os.path.dirname(sys.argv[0])


###  DISCOVERING PATH  ###
if _PATH == '':
        _PATH="."+os.sep
if _PATH[len(_PATH)-1] != os.sep: _PATH=_PATH+os.sep


###  DISCOVERING PROPERTIES ###
_prop=prop.readProps(_PATH+"cfg"+os.sep+"cfg.properties")

"""
###  FIRST EXECUTION CODE  ###
if 'code' not in _prop:
        root = Tk()
        app = GetCodeGui(master=root)
        app.mainloop()        
        if app.result != '':
                prop.writeProps(_PATH+"cfg"+os.sep+"cfg.properties",'code',app.result)
                _prop=prop.readProps(_PATH+"cfg"+os.sep+"cfg.properties")
                root.destroy()
        else:
                root.destroy()
                sys.exit(0)
"""               

###  LOGGING FUNCTIONALITY  ###
logger = logging.getLogger("system_profiler")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(_PATH+_prop['logfile'])
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)


###  MAIN MODULE CLASS  ###
class SystemProfiler:
        
    
        def __init__(self,fileOutputName,request):
                logger.info("init")
                logger.info("output file:"+fileOutputName)
                self.request = request
                self.fileOutputName = fileOutputName
                self.checkList = ['system','arch','vers','release','processor','cores','availableMemory','ipAddr','macAddr','cpuLoad','memoryLoad','hostNumber','wirelessON','diskRead','diskWrite','firewall','taskList','activeConnections']
                
                if len(self.request) != 0:
                        self.checkList = self.request.keys()
                mydict=dict(self.profiler())
                self.printXML(mydict)
        
        
        def profiler(self):
                logger.info("platform:"+sys.platform)
                metrics=None
                if sys.platform == _win:
                        metrics=OSMetrics.OSMetrics(self.checkList,_win)
                elif sys.platform == _mac:
                        metrics=OSMetrics.OSMetrics(self.checkList,_mac)
                elif sys.platform == _linux:
                        metrics=OSMetrics.OSMetrics(self.checkList,_linux)
                return metrics.fill()
        

        def printXML(self, mydict):
                ### NUOVA FUNZIONE DI STAMPA SU STRINGA ###
                result = '<?xml version="1.0" ?><SystemProfilerResults>'
                keys = mydict.keys()

                for element in keys:
                        result = result+'<'+str(element)+'>'+str(mydict[element])+'</'+str(element)+'>'

                result=result+'</SystemProfilerResults>'
                
                self.result = result

        
###  EXPOSED FUNCTION  ###
def systemProfiler(fileOutputName, request):
        return SystemProfiler(fileOutputName,request).result


###  PRINT RESULTS ON XML FILE  ###
def createDocument(fileOutputName,result):
        outFile = open(fileOutputName,"w")
        outFile.write(result)
        outFile.close()


        """
        ### OLD DOCUMENT XML PRINTING  ###
                
        doc = Document()
        spr = doc.createElement("SystemProfilerResults")
        doc.appendChild(spr)
        keys = mydict.keys()

        for element in keys:
                el = doc.createElement(element)
                spr.appendChild(el)
                value = doc.createTextNode(str(mydict[element]))
                el.appendChild(value)

        outFile = open(self.fileOutputName,"w")
        doc.writexml(outFile)
        outFile.close()
        """       
                

if __name__ == '__main__':
    
    #fileOutputName = _PATH+_prop['xmlfile']
    fileOutputName = 'systemProfiler_result.xml'    
    request = {}
    result = systemProfiler(fileOutputName,request)
    createDocument(fileOutputName,result)
