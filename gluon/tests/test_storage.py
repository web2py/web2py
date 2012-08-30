#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for storage.py """

import sys
import os
import unittest
if os.path.isdir('gluon'):
    sys.path.append(os.path.realpath('gluon'))
else:
    sys.path.append(os.path.realpath('../'))

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

