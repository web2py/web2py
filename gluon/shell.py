# -*- coding: utf-8 -*-

"""
| This file is part of the web2py Web Framework
| Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>,
| limodou <limodou@gmail.com> and srackham <srackham@gmail.com>.
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Web2py environment in the shell
--------------------------------
"""

from __future__ import print_function

import os
import sys
import code
import copy
import logging
import types
import re
import glob
import site
import traceback
import gluon.fileutils as fileutils
from gluon.settings import global_settings
from gluon.compileapp import build_environment, read_pyc, run_models_in
from gluon.restricted import RestrictedError
from gluon.globals import Request, Response, Session
from gluon.storage import Storage, List
from gluon.admin import w2p_unpack
from pydal.base import BaseAdapter
from gluon._compat import iteritems, ClassType, PY2

logger = logging.getLogger("web2py")

if not PY2:
    def execfile(filename, global_vars=None, local_vars=None):
        with open(filename, "rb") as f:
            code = compile(f.read(), filename, 'exec')
            exec(code, global_vars, local_vars)
    raw_input = input


def enable_autocomplete_and_history(adir, env):
    try:
        import rlcompleter
        import atexit
        import readline
    except ImportError:
        pass
    else:
        readline.parse_and_bind("tab: complete")
        history_file = os.path.join(adir, '.pythonhistory')
        try:
            readline.read_history_file(history_file)
        except IOError:
            open(history_file, 'a').close()
        atexit.register(readline.write_history_file, history_file)
        readline.set_completer(rlcompleter.Completer(env).complete)


REGEX_APP_PATH = '(?:.*/)?applications/(?P<a>[^/]+)'

def exec_environment(
    pyfile='',
    request=None,
    response=None,
    session=None,
):
    """Environment builder and module loader.

    Builds a web2py environment and optionally executes a Python file into
    the environment.

    A Storage dictionary containing the resulting environment is returned.
    The working directory must be web2py root -- this is the web2py default.

    """

    if request is None:
        request = Request({})
    if response is None:
        response = Response()
    if session is None:
        session = Session()

    if request.folder is None:
        mo = re.match(REGEX_APP_PATH, pyfile)
        if mo:
            a = mo.group('a')
            request.folder = os.path.abspath(os.path.join('applications', a))
        else:
            request.folder = ''
    env = build_environment(request, response, session, store_current=False)
    if pyfile:
        pycfile = pyfile + 'c'
        if os.path.isfile(pycfile):
            exec(read_pyc(pycfile), env)
        else:
            execfile(pyfile, env)
    return Storage(env)


def env(
    a,
    import_models=False,
    c=None,
    f=None,
    dir='',
    extra_request={},
):
    """
    Returns web2py execution environment for application (a), controller (c),
    function (f).
    If import_models is True the exec all application models into the
    environment.

    extra_request allows you to pass along any extra variables to the request
    object before your models get executed. This was mainly done to support
    web2py_utils.test_runner, however you can use it with any wrapper scripts
    that need access to the web2py environment.
    """

    request = Request({})
    response = Response()
    session = Session()
    request.application = a

    # Populate the dummy environment with sensible defaults.

    if not dir:
        request.folder = os.path.join('applications', a)
    else:
        request.folder = dir
    request.controller = c or 'default'
    request.function = f or 'index'
    response.view = '%s/%s.html' % (request.controller,
                                    request.function)
    cmd_opts = global_settings.cmd_options
    if cmd_opts:
        if not cmd_opts.interfaces:
            ip = cmd_opts.ip
            port = cmd_opts.port
        else:
            first_if = cmd_opts.interfaces[0]
            ip = first_if[0]
            port = first_if[1]
        request.is_shell = cmd_opts.shell is not None
    else:
        ip = '127.0.0.1'; port = 8000
        request.is_shell = False
    request.is_scheduler = False
    request.env.http_host = '%s:%s' % (ip, port)
    request.env.remote_addr = '127.0.0.1'
    request.env.web2py_runtime_gae = global_settings.web2py_runtime_gae

    for k, v in extra_request.items():
        setattr(request, k, v)

    path_info = '/%s/%s/%s' % (a, c, f)
    if request.args:
        path_info = '%s/%s' % (path_info, '/'.join(request.args))
    if request.vars:
        vars = ['%s=%s' % (k, v) if v else '%s' % k
                for (k, v) in iteritems(request.vars)]
        path_info = '%s?%s' % (path_info, '&'.join(vars))
    request.env.path_info = path_info

    # Monkey patch so credentials checks pass.

    def check_credentials(request, other_application='admin'):
        return True

    fileutils.check_credentials = check_credentials

    environment = build_environment(request, response, session)

    if import_models:
        try:
            run_models_in(environment)
        except RestrictedError as e:
            sys.stderr.write(e.traceback + '\n')
            sys.exit(1)

    response._view_environment = copy.copy(environment)

    environment['__name__'] = '__main__'
    return environment


