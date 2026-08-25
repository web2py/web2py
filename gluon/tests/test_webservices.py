#!/bin/python
# -*- coding: utf-8 -*-

"""
    Unit tests for the admin webservices controller path containment
"""

import base64
import os
import unittest

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

if __name__ == "__main__":
    unittest.main()
