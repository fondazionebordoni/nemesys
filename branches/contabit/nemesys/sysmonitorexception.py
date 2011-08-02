

class SysmonitorException(Exception):

    def __init__(self, alert_type, message):
        if isinstance (color, Status):
            self._alert_type = alert_type
        else:
            self._alert_type = alert_type.decode('utf-8')
        
        self._message = message.decode('utf-8')
 
 #Error at sysmonitor 81
 FAILPROF = SysmonitorException('FAILPROF','Non sono riuscito a trovare lo stato del computer con SystemProfiler.')      
 #Error at sysmonitor 94 110 123 170 201
 FAILREADPARAM = SysmonitorException('FAILREADPARAM','Errore in SystemProfiler.')
 #Error at sysmonitor 128
 FAILVALUEPARAM = SysmonitorException('FAILVALUEPARAM','Errore in SystemProfiler.')       