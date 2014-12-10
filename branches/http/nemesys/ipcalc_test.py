'''
Created on 26/05/2014

@author: Elin Wedlund

Unit test of ipcalc

'''

import unittest
import ipcalc

class IpcalcTests(unittest.TestCase):
    
    def test_happycase(self):
        ipaddress = "192.168.112.12"
        netmask = 24
        ips = ipcalc.Network('%s/%d' % (ipaddress, netmask))
        net = ips.network()
        self.assertEqual('192.168.112.0', str(net), "Network value \'%s\' WRONG!" % net)
        bcast = ips.broadcast()
        self.assertMultiLineEqual('192.168.112.255', str(bcast))
        
    def test_fastweb(self):
        ipaddress = "10.0.0.4"
        netmask = 30
        ips = ipcalc.Network('%s/%d' % (ipaddress, netmask))
        net = ips.network()
        self.assertEqual('10.0.0.4', str(net), "Network value \'%s\' WRONG!" % net)
        bcast = ips.broadcast()
        self.assertMultiLineEqual('10.0.0.7', str(bcast))
        
    def test_fastweb_odd(self):
        ipaddress = "10.0.0.5"
        netmask = 30
        ips = ipcalc.Network('%s/%d' % (ipaddress, netmask))
        net = ips.network()
        self.assertEqual('10.0.0.4', str(net), "Network value \'%s\' WRONG!" % net)
        bcast = ips.broadcast()
        self.assertMultiLineEqual('10.0.0.7', str(bcast))

    def test_fastweb_odd2(self):
        ipaddress = "10.67.14.89"
        netmask = 30
        ips = ipcalc.Network('%s/%d' % (ipaddress, netmask))
        net = ips.network()
        self.assertEqual('10.67.14.88', str(net))
        bcast = ips.broadcast()
        self.assertMultiLineEqual('10.67.14.91', str(bcast))
        check_ping(ipaddress, netmask, ips, net, bcast, False)

    def test_fastweb_odd3(self):
        ipaddress = "10.0.0.7"
        netmask = 30
        ips = ipcalc.Network('%s/%d' % (ipaddress, netmask))
        net = ips.network()
        self.assertEqual('10.0.0.4', str(net), "Network value \'%s\' WRONG!" % net)
        bcast = ips.broadcast()
        self.assertMultiLineEqual('10.0.0.7', str(bcast))
        
    def test_fastweb_fibra(self):
        ipaddress = "10.0.0.17"
        netmask = 29
        ips = ipcalc.Network('%s/%d' % (ipaddress, netmask))
        net = ips.network()
        self.assertEqual('10.0.0.16', str(net), "Network value \'%s\' WRONG!" % net)
        bcast = ips.broadcast()
        self.assertMultiLineEqual('10.0.0.23', str(bcast))
        
    def test_fastweb2(self):
        ipaddress = "10.223.3.248"
        netmask = 30
        ips = ipcalc.Network('%s/%d' % (ipaddress, netmask))
        net = ips.network()
        bcast = ips.broadcast()
        
        
        self.assertEqual('10.223.3.248', str(net), "Network value \'%s\' WRONG!" % net)
        self.assertMultiLineEqual('10.223.3.251', str(bcast))
        
def main():
    unittest.main()
    
if __name__ == '__main__':
    main()
