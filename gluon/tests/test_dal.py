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
        from gluon import sqlhtml
        from gluon.dal import _default_validators
        db = DAL(check_reserved=['all'])
        self.assertEqual(db.serializers, mserializers)
        self.assertEqual(db.validators_method, _default_validators)
        self.assertEqual(db.representers['rows_render'], sqlhtml.represent)
        self.assertEqual(db.representers['rows_xml'], sqlhtml.SQLTABLE)


""" TODO:
class TestDefaultValidators(unittest.TestCase):
    def testRun(self):
        pass
"""
