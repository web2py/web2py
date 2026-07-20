#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for contribs """

import hashlib
import hmac
import os
import shutil
import unittest
from urllib.parse import urlencode

from gluon import HTTP
from gluon.contrib.generics import _resolve_pdf_image_path
from gluon.contrib import fpdf as fpdf
from gluon.contrib import pyfpdf as pyfpdf
from gluon.contrib.appconfig import AppConfig
from gluon.storage import Storage

try:
    import tornado.testing
    import tornado.web

    from gluon.contrib import websocket_messaging

    HAVE_TORNADO = True
    _AsyncHTTPTestCase = tornado.testing.AsyncHTTPTestCase
except ImportError:
    # websocket_messaging needs tornado; skip its tests instead of
    # breaking the suite when the optional dependency is missing.
    HAVE_TORNADO = False
    _AsyncHTTPTestCase = unittest.TestCase


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

    def test_autolinks_escapes_url_in_markup(self):
        from gluon.contrib import autolinks

        # a url carrying a double quote must not be able to break out of the
        # attribute / script context it gets dropped into
        link = autolinks.expand_one('http://x.com/"onmouseover="alert(1)', {})
        self.assertNotIn('"onmouseover="', link)
        self.assertIn("&quot;", link)

        img = autolinks.image('http://x.com/"onerror="alert(1).png')
        self.assertNotIn('"onerror="', img)

        comp = autolinks.web2py_component('http://x/"+alert(1)+"')
        self.assertNotIn('"+alert(1)+"', comp)

        # legitimate urls are left intact
        self.assertIn(
            'href="http://good.com/page"',
            autolinks.expand_one("http://good.com/page", {"http://good.com/page": {}}),
        )

    def test_autolinks_rejects_unsafe_url_schemes(self):
        from gluon.contrib import autolinks
        from gluon.contrib.markmin.markmin2html import render

        # markmin's regex_auto matches any "scheme://..." token, so a wiki page
        # body can reach expand_one with a script-bearing scheme
        payload = "javascript://x%0alocation=name"
        self.assertIn("markmin_unsafe", autolinks.expand_one(payload, {}))
        self.assertNotIn("href=", autolinks.expand_one(payload, {}))
        self.assertIn("markmin_unsafe", autolinks.expand_one("vbscript://x", {}))

        # same result whether markmin autolinks itself or Wiki delegates to
        # expand_one
        rendered = render(
            payload, autolinks=lambda link: autolinks.expand_one(link, {})
        )
        self.assertNotIn("href=", rendered)

        # http(s) urls still get linked
        self.assertIn(
            'href="http://good.com/page"',
            autolinks.expand_one("http://good.com/page", {"http://good.com/page": {}}),
        )

    def test_hypermedia_query_respects_policy_fields(self):
        from gluon.dal import DAL, Field
        from gluon.contrib.hypermedia import Collection

        class Args(list):
            def __call__(self, i, default=None):
                try:
                    return self[i]
                except IndexError:
                    return default

        db = DAL("sqlite:memory")
        try:
            db.define_table("thing", Field("name"), Field("secret"))
            db.thing.insert(name="alice", secret="TOPSECRET")
            db.commit()

            col = Collection(db)
            col.request = Storage(args=Args(["thing"]))
            # policy exposes id and name only; secret must stay hidden
            col.table_policy = {"query": None, "fields": ["id", "name"]}

            # a filter on the non-exposed column leaks it through items_found
            for op in ("secret", "secret.startswith", "secret.contains"):
                with self.assertRaises(ValueError):
                    col.request2query(db.thing, Storage({op: "TOP"}))
            # ordering by a non-exposed column is also refused
            with self.assertRaises(ValueError):
                col.request2query(db.thing, Storage({"_orderby": "secret"}))

            # exposed fields keep working
            query, _, _ = col.request2query(db.thing, Storage({"name": "alice"}))
            self.assertEqual(db(query).count(), 1)
            col.request2query(db.thing, Storage({"_orderby": "name"}))

            # a policy that declares no field list is unchanged (all columns)
            col.table_policy = {"query": None}
            query, _, _ = col.request2query(db.thing, Storage({"secret": "TOPSECRET"}))
            self.assertEqual(db(query).count(), 1)
        finally:
            db.close()


