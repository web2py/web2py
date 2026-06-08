#!/bin/python
# -*- coding: utf-8 -*-

"""
Unit tests for gluon.contrib.login_methods
"""

import importlib
import sys
import types
import unittest


def _rfc4515_escape(value, escape_mode=0):
    # reference implementation of ldap.filter.escape_filter_chars (RFC 4515)
    repl = {"\\": "\\5c", "*": "\\2a", "(": "\\28", ")": "\\29", "\x00": "\\00"}
    return "".join(repl.get(c, c) for c in value)


def _make_fake_ldap(captured):
    """Build a minimal fake ``ldap`` module so ldap_auth can be imported and
    driven without python-ldap / a live directory server."""
    ldap_mod = types.ModuleType("ldap")
    ldap_mod.OPT_REFERRALS = 0
    ldap_mod.SCOPE_SUBTREE = 2
    ldap_mod.SCOPE_BASE = 0
    ldap_mod.OPT_X_TLS_REQUIRE_CERT = 0
    ldap_mod.OPT_X_TLS_NEVER = 0
    ldap_mod.set_option = lambda *a, **k: None

    class LDAPError(Exception):
        pass

    class INVALID_CREDENTIALS(LDAPError):
        pass

    ldap_mod.LDAPError = LDAPError
    ldap_mod.INVALID_CREDENTIALS = INVALID_CREDENTIALS

    class FakeCon(object):
        def simple_bind_s(self, dn, pw):
            captured.setdefault("binds", []).append((dn, pw))

        def search_s(self, base, scope, filterstr="(objectClass=*)", attrs=None):
            captured["filter"] = filterstr
            return [("uid=alice," + base, {})]

        def unbind(self):
            pass

        def start_tls_s(self):
            pass

    ldap_mod.initialize = lambda uri: FakeCon()

    filter_mod = types.ModuleType("ldap.filter")
    filter_mod.escape_filter_chars = _rfc4515_escape
    ldap_mod.filter = filter_mod
    return ldap_mod, filter_mod


class TestLdapAuthFilterInjection(unittest.TestCase):
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
            for k in ("ldap", "ldap.filter", self._MODNAME)
        }
        ldap_mod, filter_mod = _make_fake_ldap(self.captured)
        sys.modules["ldap"] = ldap_mod
        sys.modules["ldap.filter"] = filter_mod
        sys.modules.pop(self._MODNAME, None)
        self.mod = importlib.import_module(self._MODNAME)
        self.escape = filter_mod.escape_filter_chars

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
