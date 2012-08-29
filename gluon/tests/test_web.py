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
        session = WebClient('http://127.0.0.1:8000/welcome/default/')
        session.get('user/register')
        session_id_welcome = session.cookies['session_id_welcome']
        data = dict(first_name = 'Homer',
                    last_name = 'Simpson',
                    email = 'homer@web2py.com',
                    password = 'test',
                    password_two = 'test',
                    _formname = 'register')
        session.post('user/register',data = data)
        
        session.get('user/login')
        data = dict(email='homer@web2py.com',
                    password='test',
                    _formname = 'login')
        session.post('user/login',data = data)
        
        session.get('index')
        # check registration and login were successful
        self.assertTrue('Welcome Homer' in session.text)   
        # check we are always in the same session
        self.assertEqual(session_id_welcome,
                         session.cookies['session_id_welcome'])
        self.assertEqual('a','b')
