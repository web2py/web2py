# -*- coding: utf-8 -*-

"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

File operations
---------------
"""

from gluon import storage
import os
import sys
import re
import tarfile
import glob
import time
import datetime
import logging
import shutil

from gluon.http import HTTP
from gzip import open as gzopen
from gluon.recfile import generate
from gluon._compat import PY2
from gluon.settings import global_settings

__all__ = (
    'parse_version',
    'read_file',
    'write_file',
    'readlines_file',
    'up',
    'abspath',
    'mktree',
    'listdir',
    'recursive_unlink',
    'cleanpath',
    'tar',
    'untar',
    'tar_compiled',
    'get_session',
    'check_credentials',
    'w2p_pack',
    'w2p_unpack',
    'create_app',
    'w2p_pack_plugin',
    'w2p_unpack_plugin',
    'fix_newlines',
    'create_missing_folders',
    'create_missing_app_folders',
    'add_path_first',
)


def parse_semantic(version="Version 1.99.0-rc.1+timestamp.2011.09.19.08.23.26"):
    """Parses a version string according to http://semver.org/ rules

    Args:
        version(str): the SemVer string

    Returns:
        tuple: Major, Minor, Patch, Release, Build Date

    """
    re_version = re.compile(r'(\d+)\.(\d+)\.(\d+)(-(?P<pre>[^\s+]*))?(\+(?P<build>\S*))')
    m = re_version.match(version.strip().split()[-1])
    if not m:
        return None
    a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
    pre_release = m.group('pre') or ''
    build = m.group('build') or ''
    if build.startswith('timestamp'):
        build = datetime.datetime.strptime(build.split('.', 1)[1], '%Y.%m.%d.%H.%M.%S')
    return (a, b, c, pre_release, build)


def parse_legacy(version="Version 1.99.0 (2011-09-19 08:23:26)"):
    """Parses "legacy" version string

    Args:
        version(str): the version string

    Returns:
        tuple: Major, Minor, Patch, Release, Build Date

    """
    re_version = re.compile(r'[^\d]+ (\d+)\.(\d+)\.(\d+)\s*\((?P<datetime>.+?)\)\s*(?P<type>[a-z]+)?')
    m = re_version.match(version)
    a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3)),
    pre_release = m.group('type') or 'dev'
    build = datetime.datetime.strptime(m.group('datetime'), '%Y-%m-%d %H:%M:%S')
    return (a, b, c, pre_release, build)


def parse_version(version):
    """Attempts to parse SemVer, fallbacks on legacy
    """
    version_tuple = parse_semantic(version)
    if not version_tuple:
        version_tuple = parse_legacy(version)
    return version_tuple


def open_file(filename, mode):
    if PY2 or 'b' in mode:
        f = open(filename, mode)
    else:
        f = open(filename, mode, encoding="utf8")
    return f


def read_file(filename, mode='r'):
    """Returns content from filename, making sure to close the file explicitly
    on exit.
    """
    with open_file(filename, mode) as f:
        return f.read()


def write_file(filename, value, mode='w'):
    """Writes <value> to filename, making sure to close the file
    explicitly on exit.
    """
    with open_file(filename, mode) as f:
        return f.write(value)


def readlines_file(filename, mode='r'):
    """Applies .split('\n') to the output of `read_file()`
    """
    return read_file(filename, mode).split('\n')


def mktree(path):
    head, tail = os.path.split(path)
    if head:
        if tail:
            mktree(head)
        if not os.path.exists(head):
            os.mkdir(head)


def listdir(path,
            expression='^.+$',
            drop=True,
            add_dirs=False,
            sort=True,
            maxnum=None,
            exclude_content_from=None,
            followlinks=False
            ):
    """
    Like `os.listdir()` but you can specify a regex pattern to filter files.
    If `add_dirs` is True, the returned items will have the full path.
    """
    if exclude_content_from is None:
        exclude_content_from = []
    if path[-1:] != os.path.sep:
        path = path + os.path.sep
    if drop:
        n = len(path)
    else:
        n = 0
    regex = re.compile(expression)
    items = []
    for (root, dirs, files) in os.walk(path, topdown=True, followlinks=followlinks):
        for dir in dirs[:]:
            if dir.startswith('.'):
                dirs.remove(dir)
        if add_dirs:
            items.append(root[n:])
        for file in sorted(files):
            if regex.match(file) and not file.startswith('.'):
                if root not in exclude_content_from:
                    items.append(os.path.join(root, file)[n:])
            if maxnum and len(items) >= maxnum:
                break
    if sort:
        return sorted(items)
    else:
        return items


def recursive_unlink(f):
    """Deletes `f`. If it's a folder, also its contents will be deleted
    """
    if os.path.isdir(f):
        for s in os.listdir(f):
            recursive_unlink(os.path.join(f, s))
        os.rmdir(f)
    elif os.path.isfile(f):
        os.unlink(f)


def cleanpath(path):
    """Turns any expression/path into a valid filename. replaces / with _ and
    removes special characters.
    """

    items = path.split('.')
    if len(items) > 1:
        path = re.sub(r'[^\w.]+', '_', '_'.join(items[:-1]) + '.'
                      + ''.join(items[-1:]))
    else:
        path = re.sub(r'[^\w.]+', '_', ''.join(items[-1:]))
    return path


def _extractall(filename, path='.', members=None):
    tar = tarfile.TarFile(filename, 'r')
    ret = tar.extractall(path, members)
    tar.close()
    return ret


def tar(file, dir, expression='^.+$',
        filenames=None, exclude_content_from=None):
    """Tars dir into file, only tars file that match expression
    """

    tar = tarfile.TarFile(file, 'w')
    try:
        if filenames is None:
            filenames = listdir(dir, expression, add_dirs=True,
                exclude_content_from=exclude_content_from)
        for file in filenames:
            tar.add(os.path.join(dir, file), file, False)
    finally:
        tar.close()


def untar(file, dir):
    """Untar file into dir
    """

    _extractall(file, dir)


def w2p_pack(filename, path, compiled=False, filenames=None):
    """Packs a web2py application.

    Args:
        filename(str): path to the resulting archive
        path(str): path to the application
        compiled(bool): if `True` packs the compiled version
        filenames(list): adds filenames to the archive
    """
    filename = abspath(filename)
    path = abspath(path)
    tarname = filename + '.tar'
    if compiled:
        tar_compiled(tarname, path, r'^[\w.-]+$',
                     exclude_content_from=['cache', 'sessions', 'errors'])
    else:
        tar(tarname, path, r'^[\w.-]+$', filenames=filenames,
            exclude_content_from=['cache', 'sessions', 'errors'])
    with open(tarname, 'rb') as tarfp, gzopen(filename, 'wb') as gzfp:
        shutil.copyfileobj(tarfp, gzfp, 4194304) # 4 MB buffer
    os.unlink(tarname)


def missing_app_folders(path):
    for subfolder in ('models', 'views', 'controllers', 'databases',
                      'modules', 'cron', 'errors', 'sessions',
                      'languages', 'static', 'private', 'uploads'):
        yield os.path.join(path, subfolder)


def create_welcome_w2p():
    is_newinstall = os.path.exists('NEWINSTALL')
    if not os.path.exists('welcome.w2p') or is_newinstall:
        logger = logging.getLogger("web2py")
        try:
            app_path = 'applications/welcome'
            for amf in missing_app_folders(app_path):
                if not os.path.exists(amf):
                    os.mkdir(amf)
            w2p_pack('welcome.w2p', app_path)
            logger.info("New installation: created welcome.w2p file")
        except:
            logger.exception("New installation error: unable to create welcome.w2p file")
            return
        if is_newinstall:
            try:
                os.unlink('NEWINSTALL')
                logger.info("New installation: removed NEWINSTALL file")
            except:
                logger.exception("New installation error: unable to remove NEWINSTALL file")


def w2p_unpack(filename, path, delete_tar=True):
    if filename == 'welcome.w2p':
        create_welcome_w2p()
    filename = abspath(filename)
    tarname = None
    if filename.endswith('.w2p'):
        tarname = filename[:-4] + '.tar'
    elif filename.endswith('.gz'):
        tarname = filename[:-3] + '.tar'
    if tarname is not None:
        with gzopen(filename, 'rb') as gzfp, open(tarname, 'wb') as tarfp:
            shutil.copyfileobj(gzfp, tarfp, 4194304) # 4 MB buffer
    else:
        tarname = filename
    path = abspath(path)
    untar(tarname, path)
    if delete_tar:
        os.unlink(tarname)


def create_app(path):
    w2p_unpack('welcome.w2p', path)


def w2p_pack_plugin(filename, path, plugin_name):
    """Packs the given plugin into a w2p file.
    Will match files at::

        <path>/*/plugin_[name].*
        <path>/*/plugin_[name]/*

    """
    filename = abspath(filename)
    path = abspath(path)
    if not filename.endswith('web2py.plugin.%s.w2p' % plugin_name):
        raise ValueError('Not a web2py plugin')
    with tarfile.open(filename, 'w:gz') as plugin_tarball:
        app_dir = path
        while app_dir.endswith('/'):
            app_dir = app_dir[:-1]
        files1 = glob.glob(
            os.path.join(app_dir, '*/plugin_%s.*' % plugin_name))
        files2 = glob.glob(
            os.path.join(app_dir, '*/plugin_%s/*' % plugin_name))
        for file in files1 + files2:
            plugin_tarball.add(file, arcname=file[len(app_dir) + 1:])


