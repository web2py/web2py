#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Support for smart import syntax for web2py applications
-------------------------------------------------------
"""
from gluon._compat import builtin, unicodeT, to_native, reload
import os
import sys
import threading
from gluon import current

NATIVE_IMPORTER = builtin.__import__
INVALID_MODULES = set(('', 'gluon', 'applications', 'custom_import'))

# backward compatibility API

def custom_import_install():
    if builtin.__import__ == NATIVE_IMPORTER:
        INVALID_MODULES.update(sys.modules.keys())
        builtin.__import__ = custom_importer


def track_changes(track=True):
    assert track in (True, False), "must be True or False"
    current.request._custom_import_track_changes = track


def is_tracking_changes():
    return current.request._custom_import_track_changes


# see https://docs.python.org/3/library/functions.html#__import__
# Changed in Python 3.3: Negative values for level are no longer supported,
# which also changes the default value to 0 (was -1)
_DEFAULT_LEVEL = 0 if sys.version_info[:2] >= (3, 3) else -1

def custom_importer(name, globals={}, locals=None, fromlist=(), level=_DEFAULT_LEVEL):
    """
    web2py's custom importer. It behaves like the standard Python importer but
    it tries to transform import statements as something like
    "import applications.app_name.modules.x".
    If the import fails, it falls back on builtin importer.
    """

    # support for non-ascii name
    if isinstance(name, unicodeT):
        name = to_native(name)

    if hasattr(current, 'request') \
            and level <= 0 \
            and name.partition('.')[0] not in INVALID_MODULES:
        # absolute import from application code
        try:
            return NATIVE_IMPORTER(name, globals, locals, fromlist, level)
        except (ImportError, KeyError):
            pass
        if current.request._custom_import_track_changes:
            base_importer = TRACK_IMPORTER
        else:
            base_importer = NATIVE_IMPORTER
        # rstrip for backward compatibility
        items = current.request.folder.rstrip(os.sep).split(os.sep)
        modules_prefix = '.'.join(items[-2:]) + '.modules'
        if not fromlist:
            # "import x" or "import x.y"
            result = None
            for itemname in name.split("."):
                new_mod = base_importer(
                    modules_prefix, globals, locals, (itemname,), level)
                modules_prefix += "." + itemname
                if result is None:
                    try:
                        result = sys.modules[modules_prefix]
                    except KeyError:
                        raise ImportError("No module named %s" % modules_prefix)
            return result
        else:
            # "from x import a, b, ..."
            pname = "%s.%s" % (modules_prefix, name)
            return base_importer(pname, globals, locals, fromlist, level)

    return NATIVE_IMPORTER(name, globals, locals, fromlist, level)


class TrackImporter(object):
    """
    An importer tracking the date of the module files and reloading them when
    they are changed.
    """

    THREAD_LOCAL = threading.local()
    PACKAGE_PATH_SUFFIX = os.path.sep + "__init__.py"

    def __init__(self):
        self._import_dates = {}  # Import dates of the files of the modules

    def __call__(self, name, globals={}, locals=None, fromlist=(), level=_DEFAULT_LEVEL):
        """
        The import method itself.
        """
        # Check the date and reload if needed:
        self._update_dates(name, globals, locals, fromlist, level)
        # Try to load the module and update the dates if it works:
        result = NATIVE_IMPORTER(name, globals, locals, fromlist, level)
        # Module maybe loaded for the 1st time so we need to set the date
        self._update_dates(name, globals, locals, fromlist, level)
        return result

    def _update_dates(self, name, globals, locals, fromlist, level):
        """
        Update all the dates associated to the statement import. A single
        import statement may import many modules.
        """
        self._reload_check(name, globals, locals, level)
        for fromlist_name in fromlist or []:
            pname = "%s.%s" % (name, fromlist_name)
            self._reload_check(pname, globals, locals, level)

    def _reload_check(self, name, globals, locals, level):
        """
        Update the date associated to the module and reload the module if
        the file changed.
        """
        module = sys.modules.get(name)
        file = self._get_module_file(module)
        if file:
            date = self._import_dates.get(file)
            new_date = None
            reload_mod = False
            mod_to_pack = False  # Module turning into a package? (special case)
            try:
                new_date = os.path.getmtime(file)
            except:
                self._import_dates.pop(file, None)  # Clean up
                # Handle module changing in package and
                # package changing in module:
                if file.endswith(".py"):
                    # Get path without file ext:
                    file = os.path.splitext(file)[0]
                    reload_mod = os.path.isdir(file) \
                        and os.path.isfile(file + self.PACKAGE_PATH_SUFFIX)
                    mod_to_pack = reload_mod
                else:  # Package turning into module?
                    file += ".py"
                    reload_mod = os.path.isfile(file)
                if reload_mod:
                    new_date = os.path.getmtime(file)  # Refresh file date
            if reload_mod or not date or new_date > date:
                self._import_dates[file] = new_date
            if reload_mod or (date and new_date > date):
                if mod_to_pack:
                    # Module turning into a package:
                    mod_name = module.__name__
                    del sys.modules[mod_name]  # Delete the module
                    # Reload the module:
                    NATIVE_IMPORTER(mod_name, globals, locals, [], level)
                else:
                    reload(module)

    def _get_module_file(self, module):
        """
        Get the absolute path file associated to the module or None.
        """
        file = getattr(module, "__file__", None)
        if file:
            # Make path absolute if not:
            file = os.path.splitext(file)[0] + ".py"  # Change .pyc for .py
            if file.endswith(self.PACKAGE_PATH_SUFFIX):
                file = os.path.dirname(file)  # Track dir for packages
        return file

TRACK_IMPORTER = TrackImporter()
