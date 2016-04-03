#!/bin/python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.tools
"""
import os
import sys
import smtplib
if sys.version < "2.7":
    import unittest2 as unittest
else:
    import unittest

from fix_path import fix_sys_path

fix_sys_path(__file__)

DEFAULT_URI = os.getenv('DB', 'sqlite:memory')

from gluon.dal import DAL, Field
from pydal.objects import Table
from tools import Auth, Mail
from gluon.globals import Request, Response, Session
from storage import Storage
from languages import translator
from gluon.http import HTTP

python_version = sys.version[:3]
IS_IMAP = "imap" in DEFAULT_URI


class TestMail(unittest.TestCase):
    """
    Test the Mail class.
    """

    class Message(object):
        def __init__(self, sender, to, payload):
            self.sender = sender
            self.to = to
            self.payload = payload

    class DummySMTP(object):
        """
        Dummy smtp server

        NOTE: Test methods should take care of always leaving inbox and users empty when they finish.
        """
        inbox = []
        users = {}

        def __init__(self, address, port, **kwargs):
            self.address = address
            self.port = port
            self.has_quit = False
            self.tls = False

        def login(self, username, password):
            if username not in self.users or self.users[username] != password:
                raise smtplib.SMTPAuthenticationError
            self.username = username
            self.password = password

        def sendmail(self, sender, to, payload):
            self.inbox.append(TestMail.Message(sender, to, payload))

        def quit(self):
            self.has_quit = True

        def ehlo(self, hostname=None):
            pass

        def starttls(self):
            self.tls = True

    def setUp(self):
        self.original_SMTP = smtplib.SMTP
        self.original_SMTP_SSL = smtplib.SMTP_SSL
        smtplib.SMTP = TestMail.DummySMTP
        smtplib.SMTP_SSL = TestMail.DummySMTP

    def tearDown(self):
        smtplib.SMTP = self.original_SMTP
        smtplib.SMTP_SSL = self.original_SMTP_SSL

    def test_hello_world(self):
        mail = Mail()
        mail.settings.server = 'smtp.example.com:25'
        mail.settings.sender = 'you@example.com'
        self.assertTrue(mail.send(to=['somebody@example.com'],
                                  subject='hello',
                                  # If reply_to is omitted, then mail.settings.sender is used
                                  reply_to='us@example.com',
                                  message='world'))
        message = TestMail.DummySMTP.inbox.pop()
        self.assertEqual(message.sender, mail.settings.sender)
        self.assertEqual(message.to, ['somebody@example.com'])
        header = "To: somebody@example.com\nReply-To: us@example.com\nSubject: hello\n"
        self.assertTrue(header in message.payload)
        self.assertTrue(message.payload.endswith('world'))

    def test_failed_login(self):
        mail = Mail()
        mail.settings.server = 'smtp.example.com:25'
        mail.settings.sender = 'you@example.com'
        mail.settings.login = 'username:password'
        self.assertFalse(mail.send(to=['somebody@example.com'],
                                   subject='hello',
                                   # If reply_to is omitted, then mail.settings.sender is used
                                   reply_to='us@example.com',
                                   message='world'))

    def test_login(self):
        TestMail.DummySMTP.users['username'] = 'password'
        mail = Mail()
        mail.settings.server = 'smtp.example.com:25'
        mail.settings.sender = 'you@example.com'
        mail.settings.login = 'username:password'
        self.assertTrue(mail.send(to=['somebody@example.com'],
                                  subject='hello',
                                  # If reply_to is omitted, then mail.settings.sender is used
                                  reply_to='us@example.com',
                                  message='world'))
        del TestMail.DummySMTP.users['username']
        TestMail.DummySMTP.inbox.pop()

    def test_html(self):
        mail = Mail()
        mail.settings.server = 'smtp.example.com:25'
        mail.settings.sender = 'you@example.com'
        self.assertTrue(mail.send(to=['somebody@example.com'],
                                  subject='hello',
                                  # If reply_to is omitted, then mail.settings.sender is used
                                  reply_to='us@example.com',
                                  message='<html><head></head><body></body></html>'))
        message = TestMail.DummySMTP.inbox.pop()
        self.assertTrue('Content-Type: text/html' in message.payload)

    def test_ssl(self):
        mail = Mail()
        mail.settings.server = 'smtp.example.com:25'
        mail.settings.sender = 'you@example.com'
        mail.settings.ssl = True
        self.assertTrue(mail.send(to=['somebody@example.com'],
                                  subject='hello',
                                  # If reply_to is omitted, then mail.settings.sender is used
                                  reply_to='us@example.com',
                                  message='world'))
        TestMail.DummySMTP.inbox.pop()

    def test_tls(self):
        mail = Mail()
        mail.settings.server = 'smtp.example.com:25'
        mail.settings.sender = 'you@example.com'
        mail.settings.tls = True
        self.assertTrue(mail.send(to=['somebody@example.com'],
                                  subject='hello',
                                  # If reply_to is omitted, then mail.settings.sender is used
                                  reply_to='us@example.com',
                                  message='world'))
        TestMail.DummySMTP.inbox.pop()


# TODO class TestRecaptcha(unittest.TestCase):


# TODO class TestRecaptcha2(unittest.TestCase):


# TODO: class TestAuthJWT(unittest.TestCase):


@unittest.skipIf(IS_IMAP, "TODO: Imap raises 'Connection refused'")
class TestAuth(unittest.TestCase):

    def setUp(self):
        request = Request(env={})
        request.application = 'a'
        request.controller = 'c'
        request.function = 'f'
        request.folder = 'applications/admin'
        response = Response()
        session = Session()
        T = translator('', 'en')
        session.connect(request, response)
        from gluon.globals import current
        current.request = request
        current.response = response
        current.session = session
        current.T = T
        self.db = DAL(DEFAULT_URI, check_reserved=['all'])
        self.auth = Auth(self.db)
        self.auth.define_tables(username=True, signature=False)
        self.db.define_table('t0', Field('tt'), self.auth.signature)
        self.auth.enable_record_versioning(self.db)
        # Create a user
        self.db.auth_user.insert(first_name='Bart',
                                 last_name='Simpson',
                                 username='user1',
                                 email='user1@test.com',
                                 password='password_123',
                                 registration_key=None,
                                 registration_id=None)

        self.db.commit()

    def test_assert_setup(self):
        self.assertEqual(self.db(self.db.auth_user.username == 'user1').select().first()['id'], 1)
        self.assertTrue('auth_user' in self.db)
        self.assertTrue('auth_group' in self.db)
        self.assertTrue('auth_membership' in self.db)
        self.assertTrue('auth_permission' in self.db)
        self.assertTrue('auth_event' in self.db)

    def test_enable_record_versioning(self):
        self.assertTrue('t0_archive' in self.db)

    def test_basic_blank_forms(self):
        for f in ['login', 'register', 'retrieve_password',
                  'retrieve_username']:
            html_form = getattr(self.auth, f)().xml()
            self.assertTrue('name="_formkey"' in html_form)

        for f in ['logout', 'verify_email', 'reset_password',
                  'change_password', 'profile', 'groups']:
            self.assertRaisesRegexp(HTTP, "303*", getattr(self.auth, f))

        self.assertRaisesRegexp(HTTP, "401*", self.auth.impersonate)

        try:
            for t in ['t0_archive', 't0', 'auth_cas', 'auth_event',
                      'auth_membership', 'auth_permission', 'auth_group',
                      'auth_user']:
                self.db[t].drop()
        except SyntaxError as e:
            # GAE doesn't support drop
            pass
        return

    def test_get_or_create_user(self):
        self.db.auth_user.insert(email='user1@test.com', password='password_123')
        self.db.commit()
        # True case
        self.assertEqual(self.auth.get_or_create_user({'email': 'user1@test.com',
                                                       'username': 'user1'})['username'], 'user1')
        # user2 doesn't exist yet and get created
        self.assertEqual(self.auth.get_or_create_user({'email': 'user2@test.com',
                                                       'username': 'user2'})['username'], 'user2')
        # user3 for corner case
        self.assertEqual(self.auth.get_or_create_user({'first_name': 'Omer',
                                                       'last_name': 'Simpson',
                                                       'email': 'user3@test.com',
                                                       'registration_id': 'user3',
                                                       'username': 'user3'})['username'], 'user3')
        # False case
        self.assertEqual(self.auth.get_or_create_user({'email': ''}), None)
        self.db.auth_user.truncate()
        self.db.commit()

    def test_login_bare(self):
        # The following test case should succeed but failed as I never received the user record but False
        # TODO: Make this test pass
        # self.assertEqual(self.auth.login_bare(username='user1', password='password_123')['username'], 'user1')
        # Failing login because bad_password
        self.assertEqual(self.auth.login_bare(username='user1', password='bad_password'), False)

    def test_register_bare(self):
        # corner case empty register call register_bare without args
        self.assertRaises(ValueError, self.auth.register_bare)
        # failing register_bare user already exist
        self.assertEqual(self.auth.register_bare(username='user1', password='wrong_password'), False)
        # successful register_bare
        self.assertEqual(self.auth.register_bare(username='user2',
                                                 email='user2@test.com',
                                                 password='password_123')['username'], 'user2')
        # raise ValueError
        self.assertRaises(ValueError, self.auth.register_bare,
                          **dict(wrong_field_name='user3', password='password_123'))
        # raise ValueError wrong email
        self.assertRaises(ValueError, self.auth.register_bare,
                          **dict(email='user4@', password='password_123'))
        self.db.auth_user.truncate()
        self.db.commit()


# TODO: class TestCrud(unittest.TestCase):
# It deprecated so far from a priority


# TODO: class TestService(unittest.TestCase):


# TODO: class TestPluginManager(unittest.TestCase):


# TODO: class TestExpose(unittest.TestCase):


# TODO: class TestWiki(unittest.TestCase):


# TODO: class TestConfig(unittest.TestCase):


# TODO: class TestToolsFunctions(unittest.TestCase):
# For all the tools.py functions

if __name__ == '__main__':
    unittest.main()
