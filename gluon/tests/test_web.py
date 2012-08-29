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
        session_id_welcome = client.cookies['session_id_welcome']

        data = dict(first_name = 'Homer',
                    last_name = 'Simpson',
                    email = 'homer@web2py.com',
                    password = 'test',
                    password_two = 'test',
                    _formname = 'register')
        client.post('user/register',data = data)

        
        data = dict(email='homer@web2py.com',
                    password='test',
                    _formname = 'login')
        client.post('user/login',data = data)
        
        client.get('index')

        # check registration and login were successful
        self.assertTrue('Welcome Homer' in client.text)   

        # check we are always in the same session
        self.assertEqual(session_id_welcome,
                         client.cookies['session_id_welcome'])

if __name__ == '__main__':
    unittest.main()
