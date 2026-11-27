#!/bin/python
# -*- coding: utf-8 -*-

"""
Unit tests for the event handlers of the helpers when
response.enable_csp() is on
"""

import glob
import os
import re
import unittest
from html.parser import HTMLParser
from unittest import mock

from gluon import fileutils
from gluon.cache import Cache
from gluon.compileapp import build_environment, run_controller_in, run_view_in
from gluon.contrib.login_methods.browserid_account import BrowserID
from gluon.dal import DAL, Field
from gluon.globals import Request, Response, Session, current
from gluon.html import FORM, INPUT, MENU
from gluon.languages import TranslatorFactory
from gluon.sqlhtml import SQLFORM, AutocompleteWidget
from gluon.storage import List
from gluon.tools import Auth, Wiki


class InlineHandlers(HTMLParser):
    """Collects what a nonce cannot cover: on*= attributes and javascript: URLs"""

    def __init__(self):
        HTMLParser.__init__(self)
        self.found = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if re.match("on[a-z]+$", name) or re.match(
                r"\s*javascript:", value or "", re.I
            ):
                self.found.append((tag, name, value))


# the attributes that replace the inline handlers, each bound by web2py.js
ATTRIBUTES = ("redirect", "void", "toggle", "autocomplete", "wiki_media", "query")


def inline_handlers(html):
    parser = InlineHandlers()
    parser.feed(html)
    parser.close()
    return parser.found


def new_request(application="a", controller="c", function="f"):
    request = Request(env={})
    request.application = application
    request.controller = controller
    request.function = function
    request.folder = "applications/%s" % application
    request.env.http_host = "127.0.0.1:8000"
    request.env.remote_addr = "127.0.0.1"
    request.client = request.env.remote_addr
    request.is_local = True
    response = Response()
    session = Session()
    session.connect(request, response)
    current.request = request
    current.response = response
    current.session = session
    current.T = TranslatorFactory("", "en")
    return request


class CSPTestCase(unittest.TestCase):
    # A nonce covers an inline <script> block but not an inline event handler
    # attribute. With response.enable_csp() a helper must therefore render
    # data-w2p_* attributes (bound by web2py.js) and no on*= attribute at all.
    # Without it the helper must keep the handlers it renders today, because
    # an application can carry an older copy of web2py.js: `inline` lists
    # them as (tag, attribute, value).

    def check(self, render, inline, attributes):
        self.assertEqual(inline_handlers(render(None)), inline)
        # report-only too: a report has to describe what enforcement will render
        for policy in ({}, {"report_only": True}):
            html = render(policy)
            self.assertEqual(inline_handlers(html), [])
            self.assertEqual(
                re.findall(r'data-w2p_(?:%s)="[^"]*"' % "|".join(ATTRIBUTES), html),
                attributes,
            )


