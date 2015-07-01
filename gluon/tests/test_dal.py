#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Unit tests for gluon.dal
"""

import os
import unittest
from fix_path import fix_sys_path

fix_sys_path(__file__)


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
        import pickle
        db = DAL(check_reserved=['all'])
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

if __name__ == '__main__':
    unittest.main()
    tearDownModule()
