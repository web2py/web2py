"""
Developed by niphlod@gmail.com
Released under web2py license because includes gluon/cache.py source code
"""

try:
    import cPickle as pickle
except:
    import pickle
import time
import re
import logging
from threading import Lock
import random
from gluon import current
from gluon.cache import CacheAbstract
from gluon.contrib.redis_utils import acquire_lock, release_lock
from gluon.contrib.redis_utils import register_release_lock, RConnectionError

logger = logging.getLogger("web2py.cache.redis")

locker = Lock()


def RedisCache(redis_conn=None, debug=False, with_lock=False, fail_gracefully=False, db=None, application=None):
    """
    Usage example: put in models::

    First of all install Redis
    Ubuntu :
    sudo apt-get install redis-server
    sudo pip install redis

    Then

        from gluon.contrib.redis_utils import RConn
        rconn = RConn()
        from gluon.contrib.redis_cache import RedisCache
        cache.redis = RedisCache(redis_conn=rconn, debug=True, with_lock=True)

    Args:
        redis_conn: a redis-like connection object
        debug: if True adds to stats() the total_hits and misses
        with_lock: sets the default locking mode for creating new keys.
            By default is False (usualy when you choose Redis you do it
            for performances reason)
            When True, only one thread/process can set a value concurrently
        fail_gracefully: if redis is unavailable, returns the value computing it
            instead of raising an exception
        application: if provided, it is used to construct the instance_name,
            allowing to share cache between different applications if needed

    It can be used pretty much the same as cache.ram()
    When you use cache.redis directly you can use :

        redis_key_and_var_name = cache.redis('redis_key_and_var_name', lambda or function,
                                             time_expire=time.time(), with_lock=True)

    to enforce locking. The with_lock parameter overrides the one set in the
    cache.redis instance creation

    cache.redis.stats()
        returns a dictionary with statistics of Redis server
        with one additional key ('w2p_keys') showing all keys currently set
        from web2py with their TTL

    A little wording on how keys are stored (and why the cache_it() function
    and the clear() one look a little bit convoluted): there are a lot of
    libraries that just store values and then use the KEYS command to delete it.
    Until recent releases of this module, that technique was used here too.
    In the need of deleting specific keys in a database with zillions keys in it
    (other web2py apps, other applications in the need of a Redis stack) the
    KEYS command is slow (it needs to scan every key in the database).
    So, we use Redis 'sets' to store keys in "buckets"...
    - every key created gets "indexed" in a bucket
    - all buckets are indexed in a fixed key that never expires
    - all keys generated within the same minute go in the same bucket
    - every bucket is then set to expire when every key within it is expired
    When we need to clear() cached keys:
    - we tell Redis to SUNION all buckets
       - gives us just the keys that are not expired yet
    - buckets that are expired are removed from the fixed set
    - we scan the keys and then delete them
    """

    locker.acquire()
    try:
        if not application:
            application = current.request.application
        instance_name = 'redis_instance_' + application
        if not hasattr(RedisCache, instance_name):
            setattr(RedisCache, instance_name,
                    RedisClient(redis_conn=redis_conn, debug=debug,
                                with_lock=with_lock, fail_gracefully=fail_gracefully,
                                application=application))
        return getattr(RedisCache, instance_name)
    finally:
        locker.release()


