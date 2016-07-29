#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for utils.py """

import unittest
import os
import threading
import time


from .fix_path import fix_sys_path

fix_sys_path(__file__)

from gluon.portalocker import lock, unlock, read_locked, write_locked
from gluon.portalocker import LockedFile, LOCK_EX
from gluon._compat import to_bytes


def tearDownModule():
    if os.path.isfile('test.txt'):
        os.unlink('test.txt')

class testPortalocker(unittest.TestCase):

    def test_LockedFile(self):
        f = LockedFile('test.txt', mode='wb')
        f.write(to_bytes('test ok'))
        f.close()
        f = LockedFile('test.txt', mode='rb')
        self.assertEqual(f.read(), to_bytes('test ok'))
        f.close()

    def test_openmultiple(self):

        def worker1():
            start = int(time.time())
            f1 = LockedFile('test.txt', mode='ab')
            time.sleep(2)
            f1.write(to_bytes("%s\t%s\n" % (start, int(time.time()))))
            f1.close()

        f = LockedFile('test.txt', mode='wb')
        f.write(to_bytes(''))
        f.close()
        th = []
        for x in range(10):
            t1 = threading.Thread(target=worker1)
            th.append(t1)
            t1.start()
        for t in th:
            t.join()
        with open('test.txt') as g:
            content = g.read()

        results = [line.strip().split('\t') for line in content.split('\n') if line]
        # all started at the same time
        starts = [line[0] for line in results]
        ends = [line[1] for line in results]
        self.assertEqual(len(set(starts)), 1)
        # end - start is at least 2
        for line in results:
            self.assertTrue(int(line[1]) - int(line[0]) >= 2)
        # ends are not the same
        self.assertTrue(len(set(ends)) == len(ends))

    def test_lock_unlock(self):

        def worker1(fh):
            time.sleep(2)
            unlock(fh)

        def worker2(fh):
            time.sleep(2)
            fh.close()

        f = open('test.txt', mode='wb')
        lock(f, LOCK_EX)
        f.write(to_bytes('test ok'))
        t1 = threading.Thread(target=worker1, args=(f, ))
        t1.start()
        start = int(time.time())
        content = read_locked('test.txt')
        end = int(time.time())
        t1.join()
        f.close()
        # it took at least 2 seconds to read
        # although nothing is there until .close()
        self.assertTrue(end - start >= 2)
        self.assertEqual(content, to_bytes(''))
        content = read_locked('test.txt')
        self.assertEqual(content, to_bytes('test ok'))

        f = LockedFile('test.txt', mode='wb')
        f.write(to_bytes('test ok'))
        t1 = threading.Thread(target=worker2, args=(f, ))
        t1.start()
        start = int(time.time())
        content = read_locked('test.txt')
        end = int(time.time())
        t1.join()
        # it took at least 2 seconds to read
        # content is there because we called close()
        self.assertTrue(end - start >= 2)
        self.assertEqual(content, to_bytes('test ok'))


    def test_read_locked(self):

        def worker(fh):
            time.sleep(2)
            fh.close()

        f = LockedFile('test.txt', mode='wb')
        f.write(to_bytes('test ok'))
        t1 = threading.Thread(target=worker, args=(f, ))
        t1.start()
        start = int(time.time())
        content = read_locked('test.txt')
        end = int(time.time())
        t1.join()
        # it took at least 2 seconds to read
        self.assertTrue(end - start >= 2)
        self.assertEqual(content, to_bytes('test ok'))

    def test_write_locked(self):

        def worker(fh):
            time.sleep(2)
            fh.close()

        f = open('test.txt', mode='wb')
        lock(f, LOCK_EX)
        t1 = threading.Thread(target=worker, args=(f, ))
        t1.start()
        start = int(time.time())
        write_locked('test.txt', to_bytes('test ok'))
        end = int(time.time())
        t1.join()
        with open('test.txt') as g:
            content = g.read()
        # it took at least 2 seconds to read
        self.assertTrue(end - start >= 2)
        self.assertEqual(content, 'test ok')

    def test_exception(self):
        self.assertRaises(RuntimeError, LockedFile, *['test.txt', 'x'])

    def test_readline(self):
        f = LockedFile('test.txt', 'wb')
        f.write(to_bytes('abc\n'))
        f.write(to_bytes('123\n'))
        f.close()
        f = LockedFile('test.txt', 'rb')
        rl = f.readline()
        self.assertTrue(to_bytes('abc') in rl)
        rl = f.readline()
        self.assertTrue(to_bytes('123') in rl)
        f.close()
        f = LockedFile('test.txt', 'rb')
        rls = f.readlines()
        f.close()
        self.assertEqual(len(rls), 2)



if __name__ == '__main__':
    unittest.main()
