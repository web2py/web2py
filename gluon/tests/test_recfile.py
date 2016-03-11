#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.recfile
"""
import unittest
import os
import shutil
import uuid
from fix_path import fix_sys_path

fix_sys_path(__file__)

from gluon import recfile


class TestRecfile(unittest.TestCase):

    def setUp(self):
        os.mkdir('tests')

    def tearDown(self):
        shutil.rmtree('tests')

    def testgeneration(self):
        for k in range(20):
            teststring = 'test%s' % k
            filename = os.path.join('tests', str(uuid.uuid4()) + '.test')
            with recfile.open(filename, "w") as g:
                g.write(teststring)
            self.assertEqual(recfile.open(filename, "r").read(), teststring)
            is_there = recfile.exists(filename)
            self.assertTrue(is_there)
            recfile.remove(filename)
            is_there = recfile.exists(filename)
            self.assertFalse(is_there)

if __name__ == '__main__':
    unittest.main()
