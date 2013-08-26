#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Unit tests for gluon.template
"""

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

from template import render


class TestVirtualFields(unittest.TestCase):

    def testRun(self):
        self.assertEqual(render(content='{{for i in range(n):}}{{=i}}{{pass}}',
                                context=dict(n=3)), '012')
        self.assertEqual(render(content='{{if n>2:}}ok{{pass}}',
                                context=dict(n=3)), 'ok')
        self.assertEqual(
            render(content='{{try:}}{{n/0}}{{except:}}fail{{pass}}',
                   context=dict(n=3)), 'fail')
        self.assertEqual(render(content='{{="<&>"}}'), '&lt;&amp;&gt;')
        self.assertEqual(render(content='"abc"'), '"abc"')
        self.assertEqual(render(content='"a\'bc"'), '"a\'bc"')
        self.assertEqual(render(content='"a\"bc"'), '"a\"bc"')
        self.assertEqual(render(content=r'''"a\"bc"'''), r'"a\"bc"')
        self.assertEqual(render(content=r'''"""abc\""""'''), r'"""abc\""""')

    def testEqualWrite(self):
        "test generation of response.write from ="
        self.assertEqual(render(content='{{="abc"}}'), 'abc')
        # whitespace is stripped
        self.assertEqual(render(content='{{ ="abc"}}'), 'abc')
        self.assertEqual(render(content='{{ ="abc" }}'), 'abc')
        self.assertEqual(render(content='{{pass\n="abc" }}'), 'abc')
        # = recognized only at the beginning of a physical line
        self.assertEqual(render(
            content='{{xyz = "xyz"\n="abc"\n="def"\n=xyz }}'), 'abcdefxyz')
        # = in python blocks
        self.assertEqual(render(content='{{if True:\n="abc"\npass }}'), 'abc')
        self.assertEqual(
            render(content='{{if True:\n="abc"\npass\n="def" }}'), 'abcdef')
        self.assertEqual(
            render(content='{{if False:\n="abc"\npass\n="def" }}'), 'def')
        self.assertEqual(render(
            content='{{if True:\n="abc"\nelse:\n="def"\npass }}'), 'abc')
        self.assertEqual(render(
            content='{{if False:\n="abc"\nelse:\n="def"\npass }}'), 'def')
        # codeblock-leading = handles internal newlines, escaped or not
        self.assertEqual(render(content='{{=list((1,2,3))}}'), '[1, 2, 3]')
        self.assertEqual(render(content='{{=list((1,2,\\\n3))}}'), '[1, 2, 3]')
        self.assertEqual(render(content='{{=list((1,2,\n3))}}'), '[1, 2, 3]')
        # ...but that means no more = operators in the codeblock
        self.assertRaises(SyntaxError, render, content='{{="abc"\n="def" }}')
        # = embedded in codeblock won't handle newlines in its argument
        self.assertEqual(
            render(content='{{pass\n=list((1,2,\\\n3))}}'), '[1, 2, 3]')
        self.assertRaises(
            SyntaxError, render, content='{{pass\n=list((1,2,\n3))}}')


if __name__ == '__main__':
    unittest.main()
