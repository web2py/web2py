#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import os
import pickle
import subprocess
import tempfile
import unittest

from gluon.restricted import TicketStorage, safe_load, safe_loads


class TestRestrictedPickle(unittest.TestCase):
    def test_safe_unpickler_loads_basic_types(self):
        payload = {"traceback": "test error", "layer": "test"}
        pickled = pickle.dumps(payload, pickle.HIGHEST_PROTOCOL)

        self.assertEqual(safe_loads(pickled), payload)
        self.assertEqual(safe_load(io.BytesIO(pickled)), payload)

    def test_safe_unpickler_rejects_unsafe_classes(self):
        pickled = pickle.dumps({"bad": subprocess.Popen}, pickle.HIGHEST_PROTOCOL)
        with self.assertRaises(pickle.UnpicklingError):
            safe_loads(pickled)

    def test_safe_unpickler_loads_full_ticket_structure(self):
        """Verify SafeUnpickler handles realistic ticket dicts with nested types."""
        payload = {
            "layer": "model",
            "code": "x = 1/0",
            "output": "",
            "traceback": "Traceback (most recent call last):\n  ...\nZeroDivisionError",
            "snapshot": {
                "pyver": "Python 3.10",
                "date": "Thu Apr 24 00:00:00 2026",
                "frames": [
                    {
                        "file": "/app/models/db.py",
                        "func": "<module>",
                        "call": "",
                        "lines": {1: "x = 1/0"},
                        "lnum": 1,
                        "dump": {"x": "undefined"},
                    }
                ],
                "etype": "ZeroDivisionError",
                "evalue": "division by zero",
                "exception": {"args": "('division by zero',)"},
                "locals": {"x": "undefined"},
            },
        }
        pickled = pickle.dumps(payload, pickle.HIGHEST_PROTOCOL)
        self.assertEqual(safe_loads(pickled), payload)
        self.assertEqual(safe_load(io.BytesIO(pickled)), payload)

    def test_safe_unpickler_loads_safe_standard_types(self):
        import datetime
        import decimal
        import uuid

        payload = {
            "date": datetime.date(2026, 4, 24),
            "datetime": datetime.datetime(2026, 4, 24, 12, 34, 56),
            "time": datetime.time(12, 34, 56),
            "timedelta": datetime.timedelta(days=1, seconds=5),
            "uuid": uuid.UUID("12345678123456781234567812345678"),
            "decimal": decimal.Decimal("1.23"),
        }
        pickled = pickle.dumps(payload, pickle.HIGHEST_PROTOCOL)
        self.assertEqual(safe_loads(pickled), payload)
        self.assertEqual(safe_load(io.BytesIO(pickled)), payload)

    def test_safe_unpickler_allows_custom_allowed_class(self):
        import sys
        import types

        module_name = "safe_unpickler_custom_module"
        module = types.ModuleType(module_name)
        exec(
            """
class CustomClass(object):
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, CustomClass) and self.value == other.value
""",
            module.__dict__,
        )
        sys.modules[module_name] = module
        try:
            payload = module.CustomClass(42)
            pickled = pickle.dumps(payload, pickle.HIGHEST_PROTOCOL)
            result = safe_loads(
                pickled,
                allowed_classes={module_name: {"CustomClass"}},
            )
            self.assertEqual(result, payload)
        finally:
            del sys.modules[module_name]

    def test_safe_unpickler_rejects_malicious_file_payload(self):
        """safe_load must reject a pickle stream containing an unsafe global."""
        malicious = pickle.dumps({"bad": subprocess.Popen}, pickle.HIGHEST_PROTOCOL)
        with self.assertRaises(pickle.UnpicklingError):
            safe_load(io.BytesIO(malicious))

    def test_safe_unpickler_handles_eof(self):
        """safe_load must raise EOFError on empty/truncated data."""
        with self.assertRaises(EOFError):
            safe_load(io.BytesIO(b""))
        with self.assertRaises(Exception):
            safe_loads(b"")

    def test_ticket_allowed_classes_permits_xml(self):
        """TicketStorage.load must round-trip ticket data containing XML objects."""
        from gluon.html import XML
        from gluon.restricted import TicketStorage

        payload = {
            "layer": "test",
            "traceback": "ZeroDivisionError: division by zero",
            "output": "error",
            "code": "a = 1/0",
            "snapshot": {
                "session": XML("<b>session data</b>"),
                "request": XML("<b>request data</b>"),
            },
        }
        pickled = pickle.dumps(payload, pickle.HIGHEST_PROTOCOL)
        result = safe_loads(pickled, allowed_classes=TicketStorage.TICKET_ALLOWED_CLASSES)
        self.assertEqual(str(result["snapshot"]["session"]), "<b>session data</b>")
        self.assertEqual(str(result["snapshot"]["request"]), "<b>request data</b>")

    def test_ticket_allowed_classes_still_blocks_unsafe(self):
        """TICKET_ALLOWED_CLASSES must not open the door to arbitrary classes."""
        from gluon.restricted import TicketStorage
        malicious = pickle.dumps({"bad": subprocess.Popen}, pickle.HIGHEST_PROTOCOL)
        with self.assertRaises(pickle.UnpicklingError):
            safe_loads(malicious, allowed_classes=TicketStorage.TICKET_ALLOWED_CLASSES)

    def test_snapshot_returns_expected_structure(self):
        """snapshot() must return frame/locals/exception keys without cgitb."""
        from gluon.restricted import snapshot

        try:
            sentinel = 42
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError:
            s = snapshot(context=5, code="", environment={})

        self.assertEqual(s["etype"], "ZeroDivisionError")
        self.assertEqual(s["evalue"], "division by zero")
        self.assertIn("frames", s)
        self.assertTrue(len(s["frames"]) > 0)
        # locals of the faulting frame must include our sentinel variable
        self.assertIn("sentinel", s["locals"])
        self.assertIn("pyver", s)
        self.assertIn("date", s)

    def test_snapshot_stores_environment_as_xml(self):
        """snapshot() must store request/response/session as XML objects."""
        from gluon.html import XML
        from gluon.restricted import snapshot

        env = {
            "request": {"application": "welcome"},
            "response": {"status": 200},
            "session": {"user": "test"},
            "db": object(),  # non-web2py key — must be ignored
        }
        try:
            raise ValueError("test")
        except ValueError:
            s = snapshot(context=5, code="", environment=env)

        self.assertIsInstance(s["request"], XML)
        self.assertIsInstance(s["response"], XML)
        self.assertIsInstance(s["session"], XML)
        self.assertNotIn("db", s)

    def test_session_file_blocks_rce_payload(self):
        """Session file loading must not execute malicious pickle."""
        from gluon.globals import Request, Session, Response

        sentinel_fd, sentinel_path = tempfile.mkstemp(prefix="web2py_session_rce_")
        os.close(sentinel_fd)
        os.remove(sentinel_path)

        class Exploit:
            def __reduce__(self):
                return (open, (sentinel_path, "w"))

        tmpdir = tempfile.mkdtemp()
        try:
            app_dir = os.path.join(tmpdir, "welcome")
            sessions_dir = os.path.join(app_dir, "sessions")
            os.makedirs(sessions_dir)

            request = Request(env={})
            request.folder = app_dir
            request.application = "welcome"
            request.client = "127.0.0.1"
            session_id = "127.0.0.1-evil"
            cookie = type("Cookie", (), {"value": session_id})()
            request.cookies = {"session_id_welcome": cookie}

            session_file = os.path.join(sessions_dir, session_id)
            with open(session_file, "wb") as f:
                pickle.dump(Exploit(), f, pickle.HIGHEST_PROTOCOL)

            s = Session()
            response = Response()
            s.connect(request, response, safe_unpickle=True)
            if getattr(response, "session_file", None):
                response.session_file.close()

            self.assertFalse(os.path.exists(sentinel_path))
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
            if os.path.exists(sentinel_path):
                os.remove(sentinel_path)

    def test_session_connect_legacy_unpickle_allows_custom_objects(self):
        import sys
        import types

        from gluon.globals import Request, Session, Response

        module_name = "legacy_unpickle_custom_module"
        module = types.ModuleType(module_name)
        exec(
            """
class CustomClass(object):
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, CustomClass) and self.value == other.value
""",
            module.__dict__,
        )
        sys.modules[module_name] = module
        try:
            tmpdir = tempfile.mkdtemp()
            app_dir = os.path.join(tmpdir, "welcome")
            sessions_dir = os.path.join(app_dir, "sessions")
            os.makedirs(sessions_dir)

            request = Request(env={})
            request.folder = app_dir
            request.application = "welcome"
            request.client = "127.0.0.1"
            session_id = "127.0.0.1-1234"
            cookie = type("Cookie", (), {"value": session_id})()
            request.cookies = {"session_id_welcome": cookie}

            session_file = os.path.join(sessions_dir, session_id)
            with open(session_file, "wb") as f:
                pickle.dump({"data": module.CustomClass(123)}, f, pickle.HIGHEST_PROTOCOL)

            s = Session()
            response = Response()
            s.connect(request, response, safe_unpickle=False)
            if getattr(response, "session_file", None):
                response.session_file.close()

            self.assertEqual(s["data"], module.CustomClass(123))
        finally:
            del sys.modules[module_name]

    def test_secure_loads_blocks_rce_payload(self):
        """secure_loads must not execute malicious pickle after decryption."""
        from gluon.utils import secure_loads, secure_dumps

        sentinel_fd, sentinel_path = tempfile.mkstemp(prefix="web2py_utils_rce_")
        os.close(sentinel_fd)
        os.remove(sentinel_path)

        class Exploit:
            def __reduce__(self):
                return (open, (sentinel_path, "w"))

        # Use secure_dumps so the data passes HMAC/signature checks and
        # actually reaches pickle.loads — that's the code path safe_unpickle protects.
        encryption_key = "test-key"
        encrypted = secure_dumps(Exploit(), encryption_key)

        try:
            result = secure_loads(encrypted, encryption_key, safe_unpickle=True)

            self.assertIsNone(result)
            self.assertFalse(os.path.exists(sentinel_path))
        finally:
            if os.path.exists(sentinel_path):
                os.remove(sentinel_path)


