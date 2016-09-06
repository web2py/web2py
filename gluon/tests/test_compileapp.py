#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for utils.py """

import unittest
import os
import shutil

from gluon.compileapp import compile_application, remove_compiled_application
from gluon.fileutils import w2p_pack, w2p_unpack
from gluon.globals import Request
from gluon.admin import app_compile, app_create, app_cleanup, check_new_version
from gluon.admin import app_uninstall
from gluon.main import global_settings


WEB2PY_VERSION_URL = "http://web2py.com/examples/default/version"


class TestPack(unittest.TestCase):
    """ Tests the compileapp.py module """

    def test_compile(self):
        #apps = ['welcome', 'admin', 'examples']
        apps = ['welcome']
        for appname in apps:
            appname_path = os.path.join(os.getcwd(), 'applications', appname)
            compile_application(appname_path)
            remove_compiled_application(appname_path)
            test_path = os.path.join(os.getcwd(), "%s.w2p" % appname)
            unpack_path = os.path.join(os.getcwd(), 'unpack', appname)
            w2p_pack(test_path, appname_path, compiled=True, filenames=None)
            w2p_pack(test_path, appname_path, compiled=False, filenames=None)
            w2p_unpack(test_path, unpack_path)
        return

    def test_admin_compile(self):
        #apps = ['welcome', 'admin', 'examples']
        request = Request(env={})
        request.application = 'a'
        request.controller = 'c'
        request.function = 'f'
        request.folder = 'applications/admin'
        apps = ['welcome']
        for appname in apps:
            appname_path = os.path.join(os.getcwd(), 'applications', appname)
            self.assertEqual(app_compile(appname_path, request), None)
            # remove any existing test_app
            new_app = 'test_app_%s' % (appname)
            if(os.path.exists('applications/%s' % (new_app))):
                shutil.rmtree('applications/%s' % (new_app))
            self.assertEqual(app_create(new_app, request), True)
            self.assertEqual(os.path.exists('applications/test_app_%s/controllers/default.py' % (appname)), True)
            self.assertEqual(app_cleanup(new_app, request), True)
            self.assertEqual(app_uninstall(new_app, request), True)
        self.assertNotEqual(check_new_version(global_settings.web2py_version, WEB2PY_VERSION_URL), -1)
        return