def w2p_unpack_plugin(filename, path, delete_tar=True):
    filename = abspath(filename)
    path = abspath(path)
    if not os.path.basename(filename).startswith('web2py.plugin.'):
        raise ValueError('Not a web2py plugin')
    w2p_unpack(filename, path, delete_tar)


def tar_compiled(file, dir, expression='^.+$',
                 exclude_content_from=None):
    """Used to tar a compiled application.
    The content of models, views, controllers is not stored in the tar file.
    """

    with tarfile.TarFile(file, 'w') as tar:
        for file in listdir(dir, expression, add_dirs=True,
                            exclude_content_from=exclude_content_from):
            filename = os.path.join(dir, file)
            if os.path.islink(filename):
                continue
            if os.path.isfile(filename) and not file.endswith('.pyc'):
                if file.startswith('models'):
                    continue
                if file.startswith('views'):
                    continue
                if file.startswith('controllers'):
                    continue
                if file.startswith('modules'):
                    continue
            tar.add(filename, file, False)


def up(path):
    return os.path.dirname(os.path.normpath(path))


def get_session(request, other_application='admin'):
    """Checks that user is authorized to access other_application"""
    if request.application == other_application:
        raise KeyError
    try:
        session_id = request.cookies['session_id_' + other_application].value
        session_filename = os.path.join(
            up(request.folder), other_application, 'sessions', session_id)
        if not os.path.exists(session_filename):
            session_filename = generate(session_filename)
        osession = storage.load_storage(session_filename)
    except Exception:
        osession = storage.Storage()
    return osession


