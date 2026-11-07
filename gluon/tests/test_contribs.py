#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for contribs """

import hashlib
import hmac
import os
import shutil
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from urllib.error import HTTPError
from urllib.request import Request

from gluon import HTTP, current
from gluon.contrib.generics import (_PdfFPDF, _resolve_pdf_image_path,
                                    _trusted_pdf_image_origins,
                                    _TrustedOriginRedirect, pdf_from_html,
                                    pyfpdf_from_html)
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

    def test_pam_authentication_requires_account_approval(self):
        from gluon.contrib import pam

        with patch.object(pam, "PAM_START", return_value=0), patch.object(
            pam, "PAM_AUTHENTICATE", return_value=0
        ), patch.object(pam, "PAM_ACCT_MGMT", return_value=7) as account_check:
            self.assertFalse(pam.authenticate(b"expired-user", b"password"))
            account_check.assert_called_once()

        with patch.object(pam, "PAM_START", return_value=0), patch.object(
            pam, "PAM_AUTHENTICATE", return_value=0
        ), patch.object(pam, "PAM_ACCT_MGMT", return_value=0):
            self.assertTrue(pam.authenticate(b"active-user", b"password"))

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

    def test_markdown_wiki_safe_mode_keeps_markup_escaped(self):
        from gluon.contrib.markdown import WIKI

        def render(text):
            return WIKI(text).xml()

        # a tag with no closing ">" is not matched as a tag, so it was left raw
        self.assertNotIn("<img", render("<img src=x onerror=alert(1)//"))
        # ...as was a tag swallowed by something that looks like an auto-link
        self.assertNotIn("<script", render("<ftp:[<script>alert(1);//]()>"))

        # link urls, titles and alt text must not close their attribute,
        # including through a code span that is only expanded later
        for text in (
            '[x](http://a.com/"onmouseover="alert(1))',
            '[x]: http://a.com/"onmouseover="alert(1)\n\n[y][x]',
            '![](`" onerror=alert(1)//`)',
            '![`" onerror=alert(1)//`](a.png)',
            '[x](http://a.com "t `" onmouseover=alert(1)` u")',
        ):
            out = render(text)
            self.assertNotIn('"onmouseover=', out.replace(" ", ""))
            self.assertNotIn('"onerror=', out.replace(" ", ""))

        # script urls are not linked, however their scheme is spelled
        for url in (
            "javascript:alert(1)",
            "JavaScript:alert(1)",
            "javascript&#58;alert(1)",
            "java&#115;cript:alert(1)",
            "java\tscript:alert(1)",
            "vbscript:msgbox(1)",
        ):
            self.assertIn('<a href="#">x</a>', render("[x](%s)" % url))
            self.assertIn('<a href="#">x</a>', render("[x][1]\n\n[1]: %s" % url))

        # ordinary markdown is unchanged
        self.assertEqual(
            render(
                '[ok](http://good.com/page "t") and ![i](/static/a.png) '
                "and <http://good.com/x> and a < b"
            ),
            '<p><a href="http://good.com/page" title="t">ok</a> and '
            '<img src="/static/a.png" alt="i" /> and '
            '<a href="http://good.com/x">http://good.com/x</a> and a &lt; b</p>\n',
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

    def test_hypermedia_write_respects_policy_fields(self):
        from gluon import current
        from gluon.dal import DAL, Field
        from gluon.contrib.hypermedia import Collection
        from gluon.globals import Request, Response

        class Args(list):
            def __call__(self, i, default=None):
                try:
                    return self[i]
                except IndexError:
                    return default

        request = Request(env={"HTTP_HOST": "example.com"})
        request.application, request.controller, request.function = "app", "d", "api"
        current.request = request
        current.response = Response()

        db = DAL("sqlite:memory")
        try:
            db.define_table("thing", Field("name"), Field("owner"))

            # the policy only permits writing "name"; "owner" must stay protected,
            # matching what table2template advertises as post_writable/put_writable
            policies = {"thing": {"POST": {"query": None, "fields": ["name"]}}}

            forwarded = {}

            def insert_spy(**fields):
                forwarded.clear()
                forwarded.update(fields)
                return Storage(id=1, errors={})

            db.thing.validate_and_insert = insert_spy

            req = Storage()
            req.args = Args(["thing"])
            req.env = Storage(
                request_method="POST",
                content_type="application/x-www-form-urlencoded",
            )
            req.get_vars = Storage()
            req.post_vars = Storage(name="alice", owner="attacker")
            req.vars = req.post_vars

            Collection(db).process(req, current.response, policies)

            # The non-policy column must never reach validate_and_insert.
            self.assertNotIn("owner", forwarded)
            self.assertEqual(forwarded, {"name": "alice"})

            # The policy filter is also applied to update payloads.
            update_forwarded = {}

            def update_spy(self, **fields):
                update_forwarded.update(fields)
                return Storage(errors={})

            from pydal.objects import Set

            req.args = Args(["thing", "1"])
            req.env.request_method = "PUT"
            req.get_vars = Storage()
            req.post_vars = Storage(name="updated", owner="attacker")
            req.vars = req.post_vars
            update_policy = {
                "thing": {"PUT": {"query": None, "fields": ["id", "name"]}}
            }
            original_validate_and_update = Set.validate_and_update
            Set.validate_and_update = update_spy
            try:
                Collection(db).process(req, current.response, update_policy)
            finally:
                Set.validate_and_update = original_validate_and_update

            # The non-policy column must never reach validate_and_update.
            self.assertNotIn("owner", update_forwarded)
            self.assertEqual(update_forwarded, {"name": "updated"})

        finally:
            db.close()

    def test_hypermedia_write_handles_dal_result_dicts(self):
        from gluon import current
        from gluon.contrib.hypermedia import Collection
        from gluon.dal import DAL, Field
        from gluon.globals import Request, Response

        class Args(list):
            def __call__(self, i, default=None):
                try:
                    return self[i]
                except IndexError:
                    return default

        request = Storage(
            args=Args(["thing"]),
            env=Storage(
                request_method="POST",
                content_type="application/x-www-form-urlencoded",
            ),
            get_vars=Storage(),
            post_vars=Storage(name="alice", owner="attacker"),
            vars=Storage(name="alice", owner="attacker"),
        )
        response = Response()
        current.request = Request(env={"HTTP_HOST": "example.com"})
        current.request.application = "app"
        current.request.controller = "d"
        current.request.function = "api"

        db = DAL("sqlite:memory")
        try:
            db.define_table("thing", Field("name"), Field("owner"))
            policies = {"thing": {"POST": {"query": None, "fields": ["name"]}}}
            Collection(db).process(request, response, policies)
            inserted = db.thing(name="alice")
            self.assertTrue(inserted)
            self.assertIsNone(inserted.owner)
            self.assertEqual(response.status, 201)

            request.args = Args(["thing", str(inserted.id)])
            request.env.request_method = "PUT"
            request.get_vars = Storage()
            request.post_vars = Storage(name="updated", owner="attacker")
            request.vars = request.post_vars
            Collection(db).process(
                request,
                response,
                {"thing": {"PUT": {"query": None, "fields": ["id", "name"]}}},
            )
            updated = db.thing[inserted.id]
            self.assertEqual(updated.name, "updated")
            self.assertIsNone(updated.owner)
            self.assertEqual(response.status, 200)
        finally:
            db.close()

    def test_hypermedia_template_respects_field_writable(self):
        from gluon.contrib.hypermedia import Collection
        from gluon.dal import DAL, Field

        db = DAL("sqlite:memory")
        try:
            db.define_table("thing", Field("name"), Field("owner", writable=False))
            policies = {
                "thing": {
                    "GET": {"fields": ["name", "owner"]},
                    "POST": {"fields": ["name", "owner"]},
                    "PUT": {"fields": ["name", "owner"]},
                }
            }
            collection = Collection(db)
            collection.policies = policies
            collection.table_policy = policies["thing"]["GET"]
            template = collection.table2template(db.thing)
            fields = {item["name"]: item for item in template["data"]}

            self.assertTrue(fields["name"]["post_writable"])
            self.assertTrue(fields["name"]["put_writable"])
            self.assertFalse(fields["owner"]["post_writable"])
            self.assertFalse(fields["owner"]["put_writable"])
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


class TestPdfImageOrigin(unittest.TestCase):
    """
    Regression tests for the image pipeline behind the generic.pdf view.

    An <img> in the page being converted decides where the *server* makes
    an HTTP request, so the rules about which sources are acceptable are
    security rules, not rendering ones. The authority must never come from
    the request: HTTP_HOST is client supplied, and some WSGI servers derive
    SERVER_NAME / SERVER_PORT from it as well.
    """

    TRUSTED = ["http://app.internal:8000"]

    def _request(self, http_host="attacker.example:9999"):
        return Storage(
            {
                "application": "welcome",
                "folder": os.path.join("applications", "welcome"),
                "is_https": False,
                "env": Storage(
                    {
                        "http_host": http_host,
                        # as gunicorn would set them from the Host header
                        "server_name": http_host.split(":")[0],
                        "server_port": http_host.split(":")[-1],
                    }
                ),
            }
        )

    def assertRefused(self, src, trusted=None):
        with self.assertRaises(HTTP) as ctx:
            _resolve_pdf_image_path(src, self._request(), trusted)
        self.assertEqual(ctx.exception.status, 403, src)

    def test_network_images_refused_without_trusted_origin(self):
        # no trusted origin configured: nothing is fetched over the network,
        # whatever Host / SERVER_NAME say
        for src in (
            "/welcome/default/download/logo.png",
            "/metadata.jpg",
            "http://169.254.169.254/latest/meta-data/x.jpg",
            "https://cdn.example/a.png",
        ):
            with self.subTest(src=src):
                self.assertRefused(src)

    def test_rooted_path_uses_trusted_origin_not_request(self):
        request = self._request(http_host="127.0.0.1:31337")
        url = _resolve_pdf_image_path("/metadata.jpg", request, self.TRUSTED)
        self.assertEqual(url, "http://app.internal:8000/metadata.jpg")

    def test_absolute_url_only_from_trusted_origin(self):
        trusted = ["https://cdn.example", "http://app.internal:8000"]
        request = self._request()
        for url in ("https://cdn.example/a.png", "https://CDN.example:443/a.png"):
            self.assertEqual(_resolve_pdf_image_path(url, request, trusted), url)
        for url in (
            "http://cdn.example/a.png",  # wrong scheme
            "https://cdn.example:8443/a.png",  # wrong port
            "http://127.0.0.1:31337/a.png",
            "https://user@evil.example/a.png",
        ):
            with self.subTest(url=url):
                self.assertRefused(url, trusted)

    def test_authority_injection_paths_refused(self):
        for src in (
            "@internal:8080/logo.png",
            "evil.example/logo.png",
            "//evil/logo.png",
            "file:///etc/passwd",
            "data:image/png;base64,AAA",
        ):
            with self.subTest(src=src):
                self.assertRefused(src, self.TRUSTED)

    def test_trusted_origins_are_validated(self):
        for bad in (
            "ftp://example.com",
            "http://user:pass@example.com",
            "http://example.com/base",
            "http://example.com/?a=b",
            "http://example.com/#frag",
            "http://:8080",
            "http://example.com:notaport",
            "//example.com",
            "example.com",
        ):
            with self.subTest(origin=bad):
                with self.assertRaises(HTTP) as ctx:
                    _trusted_pdf_image_origins([bad])
                self.assertEqual(ctx.exception.status, 500)

    def test_trusted_origins_are_canonicalized(self):
        self.assertEqual(
            _trusted_pdf_image_origins(
                ["https://Example.COM/", "http://host:80", "http://[::1]:8000"]
            ),
            ["https://example.com", "http://host", "http://[::1]:8000"],
        )
        self.assertEqual(
            _trusted_pdf_image_origins("http://host:8080"), ["http://host:8080"]
        )

    def test_redirect_to_untrusted_origin_is_refused(self):
        handler = _TrustedOriginRedirect(["http://origin.example"])
        request = Request("http://origin.example/a.jpg")
        with self.assertRaises(HTTPError):
            handler.redirect_request(
                request, None, 302, "Found", {}, "http://internal.example/b.jpg"
            )

    def test_redirect_within_trusted_origins_is_allowed(self):
        handler = _TrustedOriginRedirect(
            ["http://origin.example", "https://origin.example"]
        )
        request = Request("http://origin.example/a.jpg")
        redirected = handler.redirect_request(
            request, None, 302, "Found", {}, "https://origin.example/b.jpg"
        )
        self.assertIsNotNone(redirected)

    def test_loader_does_not_follow_redirect_to_internal_host(self):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        internal_hits, origin_hits = [], []

        class Internal(BaseHTTPRequestHandler):
            def do_GET(self):
                internal_hits.append(self.path)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"\xff\xd8\xff\xe0secret")

            def log_message(self, *args):
                pass

        class Origin(BaseHTTPRequestHandler):
            def do_GET(self):
                origin_hits.append(self.path)
                self.send_response(302)
                self.send_header(
                    "Location", "http://127.0.0.1:%d/metadata.jpg" % internal_port
                )
                self.end_headers()

            def log_message(self, *args):
                pass

        internal = ThreadingHTTPServer(("127.0.0.1", 0), Internal)
        internal_port = internal.server_address[1]
        origin = ThreadingHTTPServer(("127.0.0.1", 0), Origin)
        origin_url = "http://127.0.0.1:%d" % origin.server_address[1]
        for server in (internal, origin):
            threading.Thread(target=server.serve_forever, daemon=True).start()
            self.addCleanup(server.server_close)
            self.addCleanup(server.shutdown)

        pdf = _PdfFPDF(trusted_image_origins=[origin_url])
        with self.assertRaises(HTTPError):
            pdf.load_resource("image", origin_url + "/redirect.jpg")
        self.assertEqual(origin_hits, ["/redirect.jpg"])
        self.assertEqual(internal_hits, [])


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
        out = pyfpdf_from_html(
            "<html><body><h1>Title</h1><p>a &amp; b</p></body></html>"
        )
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
        self.assertEqual(ctx.exception.headers["Content-Type"], "application/pdf")
        self.assertTrue(ctx.exception.body.startswith(b"%PDF"))

