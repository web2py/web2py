#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for utils.py """

import unittest
from fix_path import fix_sys_path

fix_sys_path(__file__)

from utils import md5_hash
from utils import compare


class TestUtils(unittest.TestCase):
    """ Tests the utils.py module """

    def test_md5_hash(self):
        """ Tests the md5_hash function """

        data = md5_hash("web2py rocks")
        self.assertEqual(data, '79509f3246a2824dee64635303e99204')
        
    def test_compare(self):
        """ Tests the compare funciton """
        
        a, b = 'test123', 'test123'
        compare_result_true = compare(a, b)
        self.assertTrue(compare_result_true)
        
        a, b = 'test123', 'test456'
        compare_result_false = compare(a, b)
        self.assertFalse(compare_result_false)


class TestPack(unittest.TestCase):
    """ Tests the compileapp.py module """

    def test_compile(self):
        from compileapp import compile_application, remove_compiled_application
        from gluon.fileutils import w2p_pack, w2p_unpack
        import os
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
