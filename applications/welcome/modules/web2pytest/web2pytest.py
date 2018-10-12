# -*- coding: utf-8 -*-

"""Infrastructure to run an Web2py application under test environment.

We create a temporary file to indicate the application she's running
under test.

By default this file is created in ramdisk (Ubuntu) to speed up
execution.

Web2py applications need this external injection mainly to know
where to create their test database.
"""

import glob
import os

__all__ = ['delete_testfile', 'create_testfile', 'is_running_under_test']

# default_path = "/tmp"
default_path = "/dev/shm/web2py_test"  # native ramdisk is faster
default_filename = "web2py_test_indicator"

_test_filename = None


def testfile_name(appname=None):
    global _test_filename
    if _test_filename:
        return _test_filename

    path = os.path.join(default_path, appname)
    _test_filename = os.path.join(path, default_filename)

    return _test_filename


def create_testfile(appname):
    """Creates a temp file to tell application she's running under a
    test environment.
    """

    fname = testfile_name(appname)

    try:
        # remove previous test data
        import shutil
        shutil.rmtree(os.path.dirname(fname))
    except OSError as e:
        pass

    try:
        os.makedirs(os.path.dirname(fname))
    except OSError as e:
        pass

    try:
        with open(fname, "w+") as f:
            f.write("web2py running in test mode.")
        return True
    except:
        return False


def delete_testfile():
    import shutil

    fname = testfile_name()
    shutil.rmtree(os.path.dirname(fname))
    return True


def testfile_exists(appname):
    fname = testfile_name(appname)

    try:
        if glob.glob(fname):
            return True
        else:
            return False
    except:
        return False


def is_running_under_test(request, appname):
    if request.get('_running_under_test') or testfile_exists(appname):
        return True
    else:
        return False