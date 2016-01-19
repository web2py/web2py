#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.globals
"""


import re
import unittest
from fix_path import fix_sys_path

fix_sys_path(__file__)

from gluon.globals import Request, Response, Session
from gluon import URL

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

class testResponse(unittest.TestCase):

    #port from python 2.7, needed for 2.5 and 2.6 tests
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
            '<script src="https://code.jquery.com/jquery-1.11.3.min.js?var=0" type="text/javascript"></script>' +
            '<link href="/a/static/css/file.css" rel="stylesheet" type="text/css" />' +
            '<script src="/a/static/css/file.ts" type="text/typescript"></script>' +
            '<script src="http://maps.google.com/maps/api/js?sensor=false" type="text/javascript"></script>'
        )


        response = Response()
        response.files.append(URL('a', 'static', 'css/file.js'))
        response.files.append(URL('a', 'static', 'css/file.css'))
        content = return_includes(response, extensions=['css'])
        self.assertEqual(content, '<link href="/a/static/css/file.css" rel="stylesheet" type="text/css" />')

        #regr test for #628
        response = Response()
        response.files.append('http://maps.google.com/maps/api/js?sensor=false')
        content = return_includes(response)
        self.assertEqual(content, '')

        #regr test for #628
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
        session_key='%s=%s'%(current.response.session_id_name,current.response.session_id)
        self.assertRegexpMatches(cookie, r'^Set-Cookie: ')
        self.assertTrue(session_key in cookie)
        self.assertTrue('Path=/' in cookie)

    def test_cookies_secure(self):
        current = setup_clean_session()
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue('secure' not in cookie)

        current = setup_clean_session()
        current.session.secure()
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue('secure' in cookie)

    def test_cookies_httponly(self):
        current = setup_clean_session()
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue('httponly' in cookie)

        current = setup_clean_session()
        current.session.httponly_cookies = True
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue('httponly' in cookie)

        current = setup_clean_session()
        current.session.httponly_cookies = False
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue('httponly' not in cookie)

if __name__ == '__main__':
    unittest.main()
