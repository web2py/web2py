#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for http.py """

import unittest

from gluon.http import HTTP, content_disposition_header, defined_status


class TestHTTP(unittest.TestCase):
    """Tests http.HTTP"""

    def test_status_message(self):
        """Tests http status code message"""

        h = HTTP

        def gen_status_str(code, message):
            return str(code) + " " + str(message)

        message = "1423 This is a custom message"
        code = 1423
        self.assertEqual(
            str(h(gen_status_str(code, message))), gen_status_str(code, message)
        )

        # test predefined codes
        for code in defined_status.keys():
            self.assertEqual(str(h(code)), gen_status_str(code, defined_status[code]))

        # test correct use of status_message
        for code in defined_status.keys():
            self.assertEqual(
                str(h(gen_status_str(code, message))), gen_status_str(code, message)
            )

        # test wrong call detection


class TestContentDisposition(unittest.TestCase):
    """Tests http.content_disposition_header"""

    def test_content_disposition_header_encodes_admin_csv_filename(self):
        filename = 'auth_user"; filename=evil.exe.csv'

        disposition = content_disposition_header(filename)

        self.assertEqual(
            disposition,
            'attachment; filename="auth_user%22%3B%20filename%3Devil.exe.csv"',
        )
        self.assertEqual(disposition.count(";"), 1)
        self.assertNotIn("filename=evil.exe", disposition)

    def test_content_disposition_header_rejects_invalid_disposition_type(self):
        with self.assertRaises(ValueError):
            content_disposition_header("report.csv", "attachment\r\nX-Evil: yes")
        with self.assertRaises(ValueError):
            content_disposition_header("report.csv", 'attachment"; filename=evil')
