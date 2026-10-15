#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for redis """

import json
import pickle
import unittest
from datetime import datetime

from gluon.globals import Request, Response, Session, current
from gluon.storage import Storage
from gluon.utils import web2py_uuid

try:
    from gluon.contrib.redis_cache import RedisCache, RedisClient
    from gluon.contrib.redis_session import RedisSession
    from gluon.contrib.redis_scheduler import RScheduler
    from gluon.contrib.redis_utils import RConn
    HAVE_REDIS = True
except (ImportError, RuntimeError):
    # The redis contrib modules raise at import time when the redis library
    # is missing; skip the whole module instead of breaking the test suite.
    HAVE_REDIS = False


class TestRedis(unittest.TestCase):
    """Tests the Redis contrib packages"""

    @classmethod
    def setUpClass(cls):
        if not HAVE_REDIS:
            raise unittest.SkipTest("Redis library not available")
        try:
            import redis
            redis.StrictRedis(host="localhost").ping()
        except Exception:
            raise unittest.SkipTest("Redis not available")

    def setUp(self):
        request = Request(env={})
        request.application = "a"
        request.controller = "c"
        request.function = "f"
        request.folder = "applications/admin"
        response = Response()
        session = Session()
        session.connect(request, response)
        from gluon.globals import current

        current.request = request
        current.response = response
        current.session = session
        self.current = current
        rconn = RConn(host="localhost")
        self.db = RedisSession(redis_conn=rconn, session_expiry=False)
        self.tname = "testtablename"
        return current

    @staticmethod
    def redis_text(value):
        return value.decode() if isinstance(value, bytes) else value

    def test_redis_cache_stores_value_and_expiry(self):
        redis = RConn(host="localhost")
        application = "cache_test_%s" % web2py_uuid()
        cache = RedisClient(redis_conn=redis, application=application)
        key = cache.__keyFormat__("value")
        bucket_set = cache.cache_set_key

        try:
            self.assertEqual(
                cache.cache_it(key, lambda: "cached value", 60), "cached value"
            )

            self.assertEqual(pickle.loads(redis.get(key)), "cached value")
            self.assertGreater(redis.ttl(key), 0)
            self.assertLessEqual(redis.ttl(key), 60)

            buckets = redis.smembers(bucket_set)
            self.assertTrue(buckets)
            bucket = next(iter(buckets))
            cached_keys = {
                self.redis_text(value) for value in redis.smembers(bucket)
            }
            self.assertIn(key, cached_keys)
        finally:
            buckets = redis.smembers(bucket_set)
            if buckets:
                redis.delete(*buckets)
            redis.delete(key, bucket_set)

    def test_inner_send_heartbeat_registers_worker_state(self):
        redis = RConn(host="localhost")
        application = "scheduler_test_%s" % web2py_uuid()
        worker_name = "worker-%s" % web2py_uuid()

        scheduler = RScheduler.__new__(RScheduler)
        scheduler._application = application
        scheduler.r_server = redis
        scheduler.worker_name = worker_name
        scheduler.group_names = ["default"]
        scheduler.heartbeat = 30
        scheduler.w_stats = Storage(status="IDLE", sleep=0)
        scheduler.now = lambda: datetime.now()

        prefix = "w2p:rsched:%s:" % application
        status_key = "%sworker_status:%s" % (prefix, worker_name)
        status_keyset = "%sworker_statuses" % prefix
        all_keys = "%sallkeys" % prefix

        try:
            with redis.pipeline() as pipe:
                pipe.watch("SEND_HEARTBEAT")
                scheduler.inner_send_heartbeat(1, pipe)
                pipe.execute()

            status = {
                self.redis_text(key): self.redis_text(value)
                for key, value in redis.hgetall(status_key).items()
            }
            self.assertEqual(status["status"], "ACTIVE")
            self.assertEqual(status["worker_name"], worker_name)
            self.assertTrue(status["first_heartbeat"])
            self.assertEqual(status["first_heartbeat"], status["last_heartbeat"])
            self.assertEqual(json.loads(status["group_names"]), ["default"])
            self.assertIn(
                status_key,
                {self.redis_text(value) for value in redis.smembers(status_keyset)},
            )
            self.assertEqual(scheduler.w_stats.status, "ACTIVE")
            self.assertEqual(scheduler.w_stats.sleep, 30)
        finally:
            tracked_keys = redis.smembers(all_keys)
            if tracked_keys:
                redis.delete(*tracked_keys)
            redis.delete(all_keys)

    def test_0_redis_session(self):
        """Basic redis read-write"""
        db = self.db
        response = self.current.response
        Field = db.Field
        db.define_table(
            self.tname,
            Field("locked", "boolean", default=False),
            Field("client_ip", length=64),
            Field("created_datetime", "datetime", default=datetime.now().isoformat()),
            Field("modified_datetime", "datetime"),
            Field("unique_key", length=64),
            Field("session_data", "blob"),
        )
        table = db[self.tname]
        unique_key = web2py_uuid()
        dd = dict(
            locked=0,
            client_ip=response.session_client,
            modified_datetime=datetime.now().isoformat(),
            unique_key=unique_key,
            session_data=pickle.dumps(
                {"test": 123, "me": 112312312}, pickle.HIGHEST_PROTOCOL
            ),
        )
        record_id = table.insert(**dd)
        data_from_db = db(table.id == record_id).select()[0]
        self.assertDictEqual(Storage(dd), data_from_db, "get inserted dict")

        dd["locked"] = 1
        table._db(table.id == record_id).update(**dd)
        data_from_db = db(table.id == record_id).select()[0]
        self.assertDictEqual(Storage(dd), data_from_db, "get the updated value")

    def test_0_redis_session_unique_key(self):
        """A session is only returned when the unique_key matches"""
        db = self.db
        Field = db.Field
        db.define_table(
            self.tname,
            Field("locked", "boolean", default=False),
            Field("client_ip", length=64),
            Field("created_datetime", "datetime", default=datetime.now().isoformat()),
            Field("modified_datetime", "datetime"),
            Field("unique_key", length=64),
            Field("session_data", "blob"),
        )
        table = db[self.tname]
        unique_key = web2py_uuid()
        record_id = table.insert(
            locked=0,
            client_ip="127.0.0.1",
            modified_datetime=datetime.now().isoformat(),
            unique_key=unique_key,
            session_data=pickle.dumps({"secret": 1}, pickle.HIGHEST_PROTOCOL),
        )
        self.assertTrue(table(record_id, unique_key=unique_key))
        self.assertFalse(table(record_id, unique_key=web2py_uuid()))
        # a cookie of the form "<record_id>:" carries an empty unique_key
        self.assertFalse(table(record_id, unique_key=""))

    def test_1_redis_delete(self):
        """Redis session get and delete sessions"""
        db = self.db
        table = db[self.tname]
        all_sessions = db(table.id > 0).select()
        self.assertIsNotNone(all_sessions, "we must have some keys in db")

        for entry in all_sessions:
            res = entry.delete_record()
            self.assertIsNone(res, "delete should return None")

        empty_sessions = db(table.id > 0).select()
        self.assertEqual(empty_sessions, [], "no sessions left")
