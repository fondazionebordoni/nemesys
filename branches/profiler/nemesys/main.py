'''
Created on 06/ott/2010

@author: antonio

Modulo per verificare che le operazioni implementate funzionino a dovere

'''
from SysProf import LocalProfilerFactory
import xml.etree.ElementTree as ET
from SysProf.NemesysException import LocalProfilerException, RisorsaException
from SysProf import Factory

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
#        alldevtype=result.findall('rete/NetworkDevice/Type')
#        for elem in alldevtype:
#          print elem.text
        print "Finito"
    except NotImplementedError as e:
        print e
    except KeyError:
        print "sistema operativo non supportato"
    except LocalProfilerException as e:
        print ("Problema nel tentativo di istanziare il profiler: %s" % e)
        
        
if __name__ == '__main__':
    main()