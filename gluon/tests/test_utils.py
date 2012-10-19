#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for utils.py """

import sys
import os
import unittest
if os.path.isdir('gluon'):
    sys.path.append(os.path.realpath('gluon'))
else:
    sys.path.append(os.path.realpath('../'))

from utils import md5_hash


class TestUtils(unittest.TestCase):
    """ Tests the utils.py module """

    def test_md5_hash(self):
        """ Tests the md5_hash function """

        data = md5_hash("web2py rocks")
        self.assertEqual(data, '79509f3246a2824dee64635303e99204')

if __name__ == '__main__':
    unittest.main()
