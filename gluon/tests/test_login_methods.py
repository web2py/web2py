#!/bin/python
# -*- coding: utf-8 -*-

"""
Unit tests for gluon.contrib.login_methods
"""

import importlib
import ssl
import sys
import types
import unittest
from urllib.parse import quote as urllib_quote

from gluon.globals import current
from gluon.storage import Storage


def _rfc4515_escape(value, escape_mode=0):
    # reference implementation of ldap.filter.escape_filter_chars (RFC 4515)
    repl = {"\\": "\\5c", "*": "\\2a", "(": "\\28", ")": "\\29", "\x00": "\\00"}
    return "".join(repl.get(c, c) for c in value)


def _rfc4514_dn_escape(value):
    # reference implementation of ldap.dn.escape_dn_chars (RFC 4514 2.4)
    if not value:
        return value
    for ch in ("\\", ",", "+", '"', "<", ">", ";", "="):
        value = value.replace(ch, "\\" + ch)
    value = value.replace("\000", "\\\000")
    if value[0] in ("#", " "):
        value = "\\" + value
    if value[-1] == " ":
        value = value[:-1] + "\\ "
    return value


def _make_fake_ldap(captured):
    """Build a minimal fake ``ldap`` module so ldap_auth can be imported and
    driven without python-ldap / a live directory server."""
    ldap_mod = types.ModuleType("ldap")
    ldap_mod.OPT_REFERRALS = 0
    ldap_mod.SCOPE_SUBTREE = 2
    ldap_mod.SCOPE_BASE = 0
    # distinct sentinels so the tests can tell the TLS options apart
    ldap_mod.OPT_X_TLS_REQUIRE_CERT = 0x6006
    ldap_mod.OPT_X_TLS_NEVER = 0
    ldap_mod.OPT_X_TLS_DEMAND = 2
    ldap_mod.OPT_X_TLS_NEWCTX = 0x6008
    ldap_mod.set_option = lambda *a, **k: captured.setdefault(
        "global_set_option", []
    ).append(tuple(a))

    class LDAPError(Exception):
        pass

    class INVALID_CREDENTIALS(LDAPError):
        pass

    ldap_mod.LDAPError = LDAPError
    ldap_mod.INVALID_CREDENTIALS = INVALID_CREDENTIALS

    class FakeCon(object):
        def set_option(self, *a):
            captured.setdefault("conn_set_option", []).append(tuple(a))

        def simple_bind_s(self, dn, pw):
            captured.setdefault("binds", []).append((dn, pw))

        def bind_s(self, dn, pw):
            captured.setdefault("binds", []).append((dn, pw))

        def search_s(self, base, scope, filterstr="(objectClass=*)", attrs=None):
            captured["filter"] = filterstr
            return [("uid=alice," + base, {})]

        def unbind(self):
            pass

        def start_tls_s(self):
            pass

    ldap_mod.initialize = lambda uri: (
        captured.setdefault("initialized", []).append(uri) or FakeCon()
    )

    filter_mod = types.ModuleType("ldap.filter")
    filter_mod.escape_filter_chars = _rfc4515_escape
    ldap_mod.filter = filter_mod

    dn_mod = types.ModuleType("ldap.dn")
    dn_mod.escape_dn_chars = _rfc4514_dn_escape
    ldap_mod.dn = dn_mod
    return ldap_mod, filter_mod, dn_mod


