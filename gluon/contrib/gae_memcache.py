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


class MemcacheClient(Client):

    def __init__(self, request):
        self.request = request
        Client.__init__(self)

    def __call__(
        self,
        key,
        f,
        time_expire=300,
        ):
        key = '%s/%s' % (self.request.application, key)
        dt = time_expire
        value = None
        obj = self.get(key)
        if obj and (dt == None or obj[0] > time.time() - dt):
            value = obj[1]
        elif f is None:
            if obj:
                self.delete(key)
        else:
            value = f()
            self.set(key, (time.time(), value))
        return value

    def increment(self, key, value=1):
        key = '%s/%s' % (self.request.application, key)
        obj = self.get(key)
        if obj:
            value = obj[1] + value
        self.set((time.time(), value))
        return value

    def clear(self, key):
        key = '%s/%s' % (self.request.application, key)
        self.delete(key)






