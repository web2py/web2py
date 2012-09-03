#!/usr/bin/env python
# -*- coding: utf-8 -*-

import __builtin__
import os
import re
import sys
import threading

# Install the new import function:
def custom_import_install(web2py_path):
    global _web2py_importer
    global _web2py_path
    if isinstance(__builtin__.__import__, _Web2pyImporter):
        return #aready installed
    _web2py_path = web2py_path
    _web2py_importer = _Web2pyImporter(web2py_path)
    __builtin__.__import__ = _web2py_importer

def is_tracking_changes():
    """
    @return: True: neo_importer is tracking changes made to Python source
    files. False: neo_import does not reload Python modules.
    """

    global _is_tracking_changes
    return _is_tracking_changes

def track_changes(track=True):
    """
    Tell neo_importer to start/stop tracking changes made to Python modules.
    @param track: True: Start tracking changes. False: Stop tracking changes.
    """

    global _is_tracking_changes
    global _web2py_importer
    global _web2py_date_tracker_importer
    assert track is True or track is False, "Boolean expected."
    if track == _is_tracking_changes:
        return
    if track:
        if not _web2py_date_tracker_importer:
            _web2py_date_tracker_importer = \
                _Web2pyDateTrackerImporter(_web2py_path)
        __builtin__.__import__ = _web2py_date_tracker_importer
    else:
        __builtin__.__import__ = _web2py_importer
    _is_tracking_changes = track

_STANDARD_PYTHON_IMPORTER = __builtin__.__import__ # Keep standard importer
_web2py_importer = None # The standard web2py importer
_web2py_date_tracker_importer = None # The web2py importer with date tracking
_web2py_path = None # Absolute path of the web2py directory

_is_tracking_changes = False # The tracking mode

class _BaseImporter(object):
    """
    The base importer. Dispatch the import the call to the standard Python
    importer.
    """

    def begin(self):
        """
        Many imports can be made for a single import statement. This method
        help the management of this aspect.
        """

    def __init__(self):
        self._STANDARD_PYTHON_IMPORTER = _STANDARD_PYTHON_IMPORTER
    def __call__(self, name, globals=None, locals=None,
                 fromlist=None, level=-1):
        """
        The import method itself.
        """
        return self._STANDARD_PYTHON_IMPORTER(name,
                                         globals,
                                         locals,
                                         fromlist,
                                         level)

    def end(self):
        """
        Needed for clean up.
        """


class _DateTrackerImporter(_BaseImporter):
    """
    An importer tracking the date of the module files and reloading them when
    they have changed.
    """

    _PACKAGE_PATH_SUFFIX = os.path.sep+"__init__.py"

    def __init__(self):
        super(_DateTrackerImporter, self).__init__()
        self._import_dates = {} # Import dates of the files of the modules
        # Avoid reloading cause by file modifications of reload:
        self._tl = threading.local()
        self._tl._modules_loaded = None

    def begin(self):
        self._tl._modules_loaded = set()

    def __call__(self, name, globals=None, locals=None,
                 fromlist=None, level=-1):
        """
        The import method itself.
        """

        globals = globals or {}
        locals = locals or {}
        fromlist = fromlist or []

        call_begin_end = self._tl._modules_loaded is None
        if call_begin_end:
            self.begin()
        try:
            self._tl.globals = globals
            self._tl.locals = locals
            self._tl.level = level

            # Check the date and reload if needed:
            self._update_dates(name, fromlist)

            # Try to load the module and update the dates if it works:
            result = super(_DateTrackerImporter, self) \
              .__call__(name, globals, locals, fromlist, level)
            # Module maybe loaded for the 1st time so we need to set the date
            self._update_dates(name, fromlist)
            return result
        except Exception:
            raise # Don't hide something that went wrong
        finally:
            if call_begin_end:
                self.end()

    def _update_dates(self, name, fromlist):
        """
        Update all the dates associated to the statement import. A single
        import statement may import many modules.
        """

        self._reload_check(name)
        if fromlist:
            for fromlist_name in fromlist:
                self._reload_check("%s.%s" % (name, fromlist_name))

    def _reload_check(self, name):
        """
        Update the date associated to the module and reload the module if
        the file has changed.
        """

        module = sys.modules.get(name)
        file = self._get_module_file(module)
        if file:
            date = self._import_dates.get(file)
            new_date = None
            reload_mod = False
            mod_to_pack = False # Module turning into a package? (special case)
            try:
                new_date = os.path.getmtime(file)
            except:
                self._import_dates.pop(file, None)  # Clean up
                # Handle module changing in package and
                #package changing in module:
                if file.endswith(".py"):
                    # Get path without file ext:
                    file = os.path.splitext(file)[0]
                    reload_mod = os.path.isdir(file) \
                      and os.path.isfile(file+self._PACKAGE_PATH_SUFFIX)
                    mod_to_pack = reload_mod
                else: # Package turning into module?
                    file += ".py"
                    reload_mod = os.path.isfile(file)
                if reload_mod:
                    new_date = os.path.getmtime(file) # Refresh file date
            if reload_mod or not date or new_date > date:
                self._import_dates[file] = new_date
            if reload_mod or (date and new_date > date):
                if module not in self._tl._modules_loaded:
                    if mod_to_pack:
                        # Module turning into a package:
                        mod_name = module.__name__
                        del sys.modules[mod_name] # Delete the module
                        # Reload the module:
                        super(_DateTrackerImporter, self).__call__ \
                          (mod_name, self._tl.globals, self._tl.locals, [],
                           self._tl.level)
                    else:
                        reload(module)
                        self._tl._modules_loaded.add(module)

    def end(self):
        self._tl._modules_loaded = None

    @classmethod
    def _get_module_file(cls, module):
        """
        Get the absolute path file associated to the module or None.
        """

        file = getattr(module, "__file__", None)
        if file:
            # Make path absolute if not:
            #file = os.path.join(cls.web2py_path, file)

            file = os.path.splitext(file)[0]+".py" # Change .pyc for .py
            if file.endswith(cls._PACKAGE_PATH_SUFFIX):
                file = os.path.dirname(file)  # Track dir for packages
        return file

