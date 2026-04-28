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

    def test_session_file_blocks_rce_payload(self):
        """Session file loading must not execute malicious pickle."""
        from gluon.globals import Request, Session, Response

        class Exploit:
            def __reduce__(self):
                import os
                return (os.system, ("echo hacked_session > /tmp/web2py_session",))

        tmpdir = tempfile.mkdtemp()
        app_dir = os.path.join(tmpdir, "welcome")
        sessions_dir = os.path.join(app_dir, "sessions")
        os.makedirs(sessions_dir)

        request = Request(env={})
        request.folder = app_dir
        request.application = "welcome"

        session_file = os.path.join(sessions_dir, "testsession")

        with open(session_file, "wb") as f:
            pickle.dump(Exploit(), f, pickle.HIGHEST_PROTOCOL)

        if os.path.exists("/tmp/web2py_session"):
            os.remove("/tmp/web2py_session")

        s = Session()
        response = Response()
        s.connect(request, response)

        self.assertFalse(os.path.exists("/tmp/web2py_session"))

    def test_secure_loads_blocks_rce_payload(self):
        """secure_loads must not execute malicious pickle after decryption."""
        from gluon.utils import secure_loads

        class Exploit:
            def __reduce__(self):
                import os
                return (os.system, ("echo hacked_utils > /tmp/web2py_utils",))

        payload = pickle.dumps(Exploit(), pickle.HIGHEST_PROTOCOL)

        if os.path.exists("/tmp/web2py_utils"):
         os.remove("/tmp/web2py_utils")

        result = secure_loads(payload, encryption_key=None)

        self.assertIsNone(result)
        self.assertFalse(os.path.exists("/tmp/web2py_utils"))


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