class TestTicketStorageFilePath(unittest.TestCase):
    def setUp(self):
        from gluon.globals import Request
        import shutil

        # _error_file computes: request.folder/../app/errors/
        # So with folder=tmpdir/welcome and app="welcome":
        # root = tmpdir/welcome/../welcome = tmpdir/welcome
        # errors_folder = tmpdir/welcome/errors
        self.tmpdir = tempfile.mkdtemp()
        self.app_dir = os.path.join(self.tmpdir, "welcome")
        self.errors_dir = os.path.join(self.app_dir, "errors")
        os.makedirs(self.errors_dir)

        self.request = Request(env={})
        self.request.folder = self.app_dir
        self.storage = TicketStorage()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_ticket(self, ticket_id, data):
        path = os.path.join(self.errors_dir, ticket_id)
        with open(path, "wb") as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

    def _write_raw_ticket(self, ticket_id, raw_bytes):
        path = os.path.join(self.errors_dir, ticket_id)
        with open(path, "wb") as f:
            f.write(raw_bytes)

    def test_load_valid_ticket_from_file(self):
        payload = {"traceback": "some error", "layer": "model", "snapshot": {}}
        self._write_ticket("abc123", payload)
        result = self.storage.load(self.request, "welcome", "abc123")
        self.assertEqual(result, payload)

    def test_load_missing_ticket_returns_empty(self):
        result = self.storage.load(self.request, "welcome", "nonexistent")
        self.assertEqual(result, {})

    def test_load_malicious_ticket_returns_empty(self):
        """A pickle with an unsafe global must be rejected silently."""
        malicious = pickle.dumps({"bad": subprocess.Popen}, pickle.HIGHEST_PROTOCOL)
        self._write_raw_ticket("evil123", malicious)
        result = self.storage.load(self.request, "welcome", "evil123")
        self.assertEqual(result, {})

    def test_load_truncated_ticket_returns_empty(self):
        """A truncated/corrupt pickle file must be handled gracefully."""
        self._write_raw_ticket("truncated", b"\x80\x05\x95")
        result = self.storage.load(self.request, "welcome", "truncated")
        self.assertEqual(result, {})


