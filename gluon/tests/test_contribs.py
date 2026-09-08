#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for contribs """

import os
import unittest

from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request

from gluon import HTTP, current
from gluon.contrib.generics import (_pdf_same_origin, _SameHostRedirect,
                                    _resolve_pdf_image_path, pdf_from_html,
                                    pyfpdf_from_html)
from gluon.contrib import fpdf as fpdf
from gluon.contrib import pyfpdf as pyfpdf
from gluon.contrib.appconfig import AppConfig
from gluon.storage import Storage


def setUpModule():
    pass


def tearDownModule():
    if os.path.isfile("appconfig.json"):
        os.unlink("appconfig.json")


class TestContribs(unittest.TestCase):
    """Tests the contrib package"""

    def test_fpdf(self):
        """Basic PDF test and sanity checks"""

        self.assertEqual(fpdf.FPDF_VERSION, pyfpdf.FPDF_VERSION, "version mistmatch")
        self.assertEqual(fpdf.FPDF, pyfpdf.FPDF, "class mistmatch")

        pdf = fpdf.FPDF()
        pdf.add_page()
        pdf.compress = False
        pdf.set_font("Arial", "", 14)
        pdf.ln(10)
        pdf.write(5, "hello world")
        pdf_out = pdf.output("", "S")

        self.assertTrue(fpdf.FPDF_VERSION.encode("utf8") in pdf_out, "version string")
        self.assertTrue(b"hello world" in pdf_out, "sample message")

    def test_appconfig(self):
        """
        Test for the appconfig module
        """
        from gluon import current

        s = Storage({"application": "admin", "folder": "applications/admin"})
        current.request = s
        simple_config = '{"config1" : "abc", "config2" : "bcd", "config3" : { "key1" : 1, "key2" : 2} }'
        with open("appconfig.json", "w") as g:
            g.write(simple_config)
        myappconfig = AppConfig("appconfig.json")
        self.assertEqual(myappconfig["config1"], "abc")
        self.assertEqual(myappconfig["config2"], "bcd")
        self.assertEqual(myappconfig.take("config1"), "abc")
        self.assertEqual(myappconfig.take("config3.key1", cast=str), "1")
        # once parsed, can't be casted to other types
        self.assertEqual(myappconfig.take("config3.key1", cast=int), "1")

        self.assertEqual(myappconfig.take("config3.key2"), 2)

        current.request = {}

    def test_pdf_image_map_allows_static_subpath(self):
        request = Storage(
            {
                "application": "welcome",
                "folder": os.path.join("applications", "welcome"),
                "is_https": False,
                "env": Storage({"http_host": "example.com"}),
            }
        )
        result = _resolve_pdf_image_path("/welcome/static/img/logo.png", request)
        expected_suffix = os.path.normpath(
            os.path.join("applications", "welcome", "static", "img", "logo.png")
        )
        self.assertTrue(result.endswith(expected_suffix), result)

    def test_pdf_image_map_rejects_static_traversal(self):
        request = Storage(
            {
                "application": "welcome",
                "folder": os.path.join("applications", "welcome"),
                "is_https": False,
                "env": Storage({"http_host": "example.com"}),
            }
        )
        with self.assertRaises(HTTP) as ctx:
            _resolve_pdf_image_path("/welcome/static/../../private/secret.txt", request)
        self.assertEqual(ctx.exception.status, 403)