class TestLdapAuthSecurity(unittest.TestCase):
    # gluon.contrib.login_methods.ldap_auth builds LDAP search filters from the
    # attacker-supplied login name. In "uid" mode (with a service bind_dn) the
    # username was interpolated into "(uid=%s)" without escaping, allowing LDAP
    # filter injection (CWE-90) -- e.g. "*)(uid=*" turns the filter into
    # "(uid=*)(uid=*)". It must be escaped, like every other mode already does.
    _MODNAME = "gluon.contrib.login_methods.ldap_auth"

    def setUp(self):
        self.captured = {}
        self._saved = {
            k: sys.modules.get(k)
            for k in ("ldap", "ldap.filter", "ldap.dn", self._MODNAME)
        }
        ldap_mod, filter_mod, dn_mod = _make_fake_ldap(self.captured)
        sys.modules["ldap"] = ldap_mod
        sys.modules["ldap.filter"] = filter_mod
        sys.modules["ldap.dn"] = dn_mod
        sys.modules.pop(self._MODNAME, None)
        self.mod = importlib.import_module(self._MODNAME)
        self.escape = filter_mod.escape_filter_chars
        self.escape_dn = dn_mod.escape_dn_chars

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        sys.modules.pop(self._MODNAME, None)

    def test_uid_mode_escapes_username_in_filter(self):
        auth = self.mod.ldap_auth(
            mode="uid",
            server="ldap.example",
            base_dn="dc=x",
            bind_dn="cn=svc,dc=x",
            bind_pw="svcpw",
            manage_user=False,
        )
        malicious = "*)(uid=*"
        auth(malicious, "pw")
        self.assertIn("filter", self.captured)
        # the username reaches the filter only in escaped form
        self.assertEqual(self.captured["filter"], "(uid=%s)" % self.escape(malicious))
        # the raw injection (a second, attacker-controlled clause) is gone
        self.assertNotIn("(uid=*)(uid=*", self.captured["filter"])
        self.assertNotIn("*", self.captured["filter"])

    def test_cn_mode_escapes_username_in_bind_dn(self):
        # In "cn" mode the bind DN is built as "cn=<username>,<base_dn>". A
        # username carrying DN metacharacters (comma/equals) must be escaped
        # with escape_dn_chars so it stays a single RDN value and cannot
        # rewrite the DN structure (LDAP DN injection, CWE-90).
        auth = self.mod.ldap_auth(
            mode="cn",
            server="ldap.example",
            base_dn="dc=x",
            manage_user=False,
        )
        malicious = "evil,ou=Admins"
        auth(malicious, "pw")
        binds = self.captured.get("binds", [])
        self.assertTrue(binds, "no bind was attempted")
        bind_dn = binds[-1][0]
        # the username reaches the bind DN only in escaped form ...
        self.assertEqual(bind_dn, "cn=%s,dc=x" % self.escape_dn(malicious))
        # ... so the injected RDN cannot appear unescaped
        self.assertNotIn("cn=evil,ou=Admins", bind_dn)

    def test_invalid_mode_fails_closed(self):
        auth = self.mod.ldap_auth(
            mode="invalid",
            server="ldap.example",
            base_dn="dc=x",
            manage_user=False,
        )

        self.assertFalse(auth("alice", "pw"))
        self.assertNotIn("initialized", self.captured)

    def test_blank_password_rejected_before_bind(self):
        # RFC 4513 5.1.2: a bind with a valid DN but an empty password is an
        # unauthenticated bind that many servers accept as success, so the
        # blank-password guard must fire before any bind. It only compared the
        # password against "", so a None password (e.g. a request var that was
        # never sent, forwarded through login_bare) slipped past and reached an
        # unauthenticated bind, authenticating the account without a password.
        auth = self.mod.ldap_auth(
            mode="uid",
            server="ldap.example",
            base_dn="dc=x",
            manage_user=False,
        )
        for blank in (None, "", b""):
            self.captured.clear()
            self.assertFalse(auth("alice", blank))
            self.assertNotIn("binds", self.captured)
            self.assertNotIn("initialized", self.captured)