class TestCSPHandlers(CSPTestCase):
    def setUp(self):
        self.request = new_request()
        self.db = DAL("sqlite:memory")
        self.db.define_table("thing", Field("name"), Field("qty", "integer"))
        self.db.define_table("item", Field("thing", "reference thing"), Field("label"))
        for k in range(5):
            self.db.thing.insert(name="n%s" % k, qty=k)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def render(self, build, policy=None, part=None):
        current.response = Response()
        if policy is not None:
            current.response.enable_csp(**policy)
        html = build().xml()
        return part(html) if part else html

    def check(self, build, inline, attributes, part=None):
        CSPTestCase.check(
            self, lambda policy: self.render(build, policy, part), inline, attributes
        )

    # FORM

    def add_button(self, url="/a/c/f?x=1&y='2'"):
        form = FORM(INPUT(_type="submit", _value="Go"))
        form.add_button("Cancel", url)
        return form

    def confirm(self, url="/a/c/f?x=1&y='2'"):
        return FORM.confirm("OK", {"Back": url})

    @staticmethod
    def buttons(html):
        # what follows is the hidden _formkey, new at each call
        return html[: html.index("<div")]

    def test_FORM_add_button(self):
        self.check(
            self.add_button,
            [
                (
                    "button",
                    "onclick",
                    "window.location=\"/a/c/f?x=1\\u0026y='2'\";return false",
                )
            ],
            ['data-w2p_redirect="/a/c/f?x=1&amp;y=&#x27;2&#x27;"'],
        )

    def test_FORM_confirm(self):
        self.check(
            self.confirm,
            [
                (
                    "input",
                    "onclick",
                    "window.location=\"/a/c/f?x=1\\u0026y='2'\";return false",
                )
            ],
            ['data-w2p_redirect="/a/c/f?x=1&amp;y=&#x27;2&#x27;"'],
            self.buttons,
        )

    def test_FORM_redirect_javascript_url(self):
        # a javascript: URL is script given by the application, and a data
        # attribute must not carry script: it stays the inline handler it is
        # today and the policy of the application decides about it
        script = "javascript:history.back()"
        for build, tag in ((self.add_button, "button"), (self.confirm, "input")):
            for policy in (None, {}, {"report_only": True}):
                html = self.render(lambda: build(script), policy)
                self.assertEqual(inline_handlers(html), [(tag, "onclick", script)])
                self.assertNotIn("data-w2p_redirect", html)

    # MENU

    menu = [
        ("Home", False, "/a/c/home"),
        ("More", True, None, [("Sub", False, "/a/c/sub")]),
    ]

    def test_MENU(self):
        self.check(
            lambda: MENU(self.menu),
            [("a", "onclick", "javascript:void(0);return false;")],
            ['data-w2p_void="true"'],
        )

    def test_MENU_mobile(self):
        self.check(
            lambda: MENU(self.menu, mobile=True),
            [("select", "onchange", "window.location=this.value")],
            ['data-w2p_redirect=""'],
        )

    # response.toolbar

    @staticmethod
    def toolbar_buttons(html):
        # the rest of the toolbar dumps the request and is not reproducible
        return "".join(re.findall("<button.*?</button>", html))

    def test_toolbar(self):
        with mock.patch("gluon.globals.web2py_uuid", return_value="U"):
            self.check(
                lambda: current.response.toolbar(),
                [
                    (
                        "button",
                        "onclick",
                        "document.location='/admin/default/design.html/a'",
                    )
                ]
                + [
                    ("button", "onclick", "jQuery('#%s-U').slideToggle()" % name)
                    for name in (
                        "request",
                        "response",
                        "session",
                        "db-tables",
                        "db-stats",
                    )
                ],
                [
                    'data-w2p_redirect="/admin/default/design.html/a"',
                    'data-w2p_toggle="request-U"',
                    'data-w2p_toggle="response-U"',
                    'data-w2p_toggle="session-U"',
                    'data-w2p_toggle="db-tables-U"',
                    'data-w2p_toggle="db-stats-U"',
                ],
                self.toolbar_buttons,
            )

    # AutocompleteWidget

    def autocomplete(self, field, value, **kwargs):
        widget = AutocompleteWidget(
            self.request, self.db.thing.name, keyword="_ac_%(fieldname)s", **kwargs
        )
        return widget(field, value)

    def test_AutocompleteWidget(self):
        self.check(
            lambda: self.autocomplete(self.db.item.label, "x"),
            [
                (
                    "input",
                    "onblur",
                    "jQuery('#_ac_name_div').delay(500).fadeOut('slow');",
                )
            ],
            ['data-w2p_autocomplete="_ac_name_div"'],
        )

    def test_AutocompleteWidget_reference(self):
        self.check(
            lambda: self.autocomplete(self.db.item.thing, 1, id_field=self.db.thing.id),
            [
                (
                    "input",
                    "onblur",
                    "jQuery('#_ac_name_div').delay(500).fadeOut('slow');",
                )
            ],
            ['data-w2p_autocomplete="_ac_name_div"'],
        )

    # SQLFORM.grid

    def grid(self, page=None, **kwargs):
        self.request.vars.page = page
        return SQLFORM.grid(
            self.db.thing,
            paginate=2,
            user_signature=False,
            deletable=False,
            csv=False,
            **kwargs
        )

    @staticmethod
    def search_form(html):
        return html[html.index("<form") : html.index("</form>")]

    @staticmethod
    def paginator(html):
        return html[html.index('<div class="web2py_paginator') :]

    # the handlers the search of the grid renders today
    open_search = (
        "input",
        "onfocus",
        "jQuery('#w2p_query_fields').change();jQuery('#w2p_query_panel').slideDown();",
    )
    clear_search = ("input", "onclick", "jQuery('#w2p_keywords').val('');")
    select_field = (
        "select",
        "onchange",
        "jQuery('.w2p_query_row').hide();jQuery('#w2p_field_'+"
        "jQuery('#w2p_query_fields').val().replace('.','-')).show();",
    )
    current_page = ("a", "onclick", "return false")

    @staticmethod
    def build_query(*fields):
        handlers = []
        for field in fields:
            handlers += [
                ("input", "onclick", "w2p_build_query('%s','%s')" % (op, field))
                for op in ("new", "and", "or")
            ]
            handlers += [("input", "onclick", "jQuery('#w2p_query_panel').slideUp()")]
        return handlers

    def test_search_menu(self):
        self.check(
            lambda: SQLFORM.search_menu([self.db.thing.name]),
            [self.select_field] + self.build_query("thing.name"),
            [
                'data-w2p_query="w2p select"',
                'data-w2p_query="w2p new thing.name"',
                'data-w2p_query="w2p and thing.name"',
                'data-w2p_query="w2p or thing.name"',
                'data-w2p_query="w2p close"',
            ],
        )

    def test_grid_search_form(self):
        self.check(
            self.grid,
            [self.open_search, self.clear_search],
            ['data-w2p_query="w2p open"', 'data-w2p_query="w2p clear"'],
            self.search_form,
        )

    def test_grid_search_form_not_advanced(self):
        # nothing to open on focus: today's empty onfocus="" stays as it is
        # without CSP and no attribute is rendered with it
        self.check(
            lambda: self.grid(advanced_search=False),
            [("input", "onfocus", ""), self.clear_search],
            ['data-w2p_query="w2p clear"'],
            self.search_form,
        )

    def test_grid_paginator(self):
        # the link of the current page has no href, so it needs no handler
        self.check(
            lambda: self.grid(page="2"),
            [self.current_page],
            [],
            self.paginator,
        )

    def test_grid(self):
        queries = ["w2p open", "w2p clear", "w2p select"]
        for name in ("id", "name", "qty"):
            queries += ["w2p %s thing.%s" % (op, name) for op in ("new", "and", "or")]
            queries += ["w2p close"]
        self.check(
            self.grid,
            [self.open_search, self.clear_search, self.select_field]
            + self.build_query("thing.id", "thing.name", "thing.qty")
            + [self.current_page],
            ['data-w2p_query="%s"' % query for query in queries],
        )

    # Wiki

    def test_wiki_editmedia(self):
        self.request.args = List(["_editmedia", "page"])
        self.request.vars.embedded = "1"
        db = self.db
        auth = Auth(db)
        auth.define_tables(username=True, signature=False)
        auth.user = db.auth_user[
            db.auth_user.insert(username="user1", email="user1@test.com")
        ]
        wiki = Wiki(auth, manage_permissions=False)
        page = db.wiki_page.insert(
            slug="page", title="page", body="", tags=[], can_edit=["everybody"]
        )
        db.wiki_media.insert(wiki_page=page, title="a picture.x", filename="f.png")
        self.check(
            lambda: wiki.editmedia("page")["content"],
            [
                (
                    "a",
                    "onclick",
                    "var c = jQuery('#wiki_page_body'); c.val(c.val() + "
                    "jQuery('<span>@////1/a-picture.png</span>').text()); return false;",
                )
            ],
            ['data-w2p_wiki_media="@////1/a-picture.png"'],
            lambda html: "".join(re.findall("<a [^>]*>copy into source</a>", html)),
        )

    # contrib

    def test_BrowserID_login_form(self):
        def login_form():
            return BrowserID(
                self.request, assertion_post_url="/a/default/user/login"
            ).login_form()

        self.check(
            login_form,
            [
                (
                    "a",
                    "onclick",
                    "javascript:navigator.id.getVerifiedEmail(gotVerifiedEmail) ; return false",
                )
            ],
            [],
        )
        # the click is bound in the nonced script that defines the callback
        html = self.render(login_form, {})
        self.assertIn("jQuery('a.browserid').click(", html)
        self.assertIn('<script nonce="%s">' % current.response.nonce, html)


