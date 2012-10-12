#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Developed by Robin Bhattacharyya (memecache for GAE)
Released under the web2py license (LGPL)

from gluon.contrib.gae_memcache import MemcacheClient
cache.ram=cache.disk=MemcacheClient(request)
"""

import time
from google.appengine.api.memcache import Client

class MemcacheClient(object):

    client = Client()

    def __init__(self, request):
        self.request = request

    def __call__(
        self,
        key,
        f,
        time_expire=300,
        ):        
        key = '%s/%s' % (self.request.application, key)
        dt = time_expire
        value = None
        obj = self.client.get(key)
        if obj and (dt == None or obj[0] > time.time() - dt):
            value = obj[1]
        elif f is None:
            if obj:
                self.client.delete(key)
        else:
            value = f()
            self.client.set(key, (time.time(), value))
        return value

    def increment(self, key, value=1):
        key = '%s/%s' % (self.request.application, key)
        obj = self.client.get(key)
        if obj:
            value = obj[1] + value
        self.client.set(key, (time.time(), value))        
        return value

    def clear(self, key = None):
        if key:
            key = '%s/%s' % (self.request.application, key)
            self.client.delete(key)
        else:
            self.client.flush_all()

    def delete(self,*a,**b):
        return self.client.delete(*a,**b)

    def get(self,*a,**b):
        return self.client.delete(*a,**b)

    def set(self,*a,**b):
        return self.client.delete(*a,**b)

    def flush_all(self,*a,**b):
        return self.client.delete(*a,**b)
