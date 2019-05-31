#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Unit tests for gluon.dal
"""

import sys
import os
import unittest

from gluon.dal import DAL, Field


def tearDownModule():
    try:
        os.unlink('dummy.db')
    except:
        pass


class TestDALSubclass(unittest.TestCase):

    def testRun(self):
        from gluon.serializers import custom_json, xml
        from gluon import sqlhtml
        db = DAL(check_reserved=['all'])
        self.assertEqual(db.serializers['json'], custom_json)
        self.assertEqual(db.serializers['xml'], xml)
        self.assertEqual(db.representers['rows_render'], sqlhtml.represent)
        self.assertEqual(db.representers['rows_xml'], sqlhtml.SQLTABLE)
        db.close()

    def testSerialization(self):
        from gluon._compat import pickle
        db = DAL('sqlite:memory', check_reserved=['all'])
        db.define_table('t_a', Field('f_a'))
        db.t_a.insert(f_a='test')
        a = db(db.t_a.id > 0).select(cacheable=True)
        s = pickle.dumps(a)
        b = pickle.loads(s)
        self.assertEqual(a.db, b.db)
        db.t_a.drop()
        db.close()

""" TODO:
class TestDefaultValidators(unittest.TestCase):
    def testRun(self):
        pass
"""


def _prepare_exec_for_file(filename):
    module = []
    if filename.endswith('.py'):
        filename = filename[:-3]
    elif os.path.split(filename)[1] == '__init__.py':
        filename = os.path.dirname(filename)
    else:
        raise IOError('The file provided (%s) is not a valid Python file.')
    filename = os.path.realpath(filename)
    dirpath = filename
    while True:
        dirpath, extra = os.path.split(dirpath)
        module.append(extra)
        if not os.path.isfile(os.path.join(dirpath, '__init__.py')):
            break
    sys.path.insert(0, dirpath)
    return '.'.join(module[::-1])


def load_pydal_tests_module():
    path = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isfile(os.path.join(path, 'web2py.py')):
        i = 0
        while i < 10:
            i += 1
            if os.path.exists(os.path.join(path, 'web2py.py')):
                break
            path = os.path.abspath(os.path.join(path, '..'))
    pydal_test_path = os.path.join(
        path, "gluon", "packages", "dal", "tests", "__init__.py")
    mname = _prepare_exec_for_file(pydal_test_path)
    mod = __import__(mname)
    return mod


def pydal_suite():
    mod = load_pydal_tests_module()
    suite = unittest.TestSuite()
    tlist = [
        getattr(mod, el) for el in mod.__dict__.keys() if el.startswith("Test")
    ]
    for t in tlist:
        suite.addTest(unittest.makeSuite(t))
    return suite


class TestDALAdapters(unittest.TestCase):
    def _run_tests(self):
        suite = pydal_suite()
        return unittest.TextTestRunner(verbosity=2).run(suite)

    def test_mysql(self):
        if os.environ.get('APPVEYOR'):
            return
        if os.environ.get('TRAVIS'):
            os.environ["DB"] = "mysql://root:@localhost/pydal"
            result = self._run_tests()
            self.assertTrue(result)
