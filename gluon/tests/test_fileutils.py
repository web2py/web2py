#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import os
import tempfile
import unittest

from gluon.fileutils import fix_newlines, get_session, parse_version, set_session
from gluon.storage import Storage, load_storage, save_storage


class TestFileUtils(unittest.TestCase):
    def test_parse_version(self):
        # Legacy
        rtn = parse_version("Version 1.99.0 (2011-09-19 08:23:26)")
        self.assertEqual(
            rtn, (1, 99, 0, "dev", datetime.datetime(2011, 9, 19, 8, 23, 26))
        )
        # Semantic
        rtn = parse_version("Version 1.99.0-rc.1+timestamp.2011.09.19.08.23.26")
        self.assertEqual(
            rtn, (1, 99, 0, "rc.1", datetime.datetime(2011, 9, 19, 8, 23, 26))
        )
        # Semantic Stable
        rtn = parse_version("Version 2.9.11-stable+timestamp.2014.09.15.18.31.17")
        self.assertEqual(
            rtn, (2, 9, 11, "stable", datetime.datetime(2014, 9, 15, 18, 31, 17))
        )
        # Semantic Beta
        rtn = parse_version("Version 2.14.1-beta+timestamp.2016.03.21.22.35.26")
        self.assertEqual(
            rtn, (2, 14, 1, "beta", datetime.datetime(2016, 3, 21, 22, 35, 26))
        )

    def test_fix_newlines(self):
        fix_newlines(os.path.dirname(os.path.abspath(__file__)))

    def _make_session_request(self, application, folder, session_id, other_application="admin"):
        return Storage(
            application=application,
            folder=folder,
            cookies={"session_id_" + other_application: Storage(value=session_id)},
        )

    def test_get_session_raises_when_application_matches_other(self):
        request = Storage(application="admin")
        with self.assertRaises(KeyError):
            get_session(request, other_application="admin")

    def test_get_session_returns_empty_storage_on_missing_cookie(self):
        request = Storage(application="welcome", cookies={})
        result = get_session(request, other_application="admin")
        self.assertIsInstance(result, Storage)

    def test_get_session_loads_existing_session_from_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            admin_sessions = os.path.join(tmpdir, "admin", "sessions")
            os.makedirs(admin_sessions)
            session_id = "test_session_123"
            session_file = os.path.join(admin_sessions, session_id)
            expected = Storage(authorized=True, last_time=12345.0)
            save_storage(expected, session_file)

            # up(request.folder) must equal tmpdir, so folder = tmpdir/welcome
            welcome_folder = os.path.join(tmpdir, "welcome")
            request = self._make_session_request("welcome", welcome_folder, session_id)

            result = get_session(request, other_application="admin")
            self.assertTrue(result.authorized)
            self.assertEqual(result.last_time, 12345.0)

    def test_get_session_returns_empty_storage_when_session_file_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            welcome_folder = os.path.join(tmpdir, "welcome")
            request = self._make_session_request("welcome", welcome_folder, "nonexistent_id")
            result = get_session(request, other_application="admin")
            self.assertIsInstance(result, Storage)

    def test_set_session_raises_when_application_matches_other(self):
        request = Storage(application="admin")
        with self.assertRaises(KeyError):
            set_session(request, Storage(), other_application="admin")

    def test_set_session_saves_session_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            admin_sessions = os.path.join(tmpdir, "admin", "sessions")
            os.makedirs(admin_sessions)
            session_id = "test_session_456"
            session_file = os.path.join(admin_sessions, session_id)

            welcome_folder = os.path.join(tmpdir, "welcome")
            request = self._make_session_request("welcome", welcome_folder, session_id)
            session = Storage(authorized=True, last_time=99999.0)

            set_session(request, session, other_application="admin")

            loaded = load_storage(session_file)
            self.assertTrue(loaded.authorized)
            self.assertEqual(loaded.last_time, 99999.0)
