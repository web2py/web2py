#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Unit tests for running web2py
"""
import sys
import os
if os.path.isdir('gluon'):
    sys.path.append(os.path.realpath('gluon'))
else:
    sys.path.append(os.path.realpath('../'))

import unittest
from contrib.webclient import WebClient

class TestWeb(unittest.TestCase):
    def testWebClient(self):
        client = WebClient('http://127.0.0.1:8000/welcome/default/')

        client.get('index')

        # register
        data = dict(first_name = 'Homer',
                    last_name = 'Simpson',
                    email = 'homer@web2py.com',
                    password = 'test',
                    password_two = 'test',
                    _formname = 'register')
        client.post('user/register',data = data)

        # logout
        client.get('user/logout')

        # login again
        data = dict(email='homer@web2py.com',
                    password='test',
                    _formname = 'login')
        client.post('user/login',data = data)

        # check registration and login were successful
        client.get('index')
        self.assertTrue('Welcome Homer' in client.text)

        client = WebClient('http://127.0.0.1:8000/admin/default/')
        client.post('index',data=dict(password='hello'))
        client.get('site')
        client.get('design/welcome')

class TestStaticCacheControl(unittest.TestCase):
    def testWebClient(self):
        s=WebClient('http://127.0.0.1:8000/welcome/')
        s.get('static/js/web2py.js')
        assert('expires' not in s.headers)
        assert(not s.headers['cache-control'].startswith('max-age'))
        text = s.text
        s.get('static/_1.2.3/js/web2py.js')
        assert(text == s.text)
        assert('expires' in s.headers)
        assert(s.headers['cache-control'].startswith('max-age'))

if __name__ == '__main__':
    unittest.main()

