'''
Created on 20/ott/2010

@author: antonio
'''
import platform
import Factory
import RisorsaFactory
import xml.etree.ElementTree as ET
from NemesysException import FactoryException, LocalProfilerException, RisorsaException


def package_home(sep, *args):
        return sep.join(args)
'''
Memorizzare o no l'istanza del profiler creato cosi da non doverlo ricreare successivamente se necessario?
se chi richiama il profiler lo cancella, ma io mantengo il riferimento qui, che succede? testare 
'''    
def getProfiler():
    try:
        name = package_home(".", 'SysProf', platform.system().lower(), 'profiler.Profiler')
        istance = Factory.class_forname(name)
    except FactoryException as e:
        raise LocalProfilerException(e)
    return istance

     
class LocalProfiler(object):

    def __init__(self, resources):
        self._available_resources = resources
        self._resources = []

    def _setResource(self, res):
        self._resources = res
        
    def profile(self, path, resource=set()):
        if (len(resource) > 0):
            unavailable_resource = resource - self._available_resources 
            if (unavailable_resource):
                raise RisorsaException('risorse non diponibili %s' % list(unavailable_resource))
            else:
                self._setResource(resource & self._available_resources)
        else:
            self._setResource(self._available_resources)

        result = ET.Element("SystemProfilerResults")
        try:
            for r in self._resources:
                singleresxml = ET.Element(str(r))
                tree = ET.ElementTree(singleresxml)
                ris = RisorsaFactory.getRisorsa(package_home(".", path, r), r)
                singleresxml = ris.getStatusInfo(singleresxml)
                testrepetition = singleresxml.find(str(r))
                if testrepetition == None:
                    result.append(singleresxml)
                else:
                    tree._setroot(testrepetition)
                    result.append(tree.getroot())                  
                del ris
                del singleresxml
                del tree
        except RisorsaException as e:
            raise RisorsaException(e) 
        return result
        
