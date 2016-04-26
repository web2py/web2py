#!/bin/python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.sqlhtml
"""
import os
import sys
if sys.version < "2.7":
    import unittest2 as unittest
else:
    import unittest

from fix_path import fix_sys_path

fix_sys_path(__file__)


from compileapp import run_controller_in, run_view_in
from languages import translator
from gluon.storage import Storage, List
import gluon.fileutils
from gluon.dal import DAL, Field, Table
from gluon.http import HTTP

DEFAULT_URI = os.getenv('DB', 'sqlite:memory')

try:
    import json
except ImportError:
    from gluon.contrib import simplejson as json


def fake_check_credentials(foo):
    return True


class TestAppAdmin(unittest.TestCase):

    def setUp(self):
        from gluon.globals import Request, Response, Session, current
        from gluon.html import A, DIV, FORM, MENU, TABLE, TR, INPUT, URL, XML
        from gluon.validators import IS_NOT_EMPTY
        from compileapp import LOAD
        from gluon.http import HTTP, redirect
        from gluon.tools import Auth
        from gluon.sql import SQLDB
        from gluon.sqlhtml import SQLTABLE, SQLFORM
        self.original_check_credentials = gluon.fileutils.check_credentials
        gluon.fileutils.check_credentials = fake_check_credentials
        request = Request(env={})
        request.application = 'welcome'
        request.controller = 'appadmin'
        request.function = self._testMethodName.split('_')[1]
        request.folder = 'applications/welcome'
        request.env.http_host = '127.0.0.1:8000'
        request.env.remote_addr = '127.0.0.1'
        response = Response()
        session = Session()
        T = translator('', 'en')
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
        gluon.fileutils.check_credentials = self.original_check_credentials

    def run_function(self):
        return run_controller_in(self.env['request'].controller, self.env['request'].function, self.env)

    def run_view(self):
        return run_view_in(self.env)

    def test_index(self):
        result = self.run_function()
        self.assertTrue('db' in result['databases'])
        self.env.update(result)
        try:
            self.run_view()
        except Exception as e:
            print e.message
            self.fail('Could not make the view')

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
            print e.message
            self.fail('Could not make the view')

    def test_insert(self):
        request = self.env['request']
        request.args = List(['db', 'auth_user'])
        result = self.run_function()
        self.assertTrue('table' in result)
        self.assertTrue('form' in result)
        self.assertTrue(str(result['table']) is 'auth_user')
        self.env.update(result)
        try:
            self.run_view()
        except Exception as e:
            print e.message
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
            print e.message
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


if __name__ == '__main__':
    unittest.main()
