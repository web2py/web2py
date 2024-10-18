#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from multiprocessing import freeze_support

def get_path():
    """Get the path of the executable or script."""
    if hasattr(sys, 'frozen'):
        # py2exe
        return os.path.dirname(os.path.abspath(sys.executable))
    elif '__file__' in globals():
        return os.path.dirname(os.path.abspath(__file__))
    else:
        # should never happen
        return os.getcwd()

def process_folder_option():
    """Process the -f (--folder) option."""
    if '-f' in sys.argv:
        fi = sys.argv.index('-f')
        # maybe session2trash arg
        if '-A' in sys.argv and fi > sys.argv.index('-A'):
            return None
    elif '--folder' in sys.argv:
        fi = sys.argv.index('--folder')
    else:
        return None

    if fi is not None and fi < len(sys.argv):
        fi += 1
        folder = sys.argv[fi]
        if not os.path.isdir(os.path.join(folder, 'gluon')):
            print("%s: error: bad folder %s" % (sys.argv[0], folder), file=sys.stderr)
            sys.exit(1)
        return os.path.abspath(folder)
    return None

def main():
    path = get_path()
    folder = process_folder_option()
    if folder is not None:
        path = folder

    os.chdir(path)

    sys.path = [path] + [p for p in sys.path if p != path]

    # important that this import is after the os.chdir
    import gluon.widget

    freeze_support()
    # support for sub-process coverage,
    # see https://coverage.readthedocs.io/en/coverage-4.3.4/subprocess.html
    if 'COVERAGE_PROCESS_START' in os.environ:
        try:
            import coverage
            coverage.process_startup()
        except:
            print('Coverage is not available')
            pass
    # start services
    gluon.widget.start()

if __name__ == '__main__':
    main()