class _Web2pyImporter(_BaseImporter):
    """
    The standard web2py importer. Like the standard Python importer but it
    tries to transform import statements as something like
    "import applications.app_name.modules.x". If the import failed, fall back
    on _BaseImporter.
    """

    _RE_ESCAPED_PATH_SEP = re.escape(os.path.sep)  # os.path.sep escaped for re

    def __init__(self, web2py_path):
        """
        @param web2py_path: The absolute path of the web2py installation.
        """

        global DEBUG
        self.super_class = super(_Web2pyImporter, self)
        self.super_class.__init__()
        self.web2py_path =  web2py_path
        self.__web2py_path_os_path_sep = self.web2py_path+os.path.sep
        self.__web2py_path_os_path_sep_len = len(self.__web2py_path_os_path_sep)
        self.__RE_APP_DIR = re.compile(
          self._RE_ESCAPED_PATH_SEP.join( \
          ( \
            #"^" + re.escape(web2py_path),   # Not working with Python 2.5
            "^(" + "applications",
            "[^",
            "]+)",
            "",
          ) ))

    def _matchAppDir(self, file_path):
        """
        Does the file in a directory inside the "applications" directory?
        """

        if file_path.startswith(self.__web2py_path_os_path_sep):
            file_path = file_path[self.__web2py_path_os_path_sep_len:]
            return self.__RE_APP_DIR.match(file_path)
        return False

    def __call__(self, name, globals=None, locals=None,
                 fromlist=None, level=-1):
        """
        The import method itself.
        """

        globals = globals or {}
        locals = locals or {}
        fromlist = fromlist or []

        self.begin()
        #try:
        # if not relative and not from applications:
        if not name.startswith(".") and level <= 0 \
                    and not name.startswith("applications.") \
                    and isinstance(globals, dict):
            # Get the name of the file do the import
            caller_file_name = os.path.join(self.web2py_path, \
                                            globals.get("__file__", ""))
            # Is the path in an application directory?
            match_app_dir = self._matchAppDir(caller_file_name)
            if match_app_dir:
                try:
                    # Get the prefix to add for the import
                    # (like applications.app_name.modules):
                    modules_prefix = \
                        ".".join((match_app_dir.group(1). \
                        replace(os.path.sep, "."), "modules"))
                    if not fromlist:
                        # import like "import x" or "import x.y"
                        return self.__import__dot(modules_prefix, name,
                            globals, locals, fromlist, level)
                    else:
                        # import like "from x import a, b, ..."
                        return self.super_class \
                            .__call__(modules_prefix+"."+name,
                                    globals, locals, fromlist, level)
                except ImportError, e:
                    try:
                        return self.super_class.__call__(name, globals, locals,
                                                    fromlist, level)
                    except ImportError, e1:
                        raise e
        return self.super_class.__call__(name, globals, locals,
                                                    fromlist, level)

    def __import__dot(self, prefix, name, globals, locals, fromlist,
                      level):
        """
        Here we will import x.y.z as many imports like:
        from applications.app_name.modules import x
        from applications.app_name.modules.x import y
        from applications.app_name.modules.x.y import z.
        x will be the module returned.
        """

        result = None
        for name in name.split("."):
            new_mod = super(_Web2pyImporter, self).__call__(prefix, globals,
                                                        locals, [name], level)
            try:
                result = result or new_mod.__dict__[name]
            except KeyError, e:
                raise ImportError, 'Cannot import module %s' % str(e)
            prefix += "." + name
        return result

class _Web2pyDateTrackerImporter(_Web2pyImporter, _DateTrackerImporter):
    """
    Like _Web2pyImporter but using a _DateTrackerImporter.
    """









