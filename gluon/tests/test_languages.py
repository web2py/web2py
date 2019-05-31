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
        T = languages.TranslatorFactory(self.langpath, self.http_accept_language)
        self.assertEqual(str(T('Hello World')),
                         'Hello World')
        self.assertEqual(str(T('Hello World## comment')),
                         'Hello World')
        self.assertEqual(str(T.M('**Hello World**')),
                         '<strong>Hello World</strong>')
                # sub_tuple testing
        self.assertEqual(str(T('%s %%{shop}', 1)),
                         '1 shop')
        self.assertEqual(str(T('%s %%{shop}', 2)),
                         '2 shops')
        self.assertEqual(str(T('%%{quark(%s)}', 1)),
                         'quark')
        self.assertEqual(str(T('%%{quark(%i)}', 2)),
                         'quarks')
        self.assertEqual(str(T('%%{!quark(%s)}', 1)),
                         'Quark')
        self.assertEqual(str(T('%%{!!quark(%i)}', 2)),
                         'Quarks')
        self.assertEqual(str(T('%%{!!!quark(%s)}', 0)),
                         'QUARKS')
        self.assertEqual(str(T('%%{?an?%i}', 1)),
                         'an')
        self.assertEqual(str(T('%%{?an?%s}', 0)),
                         '0')
        self.assertEqual(str(T('%%{??%i}', 1)),
                         '')
        self.assertEqual(str(T('%%{??%s}', 2)),
                         '2')
        self.assertEqual(str(T('%%{?%i}', 1)),
                         '')
        self.assertEqual(str(T('%%{?%s}', 0)),
                         '0')
        self.assertEqual(str(T('%%{?one?%i?zero}', 1)),
                         'one')
        self.assertEqual(str(T('%%{?one?%s?zero}', 23)),
                         '23')
        self.assertEqual(str(T('%%{?one?%i?zero}', 0)),
                         'zero')
        self.assertEqual(str(T('%%{?one?%s?}', 1)),
                         'one')
        self.assertEqual(str(T('%%{?one?%i?}', 23)),
                         '23')
        self.assertEqual(str(T('%%{?one?%s?}', 0)),
                         '')
        self.assertEqual(str(T('%%{??%i?zero}', 1)),
                         '')
        self.assertEqual(str(T('%%{??%s?zero}', 23)),
                         '23')
        self.assertEqual(str(T('%%{??%i?zero}', 0)),
                         'zero')
        self.assertEqual(str(T('%%{??1?}%s', '')),
                         '')
        self.assertEqual(str(T('%%{??%s?}', 23)),
                         '23')
        self.assertEqual(str(T('%%{??0?}%s', '')),
                         '')
        self.assertEqual(str(T('%s %%{shop[0]}', 1)),
                         '1 shop')
        self.assertEqual(str(T('%s %%{shop[0]}', 2)),
                         '2 shops')
        self.assertEqual(str(T('%i %%{?one?not_one[0]}', 1)),
                         '1 one')
        self.assertEqual(str(T('%i %%{?one?not_one[0]}', 2)),
                         '2 not_one')
        self.assertEqual(str(T('%%{??on[0]} %i', 1)),
                         ' 1')
        self.assertEqual(str(T('%%{??on[0]} %s', 0)),
                         'on 0')
        self.assertEqual(str(T('%%{?on[0]} %s', 1)),
                         ' 1')
        self.assertEqual(str(T('%%{?on[0]} %i', 2)),
                         'on 2')
        self.assertEqual(str(T('%i %%{?one?or_more?zero[0]}', 1)),
                         '1 one')
        self.assertEqual(str(T('%i %%{?one?or_more?zero[0]}', 2)),
                         '2 or_more')
        self.assertEqual(str(T('%i %%{?one?or_more?zero[0]}', 0)),
                         '0 zero')
        self.assertEqual(str(T('%i %%{?one?hands?[0]}', 1)),
                         '1 one')
        self.assertEqual(str(T('%s %%{?one?hands?[0]}', 2)),
                         '2 hands')
        self.assertEqual(str(T('%i %%{?one?hands?[0]}', 0)),
                         '0 ')
        self.assertEqual(str(T('%s %%{??or_more?zero[0]}', 1)),
                         '1 ')
        self.assertEqual(str(T('%i %%{??or_more?zero[0]}', 2)),
                         '2 or_more')
        self.assertEqual(str(T('%s %%{??or_more?zero[0]}', 0)),
                         '0 zero')
        self.assertEqual(str(T('%i%%{??nd?[0]}', 1)),
                         '1')
        self.assertEqual(str(T('%i%%{??nd?[0]}', 2)),
                         '2nd')
        self.assertEqual(str(T('%i%%{??nd?[0]}', 0)),
                         '0')
        self.assertEqual(str(T('%i%%{?st?[0]}', 1)),
                         '1st')
        self.assertEqual(str(T('%i%%{?st?[0]}', 2)),
                         '2')
        self.assertEqual(str(T('%i%%{?st?[0]}', 0)),
                         '0')
                # sub_dict testing
        self.assertEqual(str(T('%(key)s %%{is(key)}', dict(key=1))),
                         '1 is')
        self.assertEqual(str(T('%(key)i %%{is(key)}', dict(key=2))),
                         '2 are')
        self.assertEqual(str(T('%%{!!!is(%(key)s)}', dict(key=2))),
                         'ARE')
        self.assertEqual(str(T('%(key)i %%{?not_one(key)}', dict(key=1))),
                         '1 ')
        self.assertEqual(str(T('%(key)s %%{?not_one(key)}', dict(key=2))),
                         '2 not_one')
        self.assertEqual(str(T('%(key)i %%{?not_one(key)}', dict(key=0))),
                         '0 not_one')
        self.assertEqual(str(T('%(key)s %%{?one?not_one(key)}', dict(key=1))),
                         '1 one')
        self.assertEqual(str(T('%(key)i %%{?one?not_one(key)}', dict(key=2))),
                         '2 not_one')
        self.assertEqual(str(T('%(key)s %%{?one?not_one(key)}', dict(key=0))),
                         '0 not_one')
        self.assertEqual(str(T('%(key)i %%{?one?(key)}', dict(key=1))),
                         '1 one')
        self.assertEqual(str(T('%(key)s %%{?one?(key)}', dict(key=2))),
                         '2 ')
        self.assertEqual(str(T('%(key)i %%{?one?(key)}', dict(key=0))),
                         '0 ')
        self.assertEqual(str(T('%(key)s %%{??not_one(key)}', dict(key=1))),
                         '1 ')
        self.assertEqual(str(T('%(key)i %%{??not_one(key)}', dict(key=2))),
                         '2 not_one')
        self.assertEqual(str(T('%(key)s %%{?not_one(key)}', dict(key=1))),
                         '1 ')
        self.assertEqual(str(T('%(key)i %%{?not_one(key)}', dict(key=0))),
                         '0 not_one')
        self.assertEqual(str(T('%(key)s %%{?one?other?zero(key)}', dict(key=1))),
                         '1 one')
        self.assertEqual(str(T('%(key)i %%{?one?other?zero(key)}', dict(key=4))),
                         '4 other')
        self.assertEqual(str(T('%(key)s %%{?one?other?zero(key)}', dict(key=0))),
                         '0 zero')
        self.assertEqual(str(T('%(key)i %%{?one?two_or_more?(key)}', dict(key=1))),
                         '1 one')
        self.assertEqual(str(T('%(key)s %%{?one?two_or_more?(key)}', dict(key=2))),
                         '2 two_or_more')
        self.assertEqual(str(T('%(key)i %%{?one?two_or_more?(key)}', dict(key=0))),
                         '0 ')
        self.assertEqual(str(T('%(key)s %%{??two_or_more?zero(key)}', dict(key=1))),
                         '1 ')
        self.assertEqual(str(T('%(key)i %%{??two_or_more?zero(key)}', dict(key=2))),
                         '2 two_or_more')
        self.assertEqual(str(T('%(key)s %%{??two_or_more?zero(key)}', dict(key=0))),
                         '0 zero')
        self.assertEqual(str(T('%(key)i %%{??two_or_more?(key)}', dict(key=1))),
                         '1 ')
        self.assertEqual(str(T('%(key)s %%{??two_or_more?(key)}', dict(key=0))),
                         '0 ')
        self.assertEqual(str(T('%(key)i %%{??two_or_more?(key)}', dict(key=2))),
                         '2 two_or_more')
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
        T = languages.TranslatorFactory(self.langpath, self.http_accept_language)
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
        T = languages.TranslatorFactory(self.langpath, self.http_accept_language)
        elem = SPAN(T("Complete"))
        self.assertEqual(elem.flatten(), "Complete")
        elem = SPAN(T("Cannot be empty", language="ru"))
        self.assertEqual(elem.xml(), to_bytes('<span>Пустое значение недопустимо</span>'))
        self.assertEqual(elem.flatten(), 'Пустое значение недопустимо')
