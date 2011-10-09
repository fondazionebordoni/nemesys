# sysmonitor.py
# -*- coding: utf8 -*-

# Copyright (c) 2010 Fondazione Ugo Bordoni.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from SysProf import LocalProfilerFactory
from SysProf.NemesysException import LocalProfilerException, RisorsaException
from sysmonitorexception import SysmonitorException
from logger import logging
from xml.etree import ElementTree as ET
from os import path as Path
import checkhost
import netifaces
import paths
import re
import socket
import sysmonitorexception

# TODO Decidere se, quando non riesco a determinare i valori, sollevo eccezione
STRICT_CHECK = True

tag_results = 'SystemProfilerResults'
tag_threshold = 'SystemProfilerThreshold'
tag_avMem = 'RAM.totalPhysicalMemory'
tag_memLoad = 'RAM.RAMUsage'
tag_wireless = 'rete.NetworkDevice/Type'
tag_ip = 'ipAddr' #to check
tag_sys = 'sistemaOperativo.OperatingSystem'
tag_disk = 'disco.ByteTransfer'
tag_cpu = 'CPU.cpuLoad'
tag_mac = 'rete.NetworkDevice/MACAddress'
tag_activeNic= 'rete.NetworkDevice/isActive'
tag_cores = 'CPU.cores'
tag_proc = 'CPU.processor'
tag_hosts = 'hostNumber'
tag_conn = 'activeConnections'# deprecated 
tag_task = 'taskList' # deprecated

# Soglie di sistema
# ------------------------------------------------------------------------------
# Massima quantità di host in rete
th_host = 1
# Minima memoria disponibile
th_avMem = 134217728
# Massimo carico percentuale sulla memoria
th_memLoad = 95
# Massimo carico percentuale sulla CPU
th_cpu = 85
# Massimo numero di byte scritti su disco in 5 secondi
th_wdisk = 104857600
# Porte con connessioni attive da evitare
bad_conn = [80, 8080, 25, 110, 465, 993, 995, 143, 6881, 4662, 4672, 443]
# Processi che richiedono troppe risorse 
bad_proc = ['amule', 'emule', 'skype', 'dropbox', 'torrent', 'azureus', 'transmission']

logger = logging.getLogger()



def getstatus(res):
  data=ET.ElementTree()
  try:
      profiler=LocalProfilerFactory.getProfiler()
      data=profiler.profile([res])        
  except Exception as e:
    logger.error('Non sono riuscito a trovare lo stato del computer con SystemProfiler: %s.' % e)
    raise sysmonitorexception.FAILPROF
  except RisorsaException as e:
    logger.error ("Problema nel tentativo di istanziare la risorsa: %s" % e)
    raise sysmonitorexception.FAILPROF
  except LocalProfilerException as e:
    logger.error ("Problema nel tentativo di istanziare il profiler: %s" % e)
    raise sysmonitorexception.FAILPROF
  return getvalues(data, tag_results, res)

def getstringtag(tag, value,res):
  d = {tag:''}
  values = getstatus(res)

  try:
    value = str(values[tag])
  except Exception as e:
    logger.error('Errore in lettura del paramentro "%s" di SystemProfiler: %s' % (tag, e))
    if STRICT_CHECK:
      #raise Exception('Errore in lettura del paramentro "%s" di SystemProfiler.' % tag)
      raise SysmonitorException(sysmonitorexception.FAILREADPARAM, 'Errore in lettura del paramentro "%s" di SystemProfiler.' % tag)

  if value == 'None':
    return None

  return value

def getfloattag(tag, value,res):
  d = {tag:''}
  values = getstatus(res)
  try:
    value = float(values[tag])
  except Exception as e:
    logger.error('Errore in lettura del paramentro "%s" di SystemProfiler: %s' % (tag, e))
    if STRICT_CHECK:
      raise SysmonitorException(sysmonitorexception.FAILREADPARAM, 'Errore in lettura del paramentro "%s" di SystemProfiler.' % tag)

  return value

def getResProperty(tag,res):
  data=ET.ElementTree()
  try:
      profiler=LocalProfilerFactory.getProfiler()
      data=profiler.profile([res])        
  except Exception as e:
    logger.error('Non sono riuscito a trovare lo stato del computer con profiler: %s.' % e)
    raise sysmonitorexception.FAILPROF
  except RisorsaException as e:
    logger.error ("Problema nel tentativo di istanziare la risorsa: %s" % e)
    raise sysmonitorexception.FAILPROF
  except LocalProfilerException as e:
    logger.error ("Problema nel tentativo di istanziare il profiler: %s" % e)
    raise sysmonitorexception.FAILPROF
  wtf= res + '/' + tag
  return data.findall(wtf)

