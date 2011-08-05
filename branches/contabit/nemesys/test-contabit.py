from threading import Thread
from time import sleep
from contabit import *

class counter(Thread):

    def __init__(self):
        Thread.__init__(self)

    def getdev(self,req=None):
        device=getdev(req)
        return device

    def init(self,dev,nem,buffer=0):
        #status_init=initialize(IFname,IF_IP,FTP_IP,buffer)
        status_init=initialize(dev,nem)
        return status_init

    def run(self):
        status_start=start()
        return status_start

    def stop(self):
        status_stop=stop()
        return status_stop

    def getstat(self,req1=None):
#                     ,req2=None,req3=None,req4=None,req5=None,
#                     req6=None,req7=None,req8=None,req9=None,req10=None,
#                     req11=None,req12=None,req13=None,req14=None,req15=None,
#                     req16=None,req17=None,req18=None,req19=None,req20=None):
        statistics=getstat(req1)
#                        ,req2,req3,req4,req5,req6,req7,req8,req9,req10,
#                           req11,req12,req13,req14,req15,req16,req17,req18,req19,req20)
        return statistics

    def geterr(self):
        error=geterr()
        return error

    def join(self, timeout=None):
        Thread.join(self, timeout)


counter=counter()

print "\nDevices:"

print "\nFirst Request: All Devices"

device=counter.getdev()

if (device!=None):
    print
    keys=device.keys()
    keys.sort()
    for key in keys:
        print "%s \t %s" % (key,device[key])
else: print "No Devices"

print "\nSecond Request: Device by IP not assigned to the machine"

device=counter.getdev('192.168.208.50')

if (device!=None):
    print
    keys=device.keys()
    keys.sort()
    for key in keys:
        print "%s \t %s" % (key,device[key])
else: print "No Devices"

print "\nThird Request: Device by IP assigned to the machine"

device=counter.getdev('eth0')


if (device!=None):
    print
    keys=device.keys()
    keys.sort()
    for key in keys:
        print "%s \t %s" % (key,device[key])
else: print "No Devices"

print "\nInitialize.... "
status_init=counter.init('eth0','194.244.5.206')

if (status_init==0):
    print "Success\n"
else:
    print "Fail:",status_init
    print "Error:",counter.geterr()

print "Start...."

status_start=counter.start()

if (status_start==None):
    print "Success\n"
else:
    print "Fail:",status_start
    print "Error:",counter.geterr()

#print "Loop....\n"
#
#raw_input("Press Enter for First Partial Statistics\n")
#
#print "First Partial Statistics:\n"
#
#statistics=counter.getstat('payload_up_nem','payload_up_all','payload_down_nem','payload_down_all')
#
#if (statistics!=None):
#    keys=statistics.keys()
#    keys.sort()
#    for key in keys:
#        print "Key: %s \t Value: %s" % (key,statistics[key])
#else: print "No Statistics"
#
#raw_input("\nPress Enter for Second Partial Statistics\n")
#
#print "Second Partial Statistics:\n"
#
#statistics=counter.getstat()
#
#if (statistics!=None):
#    keys=statistics.keys()
#    keys.sort()
#    for key in keys:
#        print "Key: %s \t Value: %s" % (key,statistics[key])
#else: print "No Statistics"

raw_input("\nPress Enter for Stop Loop & Final Statistics\n")

print "Stop...."

status_stop=counter.stop()

if (status_stop==0):
    print "Success\n"
else:
    print "Fail:",status_stop,"\n"
    print "\nError:",counter.geterr(),"\n"

print "Final Statistics:\n"

statistics=counter.getstat()    # 'pippo','byte','pluto','paperino','payload')

if (statistics!=None):
    keys=statistics.keys()
    keys.sort()
    for key in keys:
        print "Key: %s \t Value: %s" % (key,statistics[key])
else: print "No Statistics"

if (statistics['req_err']<0):
    print
    for key, val in statistics.iteritems():
        if (val==-1):
            print "Unknow Request: %s" % key
    print

print "Join....\n"

counter.join()

print "DONE"
