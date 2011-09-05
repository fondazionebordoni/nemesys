# netran.py
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


from threading import Thread, Condition
from collections import deque

import time
import random
import sys
import sniffer
import analyzer

debug_mode=1
sniffer_init={}
analyzer_init=0

run_sniffer=0
run_analyzer=0

black_hole = deque ([])
shared_buffer = deque([])
condition = Condition()
lock=1


class Device:

    def __init__(self):

    def getdev(self,req=None):
        device=sniffer.getdev(req)
        return device


class Sniffer(Thread):

    def __init__(self,dev,buff=32*1024,snaplen=8192,timeout=1,promisc=1,debug=0):
        Thread.__init__(self)
        global debug_mode
        global sniffer_init
        debug_mode=sniffer.debugmode(debug)
        sniffer_init=sniffer.initialize(dev,buff,snaplen,timeout,promisc)


    def run(self,sniffer_mode=0):
        while(run_sniffer==1):
            global black_hole
            global shared_buffer
            global condition
            condition.acquire()
            if len(shared_buffer) == 100:
                #print("[Produzione "+str(i)+"] Buffer Pieno! Aspetto!")
                condition.wait()
            #time.sleep(0.2)
            sniffer_data=sniffer.start(sniffer_mode)
            shared_buffer.append(sniffer_data)
            #print("[Produzione "+str(i)+"] Pacchetti in coda: "+str(len(shared_buffer)))
            condition.notify()
            condition.release()
        #print("[Produzione "+str(i+1)+"] Finito!!")

    def stop(self):
        sniffer_stop=sniffer.stop()
#        if (sniffer_stop['err_flag']==0):
#            print "Success\n"
#        else:
#            print "Fail:",sniffer_stop['err_flag']
#            print "Error:",sniffer_stop['err_str']

    def getstat(self):
        sniffer_stat=sniffer.getstat()
#        if (sniffer_stat!=None):
#            keys=sniffer_stat.keys()
#            keys.sort()
#            for key in keys:
#                print "Key: %s \t Value: %s" % (key,sniffer_stat[key])
#        else:
#            print "No Statistics"

    def join(self, timeout=None):
        Thread.join(self, timeout)


class Analyzer(Thread):

    def __init__(self,dev,nem,debug=0):
        Thread.__init__(self)
        global debug_mode
        global analyzer_init
        debug_mode=analyzer.debugmode(debug)
        analyzer_init=analyzer.initialize(dev,nem)


    def run(self):
        global lock
        lock=1
        for i in range(0,1000):
            global shared_buffer
            global condition
            condition.acquire()
            if len(shared_buffer) == 0:
                #print("[Consumo "+str(i)+"]Buffer Vuoto! Aspetto!")
                condition.wait()
            #time.sleep(0.3)
            analyzer_data=shared_buffer.popleft()
            analyzer.analyze(analyzer_data['py_byte_array'],analyzer_data['block_size'],analyzer_data['blocks_num'],analyzer_data['datalink'])
            #print("[Consumo "+str(i)+"] Pacchetti in coda: "+str(len(shared_buffer)))
            condition.notify()
            condition.release()
        #print("[Consumo "+str(i+1)+"] Finito!!")
        lock=0

    def stop(self):
        analyzer_stop=analyzer.close()
#        if (analyzer_stop==0):
#            print "Success\n"
#        else:
#            print "Fail\n"

    def getstat(self):
        analyzer_stat=analyzer.getstat()
#        if (analyzer_stat!=None):
#            keys=analyzer_stat.keys()
#            keys.sort()
#            for key in keys:
#                print "Key: %s \t Value: %s" % (key,analyzer_stat[key])
#        else:
#            print "No Statistics"

    def join(self, timeout=None):
        Thread.join(self, timeout)

if __name__ == '__main__':

    print "\nDevices:"

    mydevice=Device()

    print "\nFirst Request: All Devices"

    device=mydevice.getdev()

    if (device!=None):
        print
        keys=device.keys()
        keys.sort()
        for key in keys:
            print "%s \t %s" % (key,device[key])
    else:
        print "No Devices"

    print "\nSecond Request: Device by IP not assigned to the machine"

    device=mydevice.getdev('194.244.5.206')

    if (device!=None):
        print
        keys=device.keys()
        keys.sort()
        for key in keys:
            print "%s \t %s" % (key,device[key])
    else:
        print "No Devices"

    print "\nThird Request: Device by IP assigned to the machine"

    device=mydevice.getdev('192.168.208.53')

    if (device!=None):
        print
        keys=device.keys()
        keys.sort()
        for key in keys:
            print "%s \t %s" % (key,device[key])
    else:
        print "No Devices"


    print "\nInitialize Sniffer And Analyzer...."

    mysniffer=Sniffer('eth0',32*1024,150,1,1,1)

    print "Debug Mode Sniffer:", debug_mode
    if (sniffer_init['err_flag']==0):
        print "Success Sniffer\n"
    else:
        print "Fail Sniffer:",sniffer_init['err_flag']
        print "Error Sniffer:",sniffer_init['err_str']

    myanalyzer=Analyzer('192.168.208.53','194.244.5.206',1)

    print "Debug Mode Analyzer:", debug_mode
    if (analyzer_init==0):
        print "Success Analyzer\n"
    else:
        print "Fail Analyzer\n"


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




