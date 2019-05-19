# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et ai:

"""
| This file is part of the web2py Web Framework
| Created by Attila Csipa <web2py@csipa.in.rs>
| Modified by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Cron-style interface
"""

import threading
import os
from logging import getLogger
import time
import sched
import sys
import re
from functools import reduce
import datetime
import shlex

from gluon import fileutils
from gluon._compat import to_bytes, pickle
from pydal.contrib import portalocker
from gluon.settings import global_settings

logger_name = 'web2py.cron'


_cron_stopping = False

def reset():
    global _cron_stopping
    _cron_stopping = False


_cron_subprocs_lock = threading.RLock()
_cron_subprocs = []

def subprocess_count():
    with _cron_subprocs_lock:
        return len(_cron_subprocs)


def absolute_path_link(path):
    """
    Returns an absolute path for the destination of a symlink
    """
    if os.path.islink(path):
        link = os.readlink(path)
        if not os.path.isabs(link):
            link = os.path.join(os.path.dirname(path), link)
    else:
        link = os.path.abspath(path)
    return link


def stopcron():
    """Graceful shutdown of cron"""
    global _cron_stopping
    _cron_stopping = True
    while subprocess_count():
        with _cron_subprocs_lock:
            proc = _cron_subprocs.pop()
        if proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                getLogger(logger_name).exception('error in stopcron')


class extcron(threading.Thread):

    def __init__(self, applications_parent, apps=None):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self.path = applications_parent
        self.apps = apps

    def run(self):
        getLogger(logger_name).debug('external cron invocation')
        crondance(self.path, 'external', startup=False, apps=self.apps)


class hardcron(threading.Thread):

    def __init__(self, applications_parent, apps=None):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.path = applications_parent
        self.apps = apps
        # processing of '@reboot' entries in crontab (startup=True)
        getLogger(logger_name).info('hard cron bootstrap')
        crondance(self.path, 'hard', startup=True, apps=self.apps)

    def launch(self):
        if not _cron_stopping:
            self.logger.debug('hard cron invocation')
            crondance(self.path, 'hard', startup=False, apps=self.apps)

    def run(self):
        self.logger = getLogger(logger_name)
        self.logger.info('hard cron daemon started')
        s = sched.scheduler(time.time, time.sleep)
        while not _cron_stopping:
            now = time.time()
            s.enter(60 - now % 60, 1, self.launch, ())
            s.run()


class softcron(threading.Thread):

    def __init__(self, applications_parent, apps=None):
        threading.Thread.__init__(self)
        self.path = applications_parent
        self.apps = apps

    def run(self):
        if not _cron_stopping:
            getLogger(logger_name).debug('soft cron invocation')
            crondance(self.path, 'soft', startup=False, apps=self.apps)


class Token(object):

    def __init__(self, path):
        self.path = os.path.join(path, 'cron.master')
        if not os.path.exists(self.path):
            fileutils.write_file(self.path, to_bytes(''), 'wb')
        self.master = None
        self.now = time.time()
        self.logger = getLogger(logger_name)

    def acquire(self, startup=False):
        """
        Returns the time when the lock is acquired or
        None if cron already running

        lock is implemented by writing a pickle (start, stop) in cron.master
        start is time when cron job starts and stop is time when cron completed
        stop == 0 if job started but did not yet complete
        if a cron job started within less than 60 seconds, acquire returns None
        if a cron job started before 60 seconds and did not stop,
        a warning is issued ("Stale cron.master detected")
        """
        if sys.platform == 'win32':
            locktime = 59.5
        else:
            locktime = 59.99
        if portalocker.LOCK_EX is None:
            self.logger.warning('cron disabled because no file locking')
            return None
        self.master = fileutils.open_file(self.path, 'rb+')
        ret = None
        try:
            portalocker.lock(self.master, portalocker.LOCK_EX)
            try:
                (start, stop) = pickle.load(self.master)
            except:
                start = 0
                stop = 1
            if startup or self.now - start > locktime:
                ret = self.now
                if not stop:
                    # this happens if previous cron job longer than 1 minute
                    self.logger.warning('stale cron.master detected')
                self.logger.debug('acquiring lock')
                self.master.seek(0)
                pickle.dump((self.now, 0), self.master)
                self.master.flush()
        finally:
            portalocker.unlock(self.master)
        if not ret:
            # do this so no need to release
            self.master.close()
        return ret

    def release(self):
        """
        Writes into cron.master the time when cron job was completed
        """
        ret = self.master.closed
        if not self.master.closed:
            portalocker.lock(self.master, portalocker.LOCK_EX)
            self.logger.debug('releasing cron lock')
            self.master.seek(0)
            (start, stop) = pickle.load(self.master)
            if start == self.now:  # if this is my lock
                self.master.seek(0)
                pickle.dump((self.now, time.time()), self.master)
            portalocker.unlock(self.master)
            self.master.close()
        return ret


def rangetolist(s, period='min'):
    retval = []
    if s.startswith('*'):
        if period == 'min':
            s = s.replace('*', '0-59', 1)
        elif period == 'hr':
            s = s.replace('*', '0-23', 1)
        elif period == 'dom':
            s = s.replace('*', '1-31', 1)
        elif period == 'mon':
            s = s.replace('*', '1-12', 1)
        elif period == 'dow':
            s = s.replace('*', '0-6', 1)
    match = re.match(r'(\d+)-(\d+)/(\d+)', s)
    if match:
        for i in range(int(match.group(1)), int(match.group(2)) + 1):
            if i % int(match.group(3)) == 0:
                retval.append(i)
    return retval


