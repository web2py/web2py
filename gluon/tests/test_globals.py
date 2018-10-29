#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.globals
"""


import re
import unittest

from gluon.globals import Request, Response, Session
from gluon.rewrite import regex_url_in
from gluon import URL
from gluon._compat import basestring


def setup_clean_session():
    request = Request(env={})
    request.application = 'a'
    request.controller = 'c'
    request.function = 'f'
    request.folder = 'applications/admin'
    response = Response()
    session = Session()
    session.connect(request, response)
    from gluon.globals import current
    current.request = request
    current.response = response
    current.session = session
    return current


class testRequest(unittest.TestCase):

    def setUp(self):
        from gluon.globals import current
        current.response = Response()

    def test_restful_simple(self):
        env = {'request_method': 'GET', 'PATH_INFO': '/welcome/default/index/1.pdf'}
        r = Request(env)
        regex_url_in(r, env)

        @r.restful()
        def simple_rest():
            def GET(*args, **vars):
                return args[0]
            return locals()

        self.assertEqual(simple_rest(), '1')

    def test_restful_calls_post(self):
        env = {'request_method': 'POST', 'PATH_INFO': '/welcome/default/index'}
        r = Request(env)
        regex_url_in(r, env)

        @r.restful()
        def post_rest():
            def POST(*args, **vars):
                return 'I posted'
            return locals()

        self.assertEqual(post_rest(), 'I posted')

    def test_restful_ignore_extension(self):
        env = {'request_method': 'GET', 'PATH_INFO': '/welcome/default/index/127.0.0.1'}
        r = Request(env)
        regex_url_in(r, env)

        @r.restful(ignore_extension=True)
        def ignore_rest():
            def GET(*args, **vars):
                return args[0]
            return locals()

        self.assertEqual(ignore_rest(), '127.0.0.1')


class testResponse(unittest.TestCase):

    # port from python 2.7, needed for 2.5 and 2.6 tests
    def assertRegexpMatches(self, text, expected_regexp, msg=None):
        """Fail the test unless the text matches the regular expression."""
        if isinstance(expected_regexp, basestring):
            expected_regexp = re.compile(expected_regexp)
        if not expected_regexp.search(text):
            msg = msg or "Regexp didn't match"
            msg = '%s: %r not found in %r' % (
                msg, expected_regexp.pattern, text)
            raise self.failureException(msg)

    def test_include_files(self):

        def return_includes(response, extensions=None):
            response.include_files(extensions)
            return response.body.getvalue()

        response = Response()
        response.files.append(URL('a', 'static', 'css/file.css'))
        content = return_includes(response)
        self.assertEqual(content, '<link href="/a/static/css/file.css" rel="stylesheet" type="text/css" />')

        response = Response()
        response.files.append(URL('a', 'static', 'css/file.js'))
        content = return_includes(response)
        self.assertEqual(content, '<script src="/a/static/css/file.js" type="text/javascript"></script>')

        response = Response()
        response.files.append(URL('a', 'static', 'css/file.coffee'))
        content = return_includes(response)
        self.assertEqual(content, '<script src="/a/static/css/file.coffee" type="text/coffee"></script>')

        response = Response()
        response.files.append(URL('a', 'static', 'css/file.ts'))
        content = return_includes(response)
        self.assertEqual(content, '<script src="/a/static/css/file.ts" type="text/typescript"></script>')

        response = Response()
        response.files.append(URL('a', 'static', 'css/file.less'))
        content = return_includes(response)
        self.assertEqual(content, '<link href="/a/static/css/file.less" rel="stylesheet/less" type="text/css" />')

        response = Response()
        response.files.append(('css:inline', 'background-color; white;'))
        content = return_includes(response)
        self.assertEqual(content, '<style type="text/css">\nbackground-color; white;\n</style>')

        response = Response()
        response.files.append(('js:inline', 'alert("hello")'))
        content = return_includes(response)
        self.assertEqual(content, '<script type="text/javascript">\nalert("hello")\n</script>')

        response = Response()
        response.files.append('https://code.jquery.com/jquery-1.11.3.min.js')
        content = return_includes(response)
        self.assertEqual(content, '<script src="https://code.jquery.com/jquery-1.11.3.min.js" type="text/javascript"></script>')

        response = Response()
        response.files.append('https://code.jquery.com/jquery-1.11.3.min.js?var=0')
        content = return_includes(response)
        self.assertEqual(content, '<script src="https://code.jquery.com/jquery-1.11.3.min.js?var=0" type="text/javascript"></script>')

        response = Response()
        response.files.append('https://code.jquery.com/jquery-1.11.3.min.js?var=0')
        response.files.append('https://code.jquery.com/jquery-1.11.3.min.js?var=0')
        response.files.append(URL('a', 'static', 'css/file.css'))
        response.files.append(URL('a', 'static', 'css/file.css'))
        content = return_includes(response)
        self.assertEqual(content,
                         '<script src="https://code.jquery.com/jquery-1.11.3.min.js?var=0" type="text/javascript"></script>' +
                         '<link href="/a/static/css/file.css" rel="stylesheet" type="text/css" />')

        response = Response()
        response.files.append(('js', 'http://maps.google.com/maps/api/js?sensor=false'))
        response.files.append('https://code.jquery.com/jquery-1.11.3.min.js?var=0')
        response.files.append(URL('a', 'static', 'css/file.css'))
        response.files.append(URL('a', 'static', 'css/file.ts'))
        content = return_includes(response)
        self.assertEqual(content,
                         '<script src="http://maps.google.com/maps/api/js?sensor=false" type="text/javascript"></script>' +
                         '<script src="https://code.jquery.com/jquery-1.11.3.min.js?var=0" type="text/javascript"></script>' +
                         '<link href="/a/static/css/file.css" rel="stylesheet" type="text/css" />' +
                         '<script src="/a/static/css/file.ts" type="text/typescript"></script>'
                         )

        response = Response()
        response.files.append(URL('a', 'static', 'css/file.js'))
        response.files.append(URL('a', 'static', 'css/file.css'))
        content = return_includes(response, extensions=['css'])
        self.assertEqual(content, '<link href="/a/static/css/file.css" rel="stylesheet" type="text/css" />')

        # regr test for #628
        response = Response()
        response.files.append('http://maps.google.com/maps/api/js?sensor=false')
        content = return_includes(response)
        self.assertEqual(content, '')

        # regr test for #628
        response = Response()
        response.files.append(('js', 'http://maps.google.com/maps/api/js?sensor=false'))
        content = return_includes(response)
        self.assertEqual(content, '<script src="http://maps.google.com/maps/api/js?sensor=false" type="text/javascript"></script>')

        response = Response()
        response.files.append(['js', 'http://maps.google.com/maps/api/js?sensor=false'])
        content = return_includes(response)
        self.assertEqual(content, '<script src="http://maps.google.com/maps/api/js?sensor=false" type="text/javascript"></script>')

        response = Response()
        response.files.append(('js1', 'http://maps.google.com/maps/api/js?sensor=false'))
        content = return_includes(response)
        self.assertEqual(content, '')

    def test_cookies(self):
        current = setup_clean_session()
        cookie = str(current.response.cookies)
        session_key = '%s=%s' % (current.response.session_id_name, current.response.session_id)
        self.assertRegexpMatches(cookie, r'^Set-Cookie: ')
        self.assertTrue(session_key in cookie)
        self.assertTrue('Path=/' in cookie)

    def test_cookies_secure(self):
        current = setup_clean_session()
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue('secure' not in cookie.lower())

        current = setup_clean_session()
        current.session.secure()
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue('secure' in cookie.lower())

    def test_cookies_httponly(self):
        current = setup_clean_session()
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        # cookies in PY3 have capital letters
        self.assertTrue('httponly' in cookie.lower())

        current = setup_clean_session()
        current.session.httponly_cookies = True
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue('httponly' in cookie.lower())

        current = setup_clean_session()
        current.session.httponly_cookies = False
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue('httponly' not in cookie.lower())

    def test_cookies_samesite(self):
        # Test Lax is the default mode
        current = setup_clean_session()
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue('samesite=lax' in cookie.lower())
        # Test you can disable samesite
        current = setup_clean_session()
        current.session.samesite(False)
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue('samesite' not in cookie.lower())
        # Test you can change mode
        current = setup_clean_session()
        current.session.samesite('Strict')
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue('samesite=strict' in cookie.lower())

    def test_include_meta(self):
        response = Response()
        response.meta[u'web2py'] = 'web2py'
        response.include_meta()
        self.assertEqual(response.body.getvalue(), '\n<meta name="web2py" content="web2py" />\n')
        response = Response()
        response.meta[u'meta_dict'] = {u'tag_name':'tag_value'}
        response.include_meta()
        self.assertEqual(response.body.getvalue(), '\n<meta tag_name="tag_value" />\n')

