# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et ai:
"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Command line interface
----------------------

The processing of all command line arguments is done using
the argparse library in the console function.

The basic principle is to process and check for all options
in a single place, this place is the parse_args function.
Notice that when I say all options I mean really all,
options sourced from a configuration file are included.

A brief summary of options style follows,
for the benefit of code maintainers/developers:

- use the underscore to split words in long names (as in
  '--run_system_tests')
- remember to allow the '-' too as word separator (e.g.
  '--run-system-tests') but do not use this form on help
  (add the minus version of the option to _omitted_opts
  to hide it in usage help)
- prefer short names on help messages, instead use
  all options names in warning/error messages (e.g.
  '-R/--run requires -S/--shell')

Notice that options must be included into opt_map dictionary
(defined in parse_args function) to be available in
configuration file.
"""

from __future__ import print_function

__author__ = 'Paolo Pastori'

import os.path
import argparse
import logging
import socket
import sys
import re
import ast
from collections import OrderedDict
import copy

from gluon._compat import PY2
from gluon.shell import die
from gluon.utils import is_valid_ip_address
from gluon.settings import global_settings


def warn(msg):
    print("%s: warning: %s" % (sys.argv[0], msg), file=sys.stderr)

def is_appdir(applications_parent, app):
    return os.path.isdir(os.path.join(applications_parent, 'applications', app))


def console(version):
    """
    Load command line options.
    Trivial -h/--help and --version options are also processed.

    Returns a namespace object (in the sense of argparse)
    with all options loaded.
    """

    # replacement hints for deprecated options
    deprecated_opts = {
        '--debug': '--log_level',
        '--nogui': '--no_gui',
        '--ssl_private_key': '--server_key',
        '--ssl_certificate': '--server_cert',
        '--interfaces': None, # dest is 'interfaces', hint is '--interface'
        '-n': '--min_threads', '--numthreads': '--min_threads',
        '--minthreads': '--min_threads',
        '--maxthreads': '--max_threads',
        '-z': None, '--shutdown_timeout': None,
        '--profiler': '--profiler_dir',
        '--run-cron': '--with_cron',
        '--softcron': '--soft_cron',
        '--cron': '--cron_run',
        '--test': '--run_doctests'
    }

    class HelpFormatter2(argparse.HelpFormatter):
        """Hides the options listed in _hidden_options in usage help."""

        # NOTE: preferred style for long options name is to use '_'
        #       between words (as in 'no_gui'), also accept the '-' in
        #       most of the options but do not show both versions on help
        _omitted_opts = ('--add-options', '--errors-to-console',
            '--no-banner', '--log-level', '--no-gui', '--import-models',
            '--force-migrate',
            '--server-name', '--server-key', '--server-cert', '--ca-cert',
            '--pid-filename', '--log-filename', '--min-threads',
            '--max-threads', '--request-queue-size', '--socket-timeout',
            '--profiler-dir', '--with-scheduler', '--with-cron',
            '--cron-threads', '--soft-cron', '--cron-run',
            '--run-doctests', '--run-system-tests', '--with-coverage')

        _hidden_options = _omitted_opts + tuple(deprecated_opts.keys())

        def _format_action_invocation(self, action):
            if not action.option_strings:
                return super(HelpFormatter2, self)._format_action_invocation(action)
            parts = []
            if action.nargs == 0:
                parts.extend(filter(lambda o : o not in self._hidden_options,
                                    action.option_strings))
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    if option_string in self._hidden_options:
                        continue
                    parts.append('%s %s' % (option_string, args_string))
            return ', '.join(parts)

    class ExtendAction(argparse._AppendAction):
        """Action to accumulate values in a flat list."""

        def __call__(self, parser, namespace, values, option_string=None):
            if isinstance(values, list):
                # must copy to avoid altering the option default value
                value = getattr(namespace, self.dest, None)
                if value is None:
                    value = []
                    setattr(namespace, self.dest, value)
                items = value[:]
                # for options that allows multiple args (i.e. those declared
                # with add_argument(..., nargs='+', ...)) the values are
                # always placed into a list
                while len(values) == 1 and isinstance(values[0], list):
                    values = values[0]
                items.extend(values)
                setattr(namespace, self.dest, items)
            else:
                super(ExtendAction, self).__call__(parser, namespace, values, option_string)

    parser = argparse.ArgumentParser(
        usage='python %(prog)s [options]',
        description='web2py Web Framework startup script.',
        epilog='''NOTE: unless a password is specified (-a 'passwd')
web2py will attempt to run a GUI to ask for it when starting the web server
(if not disabled with --no_gui).''',
        formatter_class=HelpFormatter2,
        add_help=False) # do not add -h/--help option

    # global options
    g = parser.add_argument_group('global options')
    g.add_argument('-h', '--help', action='help',
                   help='show this help message and exit')
    g.add_argument('--version', action='version',
                   version=version,
                   help="show program's version and exit")
    folder = os.getcwd()
    g.add_argument('-f', '--folder',
                   default=folder, metavar='WEB2PY_DIR',
                   help='web2py installation directory (%(default)s)')
    def existing_file(v):
        if not v:
            raise argparse.ArgumentTypeError('empty argument')
        if not os.path.exists(v):
            raise argparse.ArgumentTypeError("file %r not found" % v)
        return v
    g.add_argument('-L', '--config',
                   type=existing_file,
                   metavar='PYTHON_FILE',
                   help='read all options from PYTHON_FILE')
    g.add_argument('--add_options', '--add-options',
                   default=False,
                   action='store_true', help=
        'add options to existing ones, useful with -L only')
    g.add_argument('-a', '--password',
                   default='<ask>', help=
        'password to be used for administration (use "<recycle>" '
        'to reuse the last password), when no password is available '
        'the administrative web interface will be disabled')
    g.add_argument('-e', '--errors_to_console', '--errors-to-console',
                   default=False,
                   action='store_true',
                   help='log application errors to console')
    g.add_argument('--no_banner', '--no-banner',
                   default=False,
                   action='store_true',
                   help='do not print header banner')
    g.add_argument('-Q', '--quiet',
                   default=False,
                   action='store_true',
                   help='disable all output')
    integer_log_level = []
    def log_level(v):
        # try to convert a lgging level name to its numeric value,
        # could use logging.getLevelName but not with
        # 3.4 <= Python < 3.4.2, see
        # https://docs.python.org/3/library/logging.html#logging.getLevelName)
        try:
            name2level = logging._levelNames
        except AttributeError:
            # logging._levelNames has gone with Python 3.4, see
            # https://github.com/python/cpython/commit/3b84eae03ebd8122fdbdced3d85999dd9aedfc7e
            name2level = logging._nameToLevel
        try:
            return name2level[v.upper()]
        except KeyError:
            pass
        try:
            ill = int(v)
            # value deprecated: integer in range(101)
            if 0 <= ill <= 100:
                integer_log_level.append(ill)
                return ill
        except ValueError:
            pass
        raise argparse.ArgumentTypeError("bad level %r" % v)
    g.add_argument('-D', '--log_level', '--log-level',
                   '--debug', # deprecated
                   default='WARNING',
                   type=log_level,
                   metavar='LOG_LEVEL', help=
        'set log level, allowed values are: NOTSET, DEBUG, INFO, WARN, '
        'WARNING, ERROR, and CRITICAL, also lowercase (default is '
        '%(default)s)')

    # GUI options
    g = parser.add_argument_group('GUI options')
    g.add_argument('--no_gui', '--no-gui',
                   '--nogui', # deprecated
                   default=False,
                   action='store_true',
                   help='do not run GUI')
    g.add_argument('-t', '--taskbar',
                   default=False,
                   action='store_true',
                   help='run in taskbar (system tray)')

    # console options
    g = parser.add_argument_group('console options')
    g.add_argument('-S', '--shell',
                   metavar='APP_ENV', help=
        'run web2py in Python interactive shell or IPython (if installed) '
        'with specified application environment (if application does not '
        'exist it will be created). APP_ENV like a/c/f?x=y (c, f and vars '
        'optional), if APP_ENV include the action f then after the '
        'action execution the interpreter is exited')
    g.add_argument('-B', '--bpython',
                   default=False,
                   action='store_true', help=
        'use bpython (if installed) when running in interactive shell, '
        'see -S above')
    g.add_argument('-P', '--plain',
                   default=False,
                   action='store_true', help=
        'use plain Python shell when running in interactive shell, '
        'see -S above')
    g.add_argument('-M', '--import_models', '--import-models',
                   default=False,
                   action='store_true', help=
        'auto import model files when running in interactive shell '
        '(default is %(default)s), see -S above. NOTE: when the APP_ENV '
        'argument of -S include a controller c automatic import of '
        'models is always enabled')
    g.add_argument('--fake_migrate',
                   default=False,
                   action='store_true',
                   help=
                   'force DAL to fake migrate all tables; '
                   'monkeypatch in the DAL class to force _fake_migrate=True')
    g.add_argument('--force_migrate', '--force-migrate',
                   default=False,
                   action='store_true', help=
        'force DAL to migrate all tables that should be migrated when enabled; '
        'monkeypatch in the DAL class to force _migrate_enabled=True')
    g.add_argument('-R', '--run',
                   type=existing_file,
                   metavar='PYTHON_FILE', help=
        'run PYTHON_FILE in web2py environment; require -S')
    g.add_argument('-A', '--args',
                   default=[],
                   nargs=argparse.REMAINDER, help=
        'use this to pass arguments to the PYTHON_FILE above; require '
        '-R. NOTE: must be the last option because eat all remaining '
        'arguments')

    # web server options
    g = parser.add_argument_group('web server options')
    g.add_argument('-s', '--server_name', '--server-name',
                   default=socket.gethostname(),
                   help='web server name (%(default)s)')
    def ip_addr(v):
        if not is_valid_ip_address(v):
            raise argparse.ArgumentTypeError("bad IP address %s" % v)
        return v
    g.add_argument('-i', '--ip',
                   default='127.0.0.1',
                   type=ip_addr, metavar='IP_ADDR', help=
        'IP address of the server (%(default)s), accept either IPv4 or '
        'IPv6 (e.g. ::1) addresses. NOTE: this option is ignored if '
        '--interface is specified')
    def not_negative_int(v, err_label='value'):
        try:
            iv = int(v)
            if iv < 0: raise ValueError()
            return iv
        except ValueError:
            pass
        raise argparse.ArgumentTypeError("bad %s %s" % (err_label, v))
    def port(v):
        return not_negative_int(v, err_label='port')
    g.add_argument('-p', '--port',
                   default=8000,
                   type=port, metavar='NUM', help=
        'port of server (%(default)d). '
        'NOTE: this option is ignored if --interface is specified')
    g.add_argument('-k', '--server_key', '--server-key',
                   '--ssl_private_key', # deprecated
                   type=existing_file,
                   metavar='FILE', help='server private key')
    g.add_argument('-c', '--server_cert', '--server-cert',
                   '--ssl_certificate', # deprecated
                   type=existing_file,
                   metavar='FILE', help='server certificate')
    g.add_argument('--ca_cert', '--ca-cert',
                   type=existing_file,
                   metavar='FILE', help='CA certificate')
    def iface(v, sep=','):
        if not v:
            raise argparse.ArgumentTypeError('empty argument')
        if sep == ':':
            # deprecated --interfaces ip:port:key:cert:ca_cert
            # IPv6 addresses in square brackets
            if v.startswith('['):
                # IPv6
                ip, v_remainder = v.split(']', 1)
                ip = ip[1:]
                ifp = v_remainder[1:].split(':')
                ifp.insert(0, ip)
            else:
                # IPv4
                ifp = v.split(':')
        else:
            # --interface
            ifp = v.split(sep, 5)
        if not len(ifp) in (2, 4, 5):
            raise argparse.ArgumentTypeError("bad interface %r" % v)
        try:
            ip_addr(ifp[0])
            ifp[1] = port(ifp[1])
            for fv in ifp[2:]:
                existing_file(fv)
        except argparse.ArgumentTypeError as ex:
            raise argparse.ArgumentTypeError("bad interface %r (%s)" % (v, ex))
        return tuple(ifp)
    g.add_argument('--interface', dest='interfaces',
                   default=[], action=ExtendAction,
                   type=iface, nargs='+',
                   metavar='IF_INFO', help=
        'listen on specified interface, IF_INFO = '
        'IP_ADDR,PORT[,KEY_FILE,CERT_FILE[,CA_CERT_FILE]].'
        ' NOTE: this option can be used multiple times to provide additional '
        'interfaces to choose from but you can choose which one to listen to '
        'only using the GUI otherwise the first interface specified is used')
    def ifaces(v):
        # deprecated --interfaces 'if1;if2;...'
        if not v:
            raise argparse.ArgumentTypeError('empty argument')
        return [iface(i, ':') for i in v.split(';')]
    g.add_argument('--interfaces', # deprecated
                   default=argparse.SUPPRESS, # do not set if absent
                   action=ExtendAction,
                   type=ifaces,
                   help=argparse.SUPPRESS) # do not show on help
    g.add_argument('-d', '--pid_filename', '--pid-filename',
                   default='httpserver.pid',
                   metavar='FILE', help='server pid file (%(default)s)')
    g.add_argument('-l', '--log_filename', '--log-filename',
                   default='httpserver.log',
                   metavar='FILE', help='server log file (%(default)s)')
    g.add_argument('--min_threads', '--min-threads',
                   '--minthreads', '-n', '--numthreads', # deprecated
                   type=not_negative_int, metavar='NUM',
                   help='minimum number of server threads')
    g.add_argument('--max_threads', '--max-threads',
                   '--maxthreads', # deprecated
                   type=not_negative_int, metavar='NUM',
                   help='maximum number of server threads')
    g.add_argument('-q', '--request_queue_size', '--request-queue-size',
                   default=5,
                   type=not_negative_int, metavar='NUM', help=
        'max number of queued requests when server busy (%(default)d)')
    g.add_argument('-o', '--timeout',
                   default=10,
                   type=not_negative_int, metavar='SECONDS',
                   help='timeout for individual request (%(default)d seconds)')
    g.add_argument('--socket_timeout', '--socket-timeout',
                   default=5,
                   type=not_negative_int, metavar='SECONDS',
                   help='timeout for socket (%(default)d seconds)')
    g.add_argument('-z', '--shutdown_timeout', # deprecated
                   type=not_negative_int,
                   help=argparse.SUPPRESS) # do not show on help
    g.add_argument('-F', '--profiler_dir', '--profiler-dir',
                   '--profiler', # deprecated
                   help='profiler directory')

    # scheduler options
    g = parser.add_argument_group('scheduler options')
    g.add_argument('-X', '--with_scheduler', '--with-scheduler',
                   default=False,
                   action='store_true', help=
        'run schedulers alongside web server; require --K')
    def is_app(app):
        return is_appdir(folder, app)
    def scheduler(v):
        if not v:
            raise argparse.ArgumentTypeError('empty argument')
        if ',' in v:
            # legacy "app1,..."
            vl = [n.strip() for n in v.split(',')]
            return [scheduler(iv) for iv in vl]
        vp = [n.strip() for n in v.split(':')]
        app = vp[0]
        if not app:
            raise argparse.ArgumentTypeError('empty application')
        if not is_app(app):
            warn("argument -K/--scheduler: bad application %r, skipped" % app)
            return None
        return ':'.join(filter(None, vp))
    g.add_argument('-K', '--scheduler', dest='schedulers',
                   default=[], action=ExtendAction,
                   type=scheduler, nargs='+',
                   metavar='APP_INFO', help=
        'run scheduler for the specified application(s), APP_INFO = '
        'APP_NAME[:GROUPS], that is an optional list of groups can follow '
        'the application name (e.g. app:group1:group2); require a scheduler '
        "to be defined in the application's models. NOTE: this option can "
        'be used multiple times to add schedulers')

    # cron options
    g = parser.add_argument_group('cron options')
    g.add_argument('-Y', '--with_cron', '--with-cron',
                   '--run-cron', # deprecated
                   default=False,
                   action='store_true', help=
        'run cron service alongside web server')
    def crontab(v):
        if not v:
            raise argparse.ArgumentTypeError('empty argument')
        if not is_app(v):
            warn("argument --crontab: bad application %r, skipped" % v)
            return None
        return v
    g.add_argument('--crontab', dest='crontabs',
                   default=[], action=ExtendAction,
                   type=crontab, nargs='+',
                   metavar='APP_NAME', help=
        'tell cron to read the crontab for the specified application(s) '
        'only, the default behaviour is to read the crontab for all of the '
        'installed applications. NOTE: this option can be used multiple '
        'times to build the list of crontabs to be processed by cron')
    def positive_int(v, err_label='value'):
        try:
            iv = int(v)
            if iv <= 0: raise ValueError()
            return iv
        except ValueError:
            pass
        raise argparse.ArgumentTypeError("bad %s %s" % (err_label, v))
    def cron_threads(v):
        return positive_int(v, err_label='cron_threads')
    g.add_argument('--cron_threads', '--cron-threads',
                   type=cron_threads, metavar='NUM',
                   help='maximum number of cron threads (5)')
    g.add_argument('--soft_cron', '--soft-cron',
                   '--softcron', # deprecated
                   default=False,
                   action='store_true', help=
        'use cron software emulation instead of separate cron process; '
        'require -Y. NOTE: use of cron software emulation is strongly '
        'discouraged')
    g.add_argument('-C', '--cron_run', '--cron-run',
                   '--cron', # deprecated
                   default=False,
                   action='store_true', help=
        'trigger a cron run and exit; usually used when invoked '
        'from a system (external) crontab')
    g.add_argument('--cron_job', # NOTE: this is intended for internal use only
                   default=False,
                   action='store_true',
                   help=argparse.SUPPRESS) # do not show on help

    # test options
    g = parser.add_argument_group('test options')
    g.add_argument('-v', '--verbose',
                   default=False,
                   action='store_true', help='increase verbosity')
    g.add_argument('-T', '--run_doctests', '--run-doctests',
                   '--test', # deprecated
                   metavar='APP_ENV', help=
        'run doctests in application environment. APP_ENV like a/c/f (c, f '
        'optional)')
    g.add_argument('--run_system_tests', '--run-system-tests',
                   default=False,
                   action='store_true', help='run web2py test suite')
    g.add_argument('--with_coverage', '--with-coverage',
                   default=False,
                   action='store_true', help=
        'collect coverage data when used with --run_system_tests; '
        'require Python 2.7+ and the coverage module installed')

    # other options
    g = parser.add_argument_group('other options')
    g.add_argument('-G', '--GAE', dest='gae',
                   metavar='APP_NAME', help=
        'will create app.yaml and gaehandler.py and exit')

    options = parse_args(parser, sys.argv[1:],
                         deprecated_opts, integer_log_level)

    # make a copy of all options for global_settings
    copy_options = copy.deepcopy(options)
    copy_options.password = '******'
    global_settings.cmd_options = copy_options

    return options


REGEX_PEP263 = r'^[ \t\f]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)'

def get_pep263_encoding(source):
    """
    Read python source file encoding, according to PEP 263, see
    https://www.python.org/dev/peps/pep-0263/
    """
    with open(source, 'r') as sf:
        l12 = (sf.readline(), sf.readline())
    m12 = re.match(REGEX_PEP263, l12[0]) or re.match(REGEX_PEP263, l12[1])
    return m12 and m12.group(1)


IGNORE = lambda: None

def load_config(config_file, opt_map):
    """
    Load options from config file (a Python script).

    config_file(str): file name
    opt_map(dict): mapping fom option name (key) to callable (val),
        used to post-process parsed value for the option

    Notice that the configuring Python script is never executed/imported,
    instead the ast library is used to evaluate each option assignment,
    provided that it is written on a single line.

    Returns an OrderedDict with sourced options.
    """
    REGEX_ASSIGN_EXP = re.compile(r'\s*=\s*(.+)')
    map_items = opt_map.items()
    # preserve the order of loaded options even though this is not needed
    pl = OrderedDict()
    config_encoding = get_pep263_encoding(config_file)
    # NOTE: assume 'ascii' encoding when not explicitly stated (Python 2),
    #       this is not correct for Python 3 where the default is 'utf-8'
    open_kwargs = dict() if PY2 else dict(encoding=config_encoding or 'ascii')
    with open(config_file, 'r', **open_kwargs) as cfil:
        for linenum, clin in enumerate(cfil, start=1):
            if PY2 and config_encoding:
                clin = unicode(clin, config_encoding)
            clin = clin.strip()
            for opt, mapr in map_items:
                if clin.startswith(opt):
                    m = REGEX_ASSIGN_EXP.match(clin[len(opt):])
                    if m is None: continue
                    try:
                        val = opt_map[opt](ast.literal_eval(m.group(1)))
                    except:
                        die("cannot parse config file %r at line %d" % (config_file, linenum))
                    if val is not IGNORE:
                        pl[opt] = val
    return pl


def parse_args(parser, cli_args, deprecated_opts, integer_log_level,
               namespace=None):

    #print('PARSING ARGS:', cli_args)
    del integer_log_level[:]
    options = parser.parse_args(cli_args, namespace)
    #print('PARSED OPTIONS:', options)

    # warn for deprecated options
    deprecated_args = [a for a in cli_args if a in deprecated_opts]
    for da in deprecated_args:
        # verify if it was a real option by looking into
        # parsed values for the actual destination
        hint = deprecated_opts[da]
        dest = (hint or da).lstrip('-')
        default = parser.get_default(dest)
        if da == '--interfaces':
            hint = '--interface'
        if getattr(options, dest) is not default:
            # the option has been specified
            msg = "%s is deprecated" % da
            if hint:
                msg += ", use %s instead" % hint
            warn(msg)
    # warn for deprecated values
    if integer_log_level and '--debug' not in deprecated_args:
        warn('integer argument for -D/--log_level is deprecated, '
             'use label instead')
    # fix schedulers and die if all were skipped
    if None in options.schedulers:
        options.schedulers = [i for i in options.schedulers if i is not None]
        if not options.schedulers:
            die('no scheduler left')
    # fix crontabs and die if all were skipped
    if None in options.crontabs:
        options.crontabs = [i for i in options.crontabs if i is not None]
        if not options.crontabs:
            die('no crontab left')
    # taskbar
    if options.taskbar and os.name != 'nt':
        warn('--taskbar not supported on this platform, skipped')
        options.taskbar = False
    # options consistency checkings
    if options.run and not options.shell:
        die('-R/--run requires -S/--shell', exit_status=2)
    if options.args and not options.run:
        die('-A/--args requires -R/--run', exit_status=2)
    if options.with_scheduler and not options.schedulers:
        die('-X/--with_scheduler requires -K/--scheduler', exit_status=2)
    if options.soft_cron and not options.with_cron:
        die('--soft_cron requires -Y/--with_cron', exit_status=2)
    if options.shell:
        for o, os in dict(with_scheduler='-X/--with_scheduler',
                          schedulers='-K/--scheduler',
                          with_cron='-Y/--with_cron',
                          cron_run='-C/--cron_run',
                          run_doctests='-T/--run_doctests',
                          run_system_tests='--run_system_tests').items():
            if getattr(options, o):
                die("-S/--shell and %s are conflicting options" % os,
                    exit_status=2)
    if options.bpython and options.plain:
        die('-B/--bpython and -P/--plain are conflicting options',
            exit_status=2)
    if options.cron_run:
        for o, os in dict(with_cron='-Y/--with_cron',
                          run_doctests='-T/--run_doctests',
                          run_system_tests='--run_system_tests').items():
            if getattr(options, o):
                die("-C/--cron_run and %s are conflicting options" % os,
                    exit_status=2)
    if options.run_doctests and options.run_system_tests:
        die('-T/--run_doctests and --run_system_tests are conflicting options',
            exit_status=2)

    if options.config:
        # load options from file,
        # all options sourced from file that evaluates to False
        # are skipped, the special IGNORE value is used for this
        store_true = lambda v: True if v else IGNORE
        str_or_default = lambda v : str(v) if v else IGNORE
        list_or_default = lambda v : (
            [str(i) for i in v] if isinstance(v, list) else [str(v)]) if v \
            else IGNORE
        # NOTE: 'help', 'version', 'folder', 'cron_job' and 'GAE' are not
        #       sourced from file, the same applies to deprecated options
        opt_map = {
            # global options
            'config': str_or_default,
            'add_options': store_true,
            'password': str_or_default,
            'errors_to_console': store_true,
            'no_banner': store_true,
            'quiet': store_true,
            'log_level': str_or_default,
            # GUI options
            'no_gui': store_true,
            'taskbar': store_true,
            # console options
            'shell': str_or_default,
            'bpython': store_true,
            'plain': store_true,
            'import_models': store_true,
            'force_migrate': store_true,
            'run': str_or_default,
            'args': list_or_default,
            # web server options
            'server_name': str_or_default,
            'ip': str_or_default,
            'port': str_or_default,
            'server_key': str_or_default,
            'server_cert': str_or_default,
            'ca_cert': str_or_default,
            'interface': list_or_default,
            'pid_filename': str_or_default,
            'log_filename': str_or_default,
            'min_threads': str_or_default,
            'max_threads': str_or_default,
            'request_queue_size': str_or_default,
            'timeout': str_or_default,
            'socket_timeout': str_or_default,
            'profiler_dir': str_or_default,
            # scheduler options
            'with_scheduler': store_true,
            'scheduler': list_or_default,
            # cron options
            'with_cron': store_true,
            'crontab': list_or_default,
            'cron_threads': str_or_default,
            'soft_cron': store_true,
            'cron_run': store_true,
            # test options
            'verbose': store_true,
            'run_doctests': str_or_default,
            'run_system_tests': store_true,
            'with_coverage': store_true,
        }
        od = load_config(options.config, opt_map)
        #print("LOADED FROM %s:" % options.config, od)
        # convert loaded options dict as retuned by load_config
        # into a list of arguments for further parsing by parse_args
        file_args = []; args_args = [] # '--args' must be the last
        for key, val in od.items():
            if key != 'args':
                file_args.append('--' + key)
                if isinstance(val, list): file_args.extend(val)
                elif not isinstance(val, bool): file_args.append(val)
            else:
                args_args = ['--args'] + val
        file_args += args_args

        if options.add_options:
            # add options to existing ones,
            # must clear config to avoid infinite recursion
            options.config = options.add_options = None
            return parse_args(parser, file_args,
                deprecated_opts, integer_log_level, options)
        return parse_args(parser, file_args,
            deprecated_opts, integer_log_level)

    return options
