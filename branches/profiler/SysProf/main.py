'''
Created on 06/ott/2010

@author: antonio

Modulo per verificare che le operazioni implementate funzionino a dovere

'''
import LocalProfilerFactory
import xml.etree.ElementTree as ET
from NemesysException import LocalProfilerException, RisorsaException
import Factory
    
def main():
    result=ET.ElementTree()
    try:
        profiler=LocalProfilerFactory.getProfiler()
        result=profiler.profile()        
        print ET.tostring(result)
    except NotImplementedError as e:
        print e
    except KeyError:
        print "sistema operativo non supportato"
    except LocalProfilerException:
        print "Problema nel tentativo di istanziare il profiler"
        
        
if __name__ == '__main__':
    main()