'''
Created on 06/ott/2010

@author: antonio

Modulo per verificare che le operazioni implementate funzionino a dovere

'''
import LocalProfilerFactory
import xml.etree.ElementTree as ET
from NemesysException import LocalProfilerException, RisorsaException
import Factory

def mytostring(etree,s="",tag=""):
    s= s+tag+"<%s>\n" %etree.tag
    tagN = tag+ "\t"
    child= etree.getchildren()
    if child:
        for subetree in child:
            s= mytostring(subetree,s,tagN)
    else:
        s+=tagN+etree.text+"\n" 
    return s+tag+"</%s>\n"%etree.tag
        
def main():
    result=ET.ElementTree()
    try:
        profiler=LocalProfilerFactory.getProfiler()
        result=profiler.profile()        
        print mytostring(result)
    except NotImplementedError as e:
        print e
    except KeyError:
        print "sistema operativo non supportato"
    except LocalProfilerException:
        print "Problema nel tentativo di istanziare il profiler"
        
        
if __name__ == '__main__':
    main()