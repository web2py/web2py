#!/bin/python
# -*- coding: utf-8 -*-

"""
    Unit tests for scripts/update_languages.py
"""
import importlib.util
import io
import os
import unittest

SCRIPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "scripts",
    "update_languages.py",
)

_spec = importlib.util.spec_from_file_location("update_languages", SCRIPT_PATH)
update_languages = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(update_languages)


class TestSafeEval(unittest.TestCase):
    def test_parses_dict_literal(self):
        self.assertEqual(
            update_languages.safe_eval("{'hello': 'world'}"), {"hello": "world"}
        )

    def test_blank_text_returns_none(self):
        self.assertIsNone(update_languages.safe_eval(""))
        self.assertIsNone(update_languages.safe_eval("   "))


class TestWriteFile(unittest.TestCase):
    def _write_and_reload(self, contents):
        buf = io.StringIO()
        buf.close = lambda: None  # write_file() closes the file; keep it readable
        update_languages.write_file(buf, contents)
        return update_languages.safe_eval(buf.getvalue())

    def test_keys_are_sorted_case_insensitively(self):
        buf = io.StringIO()
        buf.close = lambda: None
        update_languages.write_file(
            buf, {"Banana": "banana", "apple": "apple", "Cherry": "cherry"}
        )
        text = buf.getvalue()
        # the header/footer must be present and the dict must round-trip
        self.assertTrue(text.startswith("# -*- coding: utf-8 -*-\n{\n"))
        self.assertTrue(text.rstrip().endswith("}"))
        keys_in_order = [line.split(":", 1)[0].strip() for line in text.splitlines()[2:-1]]
        self.assertEqual(keys_in_order, ["'apple'", "'Banana'", "'Cherry'"])

    def test_content_round_trips(self):
        contents = {"one": "1", "two": "2"}
        self.assertEqual(self._write_and_reload(contents), contents)
