#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for http.py """

import unittest

from gluon.http import HTTP, content_disposition_header, defined_status, redirect


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


class TestRedirect(unittest.TestCase):
    """Tests http.redirect body escaping.

    redirect() reflects the target URL into an ``<a href="...">`` element in
    the response body. The value must be HTML-attribute encoded so an
    externally-influenced location cannot break out of the attribute and
    inject markup, while the ``Location`` header keeps the raw URL form.
    """

    def _redirect_http(self, location):
        try:
            redirect(location)
        except HTTP as e:
            return e
        self.fail("redirect did not raise HTTP")

    def test_redirect_escapes_location_in_body(self):
        # A same-origin URL that passes open-redirect validation but carries
        # attribute-breakout characters in the query string.
        payload = 'https://myhost/a?next="><script>alert(1)</script>'
        e = self._redirect_http(payload)
        # The Location header keeps the raw (URL-form) value unchanged.
        self.assertEqual(e.headers["Location"], payload)
        # The reflected body must be HTML-escaped: no attribute breakout and
        # no injected element.
        self.assertNotIn('"><script>', e.body)
        self.assertNotIn("<script>", e.body)
        self.assertIn("&quot;&gt;&lt;script&gt;", e.body)

    def test_redirect_preserves_benign_location(self):
        # A normal URL is reflected verbatim (no semantic change).
        e = self._redirect_http("/app/default/index")
        self.assertEqual(e.headers["Location"], "/app/default/index")
        self.assertIn('<a href="/app/default/index">here</a>', e.body)
