#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Unit tests for gluon.dal
"""

import unittest
from fix_path import fix_sys_path

fix_sys_path(__file__)


from gluon.dal import DAL


class TestDALSubclass(unittest.TestCase):
    def testRun(self):
        import gluon.serializers as mserializers
        import gluon.validators as mvalidators
        from gluon.utils import web2py_uuid
        from gluon import sqlhtml
        db = DAL(check_reserved=['all'])
        self.assertEqual(db.serializers, mserializers)
        self.assertEqual(db.validators, mvalidators)
        self.assertEqual(db.uuid, web2py_uuid)
        self.assertEqual(db.representers['rows_render'], sqlhtml.represent)
        self.assertEqual(db.representers['rows_xml'], sqlhtml.SQLTABLE)


""" TODO:
class TestDefaultValidators(unittest.TestCase):
    def testRun(self):
        pass
"""