class TestOutboundURLTokenEncoding(unittest.TestCase):
    # loginradius_account / cas_auth build the outbound provider-validation URL
    # by interpolating an attacker-supplied request value (token / ticket) into
    # it. Without percent-encoding, "/", "&", "#" or "?" let the caller inject
    # extra path or query into that request -- the same defect the sibling
    # providers (janrain/rpx/loginza) already avoid via urlencode.
    _MALICIOUS = "abc/../x?a=1&b=2#frag"

    def test_loginradius_encodes_token(self):
        mod = importlib.import_module(
            "gluon.contrib.login_methods.loginradius_account"
        )
        captured = {}

        def fake_fetch(url, **kwargs):
            captured["url"] = url
            return "{}"

        orig = mod.fetch
        mod.fetch = fake_fetch
        try:
            req = Storage(vars=Storage(token=self._MALICIOUS))
            account = mod.LoginRadiusAccount(req, api_key="k", api_secret="s")
            account.get_user()
        finally:
            mod.fetch = orig
        expected = urllib_quote(self._MALICIOUS, safe="")
        self.assertTrue(captured["url"].endswith("/" + expected))
        self.assertNotIn(self._MALICIOUS, captured["url"])

    def test_cas_encodes_ticket(self):
        mod = importlib.import_module("gluon.contrib.login_methods.cas_auth")
        captured = {}

        class FakeResp(object):
            def read(self):
                return "no\n"

        def fake_urlopen(url, *a, **k):
            captured["url"] = url
            return FakeResp()

        orig = mod.urlopen
        saved_request = getattr(current, "request", None)
        mod.urlopen = fake_urlopen
        current.request = Storage(vars=Storage(ticket=self._MALICIOUS))
        try:
            cas = mod.CasAuth.__new__(mod.CasAuth)
            cas.cas_check_url = "https://cas.example/cas/validate"
            cas.cas_login_url = "https://cas.example/cas/login"
            cas.cas_my_url = "https://app.example/user/cas"
            cas._CAS_login()
        finally:
            mod.urlopen = orig
            if saved_request is None:
                current.request = None
            else:
                current.request = saved_request
        expected = urllib_quote(self._MALICIOUS, safe="")
        self.assertIn("ticket=" + expected, captured["url"])
        self.assertNotIn(self._MALICIOUS, captured["url"])


class TestFreeIPATLSVerification(unittest.TestCase):
    # freeipa_auth opened its ldaps bind with TLS certificate verification
    # disabled (OPT_X_TLS_REQUIRE_CERT -> OPT_X_TLS_NEVER) and, worse, set it
    # through a process-wide ldap.set_option() at import time, silently
    # downgrading certificate checking for every python-ldap user in the
    # process (a coexisting ldap_auth included). Verification must be on by
    # default and, when a self-signed cert genuinely has to be accepted,
    # disabled only on the freeipa connection.
    _MODNAME = "gluon.contrib.login_methods.freeipa_auth"

    def setUp(self):
        self.captured = {}
        self._saved = {
            k: sys.modules.get(k)
            for k in ("ldap", "ldap.filter", "ldap.dn", self._MODNAME)
        }
        ldap_mod, filter_mod, dn_mod = _make_fake_ldap(self.captured)
        sys.modules["ldap"] = ldap_mod
        sys.modules["ldap.filter"] = filter_mod
        sys.modules["ldap.dn"] = dn_mod
        sys.modules.pop(self._MODNAME, None)
        self.ldap = ldap_mod
        self.mod = importlib.import_module(self._MODNAME)
        self._never = (ldap_mod.OPT_X_TLS_REQUIRE_CERT, ldap_mod.OPT_X_TLS_NEVER)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        sys.modules.pop(self._MODNAME, None)

    def test_import_does_not_touch_global_tls_policy(self):
        self.assertNotIn("global_set_option", self.captured)

    def test_default_verifies_certificate(self):
        auth = self.mod.freeipa_auth("ipa.example", "dc=x", "admins")
        auth("alice", "pw")
        # neither the connection nor the whole process gets verification off
        self.assertNotIn(self._never, self.captured.get("conn_set_option", []))
        self.assertNotIn("global_set_option", self.captured)

    def test_self_signed_opt_in_is_scoped_to_the_connection(self):
        auth = self.mod.freeipa_auth(
            "ipa.example", "dc=x", "admins", self_signed_certificate=True
        )
        auth("alice", "pw")
        self.assertIn(self._never, self.captured.get("conn_set_option", []))
        # opting in must still not leak into the process-wide policy
        self.assertNotIn("global_set_option", self.captured)


