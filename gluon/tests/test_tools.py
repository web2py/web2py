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
from tools import Auth, Mail, Recaptcha, Recaptcha2
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
            self._parsed_payload = None

        @property
        def parsed_payload(self):
            if self._parsed_payload is None:
                import email
                self._parsed_payload = email.message_from_string(self.payload)
            return self._parsed_payload

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

    def test_alternative(self):
        mail = Mail()
        mail.settings.server = 'smtp.example.com:25'
        mail.settings.sender = 'you@example.com'
        self.assertTrue(mail.send(to=['somebody@example.com'],
                                  message=('Text only', '<html><pre>HTML Only</pre></html>')))
        message = TestMail.DummySMTP.inbox.pop()
        self.assertTrue(message.parsed_payload.is_multipart())
        self.assertTrue(message.parsed_payload.get_content_type() == 'multipart/alternative')
        parts = message.parsed_payload.get_payload()
        self.assertTrue('Text only' in parts[0].as_string())
        self.assertTrue('<html><pre>HTML Only</pre></html>' in parts[1].as_string())

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

    def test_attachment(self):
        module_file = os.path.abspath(__file__)
        mail = Mail()
        mail.settings.server = 'smtp.example.com:25'
        mail.settings.sender = 'you@example.com'
        self.assertTrue(mail.send(to=['somebody@example.com'],
                                  subject='hello',
                                  message='world',
                                  attachments=Mail.Attachment(module_file)))
        message = TestMail.DummySMTP.inbox.pop()
        attachment = message.parsed_payload.get_payload(1).get_payload(decode=True)
        with open(module_file, 'rb') as mf:
            self.assertEqual(attachment.decode('utf-8'), mf.read().decode('utf-8'))
        # Test missing attachment name error
        stream = open(module_file)
        self.assertRaises(Exception, lambda *args, **kwargs: Mail.Attachment(*args, **kwargs), stream)
        stream.close()
        # Test you can define content-id and content type
        self.assertTrue(mail.send(to=['somebody@example.com'],
                                  subject='hello',
                                  message='world',
                                  attachments=Mail.Attachment(module_file, content_id='trololo', content_type='tra/lala')))
        message = TestMail.DummySMTP.inbox.pop()
        self.assertTrue('Content-Type: tra/lala' in message.payload)
        self.assertTrue('Content-Id: <trololo>' in message.payload)


