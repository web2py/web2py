"""
Developed by niphlod@gmail.com
"""

import redis
from redis.exceptions import ConnectionError
from gluon import current
from gluon.storage import Storage
import cPickle as pickle
import time
import re
import logging
import thread

logger = logging.getLogger("web2py.session.redis")

locker = thread.allocate_lock()


def RedisSession(*args, **vars):
    """
    Usage example: put in models
    from gluon.contrib.redis_session import RedisSession
    sessiondb = RedisSession('localhost:6379',db=0, session_expiry=False)
    session.connect(request, response, db = sessiondb)

    Simple slip-in storage for session
    """

    locker.acquire()
    try:
        if not hasattr(RedisSession, 'redis_instance'):
            RedisSession.redis_instance = RedisClient(*args, **vars)
    finally:
        locker.release()
    return RedisSession.redis_instance


class RedisClient(object):

    meta_storage = {}
    MAX_RETRIES = 5
    RETRIES = 0

    def __init__(self, server='localhost:6379', db=None, debug=False, session_expiry=False):
        """session_expiry can be an integer, in seconds, to set the default expiration
           of sessions. The corresponding record will be deleted from the redis instance,
           and there's virtually no need to run sessions2trash.py
        """
        self.server = server
        self.db = db or 0
        host, port = (self.server.split(':') + ['6379'])[:2]
        port = int(port)
        self.debug = debug
        if current and current.request:
            self.app = current.request.application
        else:
            self.app = ''
        self.r_server = redis.Redis(host=host, port=port, db=self.db)
        self.tablename = None
        self.session_expiry = session_expiry

    def get(self, what, default):
        return self.tablename

    def Field(self, fieldname, type='string', length=None, default=None,
              required=False, requires=None):
        return None

    def define_table(self, tablename, *fields, **args):
        if not self.tablename:
            self.tablename = MockTable(
                self, self.r_server, tablename, self.session_expiry)
        return self.tablename

    def __getitem__(self, key):
        return self.tablename

    def __call__(self, where=''):
        q = self.tablename.query
        return q

    def commit(self):
        #this is only called by session2trash.py
        pass


class MockTable(object):

    def __init__(self, db, r_server, tablename, session_expiry):
        self.db = db
        self.r_server = r_server
        self.tablename = tablename
        #set the namespace for sessions of this app
        self.keyprefix = 'w2p:sess:%s' % tablename.replace(
            'web2py_session_', '')
        #fast auto-increment id (needed for session handling)
        self.serial = "%s:serial" % self.keyprefix
        #index of all the session keys of this app
        self.id_idx = "%s:id_idx" % self.keyprefix
        #remember the session_expiry setting
        self.session_expiry = session_expiry

    def getserial(self):
        #return an auto-increment id
        return "%s" % self.r_server.incr(self.serial, 1)

    def __getattr__(self, key):
        if key == 'id':
            #return a fake query. We need to query it just by id for normal operations
            self.query = MockQuery(field='id', db=self.r_server, prefix=self.keyprefix, session_expiry=self.session_expiry)
            return self.query
        elif key == '_db':
            #needed because of the calls in sessions2trash.py and globals.py
            return self.db

    def insert(self, **kwargs):
        #usually kwargs would be a Storage with several keys:
        #'locked', 'client_ip','created_datetime','modified_datetime'
        #'unique_key', 'session_data'
        #retrieve a new key
        newid = self.getserial()
        key = "%s:%s" % (self.keyprefix, newid)
        #add it to the index
        self.r_server.sadd(self.id_idx, key)
        #set a hash key with the Storage
        self.r_server.hmset(key, kwargs)
        if self.session_expiry:
            self.r_server.expire(key, self.session_expiry)
        return newid


class MockQuery(object):
    """a fake Query object that supports querying by id
       and listing all keys. No other operation is supported
    """
    def __init__(self, field=None, db=None, prefix=None, session_expiry=False):
        self.field = field
        self.value = None
        self.db = db
        self.keyprefix = prefix
        self.op = None
        self.session_expiry = session_expiry

    def __eq__(self, value, op='eq'):
        self.value = value
        self.op = op

    def __gt__(self, value, op='ge'):
        self.value = value
        self.op = op

    def select(self):
        if self.op == 'eq' and self.field == 'id' and self.value:
            #means that someone wants to retrieve the key self.value
            rtn = self.db.hgetall("%s:%s" % (self.keyprefix, self.value))
            if rtn == dict():
                #return an empty resultset for non existing key
                return []
            else:
                return [Storage(rtn)]
        elif self.op == 'ge' and self.field == 'id' and self.value == 0:
            #means that someone wants the complete list
            rtn = []
            id_idx = "%s:id_idx" % self.keyprefix
            #find all session keys of this app
            allkeys = self.db.smembers(id_idx)
            for sess in allkeys:
                val = self.db.hgetall(sess)
                if val == dict():
                    if self.session_expiry:
                        #clean up the idx, because the key expired
                        self.db.srem(id_idx, sess)
                        continue
                    else:
                        continue
                val = Storage(val)
                #add a delete_record method (necessary for sessions2trash.py)
                val.delete_record = RecordDeleter(
                    self.db, sess, self.keyprefix)
                rtn.append(val)
            return rtn
        else:
            raise Exception("Operation not supported")

    def update(self, **kwargs):
        #means that the session has been found and needs an update
        if self.op == 'eq' and self.field == 'id' and self.value:
            rtn = self.db.hmset("%s:%s" % (self.keyprefix, self.value), kwargs)
            if self.session_expiry:
                self.db.expire(key, self.session.expiry)
            return rtn


class RecordDeleter(object):
    """Dumb record deleter to support sessions2trash.py"""

    def __init__(self, db, key, keyprefix):
        self.db, self.key, self.keyprefix = db, key, keyprefix

    def __call__(self):
        id_idx = "%s:id_idx" % self.keyprefix
        #remove from the index
        self.db.srem(id_idx, self.key)
        #remove the key itself
        self.db.delete(self.key)
