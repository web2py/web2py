#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
from multiprocessing import freeze_support

# Determine the path of the executable or script
if hasattr(sys, 'frozen'):
    path = os.path.dirname(os.path.abspath(sys.executable))
elif '__file__' in globals():
    path = os.path.dirname(os.path.abspath(__file__))
else:
    path = os.getcwd()

# Process -f (--folder) option
fi = None
if '-f' in sys.argv:
    fi = sys.argv.index('-f')
elif '--folder' in sys.argv:
    fi = sys.argv.index('--folder')

if fi is not None and fi < len(sys.argv) - 1:
    folder = sys.argv[fi + 1]
    if not os.path.isdir(os.path.join(folder, 'gluon')):
        print(f"{sys.argv[0]}: error: bad folder {folder}", file=sys.stderr)
        sys.exit(1)
    path = os.path.abspath(folder)

os.chdir(path)
sys.path = [path] + [p for p in sys.path if p != path]

# Important that this import is after changing the directory
import gluon.widget  # Ensure that gluon is properly installed

if __name__ == '__main__':
    freeze_support()  # Required for multiprocessing on Windows
    # Support for sub-process coverage
    if 'COVERAGE_PROCESS_START' in os.environ:
        try:
            import coverage
            coverage.process_startup()
        except ImportError:
            print('Coverage is not available')
    
    # Start services
    gluon.widget.start()
