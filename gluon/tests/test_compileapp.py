# -*- coding: utf-8 -*-

""" Unit tests for compileapp.py """

import os
import shutil
from io import BytesIO
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from gluon.admin import (
    app_cleanup,
    app_compile,
    app_create,
    app_uninstall,
    check_new_version,
    plugin_install,
    safe_deposit_path,
)
from gluon.compileapp import TEST_CODE, compile_application, remove_compiled_application
from gluon.fileutils import create_app, w2p_pack, w2p_unpack
from gluon.globals import Request
from gluon.main import global_settings

test_app_name = "_test_compileapp"
test_app2_name = "_test_compileapp_admin"
test_unpack_dir = None

WEB2PY_VERSION_URL = "http://web2py.com/examples/default/version"


class TestAdminPaths(unittest.TestCase):
    def _make_request(self):
        request = Request(env={})
        request.folder = os.path.join("applications", "admin")
        return request

    def test_plugin_install_rejects_traversal_filename_with_false(self):
        request = self._make_request()

        with patch("gluon.admin.w2p_unpack_plugin") as unpack_plugin:
            result = plugin_install(
                "welcome",
                BytesIO(b"payload"),
                request,
                "web2py.plugin.evil/../../pwn.w2p",
            )

        self.assertFalse(result)
        unpack_plugin.assert_not_called()
        self.assertFalse(os.path.exists(os.path.join("applications", "pwn.w2p")))

    def test_plugin_install_rejects_dot_names_with_false(self):
        request = self._make_request()

        for candidate in ("", ".", ".."):
            with patch("gluon.admin.w2p_unpack_plugin") as unpack_plugin:
                result = plugin_install("welcome", BytesIO(b"payload"), request, candidate)
            self.assertFalse(result)
            unpack_plugin.assert_not_called()

    def test_plugin_install_accepts_safe_basename(self):
        request = self._make_request()

        with patch("gluon.admin.w2p_unpack_plugin") as unpack_plugin, patch(
            "gluon.admin.fix_newlines"
        ) as fix_newlines:
            result = plugin_install(
                "welcome", BytesIO(b"payload"), request, "web2py.plugin.safe.w2p"
            )

        self.assertTrue(result.endswith("deposit/web2py.plugin.safe.w2p"))
        self.assertTrue(os.path.exists(result))
        unpack_plugin.assert_called_once()
        fix_newlines.assert_called_once()
        os.unlink(result)

    def test_plugin_install_cleanup_does_not_raise_when_open_fails(self):
        request = self._make_request()

        with patch("gluon.admin.open", side_effect=IOError("boom")):
            result = plugin_install(
                "welcome", BytesIO(b"payload"), request, "web2py.plugin.safe.w2p"
            )

        self.assertFalse(result)

    def test_plugin_install_cleanup_removes_file_when_unpack_fails(self):
        request = self._make_request()

        with patch("gluon.admin.w2p_unpack_plugin", side_effect=RuntimeError("bad zip")):
            result = plugin_install(
                "welcome", BytesIO(b"payload"), request, "web2py.plugin.safe.w2p"
            )

        self.assertFalse(result)
        deposit_path = safe_deposit_path(request, "web2py.plugin.safe.w2p")
        self.assertFalse(os.path.exists(deposit_path))