class TestCSPWelcome(CSPTestCase):
    # the scaffolding application has to work with response.enable_csp() in a
    # model, and to render the handlers it renders today without it

    def setUp(self):
        self.original_check_credentials = fileutils.check_credentials
        fileutils.check_credentials = lambda request: True
        self.db = DAL("sqlite:memory")
        self.db.define_table("t0", Field("tt"))
        # appadmin lists a hook only if its source is in the application
        code = compile(
            "def index(*a): pass",
            os.path.abspath("applications/welcome/controllers/default.py"),
            "exec",
        )
        hooks = {}
        exec(code, hooks)
        self.db.t0._before_insert.append(hooks["index"])

    def tearDown(self):
        fileutils.check_credentials = self.original_check_credentials
        self.db.close()

    def appadmin(self, function, policy, pattern):
        request = new_request("welcome", "appadmin", function)
        if policy is not None:
            current.response.enable_csp(**policy)
        environment = build_environment(request, current.response, current.session)
        environment["db"] = self.db
        # do not let the view add words to the language files
        environment["T"].is_writable = False
        # the cache page lists keys only when there are some
        environment["cache"] = cache = Cache(request)
        cache.ram("csp", lambda: 1, 60)
        cache.disk("csp", lambda: 1, 60)
        page = run_controller_in("appadmin", function, environment)
        if isinstance(page, dict):
            environment.update(page)
            page = run_view_in(environment)
        self.page = page
        return "".join(re.findall(pattern, page))

    def test_appadmin_hooks(self):
        self.check(
            lambda policy: self.appadmin("hooks", policy, "<a [^>]*>db.t0</a>"),
            [("a", "onclick", "collapse('a_dbt0')")],
            ['data-w2p_toggle="a_dbt0"'],
        )
        self.assertEqual(inline_handlers(self.page), [])

    def test_appadmin_ccache(self):
        self.check(
            lambda policy: self.appadmin(
                "ccache", policy, "<button [^>]*>[^<]*Keys</button>"
            ),
            [
                (
                    "button",
                    "onclick",
                    'jQuery("#%s_keys").toggle().toggleClass( "w2p_hidden" );' % name,
                )
                for name in ("all", "ram", "disk")
            ],
            [
                'data-w2p_toggle="all_keys"',
                'data-w2p_toggle="ram_keys"',
                'data-w2p_toggle="disk_keys"',
            ],
        )
        self.assertEqual(inline_handlers(self.page), [])
        # the hand-written blocks of the views carry the nonce of the response
        nonce = current.response.nonce
        for tag in re.findall(r"<(?:script|style)\b[^>]*>", self.page):
            self.assertTrue("src=" in tag or 'nonce="%s"' % nonce in tag, tag)

    def test_views_inline_blocks_have_a_nonce(self):
        # hand-written <script> and <style> blocks need the nonce of the
        # response; a <script src=...> is covered by 'self'
        missing = []
        views = os.path.join("applications", "welcome", "views")
        for path in sorted(glob.glob(os.path.join(views, "**", "*.*"), recursive=True)):
            with open(path, encoding="utf8") as view:
                for number, line in enumerate(view, 1):
                    for tag in re.findall(r"<(?:script|style)\b[^>]*>", line, re.I):
                        if "src=" not in tag and "response.nonce" not in line:
                            missing.append(
                                "%s:%s" % (os.path.relpath(path, views), number)
                            )
        self.assertEqual(missing, [])

    def test_web2py_js_binds_the_attributes(self):
        # every attribute the helpers render needs its listener in the copies
        # of web2py.js used by the applications that enable CSP
        for application in ("welcome", "admin"):
            path = os.path.join(
                "applications", application, "static", "js", "web2py.js"
            )
            with open(path, encoding="utf8") as script:
                source = script.read()
            missing = [n for n in ATTRIBUTES if "[data-w2p_%s]" % n not in source]
            self.assertEqual(missing, [], path)
