"""
Developed by 616d41631bff906704951934ffe4015e
Released under web2py license because includes gluon/cache.py source code
"""

import redis
from gluon import current
from gluon.cache import CacheAbstract
import cPickle as pickle
import time
import re

import thread

locker = thread.allocate_lock()

def RedisCache(*args, **vars):
    """
    Usage example: put in models

    from gluon.contrib.redis import RedisCache
    cache.redis = RedisCache('localhost:6379',db=None, debug=True)

    cache.redis.stats() 
    
    return a dictionary with statistics of Redis server
    with one additional key ('w2p_keys') showing all keys currently set
    from web2py with their TTL
    if debug=True additional tracking is activate and another key is added
    ('w2p_stats') showing total_hits and misses    
    """
    
    locker.acquire()
    try:
        if not hasattr(RedisCache, 'redis_instance'):
            RedisCache.redis_instance = RedisClient(*args, **vars)
    finally:
        locker.release()
    return RedisCache.redis_instance


class RedisClient(object):

    meta_storage = {}

    def __init__(self, server='localhost:6379', db=None, debug=False):
        host,port = (address.split(':')+['6379'])[:2]
        port = int(port)
        self.request=current.request
        self.debug = debug
        if request:
            app = request.application
        else:
            app = ''
        
        if not app in self.meta_storage:
            self.storage = self.meta_storage[app] = {
                CacheAbstract.cache_stats_name: {
                    'hit_total': 0,
                    'misses': 0,
                    }}
        else:
            self.storage = self.meta_storage[app]

        self.r_server = redis.Redis(host=host, port=port, db=db or 0)

    def __call__(self, key, f, time_expire=300):
        if time_expire == None:
            time_expire = 10**10
        key = self.__keyFormat__(key)
        value = None
        obj = self.r_server.get(key)
        if obj:
            if self.debug:
                self.r_server.incr('web2py_cache_statistics:hit_total') 
            value = pickle.loads(obj)
        elif f is None:
            if obj: self.r_server.delete(key)
        else:
            if self.debug:
                self.r_server.incr('web2py_cache_statistics:misses')
            value = f()
            self.r_server.setex(key, pickle.dumps(value), time_expire)
        return value

    def increment(self, key, value=1, time_expire=300):
        newKey = self.__keyFormat__(key)
        obj = self.r_server.get(newKey)
        if obj:
            return self.r_server.incr(newKey, value)
        else:
            self.r_server.setex(newKey, value, time_expire)
            return value

    def clear(self, regex):
        """
        Auxiliary function called by `clear` to search and 
        clear cache entries
        """
        r = re.compile(regex)
        prefix = "w2p:%s:" % (self.request.application)
        pipe = self.r_server.pipeline()
        for a in self.r_server.keys("%s*" % \
                                        (prefix)):
            if r.match(str(a).replace(prefix, '', 1)):
                pipe.delete(a)
        pipe.execute()

    def stats(self):
        statscollector = self.r_server.info()
        if self.debug:
            statscollector['w2p_stats'] = dict(
                hit_total = self.r_server.get(
                    'web2py_cache_statistics:hit_total'),
                misses=self.r_server.get('web2py_cache_statistics:misses')
                )
        statscollector['w2p_keys'] = dict()
        for a in self.r_server.keys("w2p:%s:*" % (
                self.request.application)):
            statscollector['w2p_keys']["%s_expire_in_sec" % (a)] = \
                self.r_server.ttl(a)
        return statscollector
        
    def __keyFormat__(self, key):
        return 'w2p:%s:%s' % (self.request.application, 
                              key.replace(' ', '_'))