def set_session(request, session, other_application='admin'):
    """Checks that user is authorized to access other_application"""
    if request.application == other_application:
        raise KeyError
    session_id = request.cookies['session_id_' + other_application].value
    session_filename = os.path.join(
        up(request.folder), other_application, 'sessions', session_id)
    storage.save_storage(session, session_filename)


def check_credentials(request, other_application='admin',
                      expiration=60 * 60, gae_login=True):
    """Checks that user is authorized to access other_application"""
    if request.env.web2py_runtime_gae:
        from google.appengine.api import users
        if users.is_current_user_admin():
            return True
        elif gae_login:
            login_html = '<a href="%s">Sign in with your google account</a>.' \
                % users.create_login_url(request.env.path_info)
            raise HTTP(200, '<html><body>%s</body></html>' % login_html)
        else:
            return False
    else:
        t0 = time.time()
        dt = t0 - expiration
        s = get_session(request, other_application)
        r = (s.authorized and s.last_time and s.last_time > dt)
        if r:
            s.last_time = t0
            set_session(request, s, other_application)
        return r


def fix_newlines(path):
    regex = re.compile(r'''(\r
|\r|
)''')
    for filename in listdir(path, r'.*\.(py|html)$', drop=False):
        rdata = read_file(filename, 'r')
        wdata = regex.sub('\n', rdata)
        if wdata != rdata:
            write_file(filename, wdata, 'w')


# NOTE: same name as os.path.abspath (but signature is different)
def abspath(*relpath, **kwargs):
    """Converts relative path to absolute path based (by default) on
    applications_parent
    """
    path = os.path.join(*relpath)
    if os.path.isabs(path):
        return path
    if kwargs.get('gluon', False):
        return os.path.join(global_settings.gluon_parent, path)
    return os.path.join(global_settings.applications_parent, path)


def try_mkdir(path):
    if not os.path.exists(path):
        try:
            if os.path.islink(path):
                # path is a broken link, try to mkdir the target of the link
                # instead of the link itself.
                os.mkdir(os.path.realpath(path))
            else:
                os.mkdir(path)
        except OSError as e:
            if e.errno == 17:  # "File exists" (race condition).
                pass
            else:
                raise


def create_missing_folders():
    if not global_settings.web2py_runtime_gae:
        for path in ('applications', 'deposit', 'site-packages', 'logs'):
            try_mkdir(abspath(path, gluon=True))
    """
    OLD sys.path dance
    paths = (global_settings.gluon_parent, abspath(
        'site-packages', gluon=True), abspath('gluon', gluon=True), '')
    """
    for p in (global_settings.gluon_parent,
              abspath('site-packages', gluon=True),
              ''):
        add_path_first(p)


def create_missing_app_folders(request):
    if not global_settings.web2py_runtime_gae:
        if request.folder not in global_settings.app_folders:
            for amf in missing_app_folders(request.folder):
                try_mkdir(amf)
            global_settings.app_folders.add(request.folder)


def add_path_first(path):
    sys.path = [path] + [p for p in sys.path if (
        not p == path and not p == (path + '/'))]
    if not global_settings.web2py_runtime_gae:
        if not path in sys.path:
            site.addsitedir(path)
