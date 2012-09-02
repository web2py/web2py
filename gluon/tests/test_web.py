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
from gluon.contrib.webclient import WebClient

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

if __name__ == '__main__':
    unittest.main()