def exec_pythonrc():
    pythonrc = os.environ.get('PYTHONSTARTUP')
    if pythonrc and os.path.isfile(pythonrc):
        def execfile_getlocals(file):
            execfile(file)
            return locals()
        try:
            return execfile_getlocals(pythonrc)
        except NameError:
            pass
    return dict()


def die(msg, exit_status=1, error_preamble=True):
    if error_preamble:
        msg = "%s: error: %s" % (sys.argv[0], msg)
    print(msg, file=sys.stderr)
    sys.exit(exit_status)


def run(
    appname,
    plain=False,
    import_models=False,
    startfile=None,
    bpython=False,
    python_code=None,
    cron_job=False,
    scheduler_job=False,
    force_migrate=False,
    fake_migrate=False):
    """
    Start interactive shell or run Python script (startfile) in web2py
    controller environment. appname is formatted like:

    - a : web2py application name
    - a/c : exec the controller c into the application environment
    - a/c/f : exec the controller c, then the action f
              into the application environment
    - a/c/f?x=y : as above
    """

    (a, c, f, args, vars) = parse_path_info(appname, av=True)
    errmsg = 'invalid application name: %s' % appname
    if not a:
        die(errmsg, error_preamble=False)
    adir = os.path.join('applications', a)

    if not os.path.exists(adir):
        if not cron_job and not scheduler_job and \
            sys.stdin and not sys.stdin.name == '/dev/null':
            confirm = raw_input(
                'application %s does not exist, create (y/n)?' % a)
        else:
            logging.warn('application does not exist and will not be created')
            return
        if confirm.lower() in ('y', 'yes'):
            os.mkdir(adir)
            fileutils.create_app(adir)

    if force_migrate:
        c = 'appadmin' # Load all models (hack already used for appadmin controller)
        import_models = True
        from gluon.dal import DAL
        orig_init = DAL.__init__

        def custom_init(*args, **kwargs):
            kwargs['migrate_enabled'] = True
            kwargs['migrate'] = True
            kwargs['fake_migrate'] = fake_migrate
            logger.info('Forcing migrate_enabled=True')
            orig_init(*args, **kwargs)

        DAL.__init__ = custom_init

    if c:
        import_models = True
    extra_request = {}
    if args:
        extra_request['args'] = args
    if scheduler_job:
        extra_request['is_scheduler'] = True
    if vars:
        # underscore necessary because request.vars is a property
        extra_request['_vars'] = vars
    _env = env(a, c=c, f=f, import_models=import_models, extra_request=extra_request)

    if c:
        pyfile = os.path.join('applications', a, 'controllers', c + '.py')
        pycfile = os.path.join('applications', a, 'compiled',
                                 "controllers.%s.%s.pyc" % (c, f))
        if ((cron_job and os.path.isfile(pycfile))
            or not os.path.isfile(pyfile)):
            exec(read_pyc(pycfile), _env)
        elif os.path.isfile(pyfile):
            execfile(pyfile, _env)
        else:
            die(errmsg, error_preamble=False)

    if f:
        exec('print( %s())' % f, _env)
        return

    _env.update(exec_pythonrc())
    if startfile:
        try:
            ccode = None
            if startfile.endswith('.pyc'):
                ccode = read_pyc(startfile)
                exec(ccode, _env)
            else:
                execfile(startfile, _env)

            if import_models:
                BaseAdapter.close_all_instances('commit')
        except SystemExit:
            print(traceback.format_exc())
            if import_models:
                BaseAdapter.close_all_instances('rollback')
            raise
        except:
            print(traceback.format_exc())
            if import_models:
                BaseAdapter.close_all_instances('rollback')
    elif python_code:
        try:
            exec(python_code, _env)
            if import_models:
                BaseAdapter.close_all_instances('commit')
        except SystemExit:
            print(traceback.format_exc())
            if import_models:
                BaseAdapter.close_all_instances('rollback')
            raise
        except:
            print(traceback.format_exc())
            if import_models:
                BaseAdapter.close_all_instances('rollback')
    elif force_migrate:
        try:
            execfile("scripts/migrator.py", _env)
            if import_models:
                BaseAdapter.close_all_instances('commit')
        except SystemExit:
            print(traceback.format_exc())
            if import_models:
                BaseAdapter.close_all_instances('rollback')
            raise
        except:
            print(traceback.format_exc())
            if import_models:
                BaseAdapter.close_all_instances('rollback')
    else:
        if not plain:
            if bpython:
                try:
                    import bpython
                    bpython.embed(locals_=_env)
                    return
                except:
                    logger.warning(
                        'import bpython error; trying ipython...')
            else:
                try:
                    import IPython
                    if IPython.__version__ > '1.0.0':
                        IPython.start_ipython(user_ns=_env)
                        return
                    elif IPython.__version__ == '1.0.0':
                        from IPython.terminal.embed import InteractiveShellEmbed
                        shell = InteractiveShellEmbed(user_ns=_env)
                        shell()
                        return
                    elif IPython.__version__ >= '0.11':
                        from IPython.frontend.terminal.embed import InteractiveShellEmbed
                        shell = InteractiveShellEmbed(user_ns=_env)
                        shell()
                        return
                    else:
                        # following 2 lines fix a problem with
                        # IPython; thanks Michael Toomim
                        if '__builtins__' in _env:
                            del _env['__builtins__']
                        shell = IPython.Shell.IPShell(argv=[], user_ns=_env)
                        shell.mainloop()
                        return
                except:
                    logger.warning(
                        'import IPython error; use default python shell')
        enable_autocomplete_and_history(adir, _env)
        code.interact(local=_env)


