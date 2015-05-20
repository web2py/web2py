#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.globals
"""


import unittest
from fix_path import fix_sys_path

fix_sys_path(__file__)

from gluon.globals import Response
from gluon import URL


class testResponse(unittest.TestCase):

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

if __name__ == '__main__':
    unittest.main()
