#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Basic caching classes and methods
=================================

- Cache - The generic caching object interfacing with the others
- CacheInRam - providing caching in ram
- CacheOnDisk - provides caches on disk

Memcache is also available via a different module (see gluon.contrib.memcache)

When web2py is running on Google App Engine,
caching will be provided by the GAE memcache
(see gluon.contrib.gae_memcache)
"""
import traceback
import time
import portalocker
import shelve
import thread
import os
import logging
import re
try:
    import settings
    have_settings = True
except ImportError:
    have_settings = False

logger = logging.getLogger("web2py.cache")

__all__ = ['Cache', 'lazy_cache']


DEFAULT_TIME_EXPIRE = 300


class CacheAbstract(object):
    """
    Abstract class for cache implementations.
    Main function is now to provide referenced api documentation.

    Use CacheInRam or CacheOnDisk instead which are derived from this class.

    Attentions, Michele says:

    There are signatures inside gdbm files that are used directly
    by the python gdbm adapter that often are lagging behind in the
    detection code in python part.
    On every occasion that a gdbm store is probed by the python adapter,
    the probe fails, because gdbm file version is newer.
    Using gdbm directly from C would work, because there is backward
    compatibility, but not from python!
    The .shelve file is discarded and a new one created (with new
    signature) and it works until it is probed again...
    The possible consequences are memory leaks and broken sessions.
    """

    cache_stats_name = 'web2py_cache_statistics'

    def __init__(self, request=None):
        """
        Paremeters
        ----------
        request:
            the global request object
        """
        raise NotImplementedError

    def __call__(self, key, f,
                 time_expire=DEFAULT_TIME_EXPIRE):
        """
        Tries retrieve the value corresponding to `key` from the cache of the
        object exists and if it did not expire, else it called the function `f`
        and stores the output in the cache corresponding to `key`. In the case
        the output of the function is returned.

        :param key: the key of the object to be store or retrieved
        :param f: the function, whose output is to be cached
        :param time_expire: expiration of the cache in microseconds

        - `time_expire` is used to compare the current time with the time when
            the requested object was last saved in cache. It does not affect
            future requests.
        - Setting `time_expire` to 0 or negative value forces the cache to
            refresh.

        If the function `f` is `None` the cache is cleared.
        """
        raise NotImplementedError

    def clear(self, regex=None):
        """
        Clears the cache of all keys that match the provided regular expression.
        If no regular expression is provided, it clears all entries in cache.

        Parameters
        ----------
        regex:
            if provided, only keys matching the regex will be cleared.
            Otherwise all keys are cleared.
        """

        raise NotImplementedError

    def increment(self, key, value=1):
        """
        Increments the cached value for the given key by the amount in value

        Parameters
        ----------
        key:
            key for the cached object to be incremeneted
        value:
            amount of the increment (defaults to 1, can be negative)
        """
        raise NotImplementedError

    def _clear(self, storage, regex):
        """
        Auxiliary function called by `clear` to search and clear cache entries
        """
        r = re.compile(regex)
        for (key, value) in storage.items():
            if r.match(str(key)):
                del storage[key]


class CacheInRam(CacheAbstract):
    """
    Ram based caching

    This is implemented as global (per process, shared by all threads)
    dictionary.
    A mutex-lock mechanism avoid conflicts.
    """

    locker = thread.allocate_lock()
    meta_storage = {}

    def __init__(self, request=None):
        self.initialized = False
        self.request = request
        self.storage = {}

    def initialize(self):
        if self.initialized:
            return
        else:
            self.initialized = True
        self.locker.acquire()
        request = self.request
        if request:
            app = request.application
        else:
            app = ''
        if not app in self.meta_storage:
            self.storage = self.meta_storage[app] = {
                CacheAbstract.cache_stats_name: {'hit_total': 0, 'misses': 0}}
        else:
            self.storage = self.meta_storage[app]
        self.locker.release()

    def clear(self, regex=None):
        self.initialize()
        self.locker.acquire()
        storage = self.storage
        if regex is None:
            storage.clear()
        else:
            self._clear(storage, regex)

        if not CacheAbstract.cache_stats_name in storage.keys():
            storage[CacheAbstract.cache_stats_name] = {
                'hit_total': 0, 'misses': 0}

        self.locker.release()

    def __call__(self, key, f,
                 time_expire=DEFAULT_TIME_EXPIRE,
                 destroyer=None):
        """
        Attention! cache.ram does not copy the cached object. It just stores a reference to it.
        Turns out the deepcopying the object has some problems:
        1) would break backward compatibility
        2) would be limiting because people may want to cache live objects
        3) would work unless we deepcopy no storage and retrival which would make things slow.
        Anyway. You can deepcopy explicitly in the function generating the value to be cached.
        """
        self.initialize()

        dt = time_expire
        now = time.time()

        self.locker.acquire()
        item = self.storage.get(key, None)
        if item and f is None:
            del self.storage[key]
            if destroyer:
                destroyer(item[1])
        self.storage[CacheAbstract.cache_stats_name]['hit_total'] += 1
        self.locker.release()

        if f is None:
            return None
        if item and (dt is None or item[0] > now - dt):
            return item[1]
        elif item and (item[0] < now - dt) and destroyer:
            destroyer(item[1])
        value = f()

        self.locker.acquire()
        self.storage[key] = (now, value)
        self.storage[CacheAbstract.cache_stats_name]['misses'] += 1
        self.locker.release()
        return value

    def increment(self, key, value=1):
        self.initialize()
        self.locker.acquire()
        try:
            if key in self.storage:
                value = self.storage[key][1] + value
            self.storage[key] = (time.time(), value)
        except BaseException, e:
            self.locker.release()
            raise e
        self.locker.release()
        return value


class CacheOnDisk(CacheAbstract):
    """
    Disk based cache

    This is implemented as a shelve object and it is shared by multiple web2py
    processes (and threads) as long as they share the same filesystem.
    The file is locked wen accessed.

    Disk cache provides persistance when web2py is started/stopped but it slower
    than `CacheInRam`

    Values stored in disk cache must be pickable.
    """

    def _close_shelve_and_unlock(self):
        try:
            if self.storage:
                self.storage.close()
        finally:
            if self.locker and self.locked:
                portalocker.unlock(self.locker)
                self.locker.close()
                self.locked = False

    def _open_shelve_and_lock(self):
        """Open and return a shelf object, obtaining an exclusive lock
        on self.locker first. Replaces the close method of the
        returned shelf instance with one that releases the lock upon
        closing."""

        storage = None
        locker = None
        locked = False
        try:
            locker = locker = open(self.locker_name, 'a')
            portalocker.lock(locker, portalocker.LOCK_EX)
            locked = True
            try:
                storage = shelve.open(self.shelve_name)
            except:
                logger.error('corrupted cache file %s, will try rebuild it'
                             % (self.shelve_name))
                storage = None
            if not storage and os.path.exists(self.shelve_name):
                os.unlink(self.shelve_name)
                storage = shelve.open(self.shelve_name)
            if not CacheAbstract.cache_stats_name in storage.keys():
                storage[CacheAbstract.cache_stats_name] = {
                    'hit_total': 0, 'misses': 0}
            storage.sync()
        except Exception, e:
            if storage:
                storage.close()
                storage = None
            if locked:
                portalocker.unlock(locker)
                locker.close()
            locked = False
            raise RuntimeError(
                'unable to create/re-create cache file %s' % self.shelve_name)
        self.locker = locker
        self.locked = locked
        self.storage = storage
        return storage

    def __init__(self, request=None, folder=None):
        self.initialized = False
        self.request = request
        self.folder = folder
        self.storage = {}

    def initialize(self):
        if self.initialized:
            return
        else:
            self.initialized = True
        folder = self.folder
        request = self.request

        # Lets test if the cache folder exists, if not
        # we are going to create it
        folder = folder or os.path.join(request.folder, 'cache')

        if not os.path.exists(folder):
            os.mkdir(folder)

        ### we need this because of a possible bug in shelve that may
        ### or may not lock
        self.locker_name = os.path.join(folder, 'cache.lock')
        self.shelve_name = os.path.join(folder, 'cache.shelve')

    def clear(self, regex=None):
        self.initialize()
        storage = self._open_shelve_and_lock()
        try:
            if regex is None:
                storage.clear()
            else:
                self._clear(storage, regex)
            storage.sync()
        finally:
            self._close_shelve_and_unlock()

    def __call__(self, key, f,
                 time_expire=DEFAULT_TIME_EXPIRE):
        self.initialize()
        dt = time_expire
        storage = self._open_shelve_and_lock()
        try:
            item = storage.get(key, None)
            storage[CacheAbstract.cache_stats_name]['hit_total'] += 1
            if item and f is None:
                del storage[key]
                storage.sync()
            now = time.time()
            if f is None:
                value = None
            elif item and (dt is None or item[0] > now - dt):
                value = item[1]
            else:
                value = f()
                storage[key] = (now, value)
                storage[CacheAbstract.cache_stats_name]['misses'] += 1
                storage.sync()
        finally:
            self._close_shelve_and_unlock()

        return value

    def increment(self, key, value=1):
        self.initialize()
        storage = self._open_shelve_and_lock()
        try:
            if key in storage:
                value = storage[key][1] + value
            storage[key] = (time.time(), value)
            storage.sync()
        finally:
            self._close_shelve_and_unlock()
        return value


class CacheAction(object):
    def __init__(self, func, key, time_expire, cache, cache_model):
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
        self.func = func
        self.key = key
        self.time_expire = time_expire
        self.cache = cache
        self.cache_model = cache_model

    def __call__(self, *a, **b):
        if not self.key:
            key2 = self.__name__ + ':' + repr(a) + ':' + repr(b)
        else:
            key2 = self.key.replace('%(name)s', self.__name__)\
                .replace('%(args)s', str(a)).replace('%(vars)s', str(b))
        cache_model = self.cache_model
        if not cache_model or isinstance(cache_model, str):
            cache_model = getattr(self.cache, cache_model or 'ram')
        return cache_model(key2,
                           lambda a=a, b=b: self.func(*a, **b),
                           self.time_expire)


class Cache(object):
    """
    Sets up generic caching, creating an instance of both CacheInRam and
    CacheOnDisk.
    In case of GAE will make use of gluon.contrib.gae_memcache.

    - self.ram is an instance of CacheInRam
    - self.disk is an instance of CacheOnDisk
    """

    autokey = ':%(name)s:%(args)s:%(vars)s'

    def __init__(self, request):
        """
        Parameters
        ----------
        request:
            the global request object
        """
        # GAE will have a special caching
        if have_settings and settings.global_settings.web2py_runtime_gae:
            from contrib.gae_memcache import MemcacheClient
            self.ram = self.disk = MemcacheClient(request)
        else:
            # Otherwise use ram (and try also disk)
            self.ram = CacheInRam(request)
            try:
                self.disk = CacheOnDisk(request)
            except IOError:
                logger.warning('no cache.disk (IOError)')
            except AttributeError:
                # normally not expected anymore, as GAE has already
                # been accounted for
                logger.warning('no cache.disk (AttributeError)')

    def __call__(self,
                 key=None,
                 time_expire=DEFAULT_TIME_EXPIRE,
                 cache_model=None):
        """
        Decorator function that can be used to cache any function/method.

        Example::

            @cache('key', 5000, cache.ram)
            def f():
                return time.ctime()

        When the function f is called, web2py tries to retrieve
        the value corresponding to `key` from the cache of the
        object exists and if it did not expire, else it calles the function `f`
        and stores the output in the cache corresponding to `key`. In the case
        the output of the function is returned.

        :param key: the key of the object to be store or retrieved
        :param time_expire: expiration of the cache in microseconds
        :param cache_model: "ram", "disk", or other
            (like "memcache" if defined). It defaults to "ram".

        Notes
        -----
        `time_expire` is used to compare the curret time with the time when the
        requested object was last saved in cache. It does not affect future
        requests.
        Setting `time_expire` to 0 or negative value forces the cache to
        refresh.

        If the function `f` is an action, we suggest using
        `request.env.path_info` as key.
        """

        def tmp(func, cache=self, cache_model=cache_model):
            return CacheAction(func, key, time_expire, self, cache_model)
        return tmp

    @staticmethod
    def with_prefix(cache_model, prefix):
        """
        allow replacing cache.ram with cache.with_prefix(cache.ram,'prefix')
        it will add prefix to all the cache keys used.
        """
        return lambda key, f, time_expire=DEFAULT_TIME_EXPIRE, prefix=prefix:\
            cache_model(prefix + key, f, time_expire)


def lazy_cache(key=None, time_expire=None, cache_model='ram'):
    """
    can be used to cache any function including in modules,
    as long as the cached function is only called within a web2py request
    if a key is not provided, one is generated from the function name
    the time_expire defaults to None (no cache expiration)
    if cache_model is "ram" then the model is current.cache.ram, etc.
    """
    def decorator(f, key=key, time_expire=time_expire, cache_model=cache_model):
        key = key or repr(f)

        def g(*c, **d):
            from gluon import current
            return current.cache(key, time_expire, cache_model)(f)(*c, **d)
        g.__name__ = f.__name__
        return g
    return decorator
