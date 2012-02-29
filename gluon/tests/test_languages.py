#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.languages
"""

import sys
import os
if os.path.isdir('gluon'):
    sys.path.append(os.path.realpath('gluon'))
else:
    sys.path.append(os.path.realpath('../'))

import unittest
import languages
import tempfile
import threading
import logging

try:
    import multiprocessing

    def read_write(args):
        (filename, iterations) = args
        for i in range(0, iterations):
            content = languages.read_dict(filename)
            if not len(content):
                return False
            languages.write_dict(filename, content)
        return True

    class TestLanguagesParallel(unittest.TestCase):
    
        def setUp(self):
            self.filename = tempfile.mktemp()
            contents = dict()
            for i in range(1000):
                contents["key%d" % i] = "value%d" % i
            languages.write_dict(self.filename, contents)
            languages.read_dict(self.filename)

        def tearDown(self):
            try:
                os.remove(self.filename)
            except:
                pass
    
        def test_reads_and_writes(self):
            readwriters = 10
            pool = multiprocessing.Pool(processes = readwriters)
            results = pool.map(read_write, [[self.filename, 10]] * readwriters)
            for result in results:
                self.assertTrue(result)

except ImportError:
    logging.warning("Skipped test case, no multiprocessing module.")
        
if __name__ == '__main__':
    unittest.main()
