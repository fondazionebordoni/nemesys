'''
Created on 20/ott/2010

@author: antonio
'''
import platform
import Factory
import RisorsaFactory
import xml.etree.ElementTree as ET
from NemesysException import FactoryException, LocalProfilerException, RisorsaException


def package_home(path,rest):
        return ".".join([path,rest])
'''
Memorizzare o no l'istanza del profiler creato cosi da non doverlo ricreare successivamente se necessario?
se chi richiama il profiler lo cancella, ma io mantengo il riferimento qui, che succede? testare 
'''    
def getProfiler():
    try:
        name = package_home(platform.system().lower(), 'profiler.Profiler')
        istance= Factory.class_forname(name)
    except FactoryException as e:
        raise LocalProfilerException(e)
    return istance
'''
class LocalProfilerException(Exception):
    def __init__(self,value):
        Exception.__init__(self)
        self.value=value
'''        
class LocalProfiler(object):

    def __init__(self):
        self._resources=[]
        
    '''    
    @abstractmethod
    def profile(self):
        raise NotImplementedError
        
    #
    '''

    def profile(self,path):
        result = ET.Element("SystemProfilerResults")
        try:
            for r in self._resources:
                ris = RisorsaFactory.getRisorsa(package_home(path,r), r)
                result=ris.getStatusInfo(result)
                del ris
                
        except AttributeError:
            raise NotImplementedError("Risorsa non monitorabile")
        except RisorsaException as e:
            raise RisorsaException(e)
        return result
    #'''
        