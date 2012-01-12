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
- CacheInDisk - provides caches on disk

Memcache is also available via a different module (see gluon.contrib.memcache)

When web2py is running on Google App Engine,
caching will be provided by the GAE memcache
(see gluon.contrib.gae_memcache)
"""

import time
import portalocker
import shelve
import thread
import os
import logging
import re

logger = logging.getLogger("web2py.cache")

__all__ = ['Cache']


DEFAULT_TIME_EXPIRE = 300


class CacheAbstract(object):
    """
    Abstract class for cache implementations.
    Main function is now to provide referenced api documentation.

    Use CacheInRam or CacheOnDisk instead which are derived from this class.
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
                time_expire = DEFAULT_TIME_EXPIRE):
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
        self.locker.acquire()
        self.request = request
        if request:
            app = request.application
        else:
            app = ''
        if not app in self.meta_storage:
            self.storage = self.meta_storage[app] = {CacheAbstract.cache_stats_name: {
                'hit_total': 0,
                'misses': 0,
            }}
        else:
            self.storage = self.meta_storage[app]
        self.locker.release()

    def clear(self, regex=None):
        self.locker.acquire()
        storage = self.storage
        if regex is None:
            storage.clear()
        else:
            self._clear(storage, regex)

        if not CacheAbstract.cache_stats_name in storage.keys():
            storage[CacheAbstract.cache_stats_name] = {
                'hit_total': 0,
                'misses': 0,
            }

        self.locker.release()

    def __call__(self, key, f,
                time_expire = DEFAULT_TIME_EXPIRE):
        """
        Attention! cache.ram does not copy the cached object. It just stores a reference to it.
        Turns out the deepcopying the object has some problems:
        1) would break backward compatibility
        2) would be limiting because people may want to cache live objects
        3) would work unless we deepcopy no storage and retrival which would make things slow.
        Anyway. You can deepcopy explicitly in the function generating the value to be cached.
        """

        dt = time_expire

        self.locker.acquire()
        item = self.storage.get(key, None)
        if item and f is None:
            del self.storage[key]
        self.storage[CacheAbstract.cache_stats_name]['hit_total'] += 1
        self.locker.release()

        if f is None:
            return None
        if item and (dt is None or item[0] > time.time() - dt):
            return item[1]
        value = f()

        self.locker.acquire()
        self.storage[key] = (time.time(), value)
        self.storage[CacheAbstract.cache_stats_name]['misses'] += 1
        self.locker.release()
        return value

    def increment(self, key, value=1):
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

    speedup_checks = set()

    def __init__(self, request, folder=None):
        self.request = request

        # Lets test if the cache folder exists, if not
        # we are going to create it
        folder = folder or os.path.join(request.folder, 'cache')

        if not os.path.exists(folder):
            os.mkdir(folder)

        ### we need this because of a possible bug in shelve that may
        ### or may not lock
        self.locker_name = os.path.join(folder,'cache.lock')
        self.shelve_name = os.path.join(folder,'cache.shelve')

        locker, locker_locked = None, False
        speedup_key = (folder,CacheAbstract.cache_stats_name)
        if not speedup_key in self.speedup_checks or \
                not os.path.exists(self.shelve_name):
            try:
                locker = open(self.locker_name, 'a')
                portalocker.lock(locker, portalocker.LOCK_EX)
                locker_locked = True
                storage = shelve.open(self.shelve_name)
                try:
                    if not storage.has_key(CacheAbstract.cache_stats_name):
                        storage[CacheAbstract.cache_stats_name] = {
                            'hit_total': 0,
                            'misses': 0,
                            }
                        storage.sync()
                finally:
                    storage.close()
                self.speedup_checks.add(speedup_key)
            except ImportError:
                pass # no module _bsddb, ignoring exception now so it makes a ticket only if used
            except:
                logger.error('corrupted file %s, will try delete it!' \
                                 % self.shelve_name)
                try:
                    os.unlink(self.shelve_name)
                except IOError:
                    logger.warn('unable to delete file %s' % self.shelve_name)
                except OSError:
                    logger.warn('unable to delete file %s' % self.shelve_name)
            if locker_locked:
                portalocker.unlock(locker)
            if locker:
                locker.close()

    def clear(self, regex=None):
        locker = open(self.locker_name,'a')
        portalocker.lock(locker, portalocker.LOCK_EX)
        storage = shelve.open(self.shelve_name)
        try:
            if regex is None:
                storage.clear()
            else:
                self._clear(storage, regex)
            if not CacheAbstract.cache_stats_name in storage.keys():
                storage[CacheAbstract.cache_stats_name] = {
                    'hit_total': 0,
                    'misses': 0,
                }
            storage.sync()
        finally:
            storage.close()
        portalocker.unlock(locker)
        locker.close()

    def __call__(self, key, f,
                time_expire = DEFAULT_TIME_EXPIRE):
        dt = time_expire

        locker = open(self.locker_name,'a')
        portalocker.lock(locker, portalocker.LOCK_EX)
        storage = shelve.open(self.shelve_name)

        item = storage.get(key, None)
        if item and f is None:
            del storage[key]

        storage[CacheAbstract.cache_stats_name] = {
            'hit_total': storage[CacheAbstract.cache_stats_name]['hit_total'] + 1,
            'misses': storage[CacheAbstract.cache_stats_name]['misses']
        }

        storage.sync()

        portalocker.unlock(locker)
        locker.close()

        if f is None:
            return None
        if item and (dt is None or item[0] > time.time() - dt):
            return item[1]
        value = f()

        locker = open(self.locker_name,'a')
        portalocker.lock(locker, portalocker.LOCK_EX)
        storage[key] = (time.time(), value)

        storage[CacheAbstract.cache_stats_name] = {
            'hit_total': storage[CacheAbstract.cache_stats_name]['hit_total'],
            'misses': storage[CacheAbstract.cache_stats_name]['misses'] + 1
        }

        storage.sync()

        storage.close()
        portalocker.unlock(locker)
        locker.close()

        return value

    def increment(self, key, value=1):
        locker = open(self.locker_name,'a')
        portalocker.lock(locker, portalocker.LOCK_EX)
        storage = shelve.open(self.shelve_name)
        try:
            if key in storage:
                value = storage[key][1] + value
            storage[key] = (time.time(), value)
            storage.sync()
        finally:
            storage.close()
            portalocker.unlock(locker)
            locker.close()
        return value


class Cache(object):
    """
    Sets up generic caching, creating an instance of both CacheInRam and
    CacheOnDisk.
    In case of GAE will make use of gluon.contrib.gae_memcache.

    - self.ram is an instance of CacheInRam
    - self.disk is an instance of CacheOnDisk
    """

    def __init__(self, request):
        """
        Parameters
        ----------
        request:
            the global request object
        """
        # GAE will have a special caching
        import settings
        if settings.global_settings.web2py_runtime_gae:
            from contrib.gae_memcache import MemcacheClient
            self.ram=self.disk=MemcacheClient(request)
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
                key = None,
                time_expire = DEFAULT_TIME_EXPIRE,
                cache_model = None):
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
        :param cache_model: `cache.ram`, `cache.disk`, or other
            (like `cache.memcache` if defined). It defaults to `cache.ram`.

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
        if not cache_model:
            cache_model = self.ram

        def tmp(func):
            def action():
                return cache_model(key, func, time_expire)
            action.__name___ = func.__name__
            action.__doc__ = func.__doc__
            return action

        return tmp




