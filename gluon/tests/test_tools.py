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
if sys.version < "2.7":
    import unittest2 as unittest
else:
    import unittest

from fix_path import fix_sys_path

fix_sys_path(__file__)

DEFAULT_URI = os.getenv('DB', 'sqlite:memory')

from gluon.dal import DAL, Field
import tools
from tools import Auth, Mail, Expose
from gluon.globals import Request, Response, Session
from languages import translator
from gluon.http import HTTP
from gluon import SPAN, H3, TABLE, TR, TD, A, URL, current

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


def have_symlinks():
    return os.name == 'posix'

class TestExpose(unittest.TestCase):

    def setUp(self):
        self.base_dir = tempfile.mkdtemp()

        self.make_dirs()
        self.touch_files()
        self.make_readme()
        if have_symlinks():
            self.make_symlinks()

        self.set_expectations()
        tools.URL = lambda args: URL(a='a', c='c', f='f', args=args)

    def make_dirs(self):
        """setup direcotry strucutre"""
        for d in (['inside'],
                  ['inside', 'dir1'],
                  ['inside', 'dir2'],
                  ['outside']):
            os.mkdir(os.path.join(self.base_dir, *d))

    def touch_files(self):
        """create some files"""
        for f in (['inside', 'dir1', 'file1'],
                  ['inside', 'dir1', 'file2'],
                  ['outside', 'file3']):
            with open(os.path.join(self.base_dir, *f), 'a'):
                pass

    def make_readme(self):
        with open(os.path.join(self.base_dir, 'inside', 'README'), 'w') as f:
            f.write('README content')

    def make_symlinks(self):
        """setup extenstion for posix systems"""
        # inside links
        os.symlink(
            os.path.join(self.base_dir, 'inside', 'dir1'),
            os.path.join(self.base_dir, 'inside', 'dir2', 'link_to_dir1'))
        os.symlink(
            os.path.join(self.base_dir, 'inside', 'dir1', 'file1'),
            os.path.join(self.base_dir, 'inside', 'dir2', 'link_to_file1'))
        # outside links
        os.symlink(
            os.path.join(self.base_dir, 'outside'),
            os.path.join(self.base_dir, 'inside', 'link_to_outside'))
        os.symlink(
            os.path.join(self.base_dir, 'outside', 'file3'),
            os.path.join(self.base_dir, 'inside', 'link_to_file3'))

    def set_expectations(self):
        T = translator('', 'en')
        url = lambda args: URL('a', 'c', 'f', args=args)

        self.expected_folders = {}
        self.expected_folders['inside'] = SPAN(H3(T('Folders')), TABLE(
            TR(TD(A('dir1', _href=url(args=['dir1'])))),
            TR(TD(A('dir2', _href=url(args=['dir2'])))),
            _class='table',
        ))
        self.expected_folders['inside/dir1'] = ''
        if have_symlinks():
            self.expected_folders['inside/dir2'] = SPAN(H3(T('Folders')), TABLE(
                TR(TD(A('link_to_dir1', _href=url(args=['dir2', 'link_to_dir1'])))),
                _class='table',
            ))
        else:
            self.expected_folders['inside/dir2'] = ''

        self.expected_files = {}
        self.expected_files['inside'] = SPAN(H3(T('Files')), TABLE(
            TR(TD(A('README', _href=url(args=['README']))), TD('')),
            _class='table',
        ))
        self.expected_files['inside/dir1'] = SPAN(H3(T('Files')), TABLE(
            TR(TD(A('file1', _href=url(args=['dir1', 'file1']))), TD('')),
            TR(TD(A('file2', _href=url(args=['dir1', 'file2']))), TD('')),
            _class='table',
        ))
        if have_symlinks():
            self.expected_files['inside/dir2'] = SPAN(H3(T('Files')), TABLE(
                TR(TD(A('link_to_file1', _href=url(args=['dir2', 'link_to_file1']))), TD('')),
                _class='table',
            ))
        else:
            self.expected_files['inside/dir2'] = ''

    def tearDown(self):
        tools.URL = URL
        shutil.rmtree(self.base_dir)

    def make_expose(self, base, show=''):
        current.request = Request(env={})
        current.request.raw_args = show
        current.request.args = show.split('/')
        return Expose(base=os.path.join(self.base_dir, base),
                      basename='inside')

    def test_expose_inside_state(self):
        expose = self.make_expose(base='inside', show='')
        self.assertEqual(expose.args, [])
        self.assertEqual(expose.folders, ['dir1', 'dir2'])
        self.assertEqual(expose.filenames, ['README'])

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
        path = os.path.join(base, show).rstrip('/')
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


if __name__ == '__main__':
    unittest.main()
