#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.recfile
"""
import unittest
import os
import shutil
import uuid


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
            with recfile.open(filename, "r") as f:
                self.assertEqual(f.read(), teststring)
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
            with recfile.open(filename, "r", path='tests') as f:
                self.assertEqual(f.read(), teststring)
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
            with recfile.open(filename, "r") as f:
                self.assertEqual(f.read(), teststring)
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
        r = recfile.open(filename, "r")
        self.assertTrue(hasattr(r, 'read'))
        r.close()
        recfile.remove(filename, path='tests')
        self.assertFalse(recfile.exists(filename))
        self.assertRaises(IOError, recfile.remove, filename)
        self.assertRaises(IOError, recfile.open, filename, "r")
