import Factory
import xml.etree.ElementTree as ET
from NemesysException import FactoryException, RisorsaException

def getRisorsa(path,name):
    try:
        ris= Factory.class_forname(path)
        ris.setName(name)
    except FactoryException as e:
        raise RisorsaException(e)
    return ris

class Risorsa(object):
    
    def __init__(self):
        self.__name =""
        self.__params=[]

    def getStatusInfo(self,root):
        try:
            for key in self._params:
                tag=key
                cmd = getattr(self,tag)            
                root.append(self.xmlFormat(tag, cmd()))
        except AttributeError as e:
            print RisorsaException(e)
            raise RisorsaException("errore get status info")
        return root
    #'''
    
    def setName(self,name):
        self.__name=name
    
      
    def getName(self):
        return self.__name
    
    
    def xmlFormat(self,tag,val):
        val=str(val)
        invalid_char=['<','>']
        for c in invalid_char:
            if c in val:
                parts=val.split(c)
                val = "".join(parts)                  
        elem=ET.Element(tag)
        elem.text=val
        return elem