def getbooltag(tag, value,res):
  d = {tag:''}
  values = getstatus(res)
  try:
    value = str(values[tag]).lower()
  except Exception as e:
    logger.error('Errore in lettura del paramentro "%s" di SystemProfiler: %s' % (tag, e))
    if STRICT_CHECK:
      #raise Exception('Errore in lettura del paramentro "%s" di SystemProfiler.' % tag)
      raise SysmonitorException(sysmonitorexception.FAILREADPARAM, 'Errore in lettura del paramentro "%s" di SystemProfiler.' % tag)
  if STRICT_CHECK:
    if value != 'false' and value != 'true':
      logger.warning('Impossibile determinare il parametro "%s".' % tag)
      #raise Exception('Impossibile determinare il parametro "%s".' % tag)
      raise SysmonitorException(sysmonitorexception.FAILVALUEPARAM, 'Impossibile determinare il parametro "%s".' % tag)
    if value == 'false':
      return False
    else:
      return True
  else:
    return value

def checkconnections():
  '''
  Effettua il controllo sulle connessioni attive
  '''
  myip = getIp()
  connActive = getstringtag(tag_conn, '90.147.120.2:443')

  if connActive == None or len(connActive) <= 0:
    # Non ho connessioni attive
    logger.debug('Nessuna connessione di rete attiva.')
    return True

  c = []
  try:
    for j in connActive.split(';'):
      # Ignora le connessioni ipv6
      # TODO Gestire le connessioni ipv6
      if bool(re.search('^\[', j)):
        logger.warning('Connessione IPv6 attiva: %s' % j)
        continue
      ip = j.split(':')[0]
      if not checkipsyntax(ip):
        #raise Exception('Lista delle connessioni attive non conforme.')
        raise sysmonitorexception.BADCONN
      if ip == myip:
        logger.warning('Ricevuto ip %s nella lista delle connessioni attive' % ip)
        continue
      port = int(j.split(':')[1])
      # TODO Occorre chiamare un resolver per la risoluzione dei nostri ip
      if not bool(re.search('^90\.147\.120\.|^193\.104\.137\.', ip)):
        c.append(port)

  except Exception as e:
    logger.error('Errore in lettura del paramentro "%s" di SystemProfiler: %s' % (tag_conn, e))
    if STRICT_CHECK:
      #raise Exception('Errore in lettura del paramentro "%s" di SystemProfiler.' % tag_conn)
      raise SysmonitorException(sysmonitorexception.FAILREADPARAM, 'Errore in lettura del paramentro "%s" di SystemProfiler.' % tag_conn)

  for i in bad_conn:
    if i in c:
      logger.error('Porta %d aperta ed utilizzata.' % i)
      #raise Exception('Accesso ad Internet da programmi non legati alla misura. Se possibile, chiuderli.')
      raise sysmonitorexception.WARNCONN
  
  for i in c:
    if i >= 1024:
      logger.error('Porta %d aperta ed utilizzata.' % i)
      #raise Exception('Accesso ad Internet da programmi non legati alla misura. Se possibile, chiuderli.')
      raise sysmonitorexception.WARNCONN
  return True

def checktasks():
  '''
  Ettettua il controllo sui processi
  '''
  taskActive = getstringtag(tag_task, 'executer')

  if taskActive == None or len(taskActive) <= 0:
    #raise Exception('Errore nella determinazione dei processi attivi.')
    raise sysmonitorexception.BADPROC
  # WARNING Non ho modo di sapere se il valore che recupero è non plausibile (not available)

  t = []
  try:
    for j in taskActive.split(';'):
      t.append(str(j))
  except Exception as e:
    logger.error('Errore in lettura del paramentro "%s" di SystemProfiler: %s' % (tag_task, e))
    #raise Exception('Errore in lettura del paramentro "%s" di SystemProfiler.' % tag_task)
    raise SysmonitorException(sysmonitorexception.FAILREADPARAM, 'Errore in lettura del paramentro "%s" di SystemProfiler.' % tag_task)

  for i in bad_proc:
    for k in t:
      if (bool(re.search(i, k, re.IGNORECASE))):
        #raise Exception('Sono attivi processi non desiderati.', 'Chiudere il programma "%s" per proseguire le misure.' % i)
        raise sysmonitorexception.WARNPROC
  return True

def checkcpu():
  value = getfloattag(tag_cpu.split('.',1)[1], th_cpu - 1,tag_cpu.split('.',1)[0])
  if value < 0 or value > 100:
    #raise Exception('Valore di occupazione della CPU non conforme.')
    raise sysmonitorexception.BADCPU

  if value > th_cpu:
    #raise Exception('CPU occupata.')
    raise sysmonitorexception.WARNCPU

  return True

