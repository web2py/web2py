#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import sys
import configparser
from multiprocessing import freeze_support

if hasattr(sys, 'frozen'):
    # py2exe
    path = os.path.dirname(os.path.abspath(sys.executable))
elif '__file__' in globals():
    path = os.path.dirname(os.path.abspath(__file__))
else:
    # should never happen
    path = os.getcwd()

# process -f (--folder) option
if '-f' in sys.argv:
    fi = sys.argv.index('-f')
    # maybe session2trash arg
    if '-A' in sys.argv and fi > sys.argv.index('-A'):
        fi = None
elif '--folder' in sys.argv:
    fi = sys.argv.index('--folder')
else:
    fi = None

if fi and fi < len(sys.argv):
    fi += 1
    folder = sys.argv[fi]
    if not os.path.isdir(os.path.join(folder, 'gluon')):
        print("%s: error: bad folder %s" % (sys.argv[0], folder), file=sys.stderr)
        sys.exit(1)
    path = sys.argv[fi] = os.path.abspath(folder)

os.chdir(path)

sys.path = [path] + [p for p in sys.path if not p == path]

# important that this import is after the os.chdir
import gluon.widget

# Function to read configuration file with UTF-8 encoding
def read_config_with_encoding(file_path, encoding='utf-8'):
    config = configparser.ConfigParser()

    # Open the file with the desired encoding
    with open(file_path, 'r', encoding=encoding) as config_file:
        config.read_file(config_file)

    return config

if __name__ == '__main__':
    freeze_support()

    # Support for sub-process coverage
    if 'COVERAGE_PROCESS_START' in os.environ:
        try:
            import coverage
            coverage.process_startup()
        except:
            print('Coverage is not available')
            pass

    # Read configuration file
    config = read_config_with_encoding('appconfig.ini', encoding='utf-8')

    # Access config values
    try:
        print(config['SectionName']['OptionName'])
    except KeyError:
        print("Error: Section or Option not found in configuration file.")

    # Start services
    gluon.widget.start()