def parsecronline(line):
    task = {}
    if line.startswith('@reboot'):
        line = line.replace('@reboot', '-1 * * * *')
    elif line.startswith('@yearly'):
        line = line.replace('@yearly', '0 0 1 1 *')
    elif line.startswith('@annually'):
        line = line.replace('@annually', '0 0 1 1 *')
    elif line.startswith('@monthly'):
        line = line.replace('@monthly', '0 0 1 * *')
    elif line.startswith('@weekly'):
        line = line.replace('@weekly', '0 0 * * 0')
    elif line.startswith('@daily'):
        line = line.replace('@daily', '0 0 * * *')
    elif line.startswith('@midnight'):
        line = line.replace('@midnight', '0 0 * * *')
    elif line.startswith('@hourly'):
        line = line.replace('@hourly', '0 * * * *')
    params = line.strip().split(None, 6)
    if len(params) < 7:
        return None
    daysofweek = {'sun': 0, 'mon': 1, 'tue': 2, 'wed': 3,
                  'thu': 4, 'fri': 5, 'sat': 6}
    for (s, id) in zip(params[:5], ['min', 'hr', 'dom', 'mon', 'dow']):
        if not s in [None, '*']:
            task[id] = []
            vals = s.split(',')
            for val in vals:
                if val != '-1' and '-' in val and '/' not in val:
                    val = '%s/1' % val
                if '/' in val:
                    task[id] += rangetolist(val, id)
                elif val.isdigit() or val == '-1':
                    task[id].append(int(val))
                elif id == 'dow' and val[:3].lower() in daysofweek:
                    task[id].append(daysofweek[val[:3].lower()])
    task['user'] = params[5]
    task['cmd'] = params[6]
    return task


class cronlauncher(threading.Thread):

    def __init__(self, cmd):
        threading.Thread.__init__(self)
        self.cmd = cmd

    def run(self):
        import subprocess
        logger = getLogger(logger_name)
        proc = subprocess.Popen(self.cmd,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        with _cron_subprocs_lock:
            _cron_subprocs.append(proc)
        (stdoutdata, stderrdata) = proc.communicate()
        try:
            with _cron_subprocs_lock:
                _cron_subprocs.remove(proc)
        except ValueError:
            pass
        if proc.returncode != 0:
            logger.warning('%r call returned code %s:\n%s\n%s',
                ' '.join(self.cmd), proc.returncode, stdoutdata, stderrdata)
        else:
            logger.debug('%r call returned success:\n%s',
                ' '.join(self.cmd), stdoutdata)


def crondance(applications_parent, ctype='soft', startup=False, apps=None):
    """
    Does the periodic job of cron service: read the crontab(s) and launch
    the various commands.
    """
    apppath = os.path.join(applications_parent, 'applications')
    token = Token(applications_parent)
    cronmaster = token.acquire(startup=startup)
    if not cronmaster:
        return
    now_s = time.localtime()
    checks = (('min', now_s.tm_min),
              ('hr', now_s.tm_hour),
              ('mon', now_s.tm_mon),
              ('dom', now_s.tm_mday),
              ('dow', (now_s.tm_wday + 1) % 7))

    logger = getLogger(logger_name)

    if not apps:
        apps = [x for x in os.listdir(apppath)
                if os.path.isdir(os.path.join(apppath, x))]

    full_apath_links = set()

    if sys.executable.lower().endswith('pythonservice.exe'):
        _python_exe = os.path.join(sys.exec_prefix, 'python.exe')
    else:
        _python_exe = sys.executable
    base_commands = [_python_exe]
    w2p_path = fileutils.abspath('web2py.py', gluon=True)
    if os.path.exists(w2p_path):
        base_commands.append(w2p_path)
    if applications_parent != global_settings.gluon_parent:
        base_commands.extend(('-f', applications_parent))
    base_commands.extend(('--cron_job', '--no_banner', '--no_gui', '--plain'))

    for app in apps:
        if _cron_stopping:
            break
        apath = os.path.join(apppath, app)

        # if app is a symbolic link to other app, skip it
        full_apath_link = absolute_path_link(apath)
        if full_apath_link in full_apath_links:
            continue
        else:
            full_apath_links.add(full_apath_link)

        cronpath = os.path.join(apath, 'cron')
        crontab = os.path.join(cronpath, 'crontab')
        if not os.path.exists(crontab):
            continue
        try:
            cronlines = [line.strip() for line in fileutils.readlines_file(crontab, 'rt')]
            lines = [line for line in cronlines if line and not line.startswith('#')]
            tasks = [parsecronline(cline) for cline in lines]
        except Exception as e:
            logger.error('crontab read error %s', e)
            continue

        for task in tasks:
            if _cron_stopping:
                break
            if not task:
                continue
            task_min = task.get('min', [])
            if not startup and task_min == [-1]:
                continue
            citems = [(k in task and not v in task[k]) for k, v in checks]
            if task_min != [-1] and reduce(lambda a, b: a or b, citems):
                continue

            logger.info('%s cron: %s executing %r in %s at %s',
                ctype, app, task.get('cmd'),
                os.getcwd(), datetime.datetime.now())
            action = models = False
            command = task['cmd']
            if command.startswith('**'):
                action = True
                command = command[2:]
            elif command.startswith('*'):
                action = models = True
                command = command[1:]

            if action:
                commands = base_commands[:]
                if command.endswith('.py'):
                    commands.extend(('-S', app, '-R', command))
                else:
                    commands.extend(('-S', app + '/' + command))
                if models:
                    commands.append('-M')
            else:
                commands = shlex.split(command)

            try:
                # FIXME: using a new thread every time there is a task to
                #        launch is not a good idea in a long running process
                cronlauncher(commands).start()
            except Exception:
                logger.exception('error starting %r', task['cmd'])
    token.release()