def checkmem():

  avMem = getfloattag(tag_avMem.split('.')[1], th_avMem + 1,tag_avMem.split('.')[0])
  if avMem < 0:
    #raise Exception('Valore di memoria disponibile non conforme.')
    raise sysmonitorexception.BADMEM
  if avMem < th_avMem:
    #raise Exception('Memoria disponibile non sufficiente.')
    raise sysmonitorexception.LOWMEM
  memLoad = getfloattag(tag_memLoad.split('.')[1], th_memLoad - 1,tag_memLoad.split('.')[0])
  if memLoad < 0 or memLoad > 100:
    #raise Exception('Valore di occupazione della memoria non conforme.')
    raise sysmonitorexception.INVALIDMEM
  if memLoad > th_memLoad:
    #raise Exception('Memoria occupata.')
    raise sysmonitorexception.OVERMEM
    
  return True

def checkwireless():
  values = getResProperty(tag_wireless.split('.')[1],tag_wireless.split('.')[0])
  for devs in values:
    if devs.text == 'Wireless':
      raise sysmonitorexception.WARNWLAN
  return True

def checkhosts(up, down, ispid, arping=1):
  
  ip = getIp();
  mask = getNetworkMask(ip)
  logger.info("Indirizzo ip/mask: %s/%d" % (ip, mask))
  
  if (arping == 0):
    thres = th_host + 1
  else:
    thres = th_host
  
  if (mask != 0):  
    value = checkhost.countHosts(ip, mask, up, down, ispid, thres, arping)
    #value=1
    logger.info('Trovati %d host in rete.' % value)
          
    if value <= 0:
      #raise Exception('Impossibile determinare il numero di host in rete.')
      raise sysmonitorexception.BADHOST
    if value > thres:
      #raise Exception('Presenza altri host in rete.')
      raise sysmonitorexception.TOOHOST
      
    return True
  else:
    #raise Exception ('Impossibile recuperare il valore della maschera dell\'IP: %s' % ip)
    raise SysmonitorException(sysmonitorexception.BADMASK, 'Impossibile recuperare il valore della maschera dell\'IP: %s' % ip)
    
def checkdisk():

  value = getfloattag(tag_disk.split('.')[1], th_wdisk - 1,tag_disk.split('.')[0])
  if value < 0:
    #raise Exception('Impossibile detereminare il carico in lettura del disco.')
    raise sysmonitorexception.UNKDISKLOAD

  if value > th_wdisk:
    raise sysmonitorexception.DISKOVERLOAD

  return True

def fastcheck():
  '''
  Esegue un controllo veloce dello stato del pc dell'utente.
  Ritorna True se le condizioni per effettuare le misure sono corrette,
  altrimenti solleva un'eccezione
  '''

  checkcpu()
  checkmem()
  #checktasks()
  #checkconnections()

  return True

def mediumcheck():

  fastcheck()
  #checkfw()
  checkwireless()

  return True

def checkall(up, down, ispid, arping=1):

  checkhosts(up, down, ispid, arping)
  mediumcheck()
  # TODO Reinserire questo check quanto corretto il problema di determinazione del dato
  #checkdisk()
  return True

def getMac():
  '''
  restituisce indirizzo MAC del computer
  '''
  tag=tag_activeNic.split('.');
  res=tag[0]
  nestedtag=tag[1].split('/')
  tagdev=nestedtag[0]
  tagprop=nestedtag[1]
  
  tag=tag_mac.split('.');
  nestedtag=tag[1].split('/')
  tagmac=nestedtag[1]
  
  data=ET.ElementTree()
  try:
      profiler=LocalProfilerFactory.getProfiler()
      data=profiler.profile([res])        
  except Exception as e:
    logger.error('Non sono riuscito a trovare lo stato del computer con profiler: %s.' % e)
    raise sysmonitorexception.FAILPROF
  except RisorsaException as e:
    logger.error ("Problema nel tentativo di istanziare la risorsa: %s" % e)
    raise sysmonitorexception.FAILPROF
  except LocalProfilerException as e:
    logger.error ("Problema nel tentativo di istanziare il profiler: %s" % e)
    raise sysmonitorexception.FAILPROF
  tree=ET.ElementTree(data)
  whattolook= res+ '/' + tagdev
  listdev=data.findall(whattolook)
  for dev in listdev:
    tree._setroot(dev)
    devxml=tree.getroot()
    val=devxml.find(tagprop)
    if val.text == 'True':
      macelem=devxml.find(tagmac)
      return macelem.text
  return None 
  
  
def checkipsyntax(ip):

  try:
    socket.inet_aton(ip)
    parts = ip.split('.')
    if len(parts) != 4:
      return False
  except Exception:
    return False

  return True

def getIp():
  '''
  restituisce indirizzo IP del computer
  '''
  s = socket.socket(socket.AF_INET)
  s.connect(('www.google.com', 80))
  value = s.getsockname()[0]

  #value = getstringtag(tag_ip, '90.147.120.2')

  if not checkipsyntax(value):
    #raise Exception('Impossibile ottenere il dettaglio dell\'indirizzo IP')
    raise sysmonitorexception.UNKIP
  return value

