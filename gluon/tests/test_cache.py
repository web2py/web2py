#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.cache
"""
import os
import unittest
from fix_path import fix_sys_path

fix_sys_path(__file__)


from storage import Storage
from cache import CacheInRam, CacheOnDisk, Cache
from gluon.dal import DAL, Field

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
    try:
        os.unlink('dummy.db')
    except:
        pass


class TestCache(unittest.TestCase):

    # TODO: test_CacheAbstract(self):

    def test_CacheInRam(self):

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
        # test singleton behaviour
        cache = CacheInRam()
        cache.clear()
        self.assertEqual(cache('a', lambda: 3, 100), 3)
        self.assertEqual(cache('a', lambda: 4, 0), 4)
        # test key deletion
        cache('a', None)
        self.assertEqual(cache('a', lambda: 5, 100), 5)
        # test increment
        self.assertEqual(cache.increment('a'), 6)
        self.assertEqual(cache('a', lambda: 1, 100), 6)
        cache.increment('b')
        self.assertEqual(cache('b', lambda: 'x', 100), 1)

    def test_CacheOnDisk(self):

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
        # test singleton behaviour
        cache = CacheOnDisk(s)
        cache.clear()
        self.assertEqual(cache('a', lambda: 3, 100), 3)
        self.assertEqual(cache('a', lambda: 4, 0), 4)
        # test key deletion
        cache('a', None)
        self.assertEqual(cache('a', lambda: 5, 100), 5)
        # test increment
        self.assertEqual(cache.increment('a'), 6)
        self.assertEqual(cache('a', lambda: 1, 100), 6)
        cache.increment('b')
        self.assertEqual(cache('b', lambda: 'x', 100), 1)

    # TODO: def test_CacheAction(self):

    # TODO: def test_Cache(self):

    # TODO: def test_lazy_cache(self):

    def test_CacheWithPrefix(self):
        s = Storage({'application': 'admin',
                     'folder': 'applications/admin'})
        cache = Cache(s)
        prefix = cache.with_prefix(cache.ram, 'prefix')
        self.assertEqual(prefix('a', lambda: 1, 0), 1)
        self.assertEqual(prefix('a', lambda: 2, 100), 1)
        self.assertEqual(cache.ram('prefixa', lambda: 2, 100), 1)

    def test_Regex(self):
        cache = CacheInRam()
        self.assertEqual(cache('a1', lambda: 1, 0), 1)
        self.assertEqual(cache('a2', lambda: 2, 100), 2)
        cache.clear(regex=r'a*')
        self.assertEqual(cache('a1', lambda: 2, 0), 2)
        self.assertEqual(cache('a2', lambda: 3, 100), 3)

    def test_DALcache(self):
        s = Storage({'application': 'admin',
                     'folder': 'applications/admin'})
        cache = Cache(s)
        db = DAL(check_reserved=['all'])
        db.define_table('t_a', Field('f_a'))
        db.t_a.insert(f_a='test')
        db.commit()
        a = db(db.t_a.id > 0).select(cache=(cache.ram, 60), cacheable=True)
        b = db(db.t_a.id > 0).select(cache=(cache.ram, 60), cacheable=True)
        self.assertEqual(a.as_csv(), b.as_csv())
        c = db(db.t_a.id > 0).select(cache=(cache.disk, 60), cacheable=True)
        d = db(db.t_a.id > 0).select(cache=(cache.disk, 60), cacheable=True)
        self.assertEqual(c.as_csv(), d.as_csv())
        self.assertEqual(a.as_csv(), c.as_csv())
        self.assertEqual(b.as_csv(), d.as_csv())
        e = db(db.t_a.id > 0).select(cache=(cache.disk, 60))
        f = db(db.t_a.id > 0).select(cache=(cache.disk, 60))
        self.assertEqual(e.as_csv(), f.as_csv())
        self.assertEqual(a.as_csv(), f.as_csv())
        g = db(db.t_a.id > 0).select(cache=(cache.ram, 60))
        h = db(db.t_a.id > 0).select(cache=(cache.ram, 60))
        self.assertEqual(g.as_csv(), h.as_csv())
        self.assertEqual(a.as_csv(), h.as_csv())
        db.t_a.drop()
        db.close()


if __name__ == '__main__':
    setUpModule()       # pre-python-2.7
    unittest.main()
    tearDownModule()
