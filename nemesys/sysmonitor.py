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
from SysProf.NemesysException import LocalProfilerException, RisorsaException, \
  FactoryException
from logger import logging
from sysmonitorexception import SysmonitorException
from xml.etree import ElementTree as ET
import checkhost
import netifaces
import paths
import platform
import socket
import sysmonitorexception

platform_name = platform.system().lower()
if platform_name == 'windows':
  from SysProf.windows import profiler
elif platform_name == 'darwin':
  from SysProf.darwin import profiler
else:
  from SysProf.linux import profiler

# TODO Decidere se, quando non riesco a determinare i valori, sollevo eccezione
STRICT_CHECK = True

CHECK_ALL = "ALL"
CHECK_MEDIUM = "MEDIUM"

tag_results = 'SystemProfilerResults'
tag_threshold = 'SystemProfilerThreshold'
tag_avMem = 'RAM.totalPhysicalMemory'
tag_memLoad = 'RAM.RAMUsage'
#tag_wireless = 'rete.NetworkDevice/Type'
tag_wireless = 'wireless.ActiveWLAN'
tag_ip = 'ipAddr' #to check
tag_sys = 'sistemaOperativo.OperatingSystem'
tag_cpu = 'CPU.cpuLoad'
tag_mac = 'rete.NetworkDevice/MACAddress'
tag_activeNic = 'rete.NetworkDevice/isActive'
tag_proc = 'CPU.processor'
tag_hosts = 'hostNumber'

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

logger = logging.getLogger()

def getstatus(res):

  logger.debug('Recupero stato della risorsa %s' % res)
  data = ET.ElementTree()
  try:
      profiler = LocalProfilerFactory.getProfiler()
      data = profiler.profile(set([res]))
  except FactoryException as e:
    logger.error ("Problema nel tentativo di istanziare la classe: %s" % e)
    raise sysmonitorexception.FAILPROF
  except RisorsaException as e:
    logger.error ("Problema nel tentativo di istanziare la risorsa %s: %s" % (str(res), e))
    raise sysmonitorexception.FAILPROF
  except LocalProfilerException as e:
    logger.error ("Problema nel tentativo di istanziare il profiler: %s" % e)
    raise sysmonitorexception.FAILPROF
  except Exception as e:
    logger.error('Non sono riuscito a trovare lo stato del computer con SystemProfiler: %s.' % e)
    raise sysmonitorexception.FAILPROF

  return _getvalues(data, tag_results, res)

def getstringtag(tag, value, res):

  values = getstatus(res)

  try:
    value = str(values[tag])
  except Exception as e:
    logger.error('Errore in lettura del paramentro "%s" di SystemProfiler: %s' % (tag, e))
    if STRICT_CHECK:
      raise SysmonitorException(sysmonitorexception.FAILREADPARAM, 'Errore in lettura del paramentro "%s" di SystemProfiler.' % tag)

  if value == 'None':
    return None

  return value

def getfloattag(tag, value, res):

  values = getstatus(res)

  if (values == None):
    logger.error('Errore nel valore del paramentro "%s" di SystemProfiler: %s' % tag)
    raise SysmonitorException(sysmonitorexception.FAILREADPARAM, 'Errore in lettura del paramentro "%s" di SystemProfiler.' % tag)

  try:
    if (values[tag] == None):
      logger.warning('Errore durante la lettura del parametro "%s" di "%s": valore nullo (impostato d\'ufficio a 0)' % (tag, res))
      value = 0

    value = float(values[tag])
  except Exception as e:
    logger.error('Errore in lettura del paramentro "%s" di SystemProfiler: %s' % (tag, e))
    if STRICT_CHECK:
      raise SysmonitorException(sysmonitorexception.FAILREADPARAM, 'Errore in lettura del paramentro "%s" di SystemProfiler.' % tag)

  return value

def getResProperty(tag, res):
  data = ET.ElementTree()
  try:
      profiler = LocalProfilerFactory.getProfiler()
      data = profiler.profile(set([res]))
  except Exception as e:
    logger.error('Non sono riuscito a trovare lo stato del computer con profiler: %s.' % e)
    raise sysmonitorexception.FAILPROF
  except RisorsaException as e:
    logger.error ("Problema nel tentativo di istanziare la risorsa: %s" % e)
    raise sysmonitorexception.FAILPROF
  except LocalProfilerException as e:
    logger.error ("Problema nel tentativo di istanziare il profiler: %s" % e)
    raise sysmonitorexception.FAILPROF
  wtf = res + '/' + tag
  return data.findall(wtf)

def getbooltag(tag, value, res):

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

def checkcpu():
  value = getfloattag(tag_cpu.split('.', 1)[1], th_cpu - 1, tag_cpu.split('.', 1)[0])
  if value < 0 or value > 100:
    raise sysmonitorexception.BADCPU

  if value > th_cpu:
    raise sysmonitorexception.WARNCPU

  return True

