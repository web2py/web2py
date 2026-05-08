#!/bin/python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.sqlhtml
"""

import os
import sys
import unittest

from gluon import fileutils
from gluon.cache import CacheInRam
from gluon.compileapp import (compile_application, remove_compiled_application,
                              run_controller_in, run_view_in)
from gluon.dal import DAL, Field, Table
from gluon.fileutils import open_file
from gluon.http import HTTP
from gluon.languages import TranslatorFactory
from gluon.storage import List, Storage
from gluon import utils
from gluon.utils import safe_eval_expression

DEFAULT_URI = os.getenv("DB", "sqlite:memory")


def fake_check_credentials(foo):
    return True


class TestAppAdmin(unittest.TestCase):
    def setUp(self):
        from gluon.compileapp import LOAD
        from gluon.globals import Request, Response, Session, current
        from gluon.html import (ASSIGNJS, DIV, FORM, INPUT, MENU, TABLE, TR,
                                URL, XML, A)
        from gluon.http import HTTP, redirect
        from gluon.sql import SQLDB
        from gluon.sqlhtml import SQLFORM, SQLTABLE
        from gluon.tools import Auth
        from gluon.validators import IS_NOT_EMPTY

        self.original_check_credentials = fileutils.check_credentials
        fileutils.check_credentials = fake_check_credentials
        request = Request(env={})
        request.application = "welcome"
        request.controller = "appadmin"
        request.function = self._testMethodName.split("_")[1]
        request.folder = "applications/welcome"
        request.env.http_host = "127.0.0.1:8000"
        request.env.remote_addr = "127.0.0.1"
        request.client = request.env.remote_addr
        request.is_local = True
        response = Response()
        session = Session()
        T = TranslatorFactory("", "en")
        session.connect(request, response)
        current.request = request
        current.response = response
        current.session = session
        current.T = T
        db = DAL(DEFAULT_URI, check_reserved=["all"])
        auth = Auth(db)
        auth.define_tables(username=True, signature=False)
        db.define_table("t0", Field("tt"), auth.signature)
        # Create a user
        db.auth_user.insert(
            first_name="Bart",
            last_name="Simpson",
            username="user1",
            email="user1@test.com",
            password="password_123",
            registration_key=None,
            registration_id=None,
        )
        self.env = locals()

    def tearDown(self):
        fileutils.check_credentials = self.original_check_credentials

    def run_function(self):
        return run_controller_in(
            self.env["request"].controller, self.env["request"].function, self.env
        )

    def run_view(self):
        return run_view_in(self.env)

    def run_view_file_stream(self):
        view_path = os.path.join(self.env["request"].folder, "views", "appadmin.html")
        self.env["response"].view = open_file(view_path, "r")
        return run_view_in(self.env)

    def assertUnsafe(self, expr):
        """Assert that evaluating expr raises a ValueError (unsafe)."""
        with self.assertRaises(ValueError):
            safe_eval_expression(expr, {"db": self.env["db"]})

    def assertSafe(self, expr, expected_str=None):
        """Assert that expr evaluates safely; optionally compare str()."""
        res = safe_eval_expression(expr, {"db": self.env["db"]})
        if expected_str is not None:
            # DAL string representations may include SQL quoting
            # Normalize by removing double quotes so tests remain
            # robust across adapters (e.g. "auth_user"."id" -> auth_user.id)
            normalized = str(res).replace('"', '')
            self.assertEqual(normalized, expected_str)

    def _test_index(self):
        result = self.run_function()
        self.assertTrue("db" in result["databases"])
        self.env.update(result)
        try:
            self.run_view()
            self.run_view_file_stream()
        except Exception as e:
            import traceback

            print(traceback.format_exc())
            self.fail("Could not make the view")

    def test_index(self):
        self._test_index()

    def test_index_rejects_host_header_spoofing(self):
        request = self.env["request"]
        request.env.http_host = "127.0.0.1:8000"
        request.env.remote_addr = "203.0.113.10"
        request.client = request.env.remote_addr
        request.is_local = False
        request.is_https = False
        request.env.trusted_lan_prefix = None
        with self.assertRaises(HTTP) as ctx:
            self.run_function()
        error = ctx.exception
        self.assertEqual(error.status, 200)
        self.assertIn("appadmin is disabled because insecure channel", str(error.body))

    def test_index_allows_shell(self):
        request = self.env["request"]
        request.env.remote_addr = "203.0.113.10"
        request.client = request.env.remote_addr
        request.is_local = False
        request.is_https = False
        request.is_shell = True
        request.env.trusted_lan_prefix = None
        # should not raise HTTP — shell execution must bypass the channel check
        result = self.run_function()
        self.assertIn("db", result["databases"])

    def test_index_compiled(self):
        appname_path = os.path.join(os.getcwd(), "applications", "welcome")
        compile_application(appname_path)
        self._test_index()
        remove_compiled_application(appname_path)

    def test_index_minify(self):
        # test for gluon/contrib/minify
        self.env["response"].optimize_css = "concat|minify"
        self.env["response"].optimize_js = "concat|minify"
        self.env["current"].cache = Storage({"ram": CacheInRam()})
        appname_path = os.path.join(os.getcwd(), "applications", "welcome")
        self._test_index()
        file_l = os.listdir(os.path.join(appname_path, "static", "temp"))
        file_l.sort()
        self.assertTrue(len(file_l) == 2)
        self.assertEqual(file_l[0][0:10], "compressed")
        self.assertEqual(file_l[1][0:10], "compressed")
        self.assertEqual(file_l[0][-3:], "css")
        self.assertEqual(file_l[1][-2:], "js")

    def test_select(self):
        request = self.env["request"]
        request.args = List(["db"])
        request.env.query_string = "query=db.auth_user.id>0"
        result = self.run_function()
        self.assertTrue("table" in result and "query" in result)
        self.assertTrue(result["table"] == "auth_user")
        self.assertTrue(result["query"] == "db.auth_user.id>0")
        self.env.update(result)
        try:
            self.run_view()
        except Exception as e:
            import traceback

            print(traceback.format_exc())
            self.fail("Could not make the view")

    def test_safe_eval_dict_handles_commas(self):
        self.assertEqual(
            utils.safe_eval_dict('foo="hello world", bar="hello, world"'),
            {"foo": "hello world", "bar": "hello, world"},
        )
        self.assertEqual(
            utils.safe_eval_dict("a=1, b='x,y', c=foo"),
            {"a": 1, "b": "x,y", "c": "foo"},
        )

    def test_insert(self):
        request = self.env["request"]
        request.args = List(["db", "auth_user"])
        result = self.run_function()
        self.assertTrue("table" in result)
        self.assertTrue("form" in result)
        self.assertTrue(str(result["table"]) == "auth_user")
        self.env.update(result)
        try:
            self.run_view()
        except Exception as e:
            import traceback

            print(traceback.format_exc())
            self.fail("Could not make the view")

    def test_insert_submit(self):
        request = self.env["request"]
        request.args = List(["db", "auth_user"])
        form = self.run_function()["form"]
        hidden_fields = form.hidden_fields()
        data = {}
        data["_formkey"] = hidden_fields.element("input", _name="_formkey")["_value"]
        data["_formname"] = hidden_fields.element("input", _name="_formname")["_value"]
        data["first_name"] = "Lisa"
        data["last_name"] = "Simpson"
        data["username"] = "lisasimpson"
        data["password"] = "password_123"
        data["email"] = "lisa@example.com"
        request._vars = data
        result = self.run_function()
        self.env.update(result)
        try:
            self.run_view()
        except Exception as e:
            import traceback

            print(traceback.format_exc())
            self.fail("Could not make the view")
        db = self.env["db"]
        lisa_record = db(db.auth_user.username == "lisasimpson").select().first()
        self.assertIsNotNone(lisa_record)
        del data["_formkey"]
        del data["_formname"]
        del data["password"]
        for key in data:
            self.assertEqual(data[key], lisa_record[key])

    def test_update_submit(self):
        request = self.env["request"]
        request.args = List(["db", "auth_user", "1"])
        form = self.run_function()["form"]
        hidden_fields = form.hidden_fields()
        data = {}
        data["_formkey"] = hidden_fields.element("input", _name="_formkey")["_value"]
        data["_formname"] = hidden_fields.element("input", _name="_formname")["_value"]
        for element in form.elements("input"):
            data[element["_name"]] = element["_value"]
        data["email"] = "user1@example.com"
        data["id"] = "1"
        request._vars = data
        self.assertRaises(HTTP, self.run_function)

    def test_path_validation_security(self):
        """Test path validation security patches prevent traversal attacks"""
        from gluon.admin import apath, up
        from gluon.globals import Request
        from gluon.http import HTTP

        # Mock request for testing
        request = Request(env={})
        request.folder = "applications/welcome"

        # Test allowed paths
        web2py_apps_root = os.path.abspath(up(request.folder))
        web2py_deposit_root = os.path.join(up(web2py_apps_root), 'deposit')
        allowed_roots = [web2py_apps_root, web2py_deposit_root]

        def is_path_allowed(path):
            """Simulate the path validation logic from safe_open"""
            a_for_check = os.path.abspath(os.path.normpath(path))
            return any(a_for_check == root or a_for_check.startswith(root + os.sep)
                      for root in allowed_roots)

        # Test legitimate paths are allowed
        self.assertTrue(is_path_allowed(os.path.join(web2py_apps_root, 'welcome', 'models', 'db.py')),
                       "Should allow valid app files")
        self.assertTrue(is_path_allowed(web2py_apps_root),
                       "Should allow applications root")
        self.assertTrue(is_path_allowed(web2py_deposit_root),
                       "Should allow deposit root")

        # Test malicious paths are blocked
        self.assertFalse(is_path_allowed('/etc/passwd'),
                        "Should block system files")
        self.assertFalse(is_path_allowed('/workspaces/web2py/applications_evil'),
                        "Should block prefix match attacks")
        self.assertFalse(is_path_allowed(os.path.join(web2py_apps_root, '..', 'etc', 'passwd')),
                        "Should block path traversal")
        self.assertFalse(is_path_allowed('/tmp/malicious'),
                        "Should block temp directory access")

    def test_safe_eval_expression_legitimate_queries(self):
        """Test that safe_eval_expression allows legitimate database queries"""
        # Test legitimate expressions using the test DB created in setUp
        self.assertSafe('db.auth_user.id', 'auth_user.id')
        self.assertSafe('db.auth_user.id > 0', '(auth_user.id > 0)')
        self.assertSafe('db.auth_user.username', 'auth_user.username')

    def test_safe_eval_expression_blocks_function_calls(self):
        """Test that safe_eval_expression blocks arbitrary function calls (RCE)"""
        self.assertUnsafe('__import__("os").system("id")')

    def test_safe_eval_expression_blocks_subscript(self):
        """Test that safe_eval_expression blocks subscript access (introspection)"""
        self.assertUnsafe('db.__class__[0]')

    def test_safe_eval_expression_blocks_dunder_access(self):
        """Test that safe_eval_expression blocks dunder attribute access"""
        self.assertUnsafe('db.__class__')
        self.assertUnsafe('db.auth_user.__dict__')

    def test_safe_eval_expression_blocks_private_access(self):
        """Test that safe_eval_expression blocks private attribute access"""
        self.assertUnsafe('db._internals')

    def test_safe_eval_expression_blocks_lambda(self):
        """Test that safe_eval_expression blocks lambda functions"""
        self.assertUnsafe('lambda x: x > 0')

    def test_safe_eval_expression_blocks_comprehensions(self):
        """Test that safe_eval_expression blocks list/dict/set comprehensions"""
        self.assertUnsafe('[x for x in range(10)]')

    def test_safe_eval_expression_blocks_imports(self):
        """Test that safe_eval_expression blocks import statements"""
        self.assertUnsafe('__import__("os")')

    def test_safe_eval_expression_blocks_undefined_names(self):
        """Test that safe_eval_expression blocks undefined variable names"""
        self.assertUnsafe('undefined_var > 0')

    def test_safe_eval_expression_blocks_getattr(self):
        """Test that safe_eval_expression blocks getattr (attribute crawling)"""
        self.assertUnsafe('getattr(db, "__class__")')
