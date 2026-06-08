#!/bin/python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.serializers
"""

import datetime
import decimal
import unittest

from gluon.html import SPAN
# careful with the import path 'cause of isinstance() checks
from gluon.languages import TranslatorFactory
import gluon.serializers as serializers
from gluon.serializers import *
from gluon.storage import Storage


class TestSerializers(unittest.TestCase):
    def testYAMLUsesSafeLoader(self):
        class FakeYaml(object):
            def load(self, data):
                raise AssertionError("unsafe YAML loader was called")

            def safe_load(self, data):
                return {"safe": data}

        original_have_yaml = serializers.have_yaml
        original_yamlib = serializers.yamlib if serializers.have_yaml else None
        try:
            serializers.have_yaml = True
            serializers.yamlib = FakeYaml()
            self.assertEqual(serializers.loads_yaml("x: 1"), {"safe": "x: 1"})
        finally:
            serializers.have_yaml = original_have_yaml
            if original_yamlib is not None:
                serializers.yamlib = original_yamlib

    def testYAML(self):
        if not have_yaml:
            self.skipTest("No YAML serializer available")

        data = {"a": [1, 2], "b": {"c": True}}
        self.assertEqual(loads_yaml(yaml(data)), data)

    def testYAMLRejectsPythonObjectTags(self):
        if not have_yaml:
            self.skipTest("No YAML serializer available")

        payload = "!!python/object/apply:builtins.exec ['x = 1']"
        with self.assertRaises(yamlib.YAMLError):
            loads_yaml(payload)

    def testICSEscapesUntrustedFields(self):
        # a newline in an attacker-controlled field must not be able to close
        # the current property/component and inject new iCalendar content
        events = [
            {
                "id": "1",
                "title": "Lunch\nEND:VEVENT\nBEGIN:VEVENT\nUID:evil\n"
                "SUMMARY:INJECTED\nATTENDEE:mailto:victim@example.com",
                "start_datetime": datetime.datetime(2024, 1, 1, 10, 0, 0),
                "stop_datetime": datetime.datetime(2024, 1, 1, 11, 0, 0),
            }
        ]
        out = ics(events, title="My Cal")
        lines = out.split("\n")
        # exactly one real event, and no injected ATTENDEE/extra UID lines
        self.assertEqual(len([ln for ln in lines if ln == "BEGIN:VEVENT"]), 1)
        self.assertEqual(len([ln for ln in lines if ln == "END:VEVENT"]), 1)
        self.assertEqual(len([ln for ln in lines if ln.startswith("ATTENDEE")]), 0)
        self.assertEqual(len([ln for ln in lines if ln.startswith("UID:")]), 1)
        # the smuggled payload survives only as escaped TEXT on the SUMMARY line
        summary = [ln for ln in lines if ln.startswith("SUMMARY:")][-1]
        self.assertIn("\\n", summary)

    def testICSTextEscaping(self):
        # RFC 5545 section 3.3.11: backslash, semicolon and comma are escaped
        events = [
            {
                "id": "a;b,c",
                "title": "Tea, Coffee; and back\\slash",
                "start_datetime": datetime.datetime(2024, 1, 1, 0, 0, 0),
                "stop_datetime": datetime.datetime(2024, 1, 1, 1, 0, 0),
            }
        ]
        out = ics(events)
        self.assertIn("UID:a\\;b\\,c", out)
        self.assertIn("SUMMARY:Tea\\, Coffee\\; and back\\\\slash", out)

    def testICSUriStripsNewlines(self):
        # a URL property value must not be able to inject a new line either
        events = [
            {
                "id": "1",
                "title": "ok",
                "start_datetime": datetime.datetime(2024, 1, 1, 0, 0, 0),
                "stop_datetime": datetime.datetime(2024, 1, 1, 1, 0, 0),
            }
        ]
        out = ics(events, link="http://x/[id]\r\nATTENDEE:mailto:victim@example.com")
        self.assertEqual(len([ln for ln in out.split("\n") if ln.startswith("ATTENDEE")]), 0)
        self.assertIn("URL:http://x/1ATTENDEE:mailto:victim@example.com", out)

    def testXMLRejectsUntrustedKeys(self):
        # xml_rec turns dict keys into tag names; rather than emit malformed /
        # injectable markup from an attacker-controlled key, the serialiser
        # rejects any key that is not a valid XML element name (fail closed)
        with self.assertRaises(ValueError):
            serializers.xml({"data": {'k]><script>alert(1)</script><x y=': "v"}})

    def testXMLKeepsValidKeys(self):
        # keys that are already valid XML names are emitted verbatim
        out = serializers.xml({"book": {"title": "ok", "qty": 3}})
        self.assertIn("<book>", out)
        self.assertIn("<title>ok</title>", out)
        self.assertIn("<qty>3</qty>", out)
        # values are still xml-escaped as before
        self.assertIn("&", serializers.xml({"a": "x & y"}))

    def testXMLSafeKey(self):
        # already-valid names pass through unchanged
        self.assertEqual(serializers.xml_safe_key("book"), "book")
        self.assertEqual(serializers.xml_safe_key("ns:item"), "ns:item")
        # the empty-key "no wrapper element" sentinel is preserved
        self.assertEqual(serializers.xml_safe_key(""), "")
        # invalid names are rejected, not rewritten
        with self.assertRaises(ValueError):
            serializers.xml_safe_key('a"><b')
        # a name may not start with a digit
        with self.assertRaises(ValueError):
            serializers.xml_safe_key("1x")

    def testJSON(self):
        # the main and documented "way" is to use the json() function
        # it has a few corner-cases that make json() be somewhat
        # different from the standard buyt being compliant
        # it's just a matter of conventions

        # incompatible spacing, newer simplejson already account
        # for this but it's still better to remember
        weird = {"JSON": "ro" + "\u2028" + "ck" + "\u2029" + "s!"}
        rtn = json(weird)
        self.assertEqual(rtn, '{"JSON": "ro\\u2028ck\\u2029s!"}')
        # date, datetime, time strictly as strings in isoformat, minus the T
        objs = [
            datetime.datetime(2014, 1, 1, 12, 15, 35),
            datetime.date(2014, 1, 1),
            datetime.time(12, 15, 35),
        ]
        iso_objs = [obj.isoformat()[:19].replace("T", " ") for obj in objs]
        json_objs = [json(obj) for obj in objs]
        json_web2pyfied = [json(obj) for obj in iso_objs]
        self.assertEqual(json_objs, json_web2pyfied)
        # int or long int()ified
        # self.assertEqual(json(1), json(1))
        # decimal stringified
        obj = {"a": decimal.Decimal("4.312312312312")}
        self.assertEqual(json(obj), '{"a": 4.312312312312}')
        # lazyT translated
        T = TranslatorFactory("", "en")
        lazy_translation = T("abc")
        self.assertEqual(json(lazy_translation), '"abc"')
        # html helpers are xml()ed before too
        self.assertEqual(json(SPAN("abc"), cls=None), '"<span>abc</span>"')
        self.assertEqual(
            json(SPAN("abc")), '"\\u003cspan\\u003eabc\\u003c/span\\u003e"'
        )
        # unicode keys make a difference with loads_json
        base = {"è": 1, "b": 2}
        base_enc = json(base)
        base_load = loads_json(base_enc)
        self.assertEqual(base, base_load)
        # if unicode_keys is false, the standard behaviour is assumed
        base_load = loads_json(base_enc, unicode_keys=False)
        self.assertEqual(base, base_load)