def checkmem():

  avMem = getfloattag(tag_avMem.split('.')[1], th_avMem + 1, tag_avMem.split('.')[0])
  logger.debug("Memoria disponibile: %2f" % avMem)
  if avMem < 0:
    #raise Exception('Valore di memoria disponibile non conforme.')
    raise sysmonitorexception.BADMEM
  if avMem < th_avMem:
    #raise Exception('Memoria disponibile non sufficiente.')
    raise sysmonitorexception.LOWMEM

  memLoad = getfloattag(tag_memLoad.split('.')[1], th_memLoad - 1, tag_memLoad.split('.')[0])
  logger.debug("Memoria occupata: %d%%" % memLoad)
  if memLoad < 0 or memLoad > 100:
    #raise Exception('Valore di occupazione della memoria non conforme.')
    raise sysmonitorexception.INVALIDMEM
  if memLoad > th_memLoad:
    #raise Exception('Memoria occupata.')
    raise sysmonitorexception.OVERMEM

  return True

def checkwireless():
  profiler = LocalProfilerFactory.getProfiler()
  data = profiler.profile(set(['rete']))
  for device in data.findall('rete/NetworkDevice'):
    logger.debug(ET.tostring(device))
    status = device.find('Status').text
    if (status == 'Enabled'):
        type = device.find('Type').text
        if (type == 'Wireless'):
            raise sysmonitorexception.WARNWLAN
  return True

def checkhosts(up, down, ispid, arping = 1):

  ip = getIp();
  mask = getNetworkMask(ip)
  dev = getDev(ip = ip)

  logger.info("Indirizzo ip/mask: %s/%d, device: %s, provider: %s" % (ip, mask, dev, ispid))

  if (arping == 0):
    thres = th_host + 1
  else:
    thres = th_host

  if (mask != 0):
    mac = None
    try:
        mac = getMac()
        if (mac == None):
          mac = getMac() # try again to get a MAC from the active NIC
    except:
        pass

    value = checkhost.countHosts(ip, mask, up, down, ispid, thres, arping, mac, dev)
    logger.info('Trovati %d host in rete.' % value)

    if value < 0:
      raise sysmonitorexception.BADHOST
    elif (value == 0):
      if arping == 1:
        logger.warning("Passaggio a PING per controllo host in rete")
        return checkhosts(up, down, ispid, 0)
      else:
        raise sysmonitorexception.BADHOST
    elif value > thres:
      raise sysmonitorexception.TOOHOST

    return True
  else:
    raise SysmonitorException(sysmonitorexception.BADMASK, 'Impossibile recuperare il valore della maschera dell\'IP: %s' % ip)

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

def checkall(up, down, ispid, arping = 1):

  mediumcheck()
  checkhosts(up, down, ispid, arping)
  # TODO Reinserire questo check quanto corretto il problema di determinazione del dato
  #checkdisk()
  return True

def getMac():
  '''
  restituisce indirizzo MAC del computer
  '''
  tag = tag_activeNic.split('.');
  res = tag[0]
  nestedtag = tag[1].split('/')
  tagdev = nestedtag[0]
  tagprop = nestedtag[1]

  tag = tag_mac.split('.');
  nestedtag = tag[1].split('/')
  tagmac = nestedtag[1]

  data = ET.ElementTree()
  try:
      profiler = LocalProfilerFactory.getProfiler()
      data = profiler.profile(set([res]))
  except Exception as e:
    logger.error('Non sono riuscito a trovare lo stato del computer con profiler: %s.' % e)
    raise sysmonitorexception.FAILPROF
  except RisorsaException as e:
    logger.error ("Problema nel tentativo di istanziare la risorsa: %s" % e)
    raise sysmonitorexception.FAILPROF
  except LocalProfilerException as e:
    logger.error ("Problema nel tentativo di istanziare il profiler: %s" % e)
    raise sysmonitorexception.FAILPROF
  tree = ET.ElementTree(data)
  whattolook = res + '/' + tagdev
  listdev = data.findall(whattolook)
  for dev in listdev:
    tree._setroot(dev)
    devxml = tree.getroot()
    val = devxml.find(tagprop)
    if val.text == 'True':
      macelem = devxml.find(tagmac)
      return macelem.text
  return None


def _checkipsyntax(ip):

  try:
    socket.inet_aton(ip)
    parts = ip.split('.')
    if len(parts) != 4:
      return False
  except Exception:
    return False

  return True

def getIp(host = 'finaluser.agcom244.fub.it', port = 443):
  '''
  restituisce indirizzo IP del computer
  '''
  s = socket.socket(socket.AF_INET)
  s.connect((host, port))
  value = s.getsockname()[0]

  #value = getstringtag(tag_ip, '90.147.120.2')

  if not _checkipsyntax(value):
    #raise Exception('Impossibile ottenere il dettaglio dell\'indirizzo IP')
    raise sysmonitorexception.UNKIP
  return value

