#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for old doctests in validators.py, utf8.py, html.py,
    markmin2html.py.
    Don't abuse doctests, web2py > 2.4.5 will accept only unittests
"""
import sys
import os
import unittest
import doctest


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

def load_tests(loader, tests, ignore):

    
    tests.addTests(
        doctest.DocTestSuite('html')
        )
    tests.addTests(
        doctest.DocTestSuite('utf8')
        )

    tests.addTests(
        doctest.DocTestSuite('contrib.markmin.markmin2html',
        )
    )

    return tests

if __name__ == '__main__':
    unittest.main()
