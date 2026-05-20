#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for gluon.form.Form CSRF handling.

Regression for a CSRF bypass: the prior `post_vars._formkey == self.formkey`
check defaulted both sides to `None` when the session had never issued a key
for this form, so the very first POST passed the CSRF check with no token.
"""

import unittest

from gluon import current
from gluon.dal import DAL, Field
from gluon.form import Form
from gluon.storage import Storage


def _make_request(method, post_vars=None):
    return Storage(
        method=method,
        post_vars=Storage(post_vars or {}),
        folder="./",
        application="test",
    )


class TestFormCSRF(unittest.TestCase):
    def setUp(self):
        self.db = DAL("sqlite:memory:")
        self.db.define_table("thing", Field("name", "string"))
        current.session = Storage()

    def tearDown(self):
        self.db.close()
        current.__dict__.clear()

    def test_csrf_bypass_when_no_prior_formkey(self):
        # Session has a formkey for an unrelated form, never for "thing".
        # Attacker POSTs with no _formkey at all.
        current.session._formkeys = {"other": "some-prior-uuid"}
        current.request = _make_request("POST", {"name": "attacker"})

        form = Form(self.db.thing)

        self.assertFalse(form.accepted)
        self.assertEqual(self.db(self.db.thing).count(), 0)

    def test_csrf_bypass_with_empty_session(self):
        # Completely fresh session, no _formkeys dict at all.
        current.request = _make_request("POST", {"name": "attacker"})

        form = Form(self.db.thing)

        self.assertFalse(form.accepted)
        self.assertEqual(self.db(self.db.thing).count(), 0)

    def test_csrf_rejects_none_formkey_param(self):
        # Session has a real key issued for this form, but attacker omits the
        # _formkey parameter. None must not match the stored UUID.
        current.session._formkeys = {"thing": "issued-uuid-1234"}
        current.request = _make_request("POST", {"name": "attacker"})

        form = Form(self.db.thing)

        self.assertFalse(form.accepted)

    def test_csrf_rejects_wrong_formkey(self):
        current.session._formkeys = {"thing": "issued-uuid-1234"}
        current.request = _make_request(
            "POST", {"name": "evil", "_formkey": "guessed-wrong"}
        )

        form = Form(self.db.thing)

        self.assertFalse(form.accepted)

    def test_csrf_accepts_matching_formkey(self):
        current.session._formkeys = {"thing": "issued-uuid-1234"}
        current.request = _make_request(
            "POST", {"name": "legit", "_formkey": "issued-uuid-1234"}
        )

        form = Form(self.db.thing)

        self.assertTrue(form.accepted)

    def test_get_issues_formkey_then_post_accepts(self):
        # GET renders the form and seeds the session key, POST then validates.
        current.request = _make_request("GET")
        rendered = Form(self.db.thing)
        issued = rendered.formkey
        self.assertIsNotNone(issued)

        current.request = _make_request(
            "POST", {"name": "legit", "_formkey": issued}
        )
        submitted = Form(self.db.thing)

        self.assertTrue(submitted.accepted)

    def test_csrf_disabled_allows_no_token(self):
        # csrf=False is the explicit opt-out; behaviour must still let the
        # request through.
        current.request = _make_request("POST", {"name": "ok"})

        form = Form(self.db.thing, csrf=False)

        self.assertTrue(form.accepted)


if __name__ == "__main__":
    unittest.main()
