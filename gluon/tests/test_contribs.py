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
from gluon.contrib.generics import (_pdf_same_origin, _SameHostRedirect,
                                    _resolve_pdf_image_path, pdf_from_html,
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

    def test_pdf_image_map_allows_same_origin_path(self):
        request = Storage(
            {
                "application": "welcome",
                "folder": os.path.join("applications", "welcome"),
                "is_https": False,
                "env": Storage(
                    {
                        "http_host": "example.com",
                        "server_name": "example.com",
                        "server_port": "80",
                    }
                ),
            }
        )
        result = _resolve_pdf_image_path("/welcome/default/download/logo.png", request)
        self.assertEqual(result, "http://example.com/welcome/default/download/logo.png")

    def test_pdf_image_map_rejects_cross_host_fetch(self):
        request = Storage(
            {
                "application": "welcome",
                "folder": os.path.join("applications", "welcome"),
                "is_https": False,
                "env": Storage({"http_host": "example.com:8000"}),
            }
        )
        # "@internal:8080/x" would build http://example.com:8000@internal:8080/x,
        # i.e. the server-side fetch would connect to internal:8080.
        for path in (
            "@internal:8080/logo.png",
            "evil.example/logo.png",
            "//evil/logo.png",
        ):
            with self.assertRaises(HTTP) as ctx:
                _resolve_pdf_image_path(path, request)
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
        # Host is client-supplied, so a rooted path must not be fetched
        # from whatever host the caller names
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

    def test_absolute_http_urls_are_passed_through(self):
        # external images stay supported: the page named the host itself
        request = self._request()
        for url in ("http://cdn.example/a.png", "https://cdn.example/a.png"):
            self.assertEqual(_resolve_pdf_image_path(url, request), url)

    def test_other_schemes_are_refused(self):
        request = self._request()
        for src in ("file:///etc/passwd", "data:image/png;base64,AAA"):
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