class TestPdfImageOrigin(unittest.TestCase):
    """
    Regression tests for the image pipeline behind the generic.pdf view.

    An <img> in the page being converted decides where the *server* makes
    an HTTP request, so the rules about which sources are acceptable are
    security rules, not rendering ones. In particular the authority must
    never come from the request: Host is supplied by the client.
    """

    def _request(self, http_host="attacker.example:9999"):
        return Storage(
            {
                "application": "welcome",
                "folder": os.path.join("applications", "welcome"),
                "is_https": False,
                "env": Storage(
                    {
                        "http_host": http_host,
                        "server_name": "app.internal",
                        "server_port": "8000",
                    }
                ),
            }
        )

    def test_same_origin_ignores_the_host_header(self):
        # the reported SSRF: Host is client-supplied, so a rooted path
        # must not be fetched from whatever host the caller names
        request = self._request(http_host="127.0.0.1:31337")
        self.assertEqual(_pdf_same_origin(request), "http://app.internal:8000")
        self.assertEqual(
            _resolve_pdf_image_path("/metadata.jpg", request),
            "http://app.internal:8000/metadata.jpg",
        )

    def test_same_origin_omits_the_default_port(self):
        request = self._request()
        request.env.server_port = "80"
        self.assertEqual(_pdf_same_origin(request), "http://app.internal")
        request.is_https = True
        request.env.server_port = "443"
        self.assertEqual(_pdf_same_origin(request), "https://app.internal")

    def test_path_cannot_smuggle_an_authority(self):
        # "@" would turn the origin into userinfo and evil.example into
        # the host actually contacted
        request = self._request()
        with self.assertRaises(HTTP) as ctx:
            _resolve_pdf_image_path("@evil.example/x.jpg", request)
        self.assertEqual(ctx.exception.status, 403)

    def test_double_slash_path_stays_on_this_origin(self):
        request = self._request()
        url = _resolve_pdf_image_path("//evil.example/x.jpg", request)
        self.assertEqual(urlsplit(url).netloc, "app.internal:8000")

    def test_absolute_http_urls_are_passed_through(self):
        # external images stay supported: the page named the host itself
        request = self._request()
        for url in ("http://cdn.example/a.png", "https://cdn.example/a.png"):
            self.assertEqual(_resolve_pdf_image_path(url, request), url)

    def test_other_schemes_and_relative_paths_are_refused(self):
        request = self._request()
        for src in ("file:///etc/passwd", "data:image/png;base64,AAA", "logo.png"):
            with self.subTest(src=src):
                with self.assertRaises(HTTP) as ctx:
                    _resolve_pdf_image_path(src, request)
                self.assertEqual(ctx.exception.status, 403)

    def test_cross_host_redirect_is_refused(self):
        # a redirect would otherwise hand the choice of host back to
        # whoever answers first, re-opening the same SSRF
        handler = _SameHostRedirect()
        request = Request("http://origin.example/a.jpg")
        with self.assertRaises(HTTPError):
            handler.redirect_request(
                request, None, 302, "Found", {}, "http://internal.example/b.jpg"
            )

    def test_same_host_redirect_is_allowed(self):
        # http -> https and moved paths on one host stay ordinary
        handler = _SameHostRedirect()
        request = Request("http://origin.example/a.jpg")
        redirected = handler.redirect_request(
            request, None, 302, "Found", {}, "https://origin.example/b.jpg"
        )
        self.assertIsNotNone(redirected)


class TestPdfGeneration(unittest.TestCase):
    """The generic.pdf view was broken on py3: these cover it end to end."""

    def setUp(self):
        self._request = getattr(current, "request", None)
        current.request = Storage(
            {
                "application": "welcome",
                "folder": os.path.abspath(os.path.join("applications", "welcome")),
                "is_https": False,
                "env": Storage(
                    {
                        "http_host": "127.0.0.1:8000",
                        "server_name": "127.0.0.1",
                        "server_port": "8000",
                    }
                ),
            }
        )

    def tearDown(self):
        current.request = self._request

    def test_pyfpdf_from_html_returns_pdf_bytes(self):
        out = pyfpdf_from_html("<html><body><h1>Title</h1><p>a &amp; b</p></body></html>")
        self.assertIsInstance(out, bytes)
        self.assertTrue(out.startswith(b"%PDF"), out[:20])

    def test_pyfpdf_from_html_embeds_a_local_static_image(self):
        out = pyfpdf_from_html(
            "<html><body><img src='/welcome/static/images/favicon.png'/></body></html>"
        )
        self.assertTrue(out.startswith(b"%PDF"))
        self.assertIn(b"/Image", out)

    def test_pdf_from_html_serves_the_pdf(self):
        # a PDF is binary and a view renders into a text buffer, so the
        # bytes are raised rather than returned
        with self.assertRaises(HTTP) as ctx:
            pdf_from_html("<html><body><h1>Title</h1></body></html>")
        self.assertEqual(ctx.exception.status, 200)
        self.assertEqual(
            ctx.exception.headers["Content-Type"], "application/pdf"
        )
        self.assertTrue(ctx.exception.body.startswith(b"%PDF"))

