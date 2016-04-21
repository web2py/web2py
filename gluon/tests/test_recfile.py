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

    def test_generation(self):
        for k in range(10):
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
        for k in range(10):
            teststring = 'test%s' % k
            filename = str(uuid.uuid4()) + '.test'
            with recfile.open(filename, "w", path='tests') as g:
                g.write(teststring)
            self.assertEqual(recfile.open(filename, "r", path='tests').read(), teststring)
            is_there = recfile.exists(filename, path='tests')
            self.assertTrue(is_there)
            recfile.remove(filename, path='tests')
            is_there = recfile.exists(filename, path='tests')
            self.assertFalse(is_there)
        for k in range(10):
            teststring = 'test%s' % k
            filename = os.path.join('tests', str(uuid.uuid4()), str(uuid.uuid4()) + '.test')
            with recfile.open(filename, "w") as g:
                g.write(teststring)
            self.assertEqual(recfile.open(filename, "r").read(), teststring)
            is_there = recfile.exists(filename)
            self.assertTrue(is_there)
            recfile.remove(filename)
            is_there = recfile.exists(filename)
            self.assertFalse(is_there)

    def test_existing(self):
        filename = os.path.join('tests', str(uuid.uuid4()) + '.test')
        with open(filename, 'w') as g:
            g.write('this file exists')
        self.assertTrue(recfile.exists(filename))
        self.assertTrue(hasattr(recfile.open(filename, "r"), 'read'))
        recfile.remove(filename, path='tests')
        self.assertFalse(recfile.exists(filename))
        self.assertRaises(IOError, recfile.remove, filename)
        self.assertRaises(IOError, recfile.open, filename, "r")


if __name__ == '__main__':
    unittest.main()
