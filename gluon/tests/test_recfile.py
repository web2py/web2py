#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.recfile
"""
import os
import shutil
import tempfile
import unittest
import uuid

from gluon import recfile


class TestRecfile(unittest.TestCase):
    def setUp(self):
        os.mkdir("tests")

    def tearDown(self):
        shutil.rmtree("tests")

    def test_generation(self):
        for k in range(10):
            teststring = "test%s" % k
            filename = os.path.join("tests", str(uuid.uuid4()) + ".test")
            with recfile.open(filename, "w") as g:
                g.write(teststring)
            with recfile.open(filename, "r") as f:
                self.assertEqual(f.read(), teststring)
            is_there = recfile.exists(filename)
            self.assertTrue(is_there)
            recfile.remove(filename)
            is_there = recfile.exists(filename)
            self.assertFalse(is_there)
        for k in range(10):
            teststring = "test%s" % k
            filename = str(uuid.uuid4()) + ".test"
            with recfile.open(filename, "w", path="tests") as g:
                g.write(teststring)
            with recfile.open(filename, "r", path="tests") as f:
                self.assertEqual(f.read(), teststring)
            is_there = recfile.exists(filename, path="tests")
            self.assertTrue(is_there)
            recfile.remove(filename, path="tests")
            is_there = recfile.exists(filename, path="tests")
            self.assertFalse(is_there)
        for k in range(10):
            teststring = "test%s" % k
            filename = os.path.join(
                "tests", str(uuid.uuid4()), str(uuid.uuid4()) + ".test"
            )
            with recfile.open(filename, "w") as g:
                g.write(teststring)
            with recfile.open(filename, "r") as f:
                self.assertEqual(f.read(), teststring)
            is_there = recfile.exists(filename)
            self.assertTrue(is_there)
            recfile.remove(filename)
            is_there = recfile.exists(filename)
            self.assertFalse(is_there)

    def test_existing(self):
        filename = os.path.join("tests", str(uuid.uuid4()) + ".test")
        with open(filename, "w") as g:
            g.write("this file exists")
        self.assertTrue(recfile.exists(filename))
        r = recfile.open(filename, "r")
        self.assertTrue(hasattr(r, "read"))
        r.close()
        recfile.remove(filename, path="tests")
        self.assertFalse(recfile.exists(filename))
        self.assertRaises(IOError, recfile.remove, filename)
        self.assertRaises(IOError, recfile.open, filename, "r")

    def test_path_argument_confines_generated_files(self):
        parent = tempfile.mkdtemp(dir=os.getcwd())
        self.addCleanup(lambda parent=parent: shutil.rmtree(parent, ignore_errors=True))
        sandbox = os.path.join(parent, "sandbox")
        outside_dir = os.path.join(parent, "outside")
        os.mkdir(sandbox)
        os.mkdir(outside_dir)

        outside_name = str(uuid.uuid4()) + ".test"
        outside_path = os.path.join(outside_dir, outside_name)
        with open(outside_path, "w") as g:
            g.write("outside")

        escape_paths = [
            os.path.join("..", "outside", outside_name),
            outside_path,
        ]
        for escape_path in escape_paths:
            self.assertFalse(recfile.exists(escape_path, path=sandbox))
            self.assertRaises(IOError, recfile.open, escape_path, "r", path=sandbox)
            self.assertRaises(IOError, recfile.open, escape_path, "w", path=sandbox)
            self.assertRaises(IOError, recfile.remove, escape_path, path=sandbox)

        with open(outside_path) as g:
            self.assertEqual(g.read(), "outside")

    def test_path_argument_rejects_absolute_filenames(self):
        filename = os.path.abspath(str(uuid.uuid4()) + ".test")

        self.assertRaises(IOError, recfile.open, filename, "w", path="tests")
        self.assertFalse(recfile.exists(filename, path="tests"))
        self.assertRaises(IOError, recfile.remove, filename, path="tests")

    def test_path_argument_handles_root_paths(self):
        root = os.path.abspath(os.sep)

        sandbox = tempfile.mkdtemp(dir=os.getcwd())
        self.addCleanup(lambda sandbox=sandbox: shutil.rmtree(sandbox, ignore_errors=True))

        existing_path = os.path.join(sandbox, "existing.test")
        with open(existing_path, "w") as g:
            g.write("existing")

        with recfile.open(existing_path, "r", path=root) as f:
            self.assertEqual(f.read(), "existing")
        self.assertTrue(recfile.exists(existing_path, path=root))
        recfile.remove(existing_path, path=root)
        self.assertFalse(os.path.exists(existing_path))

        generated_path = os.path.join(sandbox, "generated", "payload.test")
        self.assertFalse(os.path.exists(generated_path))
        with recfile.open(generated_path, "w", path=root) as g:
            g.write("generated")
        with recfile.open(generated_path, "r", path=root) as f:
            self.assertEqual(f.read(), "generated")
        self.assertTrue(recfile.exists(generated_path, path=root))
        self.assertFalse(os.path.exists(generated_path))
        recfile.remove(generated_path, path=root)
        self.assertFalse(recfile.exists(generated_path, path=root))

    def test_is_within_fallback_handles_root_paths(self):
        original_path = recfile.os.path

        class PathShim(object):
            abspath = staticmethod(os.path.abspath)
            dirname = staticmethod(os.path.dirname)
            exists = staticmethod(os.path.exists)
            isabs = staticmethod(os.path.isabs)
            join = staticmethod(os.path.join)
            normcase = staticmethod(os.path.normcase)
            relpath = staticmethod(os.path.relpath)
            realpath = staticmethod(os.path.realpath)
            sep = os.path.sep
            split = staticmethod(os.path.split)
            splitdrive = staticmethod(os.path.splitdrive)
            curdir = os.curdir
            pardir = os.pardir

        try:
            recfile.os.path = PathShim
            parent = tempfile.mkdtemp(dir=os.getcwd())
            self.addCleanup(lambda parent=parent: shutil.rmtree(parent, ignore_errors=True))
            root = os.path.join(parent, "sandbox")
            outside_root = os.path.join(parent, "outside")
            os.mkdir(root)
            os.mkdir(outside_root)
            inside = os.path.join(root, "inside.test")
            outside = os.path.join(outside_root, "outside.test")
            parent = os.path.dirname(root)
            self.assertTrue(recfile.is_within(inside, root))
            self.assertFalse(recfile.is_within(outside, root))
            self.assertFalse(recfile.is_within(parent, root))
        finally:
            recfile.os.path = original_path

    def test_is_within_commonpath_handles_value_error(self):
        """commonpath raises ValueError on incompatible paths (e.g. different drives
        on Windows); is_within must return False rather than propagate it."""
        original_commonpath = os.path.commonpath

        def raising_commonpath(paths):
            raise ValueError("paths on different drives")

        try:
            os.path.commonpath = raising_commonpath
            sandbox = tempfile.mkdtemp(dir=os.getcwd())
            self.addCleanup(lambda s=sandbox: shutil.rmtree(s, ignore_errors=True))
            inside = os.path.join(sandbox, "file.test")
            self.assertFalse(recfile.is_within(inside, sandbox))
        finally:
            os.path.commonpath = original_commonpath

    def test_path_argument_rejects_symlink_escapes(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks are not supported on this platform")

        parent = tempfile.mkdtemp(dir=os.getcwd())
        self.addCleanup(lambda parent=parent: shutil.rmtree(parent, ignore_errors=True))
        sandbox = os.path.join(parent, "sandbox")
        outside_dir = os.path.join(parent, "outside")
        os.mkdir(sandbox)
        os.mkdir(outside_dir)

        outside_file = os.path.join(outside_dir, "outside.test")
        with open(outside_file, "w") as g:
            g.write("outside")

        link_path = os.path.join(sandbox, "escape.test")
        try:
            os.symlink(outside_file, link_path)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(str(exc))

        self.assertFalse(recfile.exists(link_path, path=sandbox))
        self.assertRaises(IOError, recfile.open, link_path, "r", path=sandbox)
        self.assertRaises(IOError, recfile.remove, link_path, path=sandbox)

        # Write mode rewrites the name to a generated (hashed) path, so it never
        # follows the symlink. The write is confined inside the sandbox and the
        # outside file is left untouched.
        with recfile.open(link_path, "w", path=sandbox) as f:
            f.write("confined")

        with open(outside_file) as g:
            self.assertEqual(g.read(), "outside")
