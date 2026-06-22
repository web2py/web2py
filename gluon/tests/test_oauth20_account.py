#!/bin/python
# -*- coding: utf-8 -*-

"""
Unit tests for gluon.contrib.login_methods.oauth20_account

These cover the OAuth 2.0 CSRF protection (the ``state`` parameter, RFC 6749
section 10.12): the authorization request must carry an unguessable, session
bound state, and an authorization code coming back with a missing or mismatched
state must be rejected *before* it is exchanged for a token (login CSRF / code
injection).
"""

import unittest

from gluon import HTTP
from gluon.globals import current
from gluon.contrib.login_methods.oauth20_account import OAuthAccount
from gluon.storage import Storage

# name of the (name-mangled) opener factory we stub out to detect whether the
# token endpoint was reached without doing any real network I/O
_OPENER_ATTR = "_OAuthAccount__build_url_opener"


class _RecordingOpener(object):
    def __init__(self, reached):
        self._reached = reached

    def open(self, *args, **kwargs):
        self._reached["yes"] = True
        raise RuntimeError("stop after the CSRF gate")

    def close(self):
        pass


def _make_account():
    return OAuthAccount(
        client_id="cid",
        client_secret="secret",
        auth_url="https://provider.example/authorize",
        token_url="https://provider.example/token",
    )


class TestOAuth20State(unittest.TestCase):
    def setUp(self):
        current.session = Storage(token=None)
        current.request = Storage(
            vars=Storage(),
            get_vars=Storage(),
            env=Storage(
                http_host="app.example",
                https="off",
                wsgi_url_scheme="https",
                path_info="/app/default/user/login",
            ),
        )
        self.account = _make_account()
        self.reached = {}
        setattr(self.account, _OPENER_ATTR, lambda uri: _RecordingOpener(self.reached))

    def test_authorization_request_includes_session_bound_state(self):
        # starting the flow redirects to the provider; the redirect must carry a
        # state parameter equal to the value stored in the session
        try:
            self.account.login_url("/welcome")
            self.fail("expected an HTTP redirect to the authorization server")
        except HTTP as e:
            location = e.headers["Location"]
        self.assertTrue(current.session.oauth_state)
        self.assertIn("state=%s" % current.session.oauth_state, location)

    def test_mismatched_state_is_rejected_without_token_exchange(self):
        # an attacker-supplied code with the wrong state must not be honoured
        current.session.oauth_state = "the-expected-state"
        current.request.vars = Storage(code="attacker_code", state="wrong_state")
        self.assertIsNone(self.account.accessToken())
        self.assertNotIn("yes", self.reached)  # token endpoint never reached
        self.assertIsNone(current.session.token)
        self.assertIsNone(current.session.oauth_state)  # single-use

    def test_missing_state_is_rejected(self):
        # no state stored (flow never initiated by this session) -> reject
        current.session.oauth_state = None
        current.request.vars = Storage(code="attacker_code", state="anything")
        self.assertIsNone(self.account.accessToken())
        self.assertNotIn("yes", self.reached)
        self.assertIsNone(current.session.token)

    def test_matching_state_passes_the_csrf_check(self):
        # a code that comes back with the matching state clears the CSRF gate and
        # proceeds to the token endpoint (which our stub records, then aborts)
        current.session.oauth_state = "match-123"
        current.request.vars = Storage(code="good_code", state="match-123")
        try:
            self.account.accessToken()
        except RuntimeError:
            pass
        self.assertTrue(self.reached.get("yes"))
