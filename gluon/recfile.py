#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Generates names for cache and session files
--------------------------------------------
"""
import builtins
import os


def safe_join(root, *paths):
    root = os.path.realpath(root)
    target = os.path.realpath(os.path.join(root, *paths))
    if not is_within(target, root):
        raise IOError("unsafe recfile path")
    return target


def is_within(target, root):
    target = os.path.normcase(os.path.realpath(target))
    root = os.path.normcase(os.path.realpath(root))
    if hasattr(os.path, "commonpath"):
        try:
            return os.path.commonpath([target, root]) == root
        except ValueError:
            return False
    try:
        relative = os.path.relpath(target, root)
    except ValueError:
        return False
    return not (relative == os.pardir or relative.startswith(os.pardir + os.sep))


def existing_inside_root(filename, path):
    root = os.path.realpath(path)
    target = os.path.realpath(filename)
    return is_within(target, root) and os.path.exists(target)


def generate(filename, depth=2, base=512):
    if os.path.sep in filename:
        path, filename = os.path.split(filename)
    else:
        path = None
    dummyhash = (
        sum(ord(c) * 256 ** (i % 4) for i, c in enumerate(filename)) % base**depth
    )
    folders = []
    for level in range(depth - 1, -1, -1):
        code, dummyhash = divmod(dummyhash, base**level)
        folders.append("%03x" % code)
    folders.append(filename)
    if path:
        folders.insert(0, path)
    return os.path.join(*folders)


def exists(filename, path=None):
    if path is None and os.path.exists(filename):
        return True
    if path is None:
        path, filename = os.path.split(filename)
        fullfilename = os.path.join(path, generate(filename))
    else:
        if existing_inside_root(filename, path):
            return True
        try:
            fullfilename = safe_join(path, generate(filename))
        except IOError:
            return False
    if os.path.exists(fullfilename):
        return True
    return False


def remove(filename, path=None):
    if path is None and os.path.exists(filename):
        return os.unlink(filename)
    if path is None:
        path, filename = os.path.split(filename)
        fullfilename = os.path.join(path, generate(filename))
    else:
        if existing_inside_root(filename, path):
            return os.unlink(os.path.realpath(filename))
        fullfilename = safe_join(path, generate(filename))
    if os.path.exists(fullfilename):
        return os.unlink(fullfilename)
    raise IOError


def open(filename, mode="r", path=None):
    if not path:
        path, filename = os.path.split(filename)
        join = os.path.join
    else:
        join = safe_join
        if not mode.startswith("w") and existing_inside_root(filename, path):
            return builtins.open(os.path.realpath(filename), mode)
    fullfilename = None
    if not mode.startswith("w"):
        fullfilename = join(path, filename)
        if not os.path.exists(fullfilename):
            fullfilename = None
    if not fullfilename:
        fullfilename = join(path, generate(filename))
        if mode.startswith("w") and not os.path.exists(os.path.dirname(fullfilename)):
            os.makedirs(os.path.dirname(fullfilename))
    return builtins.open(fullfilename, mode)
