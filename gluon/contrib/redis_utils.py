#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Developed by niphlod@gmail.com
License MIT/BSD/GPL

Serves as base to implement Redis connection object and various utils
for redis_cache, redis_session and redis_scheduler in the future
Should-could be overriden in case redis doesn't keep up (e.g. cluster support)
to ensure compatibility with another - similar - library
"""

import logging
from threading import Lock
import time
from gluon import current

logger = logging.getLogger("web2py.redis_utils")

try:
    import redis
    from redis.exceptions import WatchError as RWatchError
    from redis.exceptions import ConnectionError as RConnectionError
except ImportError:
    logger.error("Needs redis library to work")
    raise RuntimeError('Needs redis library to work')


locker = Lock()


def RConn(*args, **vars):
    """
    Istantiates a StrictRedis connection with parameters, at the first time
    only
    """
    locker.acquire()
    try:
        instance_name = 'redis_conn_' + current.request.application
        if not hasattr(RConn, instance_name):
            setattr(RConn, instance_name, redis.StrictRedis(*args, **vars))
        return getattr(RConn, instance_name)
    finally:
        locker.release()

def acquire_lock(conn, lockname, identifier, ltime=10):
    while True:
        if conn.set(lockname, identifier, ex=ltime, nx=True):
            return identifier
        time.sleep(.01)


_LUA_RELEASE_LOCK = """
if redis.call("get", KEYS[1]) == ARGV[1]
then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


def release_lock(instance, lockname, identifier):
    return instance._release_script(
        keys=[lockname], args=[identifier])


def register_release_lock(conn):
    rtn = conn.register_script(_LUA_RELEASE_LOCK)
    return rtn