class RedisClient(object):

    meta_storage = {}
    MAX_RETRIES = 5
    RETRIES = 0

    def __init__(self, redis_conn=None, debug=False,
                 with_lock=False, fail_gracefully=False, application=None):
        self.request = current.request
        self.debug = debug
        self.with_lock = with_lock
        self.fail_gracefully = fail_gracefully
        self.application = application
        self.prefix = "w2p:cache:%s:" % application
        if self.request:
            app = application
        else:
            app = ''

        if app not in self.meta_storage:
            self.storage = self.meta_storage[app] = {
                CacheAbstract.cache_stats_name: {
                    'hit_total': 0,
                    'misses': 0,
                }}
        else:
            self.storage = self.meta_storage[app]

        self.cache_set_key = 'w2p:%s:___cache_set' % application

        self.r_server = redis_conn
        self._release_script = register_release_lock(self.r_server)

    def initialize(self):
        pass

    def __call__(self, key, f, time_expire=300, with_lock=None):
        if with_lock is None:
            with_lock = self.with_lock
        if time_expire is None:
            time_expire = 24 * 60 * 60
        newKey = self.__keyFormat__(key)
        value = None
        ttl = 0
        try:
            if f is None:
                # delete and never look back
                self.r_server.delete(newKey)
                return None
            # is there a value
            obj = self.r_server.get(newKey)
            # what's its ttl
            if obj:
                ttl = self.r_server.ttl(newKey)
            if ttl > time_expire:
                obj = None
            if obj:
                # was cached
                if self.debug:
                    self.r_server.incr('web2py_cache_statistics:hit_total')
                value = pickle.loads(obj)
            else:
                # naive distributed locking
                if with_lock:
                    lock_key = '%s:__lock' % newKey
                    randomvalue = time.time()
                    al = acquire_lock(self.r_server, lock_key, randomvalue)
                    try:
                        # someone may have computed it
                        obj = self.r_server.get(newKey)
                        if obj is None:
                            value = self.cache_it(newKey, f, time_expire)
                        else:
                            value = pickle.loads(obj)
                    finally:
                        release_lock(self, lock_key, al)
                else:
                    # without distributed locking
                    value = self.cache_it(newKey, f, time_expire)
            return value
        except RConnectionError:
            return self.retry_call(key, f, time_expire, with_lock)

    def cache_it(self, key, f, time_expire):
        if self.debug:
            self.r_server.incr('web2py_cache_statistics:misses')
        cache_set_key = self.cache_set_key
        expire_at = int(time.time() + time_expire) + 120
        bucket_key = "%s:%s" % (cache_set_key, expire_at // 60)
        value = f()
        value_ = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
        if time_expire == 0:
            time_expire = 1
        self.r_server.setex(key, time_expire, value_)
        # print '%s will expire on %s: it goes in bucket %s' % (key, time.ctime(expire_at))
        # print 'that will expire on %s' % (bucket_key, time.ctime(((expire_at / 60) + 1) * 60))
        p = self.r_server.pipeline()
        # add bucket to the fixed set
        p.sadd(cache_set_key, bucket_key)
        # sets the key
        p.setex(key, time_expire, value_)
        # add the key to the bucket
        p.sadd(bucket_key, key)
        # expire the bucket properly
        p.expireat(bucket_key, ((expire_at // 60) + 1) * 60)
        p.execute()
        return value

    def retry_call(self, key, f, time_expire, with_lock):
        self.RETRIES += 1
        if self.RETRIES <= self.MAX_RETRIES:
            logger.error("sleeping %s seconds before reconnecting" % (2 * self.RETRIES))
            time.sleep(2 * self.RETRIES)
            if self.fail_gracefully:
                self.RETRIES = 0
                return f()
            return self.__call__(key, f, time_expire, with_lock)
        else:
            self.RETRIES = 0
            if self.fail_gracefully:
                return f
            raise RConnectionError('Redis instance is unavailable')

    def increment(self, key, value=1):
        try:
            newKey = self.__keyFormat__(key)
            return self.r_server.incr(newKey, value)
        except RConnectionError:
            return self.retry_increment(key, value)

    def retry_increment(self, key, value):
        self.RETRIES += 1
        if self.RETRIES <= self.MAX_RETRIES:
            logger.error("sleeping some seconds before reconnecting")
            time.sleep(2 * self.RETRIES)
            return self.increment(key, value)
        else:
            self.RETRIES = 0
            raise RConnectionError('Redis instance is unavailable')

    def clear(self, regex):
        """
        Auxiliary function called by `clear` to search and
        clear cache entries
        """
        r = re.compile(regex)
        # get all buckets
        buckets = self.r_server.smembers(self.cache_set_key)
        # get all keys in buckets
        if buckets:
            keys = self.r_server.sunion(buckets)
        else:
            return
        prefix = self.prefix
        pipe = self.r_server.pipeline()
        for a in keys:
            if r.match(str(a).replace(prefix, '', 1)):
                pipe.delete(a)
        if random.randrange(0, 100) < 10:
            # do this just once in a while (10% chance)
            self.clear_buckets(buckets)
        pipe.execute()

    def clear_buckets(self, buckets):
        p = self.r_server.pipeline()
        for b in buckets:
            if not self.r_server.exists(b):
                p.srem(self.cache_set_key, b)
        p.execute()

    def delete(self, key):
        newKey = self.__keyFormat__(key)
        return self.r_server.delete(newKey)

    def stats(self):
        stats_collector = self.r_server.info()
        if self.debug:
            stats_collector['w2p_stats'] = dict(
                hit_total=self.r_server.get(
                    'web2py_cache_statistics:hit_total'),
                misses=self.r_server.get('web2py_cache_statistics:misses')
            )
        stats_collector['w2p_keys'] = dict()

        for a in self.r_server.keys("w2p:%s:*" % self.application):
            stats_collector['w2p_keys']["%s_expire_in_sec" % a] = self.r_server.ttl(a)
        return stats_collector

    def __keyFormat__(self, key):
        return '%s%s' % (self.prefix, key.replace(' ', '_'))