def getNetworkMask(ip):
  '''
  Restituisce un intero rappresentante la maschera di rete, in formato CIDR, 
  dell'indirizzo IP in uso
  '''
  inames = netifaces.interfaces()
  netmask = 0
  for i in inames:
    addrs = netifaces.ifaddresses(i)
    try:
      ipinfo = addrs[socket.AF_INET][0]
      address = ipinfo['addr'] 
      if (address == ip):
        netmask = ipinfo['netmask']
        return maskConversion(netmask)
      else:
        pass
    except Exception:
      pass

  return maskConversion(netmask)

def maskConversion(netmask):
  nip = netmask.split(".")
  if(len(nip) == 4):
    i = 0
    bini = range(0, len(nip))
    while i < len(nip):
      bini[i] = int(nip[i])
      i += 1
    bins = convertDecToBin(bini)
    lastChar = 1
    maskcidr = 0
    i = 0
    while i < 4:
      j = 0
      while j < 8:
        if (bins[i][j] == 1):
          if (lastChar == 0):
            return 0
          maskcidr = maskcidr + 1
        lastChar = bins[i][j]
        j = j + 1
      i = i + 1
  else:
    return 0
  return maskcidr


def convertDecToBin(dec):
  i = 0  
  bin = range(0, 4)
  for x in range(0, 4):
    bin[x] = range(0, 8)
  
  for i in range(0, 4):
    j = 7
    while j >= 0:
           
      bin[i][j] = (dec[i] & 1) + 0
      dec[i] /= 2
      j = j - 1
  return bin

#valido per windows
def getMask(ip):
  ris = None
  objWMIService = win32com.client.Dispatch("WbemScripting.SWbemLocator")
  objSWbemServices = objWMIService.ConnectServer(".", "root\cimv2")
  colItems = objSWbemServices.ExecQuery("SELECT * FROM Win32_NetworkAdapterConfiguration")
  for obj in colItems:
    ipaddrlist = obj.__getattr__('IPAddress')
    if (ipaddrlist != None) and (ip in ipaddrlist):
      ris = obj.__getattr__('IPSubnet')
      break
    else:
      pass
  return ris

def getSys():
  '''
  Restituisce array con informazioni sul sistema utilizzato per il test
  '''
  d = {tag_sys:'', tag_cores:'', tag_proc:''}

  r = []

  for keys in d:
    r.append(getstringtag(keys.split('.',1)[1], 1,keys.split('.',1)[0]))
  r.append(getMac())

  return r

def getvalues(xmlresult, tag,tagrisorsa):
  '''
  Estrae informazioni dal SystemProfiler 
  '''
  values = {}
  try:
#    for subelement in ET.XML(string):
#    for subelement in xmlresult:
    for subelement in xmlresult.find(tagrisorsa):
      values.update({subelement.tag:subelement.text})
  except Exception as e:
    logger.warning('Errore durante il recupero dello stato del computer. %s' % e)
    raise Exception('Errore durante il recupero dello stato del computer.')

  return values

if __name__ == '__main__':
  from errorcoder import Errorcoder
  errors = Errorcoder(paths.CONF_ERRORS)

  try:
    print 'Test sysmonitor getMac: %s' % getMac()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)

  '''   
   
  try:
    print 'Test sysmonitor checkall: %s' % checkall(1000, 2000, 'fst001')
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)
  '''
  try:
    print 'Test sysmonitor checkhosts: %s' % checkhosts(2000, 2000, 'fst001',1)  #ARPING
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)
  '''
  try:
    print 'Test sysmonitor fastcheck: %s' % checkhosts(2000, 2000, 'fst001',0)  #PING
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)

  try:
    print 'Test sysmonitor checkconnections: %s' % checkconnections()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)
  '''
  try:
    print 'Test sysmonitor checkcpu: %s' % checkcpu()
  except SysmonitorException as e:
    print 'Errore [%d]: (%s) %s' % (errorcode, e.alert_type, e)
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)

  try:
    print 'Test sysmonitor checkdisk: %s' % checkdisk()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)
  '''
  try:
    print 'Test sysmonitor checkfw: %s' % checkfw()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)
  '''
  try:
    print 'Test sysmonitor checkmem: %s' % checkmem()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)
  '''
  try:
    print 'Test sysmonitor checktasks: %s' % checktasks()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)
  '''
  try:
    print 'Test sysmonitor checkwireless: %s' % checkwireless()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)


  try:
    print 'Test sysmonitor getIP: %s' % getIp()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)

  try:
    print 'Test sysmonitor getSys: %s' % getSys()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)
