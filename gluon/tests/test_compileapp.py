# -*- coding: utf-8 -*-

""" Unit tests for compileapp.py """

import unittest
import os
import tempfile
import shutil

from gluon.fileutils import create_app, w2p_pack, w2p_unpack
from gluon.compileapp import compile_application, remove_compiled_application
from gluon.globals import Request
from gluon.admin import (app_compile, app_create, app_cleanup,
    app_uninstall, check_new_version)
from gluon.main import global_settings

test_app_name = '_test_compileapp'
test_app2_name = '_test_compileapp_admin'
test_unpack_dir = None

WEB2PY_VERSION_URL = "http://web2py.com/examples/default/version"

class TestPack(unittest.TestCase):
    """ Tests the compileapp.py module """

    @classmethod
    def setUpClass(cls):
        appdir = os.path.join('applications', test_app_name)
        if not os.path.exists(appdir):
            os.mkdir(appdir)
            create_app(appdir)

    @classmethod
    def tearDownClass(cls):
        appdir = os.path.join('applications', test_app_name)
        if os.path.exists(appdir):
            shutil.rmtree(appdir)
        test_pack = "%s.w2p" % test_app_name
        if os.path.exists(test_pack):
            os.unlink(test_pack)
        if test_unpack_dir:
            shutil.rmtree(test_unpack_dir)

    def test_compile(self):
        cwd = os.getcwd()
        app_path = os.path.join(cwd, 'applications', test_app_name)
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
        request.application = 'a'
        request.controller = 'c'
        request.function = 'f'
        request.folder = 'applications/admin'
        # remove any existing test app
        app_path = os.path.join('applications', test_app2_name)
        if os.path.exists(app_path):
            shutil.rmtree(app_path)

        self.assertTrue(app_create(test_app2_name, request))
        self.assertTrue(os.path.exists('applications/%s/controllers/default.py' % test_app2_name))
        self.assertIsNone(app_compile(test_app2_name, request))
        self.assertTrue(app_cleanup(test_app2_name, request))
        self.assertTrue(app_uninstall(test_app2_name, request))

    def test_check_new_version(self):
        vert = check_new_version(global_settings.web2py_version, WEB2PY_VERSION_URL)
        self.assertNotEqual(vert[0], -1)
