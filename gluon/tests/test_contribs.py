#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for contribs """

import sys
import os
import unittest
if os.path.isdir('gluon'):
    sys.path.append(os.path.realpath('gluon'))
else:
    sys.path.append(os.path.realpath('../'))

from utils import md5_hash
import contrib.fpdf as fpdf
import contrib.pyfpdf as pyfpdf


class TestContribs(unittest.TestCase):
    """ Tests the contrib package """

    def test_fpdf(self):
        """ Basic PDF test and sanity checks """

        self.assertEqual(fpdf.FPDF_VERSION, pyfpdf.FPDF_VERSION, 'version mistmatch')
        self.assertEqual(fpdf.FPDF, pyfpdf.FPDF, 'class mistmatch')

        pdf = fpdf.FPDF()
        pdf.add_page()
        pdf.compress = False
        pdf.set_font('Arial', '',14)
        pdf.ln(10)
        pdf.write(5, 'hello world')
        pdf_out = pdf.output('', 'S')

        self.assertTrue(fpdf.FPDF_VERSION in pdf_out, 'version string')
        self.assertTrue('hello world' in pdf_out, 'sample message')


if __name__ == '__main__':
    unittest.main()

