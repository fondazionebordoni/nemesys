'''
Created on 20/ott/2010

@author: antonio
'''
import platform
import Factory
import RisorsaFactory
import xml.etree.ElementTree as ET
from NemesysException import FactoryException, LocalProfilerException, RisorsaException


def package_home(sep,*args):
        return sep.join(args)
'''
Memorizzare o no l'istanza del profiler creato cosi da non doverlo ricreare successivamente se necessario?
se chi richiama il profiler lo cancella, ma io mantengo il riferimento qui, che succede? testare 
'''    
def getProfiler():
    try:
        name = package_home(".",'SysProf',platform.system().lower(), 'profiler.Profiler')
        istance= Factory.class_forname(name)
    except FactoryException as e:
        raise LocalProfilerException(e)
    return istance

     
class LocalProfiler(object):

    def __init__(self):
        self._resources=[]

    def profile(self,path):
        result = ET.Element("SystemProfilerResults")
        try:
            for r in self._resources:
                ris = RisorsaFactory.getRisorsa(package_home(".",path,r), r)
                result=ris.getStatusInfo(result)
                del ris
                
        except RisorsaException as e:
            raise NotImplementedError(e)
        return result
        