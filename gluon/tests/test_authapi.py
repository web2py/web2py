#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for authapi """
import os
import unittest
from gluon.globals import Request, Response, Session
from gluon.languages import translator
from gluon.dal import DAL, Field
from gluon.authapi import AuthAPI
from gluon.storage import Storage
from gluon._compat import to_bytes, to_native, add_charset

DEFAULT_URI = os.getenv('DB', 'sqlite:memory')


class TestAuthAPI(unittest.TestCase):

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
        self.auth = AuthAPI(self.db)
        self.auth.define_tables(username=True, signature=False)
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

    def test_login(self):
        result = self.auth.login(**{'username': 'bart', 'password': 'bart_password'})
        self.assertTrue(self.auth.is_logged_in())
        self.assertTrue(result['user']['email'] == 'bart@simpson.com')
        self.auth.logout()
        self.assertFalse(self.auth.is_logged_in())
        self.auth.settings.username_case_sensitive = False
        result = self.auth.login(**{'username': 'BarT', 'password': 'bart_password'})
        self.assertTrue(self.auth.is_logged_in())

    def test_logout(self):
        self.auth.login(**{'username': 'bart', 'password': 'bart_password'})
        self.assertTrue(self.auth.is_logged_in())
        result = self.auth.logout()
        self.assertTrue(not self.auth.is_logged_in())
        self.assertTrue(result['user'] is None)

    def test_register(self):
        self.auth.settings.login_after_registration = True
        result = self.auth.register(**{
            'username': 'lisa',
            'first_name': 'Lisa',
            'last_name': 'Simpson',
            'email': 'lisa@simpson.com',
            'password': 'lisa_password'
        })
        self.assertTrue(result['user']['email'] == 'lisa@simpson.com')
        self.assertTrue(self.auth.is_logged_in())
        with self.assertRaises(AssertionError):  # Can't register if you're logged in
            result = self.auth.register(**{
                'username': 'lisa',
                'first_name': 'Lisa',
                'last_name': 'Simpson',
                'email': 'lisa@simpson.com',
                'password': 'lisa_password'
            })
        self.auth.logout()
        self.auth.settings.login_after_registration = False
        result = self.auth.register(**{
            'username': 'barney',
            'first_name': 'Barney',
            'last_name': 'Gumble',
            'email': 'barney@simpson.com',
            'password': 'barney_password'
        })
        self.assertTrue(result['user']['email'] == 'barney@simpson.com')
        self.assertFalse(self.auth.is_logged_in())
        self.auth.settings.login_userfield = 'email'
        result = self.auth.register(**{
            'username': 'lisa',
            'first_name': 'Lisa',
            'last_name': 'Simpson',
            'email': 'lisa@simpson.com',
            'password': 'lisa_password'
        })
        self.assertTrue(result['errors']['email'] == self.auth.messages.email_taken)
        self.assertTrue(result['user'] is None)
        self.auth.settings.registration_requires_verification = True
        result = self.auth.register(**{
            'username': 'homer',
            'first_name': 'Homer',
            'last_name': 'Simpson',
            'email': 'homer@simpson.com',
            'password': 'homer_password'
        })
        self.assertTrue('key' in result['user'])

    def test_profile(self):
        with self.assertRaises(AssertionError):
            # We are not logged in
            self.auth.profile()
        self.auth.login(**{'username': 'bart', 'password': 'bart_password'})
        self.assertTrue(self.auth.is_logged_in())
        result = self.auth.profile(email='bartolo@simpson.com')
        self.assertTrue(result['user']['email'] == 'bartolo@simpson.com')
        self.assertTrue(self.auth.table_user()[result['user']['id']].email == 'bartolo@simpson.com')

    def test_change_password(self):
        with self.assertRaises(AssertionError):
            # We are not logged in
            self.auth.change_password()
        self.auth.login(**{'username': 'bart', 'password': 'bart_password'})
        self.assertTrue(self.auth.is_logged_in())
        self.auth.change_password(old_password='bart_password', new_password='1234', new_password2='1234')
        self.auth.logout()
        self.assertTrue(not self.auth.is_logged_in())
        self.auth.login(username='bart', password='1234')
        self.assertTrue(self.auth.is_logged_in())
        result = self.auth.change_password(old_password='bart_password', new_password='1234', new_password2='5678')
        self.assertTrue('new_password2' in result['errors'])
        result = self.auth.change_password(old_password='bart_password', new_password='1234', new_password2='1234')
        self.assertTrue('old_password' in result['errors'])
        # Test the default 4 min_length is enforced on change password
        result = self.auth.change_password(old_password='1234', new_password='123', new_password2='123')
        self.assertTrue('new_password' in result['errors'])

    def test_verify_key(self):
        self.auth.settings.registration_requires_verification = True
        result = self.auth.register(**{
            'username': 'homer',
            'first_name': 'Homer',
            'last_name': 'Simpson',
            'email': 'homer@simpson.com',
            'password': 'homer_password'
        })
        self.assertTrue('key' in result['user'])
        homer_id = result['user']['id']
        homers_key = result['user']['key']
        result = self.auth.verify_key(key=None)
        self.assertTrue(result['errors'] is not None)
        result = self.auth.verify_key(key='12345')
        self.assertTrue(result['errors'] is not None)
        result = self.auth.verify_key(key=homers_key)
        self.assertTrue(result['errors'] is None)
        self.assertEqual(self.auth.table_user()[homer_id].registration_key, '')
        self.auth.settings.registration_requires_approval = True
        result = self.auth.register(**{
            'username': 'lisa',
            'first_name': 'Lisa',
            'last_name': 'Simpson',
            'email': 'lisa@simpson.com',
            'password': 'lisa_password'
        })
        lisa_id = result['user']['id']
        result = self.auth.verify_key(key=result['user']['key'])
        self.assertEqual(self.auth.table_user()[lisa_id].registration_key, 'pending')
