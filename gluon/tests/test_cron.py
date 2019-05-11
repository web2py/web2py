# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et ai:
"""
    Unit tests for cron
"""

import unittest
import os
import shutil
import time

from gluon.newcron import Token, crondance, subprocess_count
from gluon.fileutils import create_app, write_file


test_app_name = '_test_cron'
appdir = os.path.join('applications', test_app_name)

def setUpModule():
    if not os.path.exists(appdir):
        os.mkdir(appdir)
        create_app(appdir)

def tearDownModule():
    if os.path.exists(appdir):
        shutil.rmtree(appdir)


TEST_CRONTAB = """@reboot peppe **applications/%s/cron/test.py
""" %  test_app_name
TEST_SCRIPT = """
from os.path import join as pjoin

with open(pjoin(request.folder, 'private', 'cron_req'), 'w') as f:
    f.write(str(request))
"""
TARGET = os.path.join(appdir, 'private', 'cron_req')

class TestCron(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        for master in (os.path.join(appdir, 'cron.master'), 'cron.master'):
            if os.path.exists(master):
                os.unlink(master)

    def test_Token(self):
        app_path = os.path.join(os.getcwd(), 'applications', test_app_name)
        t = Token(path=app_path)
        self.assertEqual(t.acquire(), t.now)
        self.assertFalse(t.release())
        self.assertIsNone(t.acquire())
        self.assertTrue(t.release())

    def test_crondance(self):
        base = os.path.join(appdir, 'cron')
        write_file(os.path.join(base, 'crontab'), TEST_CRONTAB)
        write_file(os.path.join(base, 'test.py'), TEST_SCRIPT)
        if os.path.exists(TARGET):
            os.unlink(TARGET)
        crondance(os.getcwd(), 'hard', startup=True, apps=[test_app_name])
        # must wait for the cron task, not very reliable
        time.sleep(1)
        while subprocess_count():
            time.sleep(1)
        time.sleep(1)
        self.assertTrue(os.path.exists(TARGET))
