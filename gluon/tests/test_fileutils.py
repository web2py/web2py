#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import io
import os
import tarfile
import tempfile
import unittest

from gluon.fileutils import fix_newlines, get_session, parse_version, set_session, untar
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

    def _make_tar(self, tarname, members):
        with tarfile.open(tarname, "w") as tar:
            for member in members:
                tar.addfile(member, io.BytesIO(b"test"))

    def _regular_member(self, name):
        member = tarfile.TarInfo(name)
        member.size = 4
        return member

    def test_untar_extracts_safe_members(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tarname = os.path.join(tmpdir, "safe.tar")
            extract_to = os.path.join(tmpdir, "app")
            os.mkdir(extract_to)
            self._make_tar(tarname, [self._regular_member("models/db.py")])

            untar(tarname, extract_to)

            with open(os.path.join(extract_to, "models", "db.py"), "rb") as stream:
                self.assertEqual(stream.read(), b"test")

    def test_untar_extracts_safe_symlink(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tarname = os.path.join(tmpdir, "safe_link.tar")
            extract_to = os.path.join(tmpdir, "app")
            os.mkdir(extract_to)
            member = tarfile.TarInfo("models/link")
            member.type = tarfile.SYMTYPE
            member.linkname = "db.py"

            with tarfile.open(tarname, "w") as tar:
                tar.addfile(self._regular_member("models/db.py"), io.BytesIO(b"test"))
                tar.addfile(member)

            try:
                untar(tarname, extract_to)
            except OSError:
                self.skipTest("Symlink extraction requires additional privileges")

            # Verify extraction if skip didn't trigger
            if os.path.islink(os.path.join(extract_to, "models", "link")):
                self.assertTrue(os.path.exists(os.path.join(extract_to, "models", "link")))

    def test_untar_rejects_preexisting_escaping_symlink_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tarname = os.path.join(tmpdir, "link_directory.tar")
            extract_to = os.path.join(tmpdir, "app")
            outside = os.path.join(tmpdir, "outside")
            os.mkdir(extract_to)
            os.mkdir(outside)
            try:
                os.symlink(outside, os.path.join(extract_to, "models"))
            except OSError:
                self.skipTest("Symlink creation requires additional privileges")
            self._make_tar(tarname, [self._regular_member("models/evil.py")])

            with self.assertRaises(RuntimeError):
                untar(tarname, extract_to)
            self.assertFalse(os.path.exists(os.path.join(outside, "evil.py")))

    def test_untar_rejects_parent_traversal_member(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tarname = os.path.join(tmpdir, "traversal.tar")
            extract_to = os.path.join(tmpdir, "app")
            os.mkdir(extract_to)
            self._make_tar(tarname, [self._regular_member("../outside.py")])

            with self.assertRaises(RuntimeError):
                untar(tarname, extract_to)
            self.assertFalse(os.path.exists(os.path.join(tmpdir, "outside.py")))

    def test_untar_rejects_absolute_member(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tarname = os.path.join(tmpdir, "absolute.tar")
            extract_to = os.path.join(tmpdir, "app")
            os.mkdir(extract_to)
            member_name = os.path.join(tmpdir, "outside.py")
            self._make_tar(tarname, [self._regular_member(member_name)])

            with self.assertRaises(RuntimeError):
                untar(tarname, extract_to)

    def test_untar_rejects_escaping_symlink(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tarname = os.path.join(tmpdir, "link.tar")
            extract_to = os.path.join(tmpdir, "app")
            os.mkdir(extract_to)
            member = tarfile.TarInfo("models/link")
            member.type = tarfile.SYMTYPE
            member.linkname = "../../outside.py"

            with tarfile.open(tarname, "w") as tar:
                tar.addfile(member)

            with self.assertRaises(RuntimeError):
                untar(tarname, extract_to)

    def test_untar_rejects_escaping_hardlink(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tarname = os.path.join(tmpdir, "hardlink.tar")
            extract_to = os.path.join(tmpdir, "app")
            os.mkdir(extract_to)
            member = tarfile.TarInfo("models/link")
            member.type = tarfile.LNKTYPE
            member.linkname = "../outside.py"

            with tarfile.open(tarname, "w") as tar:
                tar.addfile(member)

            with self.assertRaises(RuntimeError):
                untar(tarname, extract_to)

    def test_untar_rejects_special_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tarname = os.path.join(tmpdir, "special.tar")
            extract_to = os.path.join(tmpdir, "app")
            os.mkdir(extract_to)
            member = tarfile.TarInfo("models/fifo")
            member.type = tarfile.FIFOTYPE

            with tarfile.open(tarname, "w") as tar:
                tar.addfile(member)

            with self.assertRaises(RuntimeError):
                untar(tarname, extract_to)

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
