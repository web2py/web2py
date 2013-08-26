#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for contribs """

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


from utils import md5_hash
import contrib.fpdf as fpdf
import contrib.pyfpdf as pyfpdf


class TestContribs(unittest.TestCase):
    """ Tests the contrib package """

    def test_fpdf(self):
        """ Basic PDF test and sanity checks """

        self.assertEqual(
            fpdf.FPDF_VERSION, pyfpdf.FPDF_VERSION, 'version mistmatch')
        self.assertEqual(fpdf.FPDF, pyfpdf.FPDF, 'class mistmatch')

        pdf = fpdf.FPDF()
        pdf.add_page()
        pdf.compress = False
        pdf.set_font('Arial', '', 14)
        pdf.ln(10)
        pdf.write(5, 'hello world')
        pdf_out = pdf.output('', 'S')

        self.assertTrue(fpdf.FPDF_VERSION in pdf_out, 'version string')
        self.assertTrue('hello world' in pdf_out, 'sample message')


if __name__ == '__main__':
    unittest.main()
