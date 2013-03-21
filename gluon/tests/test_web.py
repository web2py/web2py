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
import subprocess
import time
import signal
from contrib.webclient import WebClient

webserverprocess = None

def startwebserver():
    global webserverprocess
    webserverprocess = subprocess.Popen([sys.executable, 'web2py.py', '-a',  'testpass'])
    print 'Sleeping before web2py starts...'
    for a in range(1,11):
        time.sleep(1)
        print a, '...'
    print ''

def terminate_process(pid):
    #Taken from http://stackoverflow.com/questions/1064335/in-python-2-5-how-do-i-kill-a-subprocess
    # all this shit is because we are stuck with Python 2.5 and \
    #we cannot use Popen.terminate()
    if sys.platform.startswith('win'):
        import ctypes
        PROCESS_TERMINATE = 1
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
        ctypes.windll.kernel32.TerminateProcess(handle, -1)
        ctypes.windll.kernel32.CloseHandle(handle)
    else:
        os.kill(pid, signal.SIGKILL)

def stopwebserver():
    global webserverprocess
    print 'Killing webserver'
    if sys.version_info < (2,6):
        terminate_process(webserverprocess.pid)
    else:
        webserverprocess.terminate()


class LiveTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        startwebserver()

    @classmethod
    def tearDownClass(cls):
        stopwebserver()



class TestWeb(LiveTest):
    def testRegisterAndLogin(self):
        client = WebClient('http://127.0.0.1:8000/welcome/default/')

        client.get('index')

        # register
        data = dict(first_name='Homer',
                    last_name='Simpson',
                    email='homer@web2py.com',
                    password='test',
                    password_two='test',
                    _formname='register')
        client.post('user/register', data=data)

        # logout
        client.get('user/logout')

        # login again
        data = dict(email='homer@web2py.com',
                    password='test',
                    _formname='login')
        client.post('user/login', data=data)

        # check registration and login were successful
        client.get('index')

        self.assertTrue('Welcome Homer' in client.text)

        client = WebClient('http://127.0.0.1:8000/admin/default/')
        client.post('index', data=dict(password='hello'))
        client.get('site')
        client.get('design/welcome')

    def testStaticCache(self):
        s = WebClient('http://127.0.0.1:8000/welcome/')
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
