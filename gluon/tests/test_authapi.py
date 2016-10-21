#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for authapi """

import os
import unittest
from gluon.globals import Request, Response, Session
from gluon.languages import translator
from gluon.dal import DAL, Field
from gluon.tools import Auth
from gluon.authapi import DIDO

DEFAULT_URI = os.getenv('DB', 'sqlite:memory')


class TestDIDO(unittest.TestCase):

    def setUp(self):
        self.request = Request(env={})
        self.request.application = 'a'
        self.request.controller = 'c'
        self.request.function = 'f'
        self.request.folder = 'applications/admin'
        self.response = Response()
        self.session = Session()
        T = translator('', 'en')
        self.session.connect(self.request, self.response)
        from gluon.globals import current
        self.current = current
        self.current.request = self.request
        self.current.response = self.response
        self.current.session = self.session
        self.current.T = T
        self.db = DAL(DEFAULT_URI, check_reserved=['all'])
        self.auth = Auth(self.db, api=DIDO)
        self.auth.define_tables(username=True, signature=False)
        self.db.define_table('t0', Field('tt'), self.auth.signature)
        self.auth.enable_record_versioning(self.db)
        # Create a user
        self.auth.table_user().validate_and_insert(first_name='Bart',
                                                   last_name='Simpson',
                                                   username='bart',
                                                   email='bart@simpson.com',
                                                   password='bart_password',
                                                   registration_key='',
                                                   registration_id=''
                                                   )
        self.db.commit()
        self.assertFalse(self.auth.is_logged_in())

    def test_login(self):
        result = self.auth.login(**{'username': 'bart', 'password': 'bart_password'})
        self.assertTrue(self.auth.is_logged_in())
        self.assertTrue(result['user']['email'] == 'bart@simpson.com')
        self.auth.logout()
        self.assertTrue(not self.auth.is_logged_in())

    def test_logout(self):
        self.auth.login(**{'username': 'bart', 'password': 'bart_password'})
        self.assertTrue(self.auth.is_logged_in())
        result = self.auth.logout()
        self.assertTrue(not self.auth.is_logged_in())
        self.assertTrue(result['user'] is None)

    def test_register(self):
        result = self.auth.register(**{
            'username': 'lisa',
            'first_name': 'Lisa',
            'last_name': 'Simpson',
            'email': 'lisa@simpson.com',
            'password': 'lisa_password'
        })
        self.assertTrue(result['user']['email'] == 'lisa@simpson.com')
        self.assertTrue(self.auth.is_logged_in())

    def test_profile(self):
        with self.assertRaises(AssertionError):
            # We are not logged in
            self.auth.profile()
        self.auth.login(**{'username': 'bart', 'password': 'bart_password'})
        self.assertTrue(self.auth.is_logged_in())
        result = self.auth.profile(**{'email': 'bartolo@simpson.com'})
        self.assertTrue(result['user']['email'] == 'bartolo@simpson.com')
        self.assertTrue(self.auth.table_user()[result['user']['id']].email == 'bartolo@simpson.com')
