#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for http.py """

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


from http import HTTP, defined_status


class TestHTTP(unittest.TestCase):
    """ Tests http.HTTP """

    def test_status_message(self):
        """ Tests http status code message """

        h = HTTP

        def gen_status_str(code, message):
            return str(code) + ' ' + str(message)
        message = '1423 This is a custom message'
        code = 1423
        self.assertEqual(str(h(gen_status_str(code, message))),
                         gen_status_str(code, message))

        # test predefined codes
        for code in defined_status.keys():
            self.assertEqual(
                str(h(code)),
                gen_status_str(code, defined_status[code]))

        # test correct use of status_message
        for code in defined_status.keys():
            self.assertEqual(str(h(gen_status_str(code, message))),
                             gen_status_str(code, message))

        # test wrong call detection




if __name__ == '__main__':
    unittest.main()
