from gluon.contrib.memcache.memcache import Client
from gluon.cache import CacheAbstract
import time

"""
examle of usage:

cache.memcache = MemcacheClient(request,[127.0.0.1:11211],debug=true)
"""

import cPickle as pickle
import thread

locker = thread.allocate_lock()

def MemcacheClient(*a, **b):
    locker.acquire()
    try:
        if not hasattr(MemcacheClient, '__mc_instance'):
            MemcacheClient.__mc_instance = _MemcacheClient(*a, **b)
    finally:
        locker.release()
    return MemcacheClient.__mc_instance

class _MemcacheClient(Client):

    meta_storage = {}

    def __init__(self, request, servers, debug=0, pickleProtocol=0,
                 pickler=pickle.Pickler, unpickler=pickle.Unpickler,
                 pload=None, pid=None):
        self.request=request
        if request:
            app = request.application
        else:
            app = ''
        Client.__init__(self, servers, debug, pickleProtocol,
                        pickler, unpickler, pload, pid)
        if not app in self.meta_storage:
            self.storage = self.meta_storage[app] = {
                CacheAbstract.cache_stats_name: {
                    'hit_total': 0,
                    'misses': 0,
                    }}
        else:
            self.storage = self.meta_storage[app]


    def __call__(self, key, f, time_expire=300):
        if time_expire == None:
            time_expire = 10**10
        # this must be commented because get and set are redefined
        # key = self.__keyFormat__(key)
        value = None
        obj = self.get(key)
        if obj:
            value = obj
        elif f is None:
            if obj: self.delete(key)
        else:
            value = f()
            self.set(key, value, time_expire)
        return value

    def increment(self, key, value=1, time_expire=300):
        newKey = self.__keyFormat__(key)
        obj = Client.get(self, newKey)
        if obj:
            return Client.incr(self, newKey, value)
        else:
            Client.set(self, newKey, value, time_expire)
            return value

    def set(self, key, value, time_expire=300):
        newKey = self.__keyFormat__(key)
        return Client.set(self, newKey, value, time_expire)

    def get(self, key):
        newKey = self.__keyFormat__(key)
        return Client.get(self, newKey)

    def delete(self, key):
        newKey = self.__keyFormat__(key)
        return Client.delete(self, newKey)

    def __keyFormat__(self, key):
        return '%s/%s' % (self.request.application, key.replace(' ', '_'))


