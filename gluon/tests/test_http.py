#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for http.py """

import sys
import os
import unittest
if os.path.isdir('gluon'):
    sys.path.append(os.path.realpath('gluon'))
else:
    sys.path.append(os.path.realpath('../'))

from http import HTTP, defined_status


class TestHTTP(unittest.TestCase):
    """ Tests http.HTTP """

    def test_status_message(self):
        """ Tests http status code message """

        h = HTTP
        
        def gen_status_str(code, message):
            return str(code) + ' ' + str(message)
        message = 'This is a custom message'
        code = 1423
        self.assertEqual(str(h(code, status_message=message)), gen_status_str(code, message))

        # test predefined codes
        for code in defined_status.keys():
            self.assertEqual(str(h(code)), gen_status_str(code, defined_status[code]))
        
        # test correct use of status_message 
        for code in defined_status.keys():
            self.assertEqual(str(h(code, status_message=message)), gen_status_str(code, message))

        # test wrong call detection

        

        
if __name__ == '__main__':
    unittest.main()