def _make_fake_smtplib(captured):
    """Minimal fake ``smtplib`` recording the context passed to starttls and
    the credentials handed to login, so email_auth can be driven without a
    real SMTP server."""
    import ssl as _ssl

    class SMTPException(Exception):
        pass

    class SMTP(object):
        def __init__(self, host, port, *a, **k):
            captured["server"] = (host, port)

        def ehlo(self, *a, **k):
            pass

        def starttls(self, *a, **k):
            captured.setdefault("starttls_calls", []).append(k.get("context"))

        def login(self, email, password):
            captured["login"] = (email, password)

        def sendmail(self, *a, **k):
            return {}

        def quit(self):
            pass

    fake = types.ModuleType("smtplib")
    fake.SMTP = SMTP
    fake.SMTPException = SMTPException
    fake._ssl = _ssl
    return fake


class TestEmailAuthTLSVerification(unittest.TestCase):
    # email_auth authenticates by binding to the user's own mail provider with
    # their real password. It called smtplib.SMTP.starttls() with no context,
    # so the TLS layer used ssl._create_stdlib_context() (check_hostname=False,
    # verify_mode=CERT_NONE) and never validated the server certificate: an
    # on-path attacker presenting a forged cert captured the credentials.
    _MODNAME = "gluon.contrib.login_methods.email_auth"

    def setUp(self):
        self.captured = {}
        self.mod = importlib.import_module(self._MODNAME)
        self._saved_smtplib = self.mod.smtplib
        self.mod.smtplib = _make_fake_smtplib(self.captured)

    def tearDown(self):
        self.mod.smtplib = self._saved_smtplib

    def test_starttls_uses_verifying_context(self):
        auth = self.mod.email_auth("smtp.gmail.com:587", "@gmail.com")
        self.assertTrue(auth("victim@gmail.com", "s3cret"))
        contexts = self.captured.get("starttls_calls", [])
        self.assertEqual(len(contexts), 1)
        ctx = contexts[0]
        self.assertIsInstance(ctx, ssl.SSLContext)
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

    def test_valid_login_still_succeeds(self):
        auth = self.mod.email_auth("smtp.gmail.com:587", "@gmail.com")
        self.assertTrue(auth("victim@gmail.com", "s3cret"))
        self.assertEqual(self.captured.get("login"), ("victim@gmail.com", "s3cret"))


class TestFreeIPAAuthSecurity(unittest.TestCase):
    # freeipa_auth binds as "uid=<username>,cn=users,<basedn>" with the
    # submitted password. Its blank-credential guard only compared against "",
    # so a None password reached bind_s() as an RFC 4513 5.1.2 unauthenticated
    # bind and logged the account in without a password.
    _MODNAME = "gluon.contrib.login_methods.freeipa_auth"

    def setUp(self):
        self.captured = {}
        self._saved = {
            k: sys.modules.get(k)
            for k in ("ldap", "ldap.filter", "ldap.dn", self._MODNAME)
        }
        ldap_mod, filter_mod, dn_mod = _make_fake_ldap(self.captured)
        sys.modules["ldap"] = ldap_mod
        sys.modules["ldap.filter"] = filter_mod
        sys.modules["ldap.dn"] = dn_mod
        sys.modules.pop(self._MODNAME, None)
        self.mod = importlib.import_module(self._MODNAME)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        sys.modules.pop(self._MODNAME, None)

    def test_blank_password_rejected_before_bind(self):
        auth = self.mod.freeipa_auth(
            server="ipa.example", basedn="dc=x", group="admins"
        )
        for blank in (None, "", b""):
            self.captured.clear()
            self.assertFalse(auth("alice", blank))
            self.assertNotIn("binds", self.captured)
            self.assertNotIn("initialized", self.captured)

    def test_valid_login_still_succeeds(self):
        auth = self.mod.freeipa_auth(
            server="ipa.example", basedn="dc=x", group="admins"
        )
        self.assertTrue(auth("alice", "s3cret"))
        self.assertEqual(
            self.captured.get("binds"), [("uid=alice,cn=users,dc=x", "s3cret")]
        )


if __name__ == "__main__":
    unittest.main()
