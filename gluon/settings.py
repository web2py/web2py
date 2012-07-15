"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""

import os
import sys
import platform
from storage import Storage

global_settings = Storage()
settings = global_settings  # legacy compatibility

if not hasattr(os, 'mkdir'):
    global_settings.db_sessions = True

if global_settings.db_sessions is not True:
    global_settings.db_sessions = set()

global_settings.gluon_parent = os.environ.get('web2py_path', os.getcwd())

global_settings.applications_parent = global_settings.gluon_parent

global_settings.app_folders = set()

global_settings.debugging = False

global_settings.is_pypy = hasattr(platform,'python_implementation') and \
                          platform.python_implementation() == 'PyPy'

global_settings.is_jython = 'java' in sys.platform.lower() or \
                            hasattr(sys, 'JYTHON_JAR') or \
                            str(sys.copyright).find('Jython') > 0

version_info = open(os.path.join(global_settings.gluon_parent, 'VERSION'), 'r')
raw_version_string = version_info.read().strip()
version_info.close()

from fileutils import parse_version # we need fileutils import here, because
                                    # fileutils also imports settings
global_settings.web2py_version = parse_version(raw_version_string)


