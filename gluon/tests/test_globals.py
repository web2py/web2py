#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.globals
"""


import re
import unittest
from io import BytesIO

from gluon import URL
from gluon.globals import Request, Response, Session
from gluon.rewrite import regex_url_in


def setup_clean_session():
    request = Request(env={})
    request.application = "a"
    request.controller = "c"
    request.function = "f"
    request.folder = "applications/admin"
    response = Response()
    session = Session()
    session.connect(request, response)
    from gluon.globals import current

    current.request = request
    current.response = response
    current.session = session
    return current


class testRequest(unittest.TestCase):
    def setUp(self):
        from gluon.globals import current

        current.response = Response()

    def test_restful_simple(self):
        env = {"request_method": "GET", "PATH_INFO": "/welcome/default/index/1.pdf"}
        r = Request(env)
        regex_url_in(r, env)

        @r.restful()
        def simple_rest():
            def GET(*args, **vars):
                return args[0]

            return locals()

        self.assertEqual(simple_rest(), "1")

    def test_restful_calls_post(self):
        env = {"request_method": "POST", "PATH_INFO": "/welcome/default/index"}
        r = Request(env)
        regex_url_in(r, env)

        @r.restful()
        def post_rest():
            def POST(*args, **vars):
                return "I posted"

            return locals()

        self.assertEqual(post_rest(), "I posted")

    def test_restful_ignore_extension(self):
        env = {"request_method": "GET", "PATH_INFO": "/welcome/default/index/127.0.0.1"}
        r = Request(env)
        regex_url_in(r, env)

        @r.restful(ignore_extension=True)
        def ignore_rest():
            def GET(*args, **vars):
                return args[0]

            return locals()

        self.assertEqual(ignore_rest(), "127.0.0.1")


class testResponse(unittest.TestCase):
    # port from python 2.7, needed for 2.5 and 2.6 tests
    def assertRegexpMatches(self, text, expected_regexp, msg=None):
        """Fail the test unless the text matches the regular expression."""
        if isinstance(expected_regexp, str):
            expected_regexp = re.compile(expected_regexp)
        if not expected_regexp.search(text):
            msg = msg or "Regexp didn't match"
            msg = "%s: %r not found in %r" % (msg, expected_regexp.pattern, text)
            raise self.failureException(msg)

    def test_include_files(self):
        def return_includes(response, extensions=None):
            response.include_files(extensions)
            return response.body.getvalue()

        response = Response()
        response.files.append(URL("a", "static", "css/file.css"))
        content = return_includes(response)
        self.assertEqual(
            content,
            '<link href="/a/static/css/file.css" rel="stylesheet" type="text/css" />',
        )

        response = Response()
        response.files.append(URL("a", "static", "css/file.js"))
        content = return_includes(response)
        self.assertEqual(
            content,
            '<script src="/a/static/css/file.js" type="text/javascript"></script>',
        )

        response = Response()
        response.files.append(URL("a", "static", "css/file.coffee"))
        content = return_includes(response)
        self.assertEqual(
            content,
            '<script src="/a/static/css/file.coffee" type="text/coffee"></script>',
        )

        response = Response()
        response.files.append(URL("a", "static", "css/file.ts"))
        content = return_includes(response)
        self.assertEqual(
            content,
            '<script src="/a/static/css/file.ts" type="text/typescript"></script>',
        )

        response = Response()
        response.files.append(URL("a", "static", "css/file.less"))
        content = return_includes(response)
        self.assertEqual(
            content,
            '<link href="/a/static/css/file.less" rel="stylesheet/less" type="text/css" />',
        )

        response = Response()
        response.files.append(("css:inline", "background-color; white;"))
        content = return_includes(response)
        self.assertEqual(
            content, '<style type="text/css">\nbackground-color; white;\n</style>'
        )

        response = Response()
        response.files.append(("js:inline", 'alert("hello")'))
        content = return_includes(response)
        self.assertEqual(
            content, '<script type="text/javascript">\nalert("hello")\n</script>'
        )

        response = Response()
        response.files.append("https://code.jquery.com/jquery-1.11.3.min.js")
        content = return_includes(response)
        self.assertEqual(
            content,
            '<script src="https://code.jquery.com/jquery-1.11.3.min.js" type="text/javascript"></script>',
        )

        response = Response()
        response.files.append("https://code.jquery.com/jquery-1.11.3.min.js?var=0")
        content = return_includes(response)
        self.assertEqual(
            content,
            '<script src="https://code.jquery.com/jquery-1.11.3.min.js?var=0" type="text/javascript"></script>',
        )

        response = Response()
        response.files.append("https://code.jquery.com/jquery-1.11.3.min.js?var=0")
        response.files.append("https://code.jquery.com/jquery-1.11.3.min.js?var=0")
        response.files.append(URL("a", "static", "css/file.css"))
        response.files.append(URL("a", "static", "css/file.css"))
        content = return_includes(response)
        self.assertEqual(
            content,
            '<script src="https://code.jquery.com/jquery-1.11.3.min.js?var=0" type="text/javascript"></script>'
            + '<link href="/a/static/css/file.css" rel="stylesheet" type="text/css" />',
        )

        response = Response()
        response.files.append(("js", "http://maps.google.com/maps/api/js?sensor=false"))
        response.files.append("https://code.jquery.com/jquery-1.11.3.min.js?var=0")
        response.files.append(URL("a", "static", "css/file.css"))
        response.files.append(URL("a", "static", "css/file.ts"))
        content = return_includes(response)
        self.assertEqual(
            content,
            '<script src="http://maps.google.com/maps/api/js?sensor=false" type="text/javascript"></script>'
            + '<script src="https://code.jquery.com/jquery-1.11.3.min.js?var=0" type="text/javascript"></script>'
            + '<link href="/a/static/css/file.css" rel="stylesheet" type="text/css" />'
            + '<script src="/a/static/css/file.ts" type="text/typescript"></script>',
        )

        response = Response()
        response.files.append(URL("a", "static", "css/file.js"))
        response.files.append(URL("a", "static", "css/file.css"))
        content = return_includes(response, extensions=["css"])
        self.assertEqual(
            content,
            '<link href="/a/static/css/file.css" rel="stylesheet" type="text/css" />',
        )

        # regr test for #628
        response = Response()
        response.files.append("http://maps.google.com/maps/api/js?sensor=false")
        content = return_includes(response)
        self.assertEqual(content, "")

        # regr test for #628
        response = Response()
        response.files.append(("js", "http://maps.google.com/maps/api/js?sensor=false"))
        content = return_includes(response)
        self.assertEqual(
            content,
            '<script src="http://maps.google.com/maps/api/js?sensor=false" type="text/javascript"></script>',
        )

        response = Response()
        response.files.append(["js", "http://maps.google.com/maps/api/js?sensor=false"])
        content = return_includes(response)
        self.assertEqual(
            content,
            '<script src="http://maps.google.com/maps/api/js?sensor=false" type="text/javascript"></script>',
        )

        response = Response()
        response.files.append(
            ("js1", "http://maps.google.com/maps/api/js?sensor=false")
        )
        content = return_includes(response)
        self.assertEqual(content, "")

    def test_enable_csp_rejects_injected_policy_tokens(self):
        response = Response()
        with self.assertRaises(ValueError):
            response.enable_csp(script_src="'self'; img-src *")

        response = Response()
        response.headers["Content-Security-Policy"] = "script>src 'self'"
        with self.assertRaises(ValueError):
            response.enable_csp()

        response = Response()
        response.headers["Content-Security-Policy"] = "report-to group,name"
        with self.assertRaises(ValueError):
            response.enable_csp()

        response = Response()
        with self.assertRaises(ValueError):
            response.enable_csp(report_to="group,name")

        response = Response()
        response.headers["Content-Security-Policy"] = "report-to group,name"
        with self.assertRaises(ValueError):
            response.enable_csp()

        response = Response()
        with self.assertRaises(ValueError):
            response.enable_csp(script_src="https://good.example/\x00evil")

        response = Response()
        response.headers["Content-Security-Policy"] = "default-src 'self'; report-to group,name"
        with self.assertRaises(ValueError):
            response.enable_csp()

    def test_enable_csp_rejects_non_string_iterable_tokens(self):
        for invalid in ([None], [123], [b"foo"]):
            response = Response()
            with self.assertRaises(TypeError):
                response.enable_csp(script_src=invalid)

    def test_enable_csp_accepts_valid_policy_tokens(self):
        response = Response()
        response.enable_csp(
            script_src=(
                "'self' 'none' 'unsafe-inline' 'unsafe-eval' "
                "'nonce-abcDEF0123+/_=' "
                "'sha256-abcDEF0123+/_=' "
                "*.example.com https://cdn.example.com blob: data: ws: wss:"
            ),
            report_uri="https://example.com/report",
            report_to="csp-endpoint",
            sandbox="allow-scripts allow-same-origin",
            upgrade_insecure_requests="",
        )
        csp = response.headers["Content-Security-Policy"]
        self.assertIn("'self'", csp)
        self.assertIn("'unsafe-inline'", csp)
        self.assertIn("'nonce-abcDEF0123+/_='", csp)
        self.assertIn("'sha256-abcDEF0123+/_='", csp)
        self.assertIn("*.example.com", csp)
        self.assertIn("blob:", csp)
        self.assertIn("data:", csp)
        self.assertIn("ws:", csp)
        self.assertIn("wss:", csp)
        self.assertIn("report-uri https://example.com/report", csp)
        self.assertIn("report-to csp-endpoint", csp)
        self.assertIn("sandbox allow-scripts allow-same-origin", csp)
        self.assertIn("upgrade-insecure-requests", csp)

    def test_enable_csp_accepts_existing_policy_lists(self):
        response = Response()
        response.headers["Content-Security-Policy"] = (
            "default-src 'self', report-uri https://example.com/report"
        )
        response.enable_csp(report_to="csp-endpoint")
        csp = response.headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("report-uri https://example.com/report", csp)
        self.assertIn("report-to csp-endpoint", csp)
        self.assertIn("script-src 'self'", csp)
        self.assertIn("style-src 'self'", csp)

        response = Response()
        response.headers["Content-Security-Policy"] = (
            "default-src 'self',report-uri https://example.com/report"
        )
        response.enable_csp(report_to="csp-endpoint")
        csp = response.headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("report-uri https://example.com/report", csp)
        self.assertIn("report-to csp-endpoint", csp)

        response = Response()
        response.headers["Content-Security-Policy"] = (
            "default-src 'self',x-foo bar"
        )
        response.enable_csp()
        csp = response.headers["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("x-foo bar", csp)

    def test_cookies(self):
        current = setup_clean_session()
        cookie = str(current.response.cookies)
        session_key = "%s=%s" % (
            current.response.session_id_name,
            current.response.session_id,
        )
        self.assertRegexpMatches(cookie, r"^Set-Cookie: ")
        self.assertTrue(session_key in cookie)
        self.assertTrue("Path=/" in cookie)

    def test_cookies_secure(self):
        current = setup_clean_session()
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue("secure" not in cookie.lower())

        current = setup_clean_session()
        current.session.secure()
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue("secure" in cookie.lower())

    def test_cookies_httponly(self):
        current = setup_clean_session()
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        # cookies in PY3 have capital letters
        self.assertTrue("httponly" in cookie.lower())

        current = setup_clean_session()
        current.session.httponly_cookies = True
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue("httponly" in cookie.lower())

        current = setup_clean_session()
        current.session.httponly_cookies = False
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue("httponly" not in cookie.lower())

    def test_cookies_samesite(self):
        # Test Lax is the default mode
        current = setup_clean_session()
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue("samesite=lax" in cookie.lower())
        # Test you can disable samesite
        current = setup_clean_session()
        current.session.samesite(False)
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue("samesite" not in cookie.lower())
        # Test you can change mode
        current = setup_clean_session()
        current.session.samesite("Strict")
        current.session._fixup_before_save()
        cookie = str(current.response.cookies)
        self.assertTrue("samesite=strict" in cookie.lower())

    def test_include_meta(self):
        response = Response()
        response.meta["web2py"] = "web2py"
        response.include_meta()
        self.assertEqual(
            response.body.getvalue(), '\n<meta name="web2py" content="web2py" />\n'
        )
        response = Response()
        response.meta["meta_dict"] = {"tag_name": "tag_value"}
        response.include_meta()
        self.assertEqual(response.body.getvalue(), '\n<meta tag_name="tag_value" />\n')


class testFileUpload(unittest.TestCase):
    BOUNDARY = b"testboundary"

    def _build_multipart(self, fields=None, files=None):
        body = b""
        for name, value in (fields or {}).items():
            body += b"--" + self.BOUNDARY + b"\r\n"
            body += b'Content-Disposition: form-data; name="' + name.encode() + b'"\r\n'
            body += b"\r\n"
            body += value.encode("utf-8") + b"\r\n"
        for name, (filename, content) in (files or {}).items():
            body += b"--" + self.BOUNDARY + b"\r\n"
            body += (
                b'Content-Disposition: form-data; name="'
                + name.encode()
                + b'"; filename="'
                + filename.encode()
                + b'"\r\n'
            )
            body += b"Content-Type: application/octet-stream\r\n"
            body += b"\r\n"
            body += content + b"\r\n"
        body += b"--" + self.BOUNDARY + b"--\r\n"
        return body

    def _make_request(self, body):
        boundary = self.BOUNDARY.decode()
        env = {
            "request_method": "POST",
            "CONTENT_TYPE": "multipart/form-data; boundary=" + boundary,
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": BytesIO(body),
        }
        return Request(env)

    def test_file_upload_filename(self):
        body = self._build_multipart(files={"upload": ("hello.txt", b"hello world")})
        r = self._make_request(body)
        self.assertEqual(r.post_vars["upload"].filename, "hello.txt")

    def test_file_upload_content(self):
        body = self._build_multipart(files={"upload": ("data.bin", b"binary\x00content")})
        r = self._make_request(body)
        self.assertEqual(r.post_vars["upload"].file.read(), b"binary\x00content")

    def test_file_upload_with_text_field(self):
        body = self._build_multipart(
            fields={"description": "my description"},
            files={"upload": ("report.pdf", b"%PDF content")},
        )
        r = self._make_request(body)
        self.assertEqual(r.post_vars["description"], "my description")
        self.assertEqual(r.post_vars["upload"].filename, "report.pdf")

    def test_duplicate_field_names_become_list(self):
        boundary = self.BOUNDARY
        body = (
            b"--" + boundary + b"\r\n"
            b'Content-Disposition: form-data; name="tag"\r\n\r\nfoo\r\n'
            b"--" + boundary + b"\r\n"
            b'Content-Disposition: form-data; name="tag"\r\n\r\nbar\r\n'
            b"--" + boundary + b"--\r\n"
        )
        r = self._make_request(body)
        tags = r.post_vars["tag"]
        self.assertIsInstance(tags, list)
        self.assertIn("foo", tags)
        self.assertIn("bar", tags)

    def test_multiple_file_input(self):
        boundary = self.BOUNDARY
        body = (
            b"--" + boundary + b"\r\n"
            b'Content-Disposition: form-data; name="files"; filename="a.txt"\r\n'
            b"Content-Type: text/plain\r\n\r\nfile a content\r\n"
            b"--" + boundary + b"\r\n"
            b'Content-Disposition: form-data; name="files"; filename="b.txt"\r\n'
            b"Content-Type: text/plain\r\n\r\nfile b content\r\n"
            b"--" + boundary + b"--\r\n"
        )
        r = self._make_request(body)
        uploads = r.post_vars["files"]
        self.assertIsInstance(uploads, list)
        filenames = [u.filename for u in uploads]
        self.assertIn("a.txt", filenames)
        self.assertIn("b.txt", filenames)
