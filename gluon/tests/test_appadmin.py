#!/bin/python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.sqlhtml
"""

import os
import sys
import unittest


from gluon.compileapp import run_controller_in, run_view_in, compile_application, remove_compiled_application
from gluon.languages import TranslatorFactory
from gluon.storage import Storage, List
from gluon import fileutils
from gluon.dal import DAL, Field, Table
from gluon.http import HTTP
from gluon.fileutils import open_file
from gluon.cache import CacheInRam

DEFAULT_URI = os.getenv('DB', 'sqlite:memory')



def fake_check_credentials(foo):
    return True


class TestAppAdmin(unittest.TestCase):

    def setUp(self):
        from gluon.globals import Request, Response, Session, current
        from gluon.html import A, DIV, FORM, MENU, TABLE, TR, INPUT, URL, XML
        from gluon.html import ASSIGNJS
        from gluon.validators import IS_NOT_EMPTY
        from gluon.compileapp import LOAD
        from gluon.http import HTTP, redirect
        from gluon.tools import Auth
        from gluon.sql import SQLDB
        from gluon.sqlhtml import SQLTABLE, SQLFORM
        self.original_check_credentials = fileutils.check_credentials
        fileutils.check_credentials = fake_check_credentials
        request = Request(env={})
        request.application = 'welcome'
        request.controller = 'appadmin'
        request.function = self._testMethodName.split('_')[1]
        request.folder = 'applications/welcome'
        request.env.http_host = '127.0.0.1:8000'
        request.env.remote_addr = '127.0.0.1'
        response = Response()
        session = Session()
        T = TranslatorFactory('', 'en')
        session.connect(request, response)
        current.request = request
        current.response = response
        current.session = session
        current.T = T
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        auth = Auth(db)
        auth.define_tables(username=True, signature=False)
        db.define_table('t0', Field('tt'), auth.signature)
        # Create a user
        db.auth_user.insert(first_name='Bart',
                            last_name='Simpson',
                            username='user1',
                            email='user1@test.com',
                            password='password_123',
                            registration_key=None,
                            registration_id=None)
        self.env = locals()

    def tearDown(self):
        fileutils.check_credentials = self.original_check_credentials

    def run_function(self):
        return run_controller_in(self.env['request'].controller, self.env['request'].function, self.env)

    def run_view(self):
        return run_view_in(self.env)

    def run_view_file_stream(self):
        view_path = os.path.join(self.env['request'].folder, 'views', 'appadmin.html')
        self.env['response'].view = open_file(view_path, 'r')
        return run_view_in(self.env)

    def _test_index(self):
        result = self.run_function()
        self.assertTrue('db' in result['databases'])
        self.env.update(result)
        try:
            self.run_view()
            self.run_view_file_stream()
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.fail('Could not make the view')

    def test_index(self):
        self._test_index()

    def test_index_compiled(self):
        appname_path = os.path.join(os.getcwd(), 'applications', 'welcome')
        compile_application(appname_path)
        self._test_index()
        remove_compiled_application(appname_path)

    def test_index_minify(self):
        # test for gluon/contrib/minify
        self.env['response'].optimize_css = 'concat|minify'
        self.env['response'].optimize_js = 'concat|minify'
        self.env['current'].cache = Storage({'ram':CacheInRam()})
        appname_path = os.path.join(os.getcwd(), 'applications', 'welcome')
        self._test_index()
        file_l = os.listdir(os.path.join(appname_path, 'static', 'temp'))
        file_l.sort()
        self.assertTrue(len(file_l) == 2)
        self.assertEqual(file_l[0][0:10], 'compressed')
        self.assertEqual(file_l[1][0:10], 'compressed')
        self.assertEqual(file_l[0][-3:], 'css')
        self.assertEqual(file_l[1][-2:], 'js')

    def test_select(self):
        request = self.env['request']
        request.args = List(['db'])
        request.env.query_string = 'query=db.auth_user.id>0'
        result = self.run_function()
        self.assertTrue('table' in result and 'query' in result)
        self.assertTrue(result['table'] == 'auth_user')
        self.assertTrue(result['query'] == 'db.auth_user.id>0')
        self.env.update(result)
        try:
            self.run_view()
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.fail('Could not make the view')

    def test_insert(self):
        request = self.env['request']
        request.args = List(['db', 'auth_user'])
        result = self.run_function()
        self.assertTrue('table' in result)
        self.assertTrue('form' in result)
        self.assertTrue(str(result['table']) == 'auth_user')
        self.env.update(result)
        try:
            self.run_view()
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.fail('Could not make the view')

    def test_insert_submit(self):
        request = self.env['request']
        request.args = List(['db', 'auth_user'])
        form = self.run_function()['form']
        hidden_fields = form.hidden_fields()
        data = {}
        data['_formkey'] = hidden_fields.element('input', _name='_formkey')['_value']
        data['_formname'] = hidden_fields.element('input', _name='_formname')['_value']
        data['first_name'] = 'Lisa'
        data['last_name'] = 'Simpson'
        data['username'] = 'lisasimpson'
        data['password'] = 'password_123'
        data['email'] = 'lisa@example.com'
        request._vars = data
        result = self.run_function()
        self.env.update(result)
        try:
            self.run_view()
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.fail('Could not make the view')
        db = self.env['db']
        lisa_record = db(db.auth_user.username == 'lisasimpson').select().first()
        self.assertIsNotNone(lisa_record)
        del data['_formkey']
        del data['_formname']
        del data['password']
        for key in data:
            self.assertEqual(data[key], lisa_record[key])

    def test_update_submit(self):
        request = self.env['request']
        request.args = List(['db', 'auth_user', '1'])
        form = self.run_function()['form']
        hidden_fields = form.hidden_fields()
        data = {}
        data['_formkey'] = hidden_fields.element('input', _name='_formkey')['_value']
        data['_formname'] = hidden_fields.element('input', _name='_formname')['_value']
        for element in form.elements('input'):
            data[element['_name']] = element['_value']
        data['email'] = 'user1@example.com'
        data['id'] = '1'
        request._vars = data
        self.assertRaises(HTTP, self.run_function)