class TestPack(unittest.TestCase):
    """Tests the compileapp.py module"""

    @classmethod
    def setUpClass(cls):
        appdir = os.path.join("applications", test_app_name)
        if not os.path.exists(appdir):
            os.mkdir(appdir)
            create_app(appdir)

    @classmethod
    def tearDownClass(cls):
        appdir = os.path.join("applications", test_app_name)
        if os.path.exists(appdir):
            shutil.rmtree(appdir)
        test_pack = "%s.w2p" % test_app_name
        if os.path.exists(test_pack):
            os.unlink(test_pack)
        if test_unpack_dir:
            shutil.rmtree(test_unpack_dir)

    def test_compile(self):
        cwd = os.getcwd()
        app_path = os.path.join(cwd, "applications", test_app_name)
        self.assertIsNone(compile_application(app_path))
        remove_compiled_application(app_path)
        test_pack = os.path.join(cwd, "%s.w2p" % test_app_name)
        w2p_pack(test_pack, app_path, compiled=True, filenames=None)
        w2p_pack(test_pack, app_path, compiled=False, filenames=None)
        global test_unpack_dir
        test_unpack_dir = tempfile.mkdtemp()
        w2p_unpack(test_pack, test_unpack_dir)

    def test_admin_compile(self):
        request = Request(env={})
        request.application = "a"
        request.controller = "c"
        request.function = "f"
        request.folder = "applications/admin"
        # remove any existing test app
        app_path = os.path.join("applications", test_app2_name)
        if os.path.exists(app_path):
            shutil.rmtree(app_path)

        self.assertTrue(app_create(test_app2_name, request))
        self.assertTrue(
            os.path.exists("applications/%s/controllers/default.py" % test_app2_name)
        )
        self.assertIsNone(app_compile(test_app2_name, request))
        self.assertTrue(app_cleanup(test_app2_name, request))
        self.assertTrue(app_uninstall(test_app2_name, request))

    def test_admin_test_runner_no_eval(self):
        self.assertNotIn("eval(", TEST_CODE)

    def test_check_new_version(self):
        # check_new_version normally performs a live network request to
        # WEB2PY_VERSION_URL; mock urlopen so the test is deterministic and
        # does not depend on the remote server being reachable.
        myversion = "2.0.0-stable+timestamp.2020.01.01.00.00.00"
        newer = "9.9.9-stable+timestamp.2099.01.01.00.00.00"
        older = "1.0.0-stable+timestamp.2000.01.01.00.00.00"

        with patch(
            "gluon.admin.urllib.request.urlopen",
            return_value=BytesIO(newer.encode("utf8")),
        ):
            state, version = check_new_version(myversion, WEB2PY_VERSION_URL)
        self.assertEqual(state, True)
        self.assertEqual(version, newer)

        with patch(
            "gluon.admin.urllib.request.urlopen",
            return_value=BytesIO(older.encode("utf8")),
        ):
            state, version = check_new_version(myversion, WEB2PY_VERSION_URL)
        self.assertEqual(state, False)
        self.assertEqual(version, older)

    def test_admin_unzip_path_traversal(self):
        tmpdir = tempfile.mkdtemp()
        try:
            zip_path = os.path.join(tmpdir, "evil.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("web2py/../evil.txt", "bad")
                zf.writestr("web2py/subdir/../../evil2.txt", "bad")
                zf.writestr("web2py/safe.txt", "good")

            from gluon.admin import unzip

            with self.assertRaises(RuntimeError):
                unzip(zip_path, tmpdir, subfolder="web2py")

            self.assertFalse(os.path.exists(os.path.join(tmpdir, "evil.txt")))
            self.assertFalse(os.path.exists(os.path.join(tmpdir, "evil2.txt")))
        finally:
            shutil.rmtree(tmpdir)

    def test_admin_unzip_rejects_preexisting_escaping_symlink_directory(self):
        tmpdir = tempfile.mkdtemp()
        try:
            extract_to = os.path.join(tmpdir, "web2py")
            outside = os.path.join(tmpdir, "outside")
            os.mkdir(extract_to)
            os.mkdir(outside)
            try:
                os.symlink(outside, os.path.join(extract_to, "models"))
            except OSError:
                self.skipTest("Symlink creation requires additional privileges")
            zip_path = os.path.join(tmpdir, "evil.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("web2py/models/evil.py", "bad")

            from gluon.admin import unzip

            with self.assertRaises(RuntimeError):
                unzip(zip_path, extract_to, subfolder="web2py")
            self.assertFalse(os.path.exists(os.path.join(outside, "evil.py")))
        finally:
            shutil.rmtree(tmpdir)
