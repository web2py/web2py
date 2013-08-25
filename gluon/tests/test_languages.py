#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.languages
"""

import sys
import os
import unittest
import tempfile
import threading
import logging


def fix_sys_path():
    """
    logic to have always the correct sys.path
     '', web2py/gluon, web2py/site-packages, web2py/ ...
    """

    def add_path_first(path):
        sys.path = [path] + [p for p in sys.path if (
            not p == path and not p == (path + '/'))]

    path = os.path.dirname(os.path.abspath(__file__))

    if not os.path.isfile(os.path.join(path,'web2py.py')):
        i = 0
        while i<10:
            i += 1
            if os.path.exists(os.path.join(path,'web2py.py')):
                break
            path = os.path.abspath(os.path.join(path, '..'))

    paths = [path,
             os.path.abspath(os.path.join(path, 'site-packages')),
             os.path.abspath(os.path.join(path, 'gluon')),
             '']
    [add_path_first(path) for path in paths]
fix_sys_path()


import languages
from storage import Storage

try:
    import multiprocessing

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

        def test_reads_and_writes(self):
            readwriters = 10
            pool = multiprocessing.Pool(processes=readwriters)
            results = pool.map(read_write, [[self.filename, 10]] * readwriters)
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

except ImportError:
    logging.warning("Skipped test case, no multiprocessing module.")

if __name__ == '__main__':
    unittest.main()
