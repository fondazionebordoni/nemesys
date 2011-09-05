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
import contabyte

debug_mode=1
sniffer_init={}
contabyte_init=0

sniffer_flag=0
analyzer_flag=0

run_sniffer=0
run_contabyte=0

black_hole = []
shared_buffer = deque([])
condition = Condition()


class Device:

    def __init__(self): None

    def getdev(self,req=None):
        device=sniffer.getdev(req)
        return device


class Sniffer(Thread):

    def __init__(self,dev,buff=32*1024,snaplen=8192,timeout=1,promisc=1,debug=0):
        Thread.__init__(self)
        global debug_mode
        global sniffer_init
        global run_sniffer
        debug_mode=sniffer.debugmode(debug)
        sniffer_init=sniffer.initialize(dev,buff,snaplen,timeout,promisc)
        if (sniffer_init['err_flag']==0):
            run_sniffer=1

    def run(self,sniffer_mode=0):
        global run_sniffer
        global sniffer_flag
        sniffer_flag=1
        while (run_sniffer==1):
            global analyzer_flag
            global black_hole
            global shared_buffer
            global condition
            if (analyzer_flag==1):
                condition.acquire()
                if (len(shared_buffer) == 100):
                    condition.wait()
                sniffer_data=sniffer.start(sniffer_mode)
                shared_buffer.append(sniffer_data)
                condition.notify()
                condition.release()
            else:
                sniffer_data=sniffer.start(sniffer_mode)
                black_hole.insert(0,sniffer_data)
        sniffer_flag=0


    def stop(self):
        global run_sniffer
        global shared_buffer
        while (len(shared_buffer) != 0): None
        run_sniffer=0
        while (sniffer_flag != 0): None
        sniffer_stop=sniffer.stop()
        return sniffer_stop


    def getstat(self):
        sniffer_stat=sniffer.getstat()
        return sniffer_stat


    def join(self, timeout=None):
        Thread.join(self, timeout)


class Contabyte(Thread):

    def __init__(self,dev,nem,debug=0):
        Thread.__init__(self)
        global debug_mode
        global contabyte_init
        global run_contabyte
        debug_mode=contabyte.debugmode(debug)
        contabyte_init=contabyte.initialize(dev,nem)
        if (contabyte_init==0):
            run_contabyte=1


    def run(self):
        global run_contabyte
        global analyzer_flag
        analyzer_flag=1
        while (run_contabyte==1):
            global sniffer_flag
            global shared_buffer
            global condition
            if (sniffer_flag==1):
                condition.acquire()
                if (len(shared_buffer) == 0):
                    condition.wait()
                contabyte_data=shared_buffer.popleft()
                contabyte.analyze(contabyte_data['py_byte_array'],contabyte_data['block_size'],contabyte_data['blocks_num'],contabyte_data['datalink'])
                condition.notify()
                condition.release()
            else:
                run_contabyte=0
        analyzer_flag=0


    def stop(self):
        global analyzer_flag
        global shared_buffer
        global run_contabyte
        analyzer_flag=0
        while (len(shared_buffer) != 0): None
        run_contabyte=0
        contabyte_stop=contabyte.close()
        return contabyte_stop


    def getstat(self):
        contabyte_stat=contabyte.getstat()
        return contabyte_stat


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


    print "\nInitialize Sniffer And Contabyte...."

    mysniffer=Sniffer('eth0',32*1024,150,1,1,1)

    print "Debug Mode Sniffer:", debug_mode
    if (sniffer_init['err_flag']==0):
        print "Success Sniffer\n"
    else:
        print "Fail Sniffer:",sniffer_init['err_flag']
        print "Error Sniffer:",sniffer_init['err_str']

    mycontabyte=Contabyte('192.168.208.53','194.244.5.206',1)

    print "Debug Mode Contabyte:", debug_mode
    if (contabyte_init==0):
        print "Success Contabyte\n"
    else:
        print "Fail Contabyte\n"


    print "Start Sniffer And Contabyte...."

    mysniffer.start()
    mycontabyte.start()

    print "Sniffing And Analyzing...."

    time.sleep(30)

    contabyte_stop=mycontabyte.stop()
    if (contabyte_stop==0):
        print "Success Contabyte"
    else:
        print "Fail\n"

    time.sleep(1)

    sniffer_stop=mysniffer.stop()
    if (sniffer_stop['err_flag']==0):
        print "Success Sniffer"
    else:
        print "Fail:",sniffer_stop['err_flag']
        print "Error:",sniffer_stop['err_str']

    time.sleep(1)

    print "Sniffer And Contabyte Statistics:\n"

    sniffer_stat=mysniffer.getstat()
    if (sniffer_stat!=None):
        keys=sniffer_stat.keys()
        keys.sort()
        for key in keys:
            print "Key: %s \t Value: %s" % (key,sniffer_stat[key])
    else:
        print "No Statistics"

    print

    contabyte_stat=mycontabyte.getstat()
    if (contabyte_stat!=None):
        keys=contabyte_stat.keys()
        keys.sort()
        for key in keys:
            print "Key: %s \t Value: %s" % (key,contabyte_stat[key])
    else:
        print "No Statistics"

    print "\nJoin...."

    mysniffer.join()
    mycontabyte.join()

    print "DONE"




