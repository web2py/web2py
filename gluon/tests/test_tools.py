#!/bin/python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.tools
"""
import os
import sys
import shutil
import tempfile
import smtplib
import datetime
import unittest

DEFAULT_URI = os.getenv('DB', 'sqlite:memory')

from gluon.dal import DAL, Field
from pydal.objects import Table
from gluon import tools
from gluon.tools import Auth, Mail, Recaptcha2, prettydate, Expose
from gluon._compat import PY2, to_bytes
from gluon.globals import Request, Response, Session
from gluon.storage import Storage
from gluon.languages import TranslatorFactory
from gluon.http import HTTP
from gluon import SPAN, H3, TABLE, TR, TD, A, URL, current

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
            self.assertEqual(to_bytes(attachment), to_bytes(mf.read()))
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


# TODO: class TestAuthJWT(unittest.TestCase):
class TestAuthJWT(unittest.TestCase):
    def setUp(self):
        from gluon.tools import AuthJWT

        from gluon import current

        self.request = Request(env={})
        self.request.application = 'a'
        self.request.controller = 'c'
        self.request.function = 'f'
        self.request.folder = 'applications/admin'
        self.current = current
        self.current.request = self.request

        self.db = DAL(DEFAULT_URI, check_reserved=['all'])
        self.auth = Auth(self.db)
        self.auth.define_tables(username=True, signature=False)
        self.user_data = dict(username='jwtuser', password='jwtuser123')
        self.db.auth_user.insert(username=self.user_data['username'],
                                 password=str(
                                     self.db.auth_user.password.requires[0](
                                         self.user_data['password'])[0]))
        self.jwtauth = AuthJWT(self.auth, secret_key='secret', verify_expiration=True)

    def test_jwt_token_manager(self):
        import gluon.serializers
        self.request.vars.update(self.user_data)
        self.token = self.jwtauth.jwt_token_manager()
        self.assertIsNotNone(self.token)
        del self.request.vars['username']
        del self.request.vars['password']
        self.request.vars._token = gluon.serializers.json_parser.loads(self.token)['token']
        self.token = self.jwtauth.jwt_token_manager()
        self.assertIsNotNone(self.token)

    def test_allows_jwt(self):
        import gluon.serializers
        self.request.vars.update(self.user_data)
        self.token = self.jwtauth.jwt_token_manager()
        self.assertIsNotNone(self.token)
        del self.request.vars['username']
        del self.request.vars['password']
        self.token = self.jwtauth.jwt_token_manager()
        self.request.vars._token = gluon.serializers.json_parser.loads(self.token)['token']

        @self.jwtauth.allows_jwt()
        def optional_auth():
            self.assertEqual(self.user_data['username'], self.auth.user.username)
        optional_auth()


@unittest.skipIf(IS_IMAP, "TODO: Imap raises 'Connection refused'")
# class TestAuth(unittest.TestCase):
#
#     def setUp(self):
#         request = Request(env={})
#         request.application = 'a'
#         request.controller = 'c'
#         request.function = 'f'
#         request.folder = 'applications/admin'
#         response = Response()
#         session = Session()
#         T = TranslatorFactory('', 'en')
#         session.connect(request, response)
#         from gluon.globals import current
#         current.request = request
#         current.response = response
#         current.session = session
#         current.T = T
#         self.db = DAL(DEFAULT_URI, check_reserved=['all'])
#         self.auth = Auth(self.db)
#         self.auth.define_tables(username=True, signature=False)
#         self.db.define_table('t0', Field('tt'), self.auth.signature)
#         self.auth.enable_record_versioning(self.db)
#         # Create a user
#         self.auth.get_or_create_user(dict(first_name='Bart',
#                                           last_name='Simpson',
#                                           username='bart',
#                                           email='bart@simpson.com',
#                                           password='bart_password',
#                                           registration_key='bart',
#                                           registration_id=''
#                                           ))
#         # self.auth.settings.registration_requires_verification = False
#         # self.auth.settings.registration_requires_approval = False
#
#     def test_assert_setup(self):
#         self.assertEqual(self.db(self.db.auth_user.username == 'bart').select().first()['username'], 'bart')
#         self.assertTrue('auth_user' in self.db)
#         self.assertTrue('auth_group' in self.db)
#         self.assertTrue('auth_membership' in self.db)
#         self.assertTrue('auth_permission' in self.db)
#         self.assertTrue('auth_event' in self.db)
#
#     def test_enable_record_versioning(self):
#         self.assertTrue('t0_archive' in self.db)
#
#     def test_basic_blank_forms(self):
#         for f in ['login', 'retrieve_password',
#                   'retrieve_username',
#                   # 'register'  # register complain about : client_side=self.settings.client_side
#                   ]:
#             html_form = getattr(self.auth, f)().xml()
#             self.assertTrue('name="_formkey"' in html_form)
#
#         # NOTE: Not sure it is the proper way to logout_bare() as there is not methods for that and auth.logout() failed
#         self.auth.logout_bare()
#         # self.assertTrue(self.auth.is_logged_in())
#
#         for f in ['logout', 'verify_email', 'reset_password',
#                   'change_password', 'profile', 'groups']:
#             self.assertRaisesRegexp(HTTP, "303*", getattr(self.auth, f))
#
#         self.assertRaisesRegexp(HTTP, "401*", self.auth.impersonate)
#
#         try:
#             for t in ['t0_archive', 't0', 'auth_cas', 'auth_event',
#                       'auth_membership', 'auth_permission', 'auth_group',
#                       'auth_user']:
#                 self.db[t].drop()
#         except SyntaxError as e:
#             # GAE doesn't support drop
#             pass
#         return
#
#     def test_get_or_create_user(self):
#         self.db.auth_user.insert(email='user1@test.com', username='user1', password='password_123')
#         self.db.commit()
#         # True case
#         self.assertEqual(self.auth.get_or_create_user({'email': 'user1@test.com',
#                                                        'username': 'user1',
#                                                        'password': 'password_123'
#                                                        })['username'], 'user1')
#         # user2 doesn't exist yet and get created
#         self.assertEqual(self.auth.get_or_create_user({'email': 'user2@test.com',
#                                                        'username': 'user2'})['username'], 'user2')
#         # user3 for corner case
#         self.assertEqual(self.auth.get_or_create_user({'first_name': 'Omer',
#                                                        'last_name': 'Simpson',
#                                                        'email': 'user3@test.com',
#                                                        'registration_id': 'user3',
#                                                        'username': 'user3'})['username'], 'user3')
#         # False case
#         self.assertEqual(self.auth.get_or_create_user({'email': ''}), None)
#         self.db.auth_user.truncate()
#         self.db.commit()
#
#     def test_login_bare(self):
#         # The following test case should succeed but failed as I never received the user record but False
#         self.auth.login_bare(username='bart@simpson.com', password='bart_password')
#         self.assertTrue(self.auth.is_logged_in())
#         # Failing login because bad_password
#         self.assertEqual(self.auth.login_bare(username='bart', password='wrong_password'), False)
#         self.db.auth_user.truncate()
#
#     def test_register_bare(self):
#         # corner case empty register call register_bare without args
#         self.assertRaises(ValueError, self.auth.register_bare)
#         # failing register_bare user already exist
#         self.assertEqual(self.auth.register_bare(username='bart', password='wrong_password'), False)
#         # successful register_bare
#         self.assertEqual(self.auth.register_bare(username='user2',
#                                                  email='user2@test.com',
#                                                  password='password_123')['username'], 'user2')
#         # raise ValueError
#         self.assertRaises(ValueError, self.auth.register_bare,
#                           **dict(wrong_field_name='user3', password='password_123'))
#         # raise ValueError wrong email
#         self.assertRaises(ValueError, self.auth.register_bare,
#                           **dict(email='user4@', password='password_123'))
#         self.db.auth_user.truncate()
#         self.db.commit()
#
#     def test_bulk_register(self):
#         self.auth.login_bare(username='bart', password='bart_password')
#         self.auth.settings.bulk_register_enabled = True
#         bulk_register_form = self.auth.bulk_register(max_emails=10).xml()
#         self.assertTrue('name="_formkey"' in bulk_register_form)
#
#     def test_change_password(self):
#         self.auth.login_bare(username='bart', password='bart_password')
#         change_password_form = getattr(self.auth, 'change_password')().xml()
#         self.assertTrue('name="_formkey"' in change_password_form)
#
#     def test_profile(self):
#         self.auth.login_bare(username='bart', password='bart_password')
#         profile_form = getattr(self.auth, 'profile')().xml()
#         self.assertTrue('name="_formkey"' in profile_form)
#
#     # def test_impersonate(self):
#     #     # Create a user to be impersonated
#     #     self.auth.get_or_create_user(dict(first_name='Omer',
#     #                                       last_name='Simpson',
#     #                                       username='omer',
#     #                                       email='omer@test.com',
#     #                                       password='password_omer',
#     #                                       registration_key='',
#     #                                       registration_id=''))
#     #     # Create impersonate group, assign bart to impersonate group and add impersonate permission over auth_user
#     #     self.auth.add_group('impersonate')
#     #     self.auth.add_membership(user_id=1,
#     #                              group_id=self.db(self.db.auth_user.username == 'bart'
#     #                                               ).select(self.db.auth_user.id).first().id)
#     #     self.auth.add_permission(group_id=self.db(self.db.auth_group.role == 'impersonate'
#     #                                               ).select(self.db.auth_group.id).first().id,
#     #                              name='impersonate',
#     #                              table_name='auth_user',
#     #                              record_id=0)
#     #     # Bart login
#     #     self.auth.login_bare(username='bart', password='bart_password')
#     #     self.assertTrue(self.auth.is_logged_in())
#     #     # Bart impersonate Omer
#     #     omer_id = self.db(self.db.auth_user.username == 'omer').select(self.db.auth_user.id).first().id
#     #     impersonate_form = self.auth.impersonate(user_id=omer_id)
#     #     self.assertTrue(self.auth.is_impersonating())
#     #     self.assertEqual(impersonate_form, 'test')
#
#     # def test_impersonate(self):
#     #     request = Request(env={})
#     #     request.application = 'a'
#     #     request.controller = 'c'
#     #     request.function = 'f'
#     #     request.folder = 'applications/admin'
#     #     response = Response()
#     #     session = Session()
#     #     T = TranslatorFactory('', 'en')
#     #     session.connect(request, response)
#     #     from gluon.globals import current
#     #     current.request = request
#     #     current.response = response
#     #     current.session = session
#     #     current.T = T
#     #     db = DAL(DEFAULT_URI, check_reserved=['all'])
#     #     auth = Auth(db)
#     #     auth.define_tables(username=True, signature=False)
#     #     db.define_table('t0', Field('tt'), auth.signature)
#     #     auth.enable_record_versioning(db)
#     #     # Create a user
#     #     auth.get_or_create_user(dict(first_name='Bart',
#     #                                       last_name='Simpson',
#     #                                       username='bart',
#     #                                       email='bart@simpson.com',
#     #                                       password='bart_password',
#     #                                       registration_key='bart',
#     #                                       registration_id=''
#     #                                       ))
#     #     # Create a user to be impersonated
#     #     auth.get_or_create_user(dict(first_name='Omer',
#     #                                       last_name='Simpson',
#     #                                       username='omer',
#     #                                       email='omer@test.com',
#     #                                       password='password_omer',
#     #                                       registration_key='',
#     #                                       registration_id=''))
#     #     # Create impersonate group, assign bart to impersonate group and add impersonate permission over auth_user
#     #     auth.add_group('impersonate')
#     #     auth.add_membership(user_id=1,
#     #                              group_id=db(db.auth_user.username == 'bart'
#     #                                               ).select(db.auth_user.id).first().id)
#     #     auth.add_permission(group_id=db(db.auth_group.role == 'impersonate'
#     #                                               ).select(db.auth_group.id).first().id,
#     #                              name='impersonate',
#     #                              table_name='auth_user',
#     #                              record_id=0)
#     #     # Bart login
#     #     auth.login_bare(username='bart', password='bart_password')
#     #     # Bart impersonate Omer
#     #     omer_id = db(db.auth_user.username == 'omer').select(db.auth_user.id).first().id
#     #     impersonate_form = auth.impersonate(user_id=omer_id)
#     #     self.assertTrue(auth.is_impersonating())
#     #     self.assertEqual(impersonate_form, 'test')
class TestAuth(unittest.TestCase):

    def myassertRaisesRegex(self, *args, **kwargs):
        if PY2:
            return getattr(self, 'assertRaisesRegexp')(*args, **kwargs)
        return getattr(self, 'assertRaisesRegex')(*args, **kwargs)

    def setUp(self):
        self.request = Request(env={})
        self.request.application = 'a'
        self.request.controller = 'c'
        self.request.function = 'f'
        self.request.folder = 'applications/admin'
        self.response = Response()
        self.session = Session()
        T = TranslatorFactory('', 'en')
        self.session.connect(self.request, self.response)
        from gluon.globals import current
        self.current = current
        self.current.request = self.request
        self.current.response = self.response
        self.current.session = self.session
        self.current.T = T
        self.db = DAL(DEFAULT_URI, check_reserved=['all'])
        self.auth = Auth(self.db)
        self.auth.define_tables(username=True, signature=False)
        self.db.define_table('t0', Field('tt'), self.auth.signature)
        self.auth.enable_record_versioning(self.db)
        self.auth.settings.registration_requires_verification = False
        self.auth.settings.registration_requires_approval = False
        # Create a user
        # Note: get_or_create_user() doesn't seems to create user properly it better to use register_bare() and
        #       prevent login_bare() test from succeed. db insert the user manually not properly work either.
        # Not working
        # self.auth.get_or_create_user(dict(first_name='Bart',
        #                                   last_name='Simpson',
        #                                   username='bart',
        #                                   email='bart@simpson.com',
        #                                   password='bart_password',
        #                                   # registration_key=None,
        #                                   #registration_id='bart@simpson.com'
        #                                  ),
        #                              login=False)
        # Not working
        # self.db.auth_user.insert(first_name='Bart',
        #                         last_name='Simpson',
        #                         username='bart',
        #                         email='bart@simpson.com',
        #                         password='bart_password')
        # self.db.commit()
        self.auth.register_bare(first_name='Bart',
                                last_name='Simpson',
                                username='bart',
                                email='bart@simpson.com',
                                password='bart_password')

    def test_assert_setup(self):
        self.assertTrue('auth_user' in self.db)
        self.assertTrue('auth_group' in self.db)
        self.assertTrue('auth_membership' in self.db)
        self.assertTrue('auth_permission' in self.db)
        self.assertTrue('auth_event' in self.db)
        bart_record = self.db(self.db.auth_user.username == 'bart').select().first()
        self.assertEqual(bart_record['username'], 'bart')
        self.assertEqual(bart_record['registration_key'], '')
        bart_id = self.db(self.db.auth_user.username == 'bart').select().first().id
        bart_group_id = self.db(self.db.auth_group.role == 'user_{0}'.format(bart_id)).select().first().id
        self.assertTrue(self.db((self.db.auth_membership.group_id == bart_group_id) &
                                (self.db.auth_membership.user_id == bart_id)).select().first())

    # Just calling many form functions
    def test_basic_blank_forms(self):
        for f in ['login', 'retrieve_password', 'retrieve_username', 'register']:
            html_form = getattr(self.auth, f)().xml()
            self.assertTrue(b'name="_formkey"' in html_form)

        for f in ['logout', 'verify_email', 'reset_password', 'change_password', 'profile', 'groups']:
            self.myassertRaisesRegex(HTTP, "303*", getattr(self.auth, f))

        self.myassertRaisesRegex(HTTP, "401*", self.auth.impersonate)

        try:
            for t in ['t0_archive', 't0', 'auth_cas', 'auth_event',
                      'auth_membership', 'auth_permission', 'auth_group',
                      'auth_user']:
                self.db[t].drop()
        except SyntaxError as e:
            # GAE doesn't support drop
            pass
        return

    def test_get_vars_next(self):
        self.current.request.vars._next = 'next_test'
        self.assertEqual(self.auth.get_vars_next(), 'next_test')

    # TODO: def test_navbar(self):
    # TODO: def test___get_migrate(self):

    def test_enable_record_versioning(self):
        self.assertTrue('t0_archive' in self.db)

    # TODO: def test_define_signature(self):
    # TODO: def test_define_signature(self):
    # TODO: def test_define_table(self):

    def test_log_event(self):
        self.auth.login_user(self.db(self.db.auth_user.username == 'bart').select().first())  # bypass login_bare()
        bart_id = self.db(self.db.auth_user.username == 'bart').select(self.db.auth_user.id).first().id
        # user logged in
        self.auth.log_event(description='some_log_event_description_%(var1)s',
                            vars={"var1": "var1"},
                            origin='log_event_test_1')
        rtn = self.db(self.db.auth_event.origin == 'log_event_test_1'
                      ).select(*[self.db.auth_event[f]
                                 for f in self.db.auth_event.fields if f not in ('id', 'time_stamp')]).first().as_dict()
        self.assertEqual(set(rtn.items()), set({'origin': 'log_event_test_1',
                                                'client_ip': None,
                                                'user_id': bart_id,
                                                'description': 'some_log_event_description_var1'}.items()))
        # user not logged
        self.auth.logout_bare()
        self.auth.log_event(description='some_log_event_description_%(var2)s',
                            vars={"var2": "var2"},
                            origin='log_event_test_2')
        rtn = self.db(self.db.auth_event.origin == 'log_event_test_2'
                      ).select(*[self.db.auth_event[f]
                                 for f in self.db.auth_event.fields if f not in ('id', 'time_stamp')]).first().as_dict()
        self.assertEqual(set(rtn.items()), set({'origin': 'log_event_test_2',
                                                'client_ip': None,
                                                'user_id': None,
                                                'description': 'some_log_event_description_var2'}.items()))
        # no logging tests
        self.auth.settings.logging_enabled = False
        count_log_event_test_before = self.db(self.db.auth_event.id > 0).count()
        self.auth.log_event(description='some_log_event_description_%(var3)s',
                            vars={"var3": "var3"},
                            origin='log_event_test_3')
        count_log_event_test_after = self.db(self.db.auth_event.id > 0).count()
        self.assertEqual(count_log_event_test_after, count_log_event_test_before)
        self.auth.settings.logging_enabled = True
        count_log_event_test_before = self.db(self.db.auth_event.id > 0).count()
        self.auth.log_event(description=None,
                            vars={"var4": "var4"},
                            origin='log_event_test_4')
        count_log_event_test_after = self.db(self.db.auth_event.id > 0).count()
        self.assertEqual(count_log_event_test_after, count_log_event_test_before)
        # TODO: Corner case translated description...

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

    # TODO: def test_basic(self):
    # TODO: def test_login_user(self):
    # TODO: def test__get_login_settings(self):

    def test_login_bare(self):
        self.auth.login_bare(username='bart', password='bart_password')
        self.assertTrue(self.auth.is_logged_in())
        self.auth.logout_bare()
        # Failing login because wrong_password
        self.assertFalse(self.auth.login_bare(username='bart', password='wrong_password'))
        # NOTE : The following failed for some reason, but I can't find out why
        # self.auth = Auth(self.db)
        # self.auth.define_tables(username=False, signature=False)
        # self.auth.settings.registration_requires_verification = False
        # self.auth.settings.registration_requires_approval = False
        # self.auth.register_bare(first_name='Omer',
        #                         last_name='Simpson',
        #                         # no username field passed, failed with :
        #                         # ValueError('register_bare: userfield not provided or invalid')
        #                         # Or
        #                         # username='omer',
        #                         # Or
        #                         # username='omer@simpson.com',
        #                         # In either previous cases, it failed with :
        #                         # self.assertTrue(self.auth.is_logged_in()) AssertionError: False is not true
        #                         email='omer@simpson.com',
        #                         password='omer_password')
        # self.auth.login_bare(username='omer@sympson.com', password='omer_password')
        # self.assertTrue(self.auth.is_logged_in())

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

    # TODO: def test_cas_login(self):
    # TODO: def test_cas_validate(self):
    # TODO: def test__reset_two_factor_auth(self):
    # TODO: def test_when_is_logged_in_bypass_next_in_url(self):
    # TODO: def test_login(self):
    # TODO: def test_logout(self):

    def test_logout_bare(self):
        self.auth.login_user(self.db(self.db.auth_user.username == 'bart').select().first())  # bypass login_bare()
        self.assertTrue(self.auth.is_logged_in())
        self.auth.logout_bare()
        self.assertFalse(self.auth.is_logged_in())

    # TODO: def test_register(self):

    def test_is_logged_in(self):
        self.auth.user = 'logged_in'
        self.assertTrue(self.auth.is_logged_in())
        self.auth.user = None
        self.assertFalse(self.auth.is_logged_in())

    # TODO: def test_verify_email(self):
    # TODO: def test_retrieve_username(self):

    def test_random_password(self):
        # let just check that the function is callable
        self.assertTrue(self.auth.random_password())

    # TODO: def test_reset_password_deprecated(self):
    # TODO: def test_confirm_registration(self):
    # TODO: def test_email_registration(self):

    def test_bulk_register(self):
        self.auth.login_user(self.db(self.db.auth_user.username == 'bart').select().first())  # bypass login_bare()
        self.auth.settings.bulk_register_enabled = True
        bulk_register_form = self.auth.bulk_register(max_emails=10).xml()
        self.assertTrue(b'name="_formkey"' in bulk_register_form)

    # TODO: def test_manage_tokens(self):
    # TODO: def test_reset_password(self):
    # TODO: def test_request_reset_password(self):
    # TODO: def test_email_reset_password(self):
    # TODO: def test_retrieve_password(self):

    def test_change_password(self):
        self.auth.login_user(self.db(self.db.auth_user.username == 'bart').select().first())  # bypass login_bare()
        change_password_form = getattr(self.auth, 'change_password')().xml()
        self.assertTrue(b'name="_formkey"' in change_password_form)

    def test_profile(self):
        self.auth.login_user(self.db(self.db.auth_user.username == 'bart').select().first())  # bypass login_bare()
        profile_form = getattr(self.auth, 'profile')().xml()
        self.assertTrue(b'name="_formkey"' in profile_form)

    # TODO: def test_run_login_onaccept(self):
    # TODO: def test_jwt(self):
    # TODO: def test_is_impersonating(self):

    def test_impersonate(self):
        # Create a user to be impersonated
        self.auth.get_or_create_user(dict(first_name='Omer',
                                          last_name='Simpson',
                                          username='omer',
                                          email='omer@test.com',
                                          password='password_omer',
                                          registration_key='',
                                          registration_id=''),
                                     login=False)
        self.db.commit()
        self.assertFalse(self.auth.is_logged_in())
        # Create impersonate group, assign bart to impersonate group and add impersonate permission over auth_user
        group_id = self.auth.add_group('impersonate')
        self.auth.add_membership(user_id=self.db(self.db.auth_user.username == 'bart'
                                                 ).select(self.db.auth_user.id).first().id,
                                 group_id=group_id)
        self.auth.add_permission(group_id=group_id,
                                 name='impersonate',
                                 table_name='auth_user',
                                 record_id=0)
        # Bart login
        # self.auth.login_bare(username='bart', password='bart_password')
        self.auth.login_user(self.db(self.db.auth_user.username == 'bart').select().first())  # bypass login_bare()
        self.assertTrue(self.auth.is_logged_in())
        bart_id = self.db(self.db.auth_user.username == 'bart').select(self.db.auth_user.id).first().id
        self.assertEqual(self.auth.user_id, bart_id)
        # self.session.auth = self.auth
        # self.assertTrue(self.session.auth)

        # basic impersonate() test that return a read form
        self.assertEqual(self.auth.impersonate().xml(),
                         b'<form action="#" enctype="multipart/form-data" method="post"><table><tr id="no_table_user_id__row"><td class="w2p_fl"><label class="" for="no_table_user_id" id="no_table_user_id__label">User Id: </label></td><td class="w2p_fw"><input class="integer" id="no_table_user_id" name="user_id" type="text" value="" /></td><td class="w2p_fc"></td></tr><tr id="submit_record__row"><td class="w2p_fl"></td><td class="w2p_fw"><input type="submit" value="Submit" /></td><td class="w2p_fc"></td></tr></table></form>')
        # bart impersonate itself
        self.assertEqual(self.auth.impersonate(bart_id), None)
        self.assertFalse(self.auth.is_impersonating())  # User shouldn't impersonate itself?
        # Bart impersonate Omer
        omer_id = self.db(self.db.auth_user.username == 'omer').select(self.db.auth_user.id).first().id
        impersonate_form = self.auth.impersonate(user_id=omer_id)
        self.assertTrue(self.auth.is_impersonating())
        self.assertEqual(self.auth.user_id, omer_id)  # we make it really sure
        self.assertEqual(impersonate_form.xml(),
                         b'<form action="#" enctype="multipart/form-data" method="post"><table><tr id="auth_user_id__row"><td class="w2p_fl"><label class="readonly" for="auth_user_id" id="auth_user_id__label">Id: </label></td><td class="w2p_fw"><span id="auth_user_id">2</span></td><td class="w2p_fc"></td></tr><tr id="auth_user_first_name__row"><td class="w2p_fl"><label class="readonly" for="auth_user_first_name" id="auth_user_first_name__label">First name: </label></td><td class="w2p_fw">Omer</td><td class="w2p_fc"></td></tr><tr id="auth_user_last_name__row"><td class="w2p_fl"><label class="readonly" for="auth_user_last_name" id="auth_user_last_name__label">Last name: </label></td><td class="w2p_fw">Simpson</td><td class="w2p_fc"></td></tr><tr id="auth_user_email__row"><td class="w2p_fl"><label class="readonly" for="auth_user_email" id="auth_user_email__label">E-mail: </label></td><td class="w2p_fw">omer@test.com</td><td class="w2p_fc"></td></tr><tr id="auth_user_username__row"><td class="w2p_fl"><label class="readonly" for="auth_user_username" id="auth_user_username__label">Username: </label></td><td class="w2p_fw">omer</td><td class="w2p_fc"></td></tr></table><div style="display:none;"><input name="id" type="hidden" value="2" /></div></form>')
        self.auth.logout_bare()
        # Failing impersonation
        # User lacking impersonate membership
        self.auth.login_user(self.db(self.db.auth_user.username == 'omer').select().first())  # bypass login_bare()
        # self.assertTrue(self.auth.is_logged_in())  # For developing test
        # self.assertFalse(self.auth.is_impersonating())  # For developing test
        self.myassertRaisesRegex(HTTP, "403*", self.auth.impersonate, bart_id)
        self.auth.logout_bare()
        # Try impersonate a non existing user
        self.auth.login_user(self.db(self.db.auth_user.username == 'bart').select().first())  # bypass login_bare()
        # self.assertTrue(self.auth.is_logged_in())  # For developing test
        # self.assertFalse(self.auth.is_impersonating())  # For developing test
        self.myassertRaisesRegex(HTTP, "401*", self.auth.impersonate, 1000)  # user with id 1000 shouldn't exist
        # Try impersonate user with id = 0 or '0' when bart impersonating omer
        self.auth.impersonate(user_id=omer_id)
        self.assertTrue(self.auth.is_impersonating())
        self.assertEqual(self.auth.impersonate(user_id=0), None)

    # TODO: def test_update_groups(self):

    def test_groups(self):
        self.auth.login_user(self.db(self.db.auth_user.username == 'bart').select().first())  # bypass login_bare()
        self.assertEqual(self.auth.groups().xml(),
                         b'<table><tr><td><h3>user_1(1)</h3></td></tr><tr><td><p></p></td></tr></table>')

    def test_not_authorized(self):
        self.current.request.ajax = 'facke_ajax_request'
        self.myassertRaisesRegex(HTTP, "403*", self.auth.not_authorized)
        self.current.request.ajax = None
        self.assertEqual(self.auth.not_authorized(), self.auth.messages.access_denied)

    def test_allows_jwt(self):
        self.myassertRaisesRegex(HTTP, "400*", self.auth.allows_jwt)

    # TODO: def test_requires(self):

    # def test_login(self):
    # Basic testing above in "test_basic_blank_forms()" could be refined here

    # TODO: def test_requires_login_or_token(self):
    # TODO: def test_requires_membership(self):
    # TODO: def test_requires_permission(self):
    # TODO: def test_requires_signature(self):

    def test_add_group(self):
        self.assertEqual(self.auth.add_group(role='a_group', description='a_group_role_description'),
                         self.db(self.db.auth_group.role == 'a_group').select(self.db.auth_group.id).first().id)

    def test_del_group(self):
        bart_group_id = 1  # Should be group 1, 'user_1'
        self.assertEqual(self.auth.del_group(group_id=bart_group_id), None)

    def test_id_group(self):
        self.assertEqual(self.auth.id_group(role='user_1'), 1)
        # If role don't exist it return None
        self.assertEqual(self.auth.id_group(role='non_existing_role_name'), None)

    def test_user_group(self):
        self.assertEqual(self.auth.user_group(user_id=1), 1)
        # Bart should be user 1 and it unique group should be 1, 'user_1'

    def test_user_group_role(self):
        self.auth.login_user(self.db(self.db.auth_user.username == 'bart').select().first())  # bypass login_bare()
        user_group_role = 'user_%s' % self.db(self.db.auth_user.username == 'bart'
                                              ).select(self.db.auth_user.id).first().id
        self.assertEqual(self.auth.user_group_role(), user_group_role)
        self.auth.logout_bare()
        # with user_id args
        self.assertEqual(self.auth.user_group_role(user_id=1), 'user_1')
        # test None
        self.auth.settings.create_user_groups = None
        self.assertEqual(self.auth.user_group_role(user_id=1), None)

    def test_has_membership(self):
        self.auth.login_user(self.db(self.db.auth_user.username == 'bart').select().first())  # bypass login_bare()
        self.assertTrue(self.auth.has_membership('user_1'))
        self.assertFalse(self.auth.has_membership('user_555'))
        self.assertTrue(self.auth.has_membership(group_id=1))
        self.auth.logout_bare()
        self.assertTrue(self.auth.has_membership(role='user_1', user_id=1))
        self.assertTrue(self.auth.has_membership(group_id=1, user_id=1))
        # check that event is logged
        count_log_event_test_before = self.db(self.db.auth_event.id > 0).count()
        self.assertTrue(self.auth.has_membership(group_id=1, user_id=1))
        count_log_event_test_after = self.db(self.db.auth_event.id > 0).count()
        self.assertEqual(count_log_event_test_after, count_log_event_test_before)

    def test_add_membership(self):
        user = self.db(self.db.auth_user.username == 'bart').select().first()  # bypass login_bare()
        user_id = user.id
        role_name = 'test_add_membership_group'
        group_id = self.auth.add_group(role_name)
        self.assertFalse(self.auth.has_membership(role_name))

        self.auth.add_membership(group_id=group_id, user_id=user_id)
        self.assertTrue(self.auth.has_membership(group_id, user_id=user_id))
        self.auth.del_membership(group_id=group_id, user_id=user_id)
        self.assertFalse(self.auth.has_membership(group_id, user_id=user_id))

        self.auth.add_membership(role=role_name, user_id=user_id)
        self.assertTrue(self.auth.has_membership(group_id, user_id=user_id))
        self.auth.del_membership(group_id=group_id, user_id=user_id)
        self.assertFalse(self.auth.has_membership(group_id, user_id=user_id))

        with self.myassertRaisesRegex(ValueError, '^group_id not provided or invalid$'):
            self.auth.add_membership(group_id='not_existing_group_name', user_id=user_id)
        with self.myassertRaisesRegex(ValueError, '^group_id not provided or invalid$'):
            self.auth.add_membership(role='not_existing_role_name', user_id=user_id)
        with self.myassertRaisesRegex(ValueError, '^user_id not provided or invalid$'):
            self.auth.add_membership(group_id=group_id, user_id=None)
        with self.myassertRaisesRegex(ValueError, '^user_id not provided or invalid$'):
            self.auth.add_membership(role=role_name, user_id=None)

        self.auth.login_user(user)

        self.auth.add_membership(group_id=group_id)
        self.assertTrue(self.auth.has_membership(group_id))
        self.auth.del_membership(group_id=group_id)
        self.assertFalse(self.auth.has_membership(group_id))

        self.auth.add_membership(role=role_name)
        self.assertTrue(self.auth.has_membership(group_id))
        self.auth.del_membership(group_id=group_id)
        self.assertFalse(self.auth.has_membership(group_id))

        # default usage (group_id=role_name)
        self.auth.add_membership(role_name)
        self.assertTrue(self.auth.has_membership(group_id))
        self.auth.del_membership(group_id=group_id)
        self.assertFalse(self.auth.has_membership(group_id))

        # re-adding a membership should return the existing membership
        record0_id = self.auth.add_membership(group_id)
        self.assertTrue(self.auth.has_membership(group_id))
        record1_id = self.auth.add_membership(group_id)
        self.assertEqual(record0_id, record1_id)
        self.auth.del_membership(group_id=group_id)
        self.assertFalse(self.auth.has_membership(group_id))

        with self.myassertRaisesRegex(ValueError, '^group_id not provided or invalid$'):
            self.auth.add_membership(group_id='not_existing_group_name')
        with self.myassertRaisesRegex(ValueError, '^group_id not provided or invalid$'):
            self.auth.add_membership(role='not_existing_role_name')

    def test_del_membership(self):
        self.auth.login_user(self.db(self.db.auth_user.username == 'bart').select().first())  # bypass login_bare()
        count_log_event_test_before = self.db(self.db.auth_event.id > 0).count()
        user_1_role_id = self.db(self.db.auth_membership.group_id == self.auth.id_group('user_1')
                                 ).select(self.db.auth_membership.id).first().id
        self.assertEqual(self.auth.del_membership('user_1'), user_1_role_id)
        count_log_event_test_after = self.db(self.db.auth_event.id > 0).count()
        # check that event is logged
        self.assertEqual(count_log_event_test_after, count_log_event_test_before)
        # not logged in test case
        group_id = self.auth.add_group('some_test_group')
        membership_id = self.auth.add_membership('some_test_group')
        self.assertEqual(self.auth.user_groups[group_id], 'some_test_group')
        self.auth.logout_bare()
        # not deleted
        self.assertFalse(self.auth.del_membership('some_test_group'))
        self.assertEqual(set(self.db.auth_membership(membership_id).as_dict().items()),
                         set({'group_id': 2, 'user_id': 1, 'id': 2}.items()))  # is not deleted
        # deleted
        bart_id = self.db(self.db.auth_user.username == 'bart').select(self.db.auth_user.id).first().id
        self.assertTrue(self.auth.del_membership('some_test_group', user_id=bart_id))
        self.assertEqual(self.db.auth_membership(membership_id), None)  # is really deleted

    def test_has_permission(self):
        self.auth.login_user(self.db(self.db.auth_user.username == 'bart').select().first())  # bypass login_bare()
        bart_id = self.db(self.db.auth_user.username == 'bart').select(self.db.auth_user.id).first().id
        self.auth.add_permission(group_id=self.auth.id_group('user_1'),
                                 name='some_permission',
                                 table_name='auth_user',
                                 record_id=0,
                                 )
        # True case
        self.assertTrue(self.auth.has_permission(name='some_permission',
                                                 table_name='auth_user',
                                                 record_id=0,
                                                 user_id=bart_id,
                                                 group_id=self.auth.id_group('user_1')))
        # False case
        self.assertFalse(self.auth.has_permission(name='some_other_permission',
                                                  table_name='auth_user',
                                                  record_id=0,
                                                  user_id=bart_id,
                                                  group_id=self.auth.id_group('user_1')))

    def test_add_permission(self):
        count_log_event_test_before = self.db(self.db.auth_event.id > 0).count()
        permission_id = \
            self.auth.add_permission(group_id=self.auth.id_group('user_1'),
                                     name='some_permission',
                                     table_name='auth_user',
                                     record_id=0,
                                     )
        count_log_event_test_after = self.db(self.db.auth_event.id > 0).count()
        # check that event is logged
        self.assertEqual(count_log_event_test_after, count_log_event_test_before)
        # True case
        permission_count = \
            self.db(self.db.auth_permission.id == permission_id).count()
        self.assertTrue(permission_count)
        # False case
        permission_count = \
            self.db((self.db.auth_permission.group_id == self.auth.id_group('user_1')) &
                    (self.db.auth_permission.name == 'no_permission') &
                    (self.db.auth_permission.table_name == 'no_table') &
                    (self.db.auth_permission.record_id == 0)).count()
        self.assertFalse(permission_count)
        # corner case
        self.auth.login_user(self.db(self.db.auth_user.username == 'bart').select().first())  # bypass login_bare()
        permission_id = \
            self.auth.add_permission(group_id=0,
                                     name='user_1_permission',
                                     table_name='auth_user',
                                     record_id=0,
                                     )
        permission_name = \
            self.db(self.db.auth_permission.id == permission_id).select(self.db.auth_permission.name).first().name
        self.assertEqual(permission_name, 'user_1_permission')
        # add an existing permission
        permission_id =\
            self.auth.add_permission(group_id=0,
                                     name='user_1_permission',
                                     table_name='auth_user',
                                     record_id=0,
                                     )
        self.assertTrue(permission_id)

    def test_del_permission(self):
        permission_id = \
            self.auth.add_permission(group_id=self.auth.id_group('user_1'),
                                     name='del_permission_test',
                                     table_name='auth_user',
                                     record_id=0,
                                     )
        count_log_event_test_before = self.db(self.db.auth_event.id > 0).count()
        self.assertTrue(self.auth.del_permission(group_id=self.auth.id_group('user_1'),
                                                 name='del_permission_test',
                                                 table_name='auth_user',
                                                 record_id=0,))
        count_log_event_test_after = self.db(self.db.auth_event.id > 0).count()
        # check that event is logged
        self.assertEqual(count_log_event_test_after, count_log_event_test_before)
        # really deleted
        permission_count = \
            self.db(self.db.auth_permission.id == permission_id).count()
        self.assertFalse(permission_count)

    # TODO: def test_accessible_query(self):
    # TODO: def test_archive(self):
    # TODO: def test_wiki(self):
    # TODO: def test_wikimenu(self):
    # End Auth test


# TODO: class TestCrud(unittest.TestCase):
# It deprecated so far from a priority


# TODO: class TestService(unittest.TestCase):


# TODO: class TestPluginManager(unittest.TestCase):


# TODO: class TestWiki(unittest.TestCase):


# TODO: class TestConfig(unittest.TestCase):


class TestToolsFunctions(unittest.TestCase):
    """
    Test suite for all the tools.py functions
    """
    def test_prettydate(self):
        # plain
        now = datetime.datetime.now()
        self.assertEqual(prettydate(d=now), 'now')
        one_second = now - datetime.timedelta(seconds=1)
        self.assertEqual(prettydate(d=one_second), '1 second ago')
        more_than_one_second = now - datetime.timedelta(seconds=2)
        self.assertEqual(prettydate(d=more_than_one_second), '2 seconds ago')
        one_minute = now - datetime.timedelta(seconds=60)
        self.assertEqual(prettydate(d=one_minute), '1 minute ago')
        more_than_one_minute = now - datetime.timedelta(seconds=61)
        self.assertEqual(prettydate(d=more_than_one_minute), '1 minute ago')
        two_minutes = now - datetime.timedelta(seconds=120)
        self.assertEqual(prettydate(d=two_minutes), '2 minutes ago')
        more_than_two_minutes = now - datetime.timedelta(seconds=121)
        self.assertEqual(prettydate(d=more_than_two_minutes), '2 minutes ago')
        one_hour = now - datetime.timedelta(seconds=60 * 60)
        self.assertEqual(prettydate(d=one_hour), '1 hour ago')
        more_than_one_hour = now - datetime.timedelta(seconds=3601)
        self.assertEqual(prettydate(d=more_than_one_hour), '1 hour ago')
        two_hours = now - datetime.timedelta(seconds=2 * 60 * 60)
        self.assertEqual(prettydate(d=two_hours), '2 hours ago')
        more_than_two_hours = now - datetime.timedelta(seconds=2 * 60 * 60 + 1)
        self.assertEqual(prettydate(d=more_than_two_hours), '2 hours ago')
        one_day = now - datetime.timedelta(days=1)
        self.assertEqual(prettydate(d=one_day), '1 day ago')
        more_than_one_day = now - datetime.timedelta(days=2)
        self.assertEqual(prettydate(d=more_than_one_day), '2 days ago')
        one_week = now - datetime.timedelta(days=7)
        self.assertEqual(prettydate(d=one_week), '1 week ago')
        more_than_one_week = now - datetime.timedelta(days=8)
        self.assertEqual(prettydate(d=more_than_one_week), '1 week ago')
        two_weeks = now - datetime.timedelta(days=14)
        self.assertEqual(prettydate(d=two_weeks), '2 weeks ago')
        more_than_two_weeks = now - datetime.timedelta(days=15)
        self.assertEqual(prettydate(d=more_than_two_weeks), '2 weeks ago')
        three_weeks = now - datetime.timedelta(days=21)
        self.assertEqual(prettydate(d=three_weeks), '3 weeks ago')
        one_month = now - datetime.timedelta(days=27)
        self.assertEqual(prettydate(d=one_month), '1 month ago')
        more_than_one_month = now - datetime.timedelta(days=28)
        self.assertEqual(prettydate(d=more_than_one_month), '1 month ago')
        two_months = now - datetime.timedelta(days=60)
        self.assertEqual(prettydate(d=two_months), '2 months ago')
        three_months = now - datetime.timedelta(days=90)
        self.assertEqual(prettydate(d=three_months), '3 months ago')
        one_year = now - datetime.timedelta(days=365)
        self.assertEqual(prettydate(d=one_year), '1 year ago')
        more_than_one_year = now - datetime.timedelta(days=366)
        self.assertEqual(prettydate(d=more_than_one_year), '1 year ago')
        two_years = now - datetime.timedelta(days=2 * 365)
        self.assertEqual(prettydate(d=two_years), '2 years ago')
        more_than_two_years = now - datetime.timedelta(days=2 * 365 + 1)
        self.assertEqual(prettydate(d=more_than_two_years), '2 years ago')
        # date()
        d = now.date()
        self.assertEqual(prettydate(d=d), 'now')
        one_day = now.date() - datetime.timedelta(days=1)
        self.assertEqual(prettydate(d=one_day), '1 day ago')
        tow_days = now.date() - datetime.timedelta(days=2)
        self.assertEqual(prettydate(d=tow_days), '2 days ago')
        # from now
        # from now is picky depending of the execution time, so we can't use sharp value like 1 second or 1 day
        in_one_minute = now - datetime.timedelta(seconds=-65)
        self.assertEqual(prettydate(d=in_one_minute), '1 minute from now')
        in_twenty_three_hours = now - datetime.timedelta(hours=-23.5)
        self.assertEqual(prettydate(d=in_twenty_three_hours), '23 hours from now')
        in_one_year = now - datetime.timedelta(days=-366)
        self.assertEqual(prettydate(d=in_one_year), '1 year from now')
        # utc=True
        now = datetime.datetime.utcnow()
        self.assertEqual(prettydate(d=now, utc=True), 'now')
        one_second = now - datetime.timedelta(seconds=1)
        self.assertEqual(prettydate(d=one_second, utc=True), '1 second ago')
        # not d or invalid date
        self.assertEqual(prettydate(d=None), '')
        self.assertEqual(prettydate(d='invalid_date'), '[invalid date]')


pjoin = os.path.join


def have_symlinks():
    return os.name == 'posix'


class Test_Expose__in_base(unittest.TestCase):

    def test_in_base(self):
        are_under = [
            # (sub, base)
            ('/foo/bar', '/foo'),
            ('/foo', '/foo'),
            ('/foo', '/'),
            ('/', '/'),
        ]
        for sub, base in are_under:
            self.assertTrue(Expose._Expose__in_base(subdir=sub, basedir=base, sep='/'),
                            '%s is not under %s' % (sub, base))

    def test_not_in_base(self):
        are_not_under = [
            # (sub, base)
            ('/foobar', '/foo'),
            ('/foo', '/foo/bar'),
            ('/bar', '/foo'),
            ('/foo/bar', '/bar'),
            ('/', '/x'),
        ]
        for sub, base in are_not_under:
            self.assertFalse(Expose._Expose__in_base(subdir=sub, basedir=base, sep='/'),
                             '%s should not be under %s' % (sub, base))


class TestExpose(unittest.TestCase):

    def setUp(self):
        self.base_dir = tempfile.mkdtemp()

        self.make_dirs()
        self.touch_files()
        self.make_readme()
        if have_symlinks():
            self.make_symlinks()

        # $BASE/
        # |-- inside/
        # |   |-- dir1/
        # |   |   |-- file1
        # |   |   `-- file2
        # |   |-- dir2/
        # |   |   |-- link_to_dir1/@ -> $BASE/inside/dir1/
        # |   |   `-- link_to_file1@ -> $BASE/inside/dir1/file1
        # |   |-- link_to_outside/@ -> $BASE/outside/
        # |   |-- link_to_file3@ -> $BASE/outside/file3
        # |   `-- README
        # `-- outside/
        #     `-- file3

        self.set_expectations()
        tools.URL = lambda args: URL(a='a', c='c', f='f', args=args)

    def tearDown(self):
        tools.URL = URL
        shutil.rmtree(self.base_dir)

    def make_dirs(self):
        """setup directory structure"""
        for d in (['inside'],
                  ['inside', 'dir1'],
                  ['inside', 'dir2'],
                  ['outside']):
            os.mkdir(pjoin(self.base_dir, *d))

    def touch_files(self):
        """create some files"""
        for f in (['inside', 'dir1', 'file1'],
                  ['inside', 'dir1', 'file2'],
                  ['outside', 'file3']):
            with open(pjoin(self.base_dir, *f), 'a'):
                pass

    def make_readme(self):
        with open(pjoin(self.base_dir, 'inside', 'README'), 'w') as f:
            f.write('README content')

    def make_symlinks(self):
        """setup extension for posix systems"""
        # inside links
        os.symlink(
            pjoin(self.base_dir, 'inside', 'dir1'),
            pjoin(self.base_dir, 'inside', 'dir2', 'link_to_dir1'))
        os.symlink(
            pjoin(self.base_dir, 'inside', 'dir1', 'file1'),
            pjoin(self.base_dir, 'inside', 'dir2', 'link_to_file1'))
        # outside links
        os.symlink(
            pjoin(self.base_dir, 'outside'),
            pjoin(self.base_dir, 'inside', 'link_to_outside'))
        os.symlink(
            pjoin(self.base_dir, 'outside', 'file3'),
            pjoin(self.base_dir, 'inside', 'link_to_file3'))

    def set_expectations(self):
        url = lambda args: URL('a', 'c', 'f', args=args)

        self.expected_folders = {}
        self.expected_folders['inside'] = SPAN(H3('Folders'), TABLE(
            TR(TD(A('dir1', _href=url(args=['dir1'])))),
            TR(TD(A('dir2', _href=url(args=['dir2'])))),
            _class='table',
        ))
        self.expected_folders[pjoin('inside', 'dir1')] = ''
        if have_symlinks():
            self.expected_folders[pjoin('inside', 'dir2')] = SPAN(H3('Folders'), TABLE(
                TR(TD(A('link_to_dir1', _href=url(args=['dir2', 'link_to_dir1'])))),
                _class='table',
            ))
        else:
            self.expected_folders[pjoin('inside', 'dir2')] = ''

        self.expected_files = {}
        self.expected_files['inside'] = SPAN(H3('Files'), TABLE(
            TR(TD(A('README', _href=url(args=['README']))), TD('')),
            _class='table',
        ))
        self.expected_files[pjoin('inside', 'dir1')] = SPAN(H3('Files'), TABLE(
            TR(TD(A('file1', _href=url(args=['dir1', 'file1']))), TD('')),
            TR(TD(A('file2', _href=url(args=['dir1', 'file2']))), TD('')),
            _class='table',
        ))
        if have_symlinks():
            self.expected_files[pjoin('inside', 'dir2')] = SPAN(H3('Files'), TABLE(
                TR(TD(A('link_to_file1', _href=url(args=['dir2', 'link_to_file1']))), TD('')),
                _class='table',
            ))
        else:
            self.expected_files[pjoin('inside', 'dir2')] = ''

    def make_expose(self, base, show='', follow_symlink_out=False):
        current.request = Request(env={})
        current.request.raw_args = show
        current.request.args = show.split('/')
        return Expose(base=pjoin(self.base_dir, base),
                      basename=base,
                      follow_symlink_out=follow_symlink_out)

    def test_expose_inside_state(self):
        expose = self.make_expose(base='inside', show='')
        self.assertEqual(expose.args, [])
        self.assertEqual(expose.folders, ['dir1', 'dir2'])
        self.assertEqual(expose.filenames, ['README'])

    @unittest.skipUnless(have_symlinks(), 'requires symlinks')
    def test_expose_inside_state_floow_symlink_out(self):
        expose = self.make_expose(base='inside', show='',
                                  follow_symlink_out=True)
        self.assertEqual(expose.args, [])
        self.assertEqual(expose.folders, ['dir1', 'dir2', 'link_to_outside'])
        self.assertEqual(expose.filenames, ['README', 'link_to_file3'])

    def test_expose_inside_dir1_state(self):
        expose = self.make_expose(base='inside', show='dir1')
        self.assertEqual(expose.args, ['dir1'])
        self.assertEqual(expose.folders, [])
        self.assertEqual(expose.filenames, ['file1', 'file2'])

    def test_expose_inside_dir2_state(self):
        expose = self.make_expose(base='inside', show='dir2')
        self.assertEqual(expose.args, ['dir2'])
        if have_symlinks():
            self.assertEqual(expose.folders, ['link_to_dir1'])
            self.assertEqual(expose.filenames, ['link_to_file1'])
        else:
            self.assertEqual(expose.folders, [])
            self.assertEqual(expose.filenames, [])

    def test_expose_base_inside_state(self):
        expose = self.make_expose(base='', show='inside')
        self.assertEqual(expose.args, ['inside'])
        if have_symlinks():
            self.assertEqual(expose.folders, ['dir1', 'dir2', 'link_to_outside'])
            self.assertEqual(expose.filenames, ['README', 'link_to_file3'])
        else:
            self.assertEqual(expose.folders, ['dir1', 'dir2'])
            self.assertEqual(expose.filenames, ['README'])

    def test_expose_base_inside_dir2_state(self):
        expose = self.make_expose(base='', show='inside/dir2')
        self.assertEqual(expose.args, ['inside', 'dir2'])
        if have_symlinks():
            self.assertEqual(expose.folders, ['link_to_dir1'])
            self.assertEqual(expose.filenames, ['link_to_file1'])
        else:
            self.assertEqual(expose.folders, [])
            self.assertEqual(expose.filenames, [])

    def assertSameXML(self, a, b):
        self.assertEqual(a if isinstance(a, str) else a.xml(),
                         b if isinstance(b, str) else b.xml())

    def run_test_xml_for(self, base, show):
        expose = self.make_expose(base, show)
        path = pjoin(base, show).rstrip(os.path.sep)
        request = Request(env={})
        self.assertSameXML(expose.table_files(), self.expected_files[path])
        self.assertSameXML(expose.table_folders(), self.expected_folders[path])

    def test_xml_inside(self):
        self.run_test_xml_for(base='inside', show='')

    def test_xml_dir1(self):
        self.run_test_xml_for(base='inside', show='dir1')

    def test_xml_dir2(self):
        self.run_test_xml_for(base='inside', show='dir2')

    def test_file_not_found(self):
        with self.assertRaises(HTTP):
            self.make_expose(base='inside', show='dir1/file_not_found')

    def test_not_authorized(self):
        with self.assertRaises(HTTP):
            self.make_expose(base='inside', show='link_to_file3')
