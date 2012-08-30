#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.cache
"""

import sys
import os
if os.path.isdir('gluon'):
    sys.path.append(os.path.realpath('gluon'))
else:
    sys.path.append(os.path.realpath('../'))

import unittest
from storage import Storage
from cache import CacheInRam, CacheOnDisk

oldcwd = None

def setUpModule():
    global oldcwd
    if oldcwd is None:
        oldcwd = os.getcwd()
        if not os.path.isdir('gluon'):
            os.chdir(os.path.realpath('../../'))

def tearDownModule():
    global oldcwd
    if oldcwd:
        os.chdir(oldcwd)
        oldcwd = None

class TestCache(unittest.TestCase):

    def testCacheInRam(self):

        # defaults to mode='http'

        cache = CacheInRam()
        self.assertEqual(cache('a', lambda: 1, 0), 1)
        self.assertEqual(cache('a', lambda: 2, 100), 1)
        cache.clear('b')
        self.assertEqual(cache('a', lambda: 2, 100), 1)
        cache.clear('a')
        self.assertEqual(cache('a', lambda: 2, 100), 2)
        cache.clear()
        self.assertEqual(cache('a', lambda: 3, 100), 3)
        self.assertEqual(cache('a', lambda: 4, 0), 4)

    def testCacheOnDisk(self):

        # defaults to mode='http'

        s = Storage({'application': 'admin',
                     'folder': 'applications/admin'})
        cache = CacheOnDisk(s)
        self.assertEqual(cache('a', lambda: 1, 0), 1)
        self.assertEqual(cache('a', lambda: 2, 100), 1)
        cache.clear('b')
        self.assertEqual(cache('a', lambda: 2, 100), 1)
        cache.clear('a')
        self.assertEqual(cache('a', lambda: 2, 100), 2)
        cache.clear()
        self.assertEqual(cache('a', lambda: 3, 100), 3)
        self.assertEqual(cache('a', lambda: 4, 0), 4)


if __name__ == '__main__':
    setUpModule()       # pre-python-2.7
    unittest.main()
    tearDownModule()


