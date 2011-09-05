from threading import Thread, Condition
from collections import deque

import time                                 #from time import sleep
import random
import sys
import sniffer                              #from sniffer import *
import analyzer                             #from analyzer import *

shared_buffer = deque([])
condition = Condition()
lock=1

class Sniffer(Thread):

    def __init__(self,dev,buff=32*1024,snaplen=8192,timeout=1,promisc=1,debug=0):
        Thread.__init__(self)
        debug_mode=sniffer.debugmode(debug)
        print "Debug Mode:", debug_mode
        sniffer_init=sniffer.initialize(dev,buff,snaplen,timeout,promisc)
        if (sniffer_init['err_flag']==0):
            print "Success Sniffer\n"
        else:
            print "Fail Sniffer:",sniffer_init['err_flag']
            print "Error Sniffer:",sniffer_init['err_str']

    def getdev(self,req=None):
        device=sniffer.getdev(req)
        if (device!=None):
            print
            keys=device.keys()
            keys.sort()
            for key in keys:
                print "%s \t %s" % (key,device[key])
        else:
            print "No Devices"

    def run(self,sniffer_mode=0):
        for i in range(0,1000):
            global shared_buffer
            global condition
            condition.acquire()
            if len(shared_buffer) == 100:
                print("[Produzione "+str(i)+"] Buffer Pieno! Aspetto!")
                condition.wait()
            #time.sleep(0.2)
            sniffer_data=sniffer.start(sniffer_mode)
            shared_buffer.append(sniffer_data)
            #print("[Produzione "+str(i)+"] Pacchetti in coda: "+str(len(shared_buffer)))
            condition.notify()
            condition.release()
        print("[Produzione "+str(i+1)+"] Finito!!")

    def stop(self):
        sniffer_stop=sniffer.stop()
        if (sniffer_stop['err_flag']==0):
            print "Success\n"
        else:
            print "Fail:",sniffer_stop['err_flag']
            print "Error:",sniffer_stop['err_str']

    def getstat(self):
        sniffer_stat=sniffer.getstat()
        if (sniffer_stat!=None):
            keys=sniffer_stat.keys()
            keys.sort()
            for key in keys:
                print "Key: %s \t Value: %s" % (key,sniffer_stat[key])
        else:
            print "No Statistics"

    def join(self, timeout=None):
        Thread.join(self, timeout)


class Analyzer(Thread):

    def __init__(self,dev,nem,debug=0):
        Thread.__init__(self)
        debug_mode=analyzer.debugmode(debug)
        print "Debug Mode:", debug_mode
        analyzer_init=analyzer.initialize(dev,nem)
        if (analyzer_init==0):
            print "Success Analyzer\n"
        else:
            print "Fail Analyzer\n"

    def run(self):
        global lock
        lock=1
        for i in range(0,1000):
            global shared_buffer
            global condition
            condition.acquire()
            if len(shared_buffer) == 0:
                print("[Consumo "+str(i)+"]Buffer Vuoto! Aspetto!")
                condition.wait()
            #time.sleep(0.3)
            analyzer_data=shared_buffer.popleft()
            analyzer.analyze(analyzer_data['py_byte_array'],analyzer_data['block_size'],analyzer_data['blocks_num'],analyzer_data['datalink'])
            #print("[Consumo "+str(i)+"] Pacchetti in coda: "+str(len(shared_buffer)))
            condition.notify()
            condition.release()
        print("[Consumo "+str(i+1)+"] Finito!!")
        lock=0

    def stop(self):
        analyzer_stop=analyzer.close()
        if (analyzer_stop==0):
            print "Success\n"
        else:
            print "Fail\n"

    def getstat(self):
        analyzer_stat=analyzer.getstat()
        if (analyzer_stat!=None):
            keys=analyzer_stat.keys()
            keys.sort()
            for key in keys:
                print "Key: %s \t Value: %s" % (key,analyzer_stat[key])
        else:
            print "No Statistics"

    def join(self, timeout=None):
        Thread.join(self, timeout)


def getdev(req=None):
    device=sniffer.getdev(req)
    if (device!=None):
        print
        keys=device.keys()
        keys.sort()
        for key in keys:
            print "%s \t %s" % (key,device[key])
    else:
        print "No Devices"


print "\nDevices:"

print "\nFirst Request: All Devices"

getdev()

print "\nSecond Request: Device by IP not assigned to the machine"

getdev('194.244.5.206')

print "\nThird Request: Device by IP assigned to the machine"

getdev('192.168.208.53')

print "\nInitialize Sniffer And Analyzer...."

mysniffer=Sniffer('eth0',32*1024,150,1,1,1)
myanalyzer=Analyzer('192.168.208.53','194.244.5.206',1)

print "Start Sniffer And Analyzer...."

mysniffer.start()
myanalyzer.start()

print "Sniffing And Analyzing...."

#time.sleep(8)

while(lock==1): None

mysniffer.stop()
myanalyzer.stop()

print "Sniffer And Analyzer Statistics:\n"

mysniffer.getstat()
myanalyzer.getstat()

print "\nJoin...."

mysniffer.join()
myanalyzer.join()

print "DONE"




