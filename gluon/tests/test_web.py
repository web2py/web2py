# -*- coding: utf-8 -*-
"""
    Unit tests for running web2py
"""

from __future__ import print_function

import sys
import os
import unittest
import subprocess
import time
import shutil

from gluon.contrib.webclient import WebClient
from gluon._compat import urllib2, PY2
from gluon.fileutils import create_app

test_app_name = '_test_web'

webserverprocess = None

def startwebserver():
    global webserverprocess
    path = path = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isfile(os.path.join(path, 'web2py.py')):
        i = 0
        while i < 10:
            i += 1
            if os.path.exists(os.path.join(path, 'web2py.py')):
                break
            path = os.path.abspath(os.path.join(path, '..'))
    web2py_exec = os.path.join(path, 'web2py.py')
    webserverprocess = subprocess.Popen([sys.executable, web2py_exec, '-a', 'testpass'])
    print('Sleeping before web2py starts...')
    for a in range(1, 11):
        time.sleep(1)
        print("%d..." % a)
        try:
            c = WebClient('http://127.0.0.1:8000/')
            c.get(test_app_name)
            break
        except:
            continue
    print('')


def stopwebserver():
    global webserverprocess
    print('Killing webserver')
    webserverprocess.terminate()


class Cookie(unittest.TestCase):
    def testParseMultipleEquals(self):
        """ Test for issue #1500.
        Ensure that a cookie containing one or more '=' is correctly parsed
        """
        client = WebClient()
        client.headers['set-cookie'] = "key = value with one =;"
        client._parse_headers_in_cookies()
        self.assertIn("key", client.cookies)
        self.assertEqual(client.cookies['key'], "value with one =")

        client.headers['set-cookie'] = "key = value with one = and another one =;"
        client._parse_headers_in_cookies()
        client._parse_headers_in_cookies()
        self.assertIn("key", client.cookies)
        self.assertEqual(client.cookies['key'], "value with one = and another one =")


class LiveTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        appdir = os.path.join('applications', test_app_name)
        if not os.path.exists(appdir):
            os.mkdir(appdir)
            create_app(appdir)
        startwebserver()

    @classmethod
    def tearDownClass(cls):
        stopwebserver()
        appdir = os.path.join('applications', test_app_name)
        if os.path.exists(appdir):
            shutil.rmtree(appdir)


@unittest.skipIf("datastore" in os.getenv("DB", ""), "TODO: setup web test for app engine")
class TestWeb(LiveTest):
    def testRegisterAndLogin(self):
        client = WebClient("http://127.0.0.1:8000/%s/default/" % test_app_name)

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
        self.assertIn('Homer', client.text)

        # check registration and login were successful
        client.get('index')

        self.assertIn('Homer', client.text)

        client = WebClient('http://127.0.0.1:8000/admin/default/')
        client.post('index', data=dict(password='testpass'))
        client.get('site')
        client.get('design/' + test_app_name)

    def testStaticCache(self):
        s = WebClient("http://127.0.0.1:8000/%s/" % test_app_name)
        s.get('static/js/web2py.js')
        self.assertNotIn('expires', s.headers)
        self.assertFalse(s.headers['cache-control'].startswith('max-age'))
        text = s.text
        s.get('static/_1.2.3/js/web2py.js')
        self.assertEqual(text, s.text)
        self.assertIn('expires', s.headers)
        self.assertTrue(s.headers['cache-control'].startswith('max-age'))

    @unittest.skipIf(not(PY2), 'skip PY3 testSoap')
    def testSoap(self):
        # test soap server implementation
        from gluon.contrib.pysimplesoap.client import SoapClient, SoapFault
        url = 'http://127.0.0.1:8000/examples/soap_examples/call/soap?WSDL'
        client = SoapClient(wsdl=url)
        ret = client.SubIntegers(a=3, b=2)
        # check that the value returned is ok
        self.assertIn('SubResult', ret)
        self.assertEqual(ret['SubResult'], 1)

        try:
            ret = client.Division(a=3, b=0)
        except SoapFault as sf:
            # verify the exception value is ok
            # self.assertEqual(sf.faultstring, "float division by zero") # true only in 2.7
            self.assertEqual(sf.faultcode, "Server.ZeroDivisionError")

        # store sent and received xml for low level test
        xml_request = client.xml_request
        xml_response = client.xml_response

        # do a low level raw soap request (using
        s = WebClient('http://127.0.0.1:8000/')
        try:
            s.post('examples/soap_examples/call/soap', data=xml_request, method="POST")
        except urllib2.HTTPError as e:
            self.assertEqual(e.msg, 'INTERNAL SERVER ERROR')
        # check internal server error returned (issue 153)
        self.assertEqual(s.status, 500)
        self.assertEqual(s.text, xml_response)