# class TestRecaptcha(unittest.TestCase):
#     def test_Recaptcha(self):
#         from html import FORM
#         form = FORM(Recaptcha(public_key='public_key', private_key='private_key'))
#         self.assertEqual(form.xml(),
#                          '<form action="#" enctype="multipart/form-data" method="post"><div id="recaptcha"><script><!--\nvar RecaptchaOptions = {};\n//--></script><script src="http://www.google.com/recaptcha/api/challenge?k=public_key" type="text/javascript"></script><noscript><iframe frameborder="0" height="300" src="http://www.google.com/recaptcha/api/noscript?k=public_key" width="500"></iframe><br /><input name="recaptcha_response_field" type="hidden" value="manual_challenge" /></noscript></div></form>')
#
#
# class TestRecaptcha2(unittest.TestCase):
#     def test_Recaptcha2(self):
#         from html import FORM
#         form = FORM(Recaptcha2(public_key='public_key', private_key='private_key'))
#         rtn = '<form action="#" enctype="multipart/form-data" method="post"><div><script async="" defer="" src="https://www.google.com/recaptcha/api.js"></script><div class="g-recaptcha" data-sitekey="public_key"></div><noscript>\n<div style="width: 302px; height: 352px;">\n<div style="width: 302px; height: 352px; position: relative;">\n  <div style="width: 302px; height: 352px; position: absolute;">\n    <iframe src="https://www.google.com/recaptcha/api/fallback?k=public_key"\n            frameborder="0" scrolling="no"\n            style="width: 302px; height:352px; border-style: none;">\n    </iframe>\n  </div>\n  <div style="width: 250px; height: 80px; position: absolute; border-style: none;\n              bottom: 21px; left: 25px; margin: 0px; padding: 0px; right: 25px;">\n    <textarea id="g-recaptcha-response" name="g-recaptcha-response"\n              class="g-recaptcha-response"\n              style="width: 250px; height: 80px; border: 1px solid #c1c1c1;\n                     margin: 0px; padding: 0px; resize: none;" value="">\n    </textarea>\n  </div>\n</div>\n</div></noscript></div></form>'
#         self.assertEqual(form.xml(), rtn)

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
        self.auth.get_or_create_user(dict(first_name='Bart',
                                          last_name='Simpson',
                                          username='bart',
                                          email='bart@simpson.com',
                                          password='bart_password',
                                          registration_key='bart',
                                          registration_id=''
                                          ))
        # self.auth.settings.registration_requires_verification = False
        # self.auth.settings.registration_requires_approval = False

    def test_assert_setup(self):
        self.assertEqual(self.db(self.db.auth_user.username == 'bart').select().first()['username'], 'bart')
        self.assertTrue('auth_user' in self.db)
        self.assertTrue('auth_group' in self.db)
        self.assertTrue('auth_membership' in self.db)
        self.assertTrue('auth_permission' in self.db)
        self.assertTrue('auth_event' in self.db)

    def test_enable_record_versioning(self):
        self.assertTrue('t0_archive' in self.db)

    def test_basic_blank_forms(self):
        for f in ['login', 'retrieve_password',
                  'retrieve_username',
                  # 'register'  # register complain about : client_side=self.settings.client_side
                  ]:
            html_form = getattr(self.auth, f)().xml()
            self.assertTrue('name="_formkey"' in html_form)

        # NOTE: Not sure it is the proper way to logout_bare() as there is not methods for that and auth.logout() failed
        self.auth.logout_bare()
        # self.assertTrue(self.auth.is_logged_in())

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
        self.db.auth_user.insert(email='user1@test.com', username='user1', password='password_123')
        self.db.commit()
        # True case
        self.assertEqual(self.auth.get_or_create_user({'email': 'user1@test.com',
                                                       'username': 'user1',
                                                       'password': 'password_123'
                                                       })['username'], 'user1')
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
        self.auth.login_bare(username='bart@simpson.com', password='bart_password')
        self.assertTrue(self.auth.is_logged_in())
        # Failing login because bad_password
        self.assertEqual(self.auth.login_bare(username='bart', password='wrong_password'), False)
        self.db.auth_user.truncate()

    def test_register_bare(self):
        # corner case empty register call register_bare without args
        self.assertRaises(ValueError, self.auth.register_bare)
        # failing register_bare user already exist
        self.assertEqual(self.auth.register_bare(username='bart', password='wrong_password'), False)
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

    def test_bulk_register(self):
        self.auth.login_bare(username='bart', password='bart_password')
        self.auth.settings.bulk_register_enabled = True
        bulk_register_form = self.auth.bulk_register(max_emails=10).xml()
        self.assertTrue('name="_formkey"' in bulk_register_form)

    def test_change_password(self):
        self.auth.login_bare(username='bart', password='bart_password')
        change_password_form = getattr(self.auth, 'change_password')().xml()
        self.assertTrue('name="_formkey"' in change_password_form)

    def test_profile(self):
        self.auth.login_bare(username='bart', password='bart_password')
        profile_form = getattr(self.auth, 'profile')().xml()
        self.assertTrue('name="_formkey"' in profile_form)

    # def test_impersonate(self):
    #     # Create a user to be impersonated
    #     self.auth.get_or_create_user(dict(first_name='Omer',
    #                                       last_name='Simpson',
    #                                       username='omer',
    #                                       email='omer@test.com',
    #                                       password='password_omer',
    #                                       registration_key='',
    #                                       registration_id=''))
    #     # Create impersonate group, assign bart to impersonate group and add impersonate permission over auth_user
    #     self.auth.add_group('impersonate')
    #     self.auth.add_membership(user_id=1,
    #                              group_id=self.db(self.db.auth_user.username == 'bart'
    #                                               ).select(self.db.auth_user.id).first().id)
    #     self.auth.add_permission(group_id=self.db(self.db.auth_group.role == 'impersonate'
    #                                               ).select(self.db.auth_group.id).first().id,
    #                              name='impersonate',
    #                              table_name='auth_user',
    #                              record_id=0)
    #     # Bart login
    #     self.auth.login_bare(username='bart', password='bart_password')
    #     self.assertTrue(self.auth.is_logged_in())
    #     # Bart impersonate Omer
    #     omer_id = self.db(self.db.auth_user.username == 'omer').select(self.db.auth_user.id).first().id
    #     impersonate_form = self.auth.impersonate(user_id=omer_id)
    #     self.assertTrue(self.auth.is_impersonating())
    #     self.assertEqual(impersonate_form, 'test')

    # def test_impersonate(self):
    #     request = Request(env={})
    #     request.application = 'a'
    #     request.controller = 'c'
    #     request.function = 'f'
    #     request.folder = 'applications/admin'
    #     response = Response()
    #     session = Session()
    #     T = translator('', 'en')
    #     session.connect(request, response)
    #     from gluon.globals import current
    #     current.request = request
    #     current.response = response
    #     current.session = session
    #     current.T = T
    #     db = DAL(DEFAULT_URI, check_reserved=['all'])
    #     auth = Auth(db)
    #     auth.define_tables(username=True, signature=False)
    #     db.define_table('t0', Field('tt'), auth.signature)
    #     auth.enable_record_versioning(db)
    #     # Create a user
    #     auth.get_or_create_user(dict(first_name='Bart',
    #                                       last_name='Simpson',
    #                                       username='bart',
    #                                       email='bart@simpson.com',
    #                                       password='bart_password',
    #                                       registration_key='bart',
    #                                       registration_id=''
    #                                       ))
    #     # Create a user to be impersonated
    #     auth.get_or_create_user(dict(first_name='Omer',
    #                                       last_name='Simpson',
    #                                       username='omer',
    #                                       email='omer@test.com',
    #                                       password='password_omer',
    #                                       registration_key='',
    #                                       registration_id=''))
    #     # Create impersonate group, assign bart to impersonate group and add impersonate permission over auth_user
    #     auth.add_group('impersonate')
    #     auth.add_membership(user_id=1,
    #                              group_id=db(db.auth_user.username == 'bart'
    #                                               ).select(db.auth_user.id).first().id)
    #     auth.add_permission(group_id=db(db.auth_group.role == 'impersonate'
    #                                               ).select(db.auth_group.id).first().id,
    #                              name='impersonate',
    #                              table_name='auth_user',
    #                              record_id=0)
    #     # Bart login
    #     auth.login_bare(username='bart', password='bart_password')
    #     # Bart impersonate Omer
    #     omer_id = db(db.auth_user.username == 'omer').select(db.auth_user.id).first().id
    #     impersonate_form = auth.impersonate(user_id=omer_id)
    #     self.assertTrue(auth.is_impersonating())
    #     self.assertEqual(impersonate_form, 'test')


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
