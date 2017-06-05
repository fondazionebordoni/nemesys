'''
Created on 14/apr/2016

@author: ewedlund
'''

from common import client


class MistOptions(object):
    
    def __init__(self, options, md5conf):
        self._client = client.getclient(options)
        self._scheduler = options.scheduler
        self._repository = options.repository
        self._tasktimeout = options.tasktimeout
        self._testtimeout = options.testtimeout
        self._httptimeout = options.httptimeout
        self._md5conf = md5conf
    
    def __str__(self, *args, **kwargs):
        s = ""
        s += "============================================\n"
        options_dict = self.__dict__
        for key in options_dict: 
            s += "| %s : %s\n" % (key, options_dict[key])
        s += "============================================\n"
        return s
    
    @property
    def client(self):
        return self._client
    
    @property
    def scheduler(self):
        return self._scheduler
    
    @property
    def repository(self):
        return self._repository
    
    @property
    def tasktimeout(self):
        return self._tasktimeout
    
    @property
    def testtimeout(self):
        return self._testtimeout
    
    @property
    def httptimeout(self):
        return self._httptimeout
    
    @property
    def md5conf(self):
        return self._md5conf