def parse_path_info(path_info, av=False):
    """
    Parses path info formatted like a/c/f where c and f are optional
    and a leading `/` is accepted.
    Return tuple (a, c, f). If invalid path_info a is set to None.
    If c or f are omitted they are set to None.
    If av=True, parse args and vars
    """
    if av:
        vars = None
        if '?' in path_info:
            path_info, query = path_info.split('?', 2)
            vars = Storage()
            for var in query.split('&'):
                (var, val) = var.split('=', 2) if '=' in var else (var, None)
                vars[var] = val
        items = List(path_info.split('/'))
        args = List(items[3:]) if len(items) > 3 else None
        return (items(0), items(1), items(2), args, vars)

    mo = re.match(r'^/?(?P<a>\w+)(/(?P<c>\w+)(/(?P<f>\w+))?)?$',
                  path_info)
    if mo:
        return (mo.group('a'), mo.group('c'), mo.group('f'))
    else:
        return (None, None, None)


def test(testpath, import_models=True, verbose=False):
    """
    Run doctests in web2py environment. testpath is formatted like:

    - a: tests all controllers in application a
    - a/c: tests controller c in application a
    - a/c/f  test function f in controller c, application a

    Where a, c and f are application, controller and function names
    respectively. If the testpath is a file name the file is tested.
    If a controller is specified models are executed by default.
    """

    import doctest
    if os.path.isfile(testpath):
        mo = re.match(REGEX_APP_PATH, testpath)
        if not mo:
            die('test file is not in application directory: %s'
                % testpath)
        a = mo.group('a')
        c = f = None
        files = [testpath]
    else:
        (a, c, f) = parse_path_info(testpath)
        errmsg = 'invalid test path: %s' % testpath
        if not a:
            die(errmsg)
        cdir = os.path.join('applications', a, 'controllers')
        if not os.path.isdir(cdir):
            die(errmsg)
        if c:
            cfile = os.path.join(cdir, c + '.py')
            if not os.path.isfile(cfile):
                die(errmsg)
            files = [cfile]
        else:
            files = glob.glob(os.path.join(cdir, '*.py'))
    for testfile in files:
        globs = env(a, import_models)
        ignores = globs.keys()
        execfile(testfile, globs)

        def doctest_object(name, obj):
            """doctest obj and enclosed methods and classes."""

            if type(obj) in (types.FunctionType, type, ClassType, types.MethodType,
                             types.UnboundMethodType):

                # Reload environment before each test.

                globs = env(a, c=c, f=f, import_models=import_models)
                execfile(testfile, globs)
                doctest.run_docstring_examples(
                    obj, globs=globs,
                    name='%s: %s' % (os.path.basename(testfile),
                                     name), verbose=verbose)
                if type(obj) in (type, ClassType):
                    for attr_name in dir(obj):

                        # Execute . operator so decorators are executed.

                        o = eval('%s.%s' % (name, attr_name), globs)
                        doctest_object(attr_name, o)

        for (name, obj) in globs.items():
            if name not in ignores and (f is None or f == name):
                doctest_object(name, obj)
