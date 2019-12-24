#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for redis """

import unittest
from datetime import datetime

from gluon._compat import to_bytes, pickle
from gluon.storage import Storage
from gluon.utils import web2py_uuid
from gluon.globals import Request, Response, Session, current
from gluon.contrib.redis_utils import RConn
from gluon.contrib.redis_session import RedisSession
from gluon.contrib.redis_cache import RedisCache


class TestRedis(unittest.TestCase):
    """ Tests the Redis contrib packages """
    def setUp(self):
        request = Request(env={})
        request.application = 'a'
        request.controller = 'c'
        request.function = 'f'
        request.folder = 'applications/admin'
        response = Response()
        session = Session()
        session.connect(request, response)
        from gluon.globals import current
        current.request = request
        current.response = response
        current.session = session
        self.current = current
        rconn = RConn(host='localhost')
        self.db = RedisSession(redis_conn=rconn, session_expiry=False)
        self.tname = 'testtablename'
        return current

    def test_0_redis_session(self):
        """ Basic redis read-write """
        db = self.db
        response = self.current.response
        Field = db.Field
        db.define_table(
            self.tname,
            Field('locked', 'boolean', default=False),
            Field('client_ip', length=64),
            Field('created_datetime', 'datetime',
                  default=datetime.now().isoformat()),
            Field('modified_datetime', 'datetime'),
            Field('unique_key', length=64),
            Field('session_data', 'blob'),
        )
        table = db[self.tname]
        unique_key = web2py_uuid()
        dd = dict(
            locked=0,
            client_ip=response.session_client,
            modified_datetime=datetime.now().isoformat(),
            unique_key=unique_key,
            session_data=pickle.dumps({'test': 123, 'me': 112312312}, pickle.HIGHEST_PROTOCOL)
        )
        record_id = table.insert(**dd)
        data_from_db = db(table.id == record_id).select()[0]
        self.assertDictEqual(Storage(dd), data_from_db, 'get inserted dict')

        dd['locked'] = 1
        table._db(table.id == record_id).update(**dd)
        data_from_db = db(table.id == record_id).select()[0]
        self.assertDictEqual(Storage(dd), data_from_db, 'get the updated value')

    def test_1_redis_delete(self):
        """ Redis session get and delete sessions """
        db = self.db
        table = db[self.tname]
        all_sessions = db(table.id > 0).select()
        self.assertIsNotNone(all_sessions, 'we must have some keys in db')

        for entry in all_sessions:
            res = entry.delete_record()
            self.assertIsNone(res, 'delete should return None')

        empty_sessions = db(table.id > 0).select()
        self.assertEqual(empty_sessions, [], 'no sessions left')

