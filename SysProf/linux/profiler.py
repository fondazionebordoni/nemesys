'''
Created on 20/ott/2010

@author: antonio

Le parti commentate sono relative precedenti all'integrazione nell'unico metodo in LocalProfiler
'''
from ..LocalProfilerFactory import LocalProfiler
from ..RisorsaFactory import Risorsa


class CPU(Risorsa):
    
    
    def __init__(self):
        Risorsa.__init__(self)
        self._chisono="sono una CPU"
        self._params=['num_cpu','num_core']
        
        
    def num_cpu(self):
        return '1'
    
    def num_core(self):
        return '2'
   
class Profiler(LocalProfiler):
    
    def __init__(self):
        LocalProfiler.__init__(self)
        self._resources =['CPU']

    '''
    necessario racchiudere anche la chiamata al profile della superclasse in un try/except?
    '''
    def profile(self):
        return super(Profiler,self).profile(__name__)