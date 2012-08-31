#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Unit tests for running web2py
"""
import sys
import os
if os.path.isdir('gluon'):
    sys.path.append(os.path.realpath('gluon'))
else:
    sys.path.append(os.path.realpath('../'))

import unittest
from gluon.contrib.markmin.markmin2html import run_doctests

class TestMarkmin(unittest.TestCase):
    def testMarkmin(self):
        run_doctests()

if __name__ == '__main__':
    unittest.main()

