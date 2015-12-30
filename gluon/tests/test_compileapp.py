#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for utils.py """

import unittest
from fix_path import fix_sys_path

fix_sys_path(__file__)

from compileapp import compile_application, remove_compiled_application
from gluon.fileutils import w2p_pack, w2p_unpack
import os


class TestPack(unittest.TestCase):
    """ Tests the compileapp.py module """

    def test_compile(self):
        #apps = ['welcome', 'admin', 'examples']
        apps = ['welcome']
        for appname in apps:
            appname_path = os.path.join(os.getcwd(), 'applications', appname)
            compile_application(appname_path)
            remove_compiled_application(appname_path)
            test_path = os.path.join(os.getcwd(), "%s.w2p" % appname)
            unpack_path = os.path.join(os.getcwd(), 'unpack', appname)
            w2p_pack(test_path, appname_path, compiled=True, filenames=None)
            w2p_pack(test_path, appname_path, compiled=False, filenames=None)
            w2p_unpack(test_path, unpack_path)
        return


if __name__ == '__main__':
    unittest.main()