class TestRestrictedErrorSnapshot(unittest.TestCase):
    """Integration tests: RestrictedError captures snapshot data correctly."""

    def test_snapshot_non_empty_after_exception(self):
        """RestrictedError.snapshot must be populated when an exception is active."""
        from gluon.restricted import RestrictedError

        try:
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError:
            e = RestrictedError(layer="test", code="a = 1/0", output="error", environment={})

        self.assertIsInstance(e.snapshot, dict)
        self.assertNotEqual(e.snapshot, {})
        self.assertEqual(e.snapshot["etype"], "ZeroDivisionError")

    def test_snapshot_xml_survives_pickle_roundtrip(self):
        """A ticket dict with XML snapshot values must survive safe_loads with TICKET_ALLOWED_CLASSES.

        This is the end-to-end proof that the two bugs are fixed together:
        snapshot() producing XML objects (cgitb fix) + TICKET_ALLOWED_CLASSES allowing
        them through safe_loads (allowlist fix).
        """
        from gluon.html import XML
        from gluon.restricted import RestrictedError, TicketStorage

        env = {
            "request": {"application": "welcome"},
            "response": {"status": 200},
            "session": {"user": "alice"},
        }
        try:
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError:
            e = RestrictedError(layer="test", code="a = 1/0", output="error", environment=env)

        self.assertIsInstance(e.snapshot.get("request"), XML)
        self.assertIsInstance(e.snapshot.get("session"), XML)

        ticket_dict = {
            "layer": e.layer,
            "code": e.code,
            "output": e.output,
            "traceback": e.traceback,
            "snapshot": e.snapshot,
        }
        pickled = pickle.dumps(ticket_dict, pickle.HIGHEST_PROTOCOL)
        result = safe_loads(pickled, allowed_classes=TicketStorage.TICKET_ALLOWED_CLASSES)
        self.assertIsInstance(result["snapshot"]["request"], XML)
        self.assertIsInstance(result["snapshot"]["session"], XML)