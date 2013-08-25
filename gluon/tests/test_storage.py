#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for storage.py """

import sys
import os
import unittest


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

from storage import Storage


class TestStorage(unittest.TestCase):
    """ Tests storage.Storage """

    def test_attribute(self):
        """ Tests Storage attribute handling """

        s = Storage(a=1)

        self.assertEqual(s.a, 1)
        self.assertEqual(s['a'], 1)
        self.assertEqual(s.b, None)

        s.b = 2
        self.assertEqual(s.a, 1)
        self.assertEqual(s['a'], 1)
        self.assertEqual(s.b, 2)
        self.assertEqual(s['b'], 2)

        s['c'] = 3
        self.assertEqual(s.c, 3)
        self.assertEqual(s['c'], 3)

        s.d = list()
        self.assertTrue(s.d is s['d'])

    def test_store_none(self):
        """ Test Storage store-None handling
            s.key = None deletes an item
            s['key'] = None sets the item to None
        """

        s = Storage(a=1)

        self.assertTrue('a' in s)
        self.assertFalse('b' in s)
        s.a = None
        # self.assertFalse('a' in s) # how about this?

        s.a = 1
        self.assertTrue('a' in s)
        s['a'] = None
        self.assertTrue('a' in s)
        self.assertTrue(s.a is None)

    def test_item(self):
        """ Tests Storage item handling """

        s = Storage()

        self.assertEqual(s.d, None)
        self.assertEqual(s['d'], None)
        #self.assertRaises(KeyError, lambda x: s[x], 'd')   # old Storage
        s.a = 1
        s['a'] = None
        self.assertEquals(s.a, None)
        self.assertEquals(s['a'], None)
        self.assertTrue('a' in s)

if __name__ == '__main__':
    unittest.main()
