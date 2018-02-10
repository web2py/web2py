#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.languages
"""

import sys
import os
import shutil
import tempfile
import unittest

from gluon import languages
from gluon._compat import PY2, to_unicode, to_bytes
from gluon.storage import Messages
from gluon.html import SPAN

MP_WORKING = 0
try:
    import multiprocessing
    MP_WORKING = 1
    #due to http://bugs.python.org/issue10845, testing multiprocessing in python is impossible
    if sys.platform.startswith('win'):
        MP_WORKING = 0
    #multiprocessing is also not available on GAE. Since tests randomly
    #fail, let's not make them on it too
    if 'datastore' in os.getenv('DB', ''):
        MP_WORKING = 0
except ImportError:
    pass


def read_write(args):
    (filename, iterations) = args
    for i in range(0, iterations):
        content = languages.read_dict(filename)
        if not len(content):
            return False
        languages.write_dict(filename, content)
    return True


class TestLanguagesParallel(unittest.TestCase):

    def setUp(self):
        self.filename = tempfile.mktemp()
        contents = dict()
        for i in range(1000):
            contents["key%d" % i] = "value%d" % i
        languages.write_dict(self.filename, contents)
        languages.read_dict(self.filename)

    def tearDown(self):
        try:
            os.remove(self.filename)
        except:
            pass

    @unittest.skipIf(MP_WORKING == 0, 'multiprocessing tests unavailable')
    def test_reads_and_writes(self):
        readwriters = 10
        pool = multiprocessing.Pool(processes=readwriters)
        results = pool.map(read_write, [[self.filename, 10]] * readwriters)
        for result in results:
            self.assertTrue(result)

    @unittest.skipIf(MP_WORKING == 1, 'multiprocessing tests available')
    def test_reads_and_writes_no_mp(self):
        results = []
        for i in range(10):
            results.append(read_write([self.filename, 10]))
        for result in results:
            self.assertTrue(result)


class TestTranslations(unittest.TestCase):

    def setUp(self):
        if os.path.isdir('gluon'):
            self.langpath = 'applications/welcome/languages'
        else:
            self.langpath = os.path.realpath(
                '../../applications/welcome/languages')
        self.http_accept_language = 'en'

    def tearDown(self):
        pass

    def test_plain(self):
        T = languages.translator(self.langpath, self.http_accept_language)
        self.assertEqual(str(T('Hello World')),
                         'Hello World')
        self.assertEqual(str(T('Hello World## comment')),
                         'Hello World')
        self.assertEqual(str(T('%s %%{shop}', 1)),
                         '1 shop')
        self.assertEqual(str(T('%s %%{shop}', 2)),
                         '2 shops')
        self.assertEqual(str(T('%s %%{shop[0]}', 1)),
                         '1 shop')
        self.assertEqual(str(T('%s %%{shop[0]}', 2)),
                         '2 shops')
        self.assertEqual(str(T('%s %%{quark[0]}', 1)),
                         '1 quark')
        self.assertEqual(str(T('%s %%{quark[0]}', 2)),
                         '2 quarks')
        self.assertEqual(str(T.M('**Hello World**')),
                         '<strong>Hello World</strong>')
        T.force('it')
        self.assertEqual(str(T('Hello World')),
                         'Salve Mondo')
        self.assertEqual(to_unicode(T('Hello World')),
                         'Salve Mondo')

class TestDummyApp(unittest.TestCase):

    def setUp(self):
        pjoin = os.path.join
        self.apppath = os.path.abspath(pjoin(os.path.dirname(os.path.abspath(__file__)), 'dummy'))
        os.mkdir(self.apppath)
        os.mkdir(pjoin(self.apppath, 'languages'))
        os.mkdir(pjoin(self.apppath, 'models'))
        os.mkdir(pjoin(self.apppath, 'controllers'))
        os.mkdir(pjoin(self.apppath, 'views'))
        os.mkdir(pjoin(self.apppath, 'views', 'default'))
        os.mkdir(pjoin(self.apppath, 'modules'))
        with open(pjoin(self.apppath, 'languages', 'en.py'), 'w') as testlang:
            testlang.write(
"""
{}
"""
            )
        with open(pjoin(self.apppath, 'languages', 'pt.py'), 'w') as testlang:
            testlang.write(
"""
{}
"""
            )
        with open(pjoin(self.apppath, 'modules', 'test.py'), 'w') as testmodule:
            testmodule.write(
"""
from gluon import current

hello = current.T('hello')
"""         )
        with open(pjoin(self.apppath, 'models', 'db.py'), 'w') as testmodel:
            testmodel.write(
"""
world = T("world")
"""
            )
        with open(pjoin(self.apppath, 'controllers', 'default.py'), 'w') as testcontroller:
            testcontroller.write(
"""
def index():
    message = T('%s %%{shop}', 2)
    return dict(message=message)
"""
            )
        with open(pjoin(self.apppath, 'views', 'default', 'index.html'), 'w') as testview:
            testview.write(
"""
<html>
    <head>
    </head>
    <body>
    <h1>{{=T('ahoy')}}</h1>
    </body>
</html>
"""
            )

    def tearDown(self):
        shutil.rmtree(self.apppath)

    def test_update_all_languages(self):
        languages.update_all_languages(self.apppath)
        en_file = os.path.join(self.apppath, 'languages', 'en.py')
        pt_file = os.path.join(self.apppath, 'languages', 'pt.py')
        en_dict = languages.read_dict(en_file)
        pt_dict = languages.read_dict(pt_file)
        for key in ['hello', 'world', '%s %%{shop}', 'ahoy']:
            self.assertTrue(key in en_dict)
            self.assertTrue(key in pt_dict)

class TestMessages(unittest.TestCase):

    def setUp(self):
        if os.path.isdir('gluon'):
            self.langpath = 'applications/welcome/languages'
        else:
            self.langpath = os.path.realpath(
                '../../applications/welcome/languages')
        self.http_accept_language = 'en'

    def tearDown(self):
        pass

    def test_decode(self):
        T = languages.translator(self.langpath, self.http_accept_language)
        messages = Messages(T)
        messages.update({'email_sent':'Email sent', 'test': "ä"})
        self.assertEqual(to_unicode(messages.email_sent, 'utf-8'), 'Email sent')

class TestHTMLTag(unittest.TestCase):

    def setUp(self):
        if os.path.isdir('gluon'):
            self.langpath = 'applications/welcome/languages'
        else:
            self.langpath = os.path.realpath(
                '../../applications/welcome/languages')
        self.http_accept_language = 'en'

    def tearDown(self):
        pass

    def test_decode(self):
        T = languages.translator(self.langpath, self.http_accept_language)
        elem = SPAN(T("Complete"))
        self.assertEqual(elem.flatten(), "Complete")
        elem = SPAN(T("Cannot be empty", language="ru"))
        self.assertEqual(elem.xml(), to_bytes('<span>Пустое значение недопустимо</span>'))
        self.assertEqual(elem.flatten(), 'Пустое значение недопустимо')
