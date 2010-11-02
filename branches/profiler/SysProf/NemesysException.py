'''
Created on 27/ott/2010

@author: antonio
'''

'''
Migliorare l'implementazione delle eccezioni per rendere codice piu pulito
'''

'''
Eccezione invocazione metodo class_forname della Factory
'''

class FactoryException(Exception):
    
    def __init__(self,value):
        Exception.__init__(self)
        self.value= value
        
'''
Eccezione istanzazione LocalProfiler
'''

class LocalProfilerException(Exception):
    def __init__(self,value):
        Exception.__init__(self)
        self.value=value
        
'''
Eccezione istanzazione Risorsa
'''

class RisorsaException(Exception):
    def __init__(self,value):
        Exception.__init__(self)
        self.value=value