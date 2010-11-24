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
    s= s+tag+"<%s>" %etree.tag
    child= etree.getchildren()
    if child:
        s+="\n"
        tag += "\t"
        for subetree in child:
            s= mytostring(subetree,s,tag)
    else:
        s+=etree.text
    return s+"</%s>\n" %etree.tag
        
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