def getDev(host = 'finaluser.agcom244.fub.it', port = 443, ip = None):
  '''
  restituisce scheda attiva (guid della scheda su Windows 
  '''
  if not ip:
    local_ip_address = getIp(host, port)
  else:
    local_ip_address = ip
      

  ''' Now get the associated device '''
  found = False
  for ifName in netifaces.interfaces():
      all_addresses = netifaces.ifaddresses(ifName)
      if (netifaces.AF_INET in all_addresses):
          ip_addresses = all_addresses[netifaces.AF_INET]
          for address in ip_addresses:
              if ('addr' in address) and (address['addr'] == local_ip_address):
                  found = True
                  break
          if found:
              break
  if not found:
    raise sysmonitorexception.UNKDEV
  return ifName

def getNetworkMask(ip):
  '''
  Restituisce un intero rappresentante la maschera di rete, in formato CIDR, 
  dell'indirizzo IP in uso
  '''
  netmask = '255.255.255.0'
  
  try:
    inames = netifaces.interfaces()
    for i in inames:
      try:
        addrs = netifaces.ifaddresses(i)
        ipinfo = addrs[socket.AF_INET][0]
        address = ipinfo['addr']
        if (address == ip):
          netmask = ipinfo['netmask']
          return _maskConversion(netmask)
        else:
          pass
      except Exception as e:
        logger.warning("Errore durante il controllo dell'interfaccia %s. %s" % (i, e))
        pass
  except Exception as e:
    logger.warning("Errore durante il controllo della maschera per l'IP %s (assumo maschera: /24). %s" % (ip, e))
    pass

  return _maskConversion(netmask)

def _maskConversion(netmask):
  nip = str(netmask).split(".")
  if(len(nip) == 4):
    i = 0
    bini = range(0, len(nip))
    while i < len(nip):
      bini[i] = int(nip[i])
      i += 1
    bins = _convertDecToBin(bini)
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


def _convertDecToBin(dec):
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

def getOs():
  d = {tag_sys:''}
  r = []

  for keys in d:
    r.append(getstringtag(keys.split('.', 1)[1], 1, keys.split('.', 1)[0]))

  return r


def getSys():
  '''
  Restituisce array con informazioni sul sistema utilizzato per il test
  '''
  d = {tag_sys:'', tag_proc:''}
  r = []

  for keys in d:
    r.append(getstringtag(keys.split('.', 1)[1], 1, keys.split('.', 1)[0]))
  r.append(getMac())

  return r

def _getvalues(xmlresult, tag, tagrisorsa):
    
  '''
  Estrae informazioni dal SystemProfiler 
  '''
  values = {}
  try:
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
    print '\ncheckall'
    print 'Test sysmonitor checkall: %s' % checkall(1000, 2000, 'fst001')
  except Exception as e:
    
    if isinstance (e, SysmonitorException):
      # Inserire nel test tutte le eccezioni da bypassare
      if e.alert_type == sysmonitorexception.WARNCONN.alert_type or e.alert_type == sysmonitorexception.WARNPROC.alert_type:
        logger.warning('Misura in esecuzione con warning: %s' % e)
    
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)
  '''
  try:
    print '\ngetMac'
    print 'Test sysmonitor getMac: %s' % getMac()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)

  try:
    print '\ncheckhosts (arping)'
    print 'Test sysmonitor checkhosts: %s' % checkhosts(2000, 2000, 'fst001', 1)  #ARPING
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)
  
  try:
    print '\ncheckhosts (ping)'
    print 'Test sysmonitor checkhosts: %s' % checkhosts(2000, 2000, 'fst001', 0)  #PING
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)
  
  try:
    print '\ncheckcpu'
    print 'Test sysmonitor checkcpu: %s' % checkcpu()
  except SysmonitorException as e:
    print 'Errore [%d]: (%s) %s' % (errorcode, e.alert_type, e)
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)

  try:
    print '\ncheckmem'
    print 'Test sysmonitor checkmem: %s' % checkmem()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)

  try:
    print '\ncheckwireless'
    print 'Test sysmonitor checkwireless: %s' % checkwireless()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)

  try:
    print '\ngetIP'
    print 'Test sysmonitor getIP: %s' % getIp()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)

  try:
    print '\ngetIP (www.google.com)'
    print 'Test sysmonitor getIP: %s' % getIp('www.google.com', 80)
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)

  try:
    print '\ngetOs'
    print 'Test sysmonitor getOs: %s' % getOs()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)

  try:
    print '\ngetSys'
    print 'Test sysmonitor getSys: %s' % getSys()
  except Exception as e:
    errorcode = errors.geterrorcode(e)
    print 'Errore [%d]: %s' % (errorcode, e)
  '''
