#!/bin/python
# -*- coding: utf-8 -*-

"""
    Unit tests for the admin webservices controller path containment
"""

import base64
import os
import shutil
import tempfile
import time
import unittest
from unittest import mock

from gluon.fileutils import read_file as _read_source
from gluon.http import HTTP
from gluon.restricted import compile2, restricted


class TestWebservicesPathContainment(unittest.TestCase):
    def setUp(self):
        from gluon.globals import Request, Response, Session, current

        request = Request(env={})
        request.application = "admin"
        request.controller = "webservices"
        request.function = "read_file"
        request.folder = os.path.abspath(os.path.join("applications", "admin"))
        request.env.http_host = "127.0.0.1:8000"
        request.env.remote_addr = "127.0.0.1"
        request.client = request.env.remote_addr
        request.is_local = True
        response = Response()
        session = Session()
        session.connect(request, response)
        current.request = request
        current.response = response
        current.session = session

        from gluon.fileutils import listdir

        self.apps_root = os.path.abspath(os.path.dirname(request.folder))
        self.env = locals()
        filename = os.path.join(request.folder, "controllers", "webservices.py")
        restricted(compile2(_read_source(filename), filename), self.env,
                   layer=filename)

    def test_read_file_rejects_escape(self):
        read_file = self.env["read_file"]
        with self.assertRaises(HTTP):
            read_file("../../../../../../etc/passwd", b64=True)
        with self.assertRaises(HTTP):
            read_file("/etc/hosts", b64=True)

    def test_read_file_allows_in_tree(self):
        read_file = self.env["read_file"]
        data = base64.b64decode(read_file("admin/controllers/webservices.py",
                                          b64=True))
        self.assertIn(b"jsonrpc", data)

    def test_list_files_rejects_escape(self):
        list_files = self.env["list_files"]
        with self.assertRaises(HTTP):
            list_files("../..")

    def test_write_file_rejects_escape(self):
        write_file = self.env["write_file"]
        escaped = os.path.join(self.apps_root, os.pardir, "_ws_escape_test.tmp")
        escaped = os.path.abspath(escaped)
        try:
            with self.assertRaises(HTTP):
                write_file("../_ws_escape_test.tmp",
                           base64.b64encode(b"owned").decode(), b64=True)
            self.assertFalse(os.path.exists(escaped))
        finally:
            if os.path.exists(escaped):
                os.unlink(escaped)


class TestWebservicesLoginLockout(unittest.TestCase):
    def setUp(self):
        from gluon.validators import CRYPT

        self.root = tempfile.mkdtemp()
        self.folder = os.path.join(self.root, "applications", "admin")
        os.makedirs(os.path.join(self.folder, "private"))
        with open(os.path.join(self.root, "parameters_8000.py"), "w") as f:
            f.write('password="%s"\n' % CRYPT()("secret")[0])
        self.deny_file = os.path.join(self.folder, "private", "hosts.deny")

    def tearDown(self):
        shutil.rmtree(self.root)

    def run_access(self, password, multi_user_mode=False, crypt=None):
        from gluon.compileapp import build_environment
        from gluon.globals import Request, Response, Session

        request = Request(env={})
        request.application = "admin"
        request.controller = "webservices"
        request.function = "call"
        request.folder = self.folder
        request.env.server_port = "8000"
        request.env.remote_addr = "203.0.113.10"
        request.client = request.env.remote_addr
        request.is_https = True
        request.env.http_authorization = "Basic " + base64.b64encode(
            ("admin:" + password).encode("utf8")).decode("ascii")
        env = build_environment(request, Response(), Session())
        env.update(DEMO_MODE=False, MULTI_USER_MODE=multi_user_mode, EXPIRATION=3600,
                   restricted=restricted)
        if crypt is not None:
            env["CRYPT"] = crypt
        filename = os.path.abspath(
            os.path.join("applications", "admin", "models", "access.py"))
        restricted(compile2(_read_source(filename), filename), env,
                   layer=filename)

    def test_failed_logins_are_recorded(self):
        with mock.patch("time.sleep"):
            for i in range(3):
                with self.assertRaises(HTTP):
                    self.run_access("wrong")
        with open(self.deny_file) as f:
            self.assertTrue(f.read().startswith("203.0.113.10 3 "))
        self.run_access("secret")

    def test_locked_out_client_is_refused(self):
        with open(self.deny_file, "w") as f:
            f.write("203.0.113.10 5 %i\n" % int(time.time()))
        with mock.patch("time.sleep") as sleep:
            with self.assertRaises(HTTP) as ctx:
                self.run_access("secret")
        self.assertEqual(ctx.exception.status, 403)
        sleep.assert_called_once_with(2 ** 5)

    def test_multi_user_mode_rejects_without_verifying_password(self):
        crypt = mock.Mock(side_effect=AssertionError("password was verified"))
        with mock.patch("time.sleep") as sleep:
            with self.assertRaises(HTTP) as ctx:
                self.run_access("secret", multi_user_mode=True, crypt=crypt)
        self.assertEqual(ctx.exception.status, 403)
        crypt.assert_not_called()
        sleep.assert_not_called()
        self.assertFalse(os.path.exists(self.deny_file))


if __name__ == "__main__":
    unittest.main()
