#!/bin/python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.html
"""

import sys
import os
if os.path.isdir('gluon'):
    sys.path.append(os.path.realpath('gluon'))
else:
    sys.path.append(os.path.realpath('../'))

import unittest
from html import *


class TestBareHelpers(unittest.TestCase):

    def testRun(self):
        self.assertEqual(BR(_a='1', _b='2').xml(), '<br a="1" b="2" />')
        self.assertEqual(EMBED(_a='1', _b='2').xml(),
                         '<embed a="1" b="2" />')
        self.assertEqual(HR(_a='1', _b='2').xml(), '<hr a="1" b="2" />')
        self.assertEqual(IMG(_a='1', _b='2').xml(),
                         '<img a="1" b="2" />')
        self.assertEqual(INPUT(_a='1', _b='2').xml(),
                         '<input a="1" b="2" type="text" />')
        self.assertEqual(LINK(_a='1', _b='2').xml(),
                         '<link a="1" b="2" />')
        self.assertEqual(META(_a='1', _b='2').xml(),
                         '<meta a="1" b="2" />')

        self.assertEqual(A('<>', _a='1', _b='2').xml(),
                         '<a a="1" b="2">&lt;&gt;</a>')
        self.assertEqual(B('<>', _a='1', _b='2').xml(),
                         '<b a="1" b="2">&lt;&gt;</b>')
        self.assertEqual(BODY('<>', _a='1', _b='2').xml(),
                         '<body a="1" b="2">&lt;&gt;</body>')
        self.assertEqual(CENTER('<>', _a='1', _b='2').xml(),
                         '<center a="1" b="2">&lt;&gt;</center>')
        self.assertEqual(DIV('<>', _a='1', _b='2').xml(),
                         '<div a="1" b="2">&lt;&gt;</div>')
        self.assertEqual(EM('<>', _a='1', _b='2').xml(),
                         '<em a="1" b="2">&lt;&gt;</em>')
        self.assertEqual(FIELDSET('<>', _a='1', _b='2').xml(),
                         '<fieldset a="1" b="2">&lt;&gt;</fieldset>')
        self.assertEqual(FORM('<>', _a='1', _b='2').xml(),
                         '<form a="1" action="" b="2" enctype="multipart/form-data" method="post">&lt;&gt;</form>')
        self.assertEqual(H1('<>', _a='1', _b='2').xml(),
                         '<h1 a="1" b="2">&lt;&gt;</h1>')
        self.assertEqual(H2('<>', _a='1', _b='2').xml(),
                         '<h2 a="1" b="2">&lt;&gt;</h2>')
        self.assertEqual(H3('<>', _a='1', _b='2').xml(),
                         '<h3 a="1" b="2">&lt;&gt;</h3>')
        self.assertEqual(H4('<>', _a='1', _b='2').xml(),
                         '<h4 a="1" b="2">&lt;&gt;</h4>')
        self.assertEqual(H5('<>', _a='1', _b='2').xml(),
                         '<h5 a="1" b="2">&lt;&gt;</h5>')
        self.assertEqual(H6('<>', _a='1', _b='2').xml(),
                         '<h6 a="1" b="2">&lt;&gt;</h6>')
        self.assertEqual(HEAD('<>', _a='1', _b='2').xml(),
                         '<head a="1" b="2">&lt;&gt;</head>')
        self.assertEqual(HTML('<>', _a='1', _b='2').xml(),
                         '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">\n<html a="1" b="2" lang="en">&lt;&gt;</html>')
        self.assertEqual(IFRAME('<>', _a='1', _b='2').xml(),
                         '<iframe a="1" b="2">&lt;&gt;</iframe>')
        self.assertEqual(LABEL('<>', _a='1', _b='2').xml(),
                         '<label a="1" b="2">&lt;&gt;</label>')
        self.assertEqual(LI('<>', _a='1', _b='2').xml(),
                         '<li a="1" b="2">&lt;&gt;</li>')
        self.assertEqual(OBJECT('<>', _a='1', _b='2').xml(),
                         '<object a="1" b="2">&lt;&gt;</object>')
        self.assertEqual(OL('<>', _a='1', _b='2').xml(),
                         '<ol a="1" b="2"><li>&lt;&gt;</li></ol>')
        self.assertEqual(OPTION('<>', _a='1', _b='2').xml(),
                         '<option a="1" b="2" value="&lt;&gt;">&lt;&gt;' + \
                         '</option>')
        self.assertEqual(P('<>', _a='1', _b='2').xml(),
                         '<p a="1" b="2">&lt;&gt;</p>')
        self.assertEqual(PRE('<>', _a='1', _b='2').xml(),
                         '<pre a="1" b="2">&lt;&gt;</pre>')
        self.assertEqual(SCRIPT('<>', _a='1', _b='2').xml(),
                         '''<script a="1" b="2"><!--
<>
//--></script>''')
        self.assertEqual(SELECT('<>', _a='1', _b='2').xml(),
                         '<select a="1" b="2">'+ \
                         '<option value="&lt;&gt;">&lt;&gt;</option></select>')
        self.assertEqual(SPAN('<>', _a='1', _b='2').xml(),
                         '<span a="1" b="2">&lt;&gt;</span>')
        self.assertEqual(STYLE('<>', _a='1', _b='2').xml(),
                         '<style a="1" b="2"><!--/*--><![CDATA[/*><!--*/\n<>\n/*]]>*/--></style>')
        self.assertEqual(TABLE('<>', _a='1', _b='2').xml(),
                         '<table a="1" b="2"><tr><td>&lt;&gt;</td></tr>' + \
                         '</table>')
        self.assertEqual(TBODY('<>', _a='1', _b='2').xml(),
                         '<tbody a="1" b="2"><tr><td>&lt;&gt;</td></tr></tbody>')
        self.assertEqual(TD('<>', _a='1', _b='2').xml(),
                         '<td a="1" b="2">&lt;&gt;</td>')
        self.assertEqual(TEXTAREA('<>', _a='1', _b='2').xml(),
                        '<textarea a="1" b="2" cols="40" rows="10">&lt;&gt;' + \
                        '</textarea>')
        self.assertEqual(TFOOT('<>', _a='1', _b='2').xml(),
                         '<tfoot a="1" b="2"><tr><td>&lt;&gt;</td></tr></tfoot>')
        self.assertEqual(TH('<>', _a='1', _b='2').xml(),
                         '<th a="1" b="2">&lt;&gt;</th>')
        self.assertEqual(THEAD('<>', _a='1', _b='2').xml(),
                         '<thead a="1" b="2"><tr><td>&lt;&gt;</td></tr></thead>')
        self.assertEqual(TITLE('<>', _a='1', _b='2').xml(),
                         '<title a="1" b="2">&lt;&gt;</title>')
        self.assertEqual(TR('<>', _a='1', _b='2').xml(),
                         '<tr a="1" b="2"><td>&lt;&gt;</td></tr>')
        self.assertEqual(TT('<>', _a='1', _b='2').xml(),
                         '<tt a="1" b="2">&lt;&gt;</tt>')
        self.assertEqual(UL('<>', _a='1', _b='2').xml(),
                         '<ul a="1" b="2"><li>&lt;&gt;</li></ul>')


if __name__ == '__main__':
    unittest.main()