class TestPySimpleSoapTransport(unittest.TestCase):
    """Tests the TLS handling of the pysimplesoap transports"""

    def _serve_https(self, common_name):
        """Serve one HTTPS request with a throwaway self-signed certificate."""
        import http.server
        import ssl
        import subprocess
        import tempfile
        import threading

        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, True)
        cert = os.path.join(tmpdir, "cert.pem")
        key = os.path.join(tmpdir, "key.pem")
        try:
            subprocess.check_call(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-keyout",
                    key,
                    "-out",
                    cert,
                    "-days",
                    "1",
                    "-nodes",
                    "-subj",
                    "/CN=%s" % common_name,
                    "-addext",
                    "subjectAltName=DNS:%s,IP:127.0.0.1" % common_name,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("openssl is not available")

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"ok")

            def log_message(self, *args):
                pass

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return cert, server.server_address[1]

    def test_untrusted_certificate_is_refused(self):
        """An unknown self-signed certificate must not be accepted"""
        from gluon.contrib.pysimplesoap.transport import get_Http

        _, port = self._serve_https("localhost")
        http_transport = get_Http()(timeout=5)
        with self.assertRaises(Exception):
            http_transport.request("https://localhost:%d/" % port, "GET", None, {})

    def test_certificate_trusted_through_cacert_is_accepted(self):
        """A certificate signed by the supplied cacert bundle still works"""
        from gluon.contrib.pysimplesoap.transport import get_Http

        cert, port = self._serve_https("localhost")
        http_transport = get_Http()(timeout=5, cacert=cert)
        _, content = http_transport.request(
            "https://localhost:%d/" % port, "GET", None, {}
        )
        self.assertEqual(content, b"ok")


@unittest.skipUnless(HAVE_TORNADO, "tornado is not installed")
class TestWebsocketMessaging(_AsyncHTTPTestCase):
    """Tests the hmac gate of the websocket_messaging broadcast server"""

    hmac_key = "topsecret"

    def get_app(self):
        self.received = []
        websocket_messaging.hmac_key = self.hmac_key
        websocket_messaging.listeners.clear()
        websocket_messaging.tokens.clear()
        # stand in for a subscribed websocket client
        websocket_messaging.listeners["default"] = [self]
        return tornado.web.Application(
            [
                (r"/", websocket_messaging.PostHandler),
                (r"/token", websocket_messaging.TokenHandler),
            ]
        )

    def write_message(self, message):
        self.received.append(message)

    def post(self, path, **kwargs):
        kwargs.setdefault("group", "default")
        return self.fetch(path, method="POST", body=urlencode(kwargs)).code

    def sign(self, message):
        return hmac.new(
            self.hmac_key.encode(), message.encode(), hashlib.md5
        ).hexdigest()

    def test_post_rejects_wrong_signature(self):
        self.assertEqual(self.post("/", message="spoofed", signature="wrong"), 401)
        self.assertEqual(self.received, [])

    def test_post_rejects_missing_signature(self):
        self.assertEqual(self.post("/", message="spoofed"), 401)
        self.assertEqual(self.received, [])

    def test_post_accepts_valid_signature(self):
        self.assertEqual(
            self.post("/", message="hello", signature=self.sign("hello")), 200
        )
        self.assertEqual(self.received, ["hello"])

    def test_token_rejects_wrong_signature(self):
        self.assertEqual(self.post("/token", message="mine", signature="wrong"), 401)
        self.assertEqual(dict(websocket_messaging.tokens), {})

    def test_token_accepts_valid_signature(self):
        self.assertEqual(
            self.post("/token", message="mine", signature=self.sign("mine")), 200
        )
        self.assertEqual(dict(websocket_messaging.tokens), {"mine": None})
