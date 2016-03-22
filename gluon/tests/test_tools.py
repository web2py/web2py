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

@unittest.skipIf(IS_IMAP, "TODO: Imap raises 'Connection refused'")
class TestAuth(unittest.TestCase):

    def testRun(self):
        # setup
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
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        auth = Auth(db)
        auth.define_tables(username=True, signature=False)
        self.assertTrue('auth_user' in db)
        self.assertTrue('auth_group' in db)
        self.assertTrue('auth_membership' in db)
        self.assertTrue('auth_permission' in db)
        self.assertTrue('auth_event' in db)
        db.define_table('t0', Field('tt'), auth.signature)
        auth.enable_record_versioning(db)
        self.assertTrue('t0_archive' in db)
        for f in ['login', 'register', 'retrieve_password',
                  'retrieve_username']:
            html_form = getattr(auth, f)().xml()
            self.assertTrue('name="_formkey"' in html_form)

        for f in ['logout', 'verify_email', 'reset_password',
                  'change_password', 'profile', 'groups']:
            self.assertRaisesRegexp(HTTP, "303*", getattr(auth, f))

        self.assertRaisesRegexp(HTTP, "401*", auth.impersonate)

        try:
            for t in ['t0_archive', 't0', 'auth_cas', 'auth_event',
                      'auth_membership', 'auth_permission', 'auth_group',
                      'auth_user']:
                db[t].drop()
        except SyntaxError as e:
            # GAE doesn't support drop
            pass
        return


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
            self.address=address
            self.port = port
            self.has_quit = False
            self.tls = False

        def login(self, username, password):
            if username not in self.users or self.users[username] != password:
                raise smtplib.SMTPAuthenticationError
            self.username=username
            self.password=password

        def sendmail(self, sender, to, payload):
            self.inbox.append(TestMail.Message(sender, to, payload))

        def quit(self):
            self.has_quit=True

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






if __name__ == '__main__':
    unittest.main()
