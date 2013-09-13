#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This file is part of the web2py Web Framework
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu> and
Limodou <limodou@gmail.com>.
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

This makes uses of the pywin32 package
(http://sourceforge.net/projects/pywin32/).
You do not need to install this package to use web2py.


"""

import time
import os
import sys
import traceback
try:
    import win32serviceutil
    import win32service
    import win32event
except:
    if os.name == 'nt':
        print "Warning, winservice is unable to install the Mark Hammond Win32 extensions"
import servicemanager
import _winreg
from gluon.fileutils import up


__all__ = ['web2py_windows_service_handler']


class Service(win32serviceutil.ServiceFramework):

    _svc_name_ = '_unNamed'
    _svc_display_name_ = '_Service Template'
    _svc_description_ = '_Service Template description'

    def __init__(self, *args):
        win32serviceutil.ServiceFramework.__init__(self, *args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

    def log(self, msg):
        servicemanager.LogInfoMsg(str(msg))

    def log_error(self, msg):
        """
        Log an error message to windows application event log.
        """
        servicemanager.LogErrorMsg(str(msg))

    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        try:
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            self.start()
            win32event.WaitForSingleObject(self.stop_event,
                                           win32event.INFINITE)
        except:
            self.log(traceback.format_exc(sys.exc_info))
            self.SvcStop()
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        try:
            self.stop()
        except:
            self.log(traceback.format_exc(sys.exc_info))
        win32event.SetEvent(self.stop_event)
        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    # to be overridden

    def start(self):
        pass

    # to be overridden

    def stop(self):
        pass


class Web2pyService(Service):

    _svc_name_ = 'web2py'
    _svc_display_name_ = 'web2py Service'
    _svc_description_ = 'Web2py application framework service'
    _exe_args_ = 'options'
    server = None

    def chdir(self):
        try:
            h = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                                r'SYSTEM\CurrentControlSet\Services\%s'
                                % self._svc_name_)
            try:
                cls = _winreg.QueryValue(h, 'PythonClass')
            finally:
                _winreg.CloseKey(h)
            dir = os.path.dirname(cls)
            os.chdir(dir)
            from gluon.settings import global_settings
            global_settings.gluon_parent = dir
            return True
        except:
            self.log("Can't change to web2py working path; server is stopped")
            return False

    def start(self):
        self.log('web2py server starting')
        if not self.chdir():
            return
        if len(sys.argv) == 2:
            opt_mod = sys.argv[1]
        else:
            opt_mod = self._exe_args_
        options = __import__(opt_mod, [], [], '')
        if True:  # legacy support for old options files, which have only (deprecated) numthreads
            if hasattr(options, 'numthreads') and not hasattr(options, 'minthreads'):
                options.minthreads = options.numthreads
            if not hasattr(options, 'minthreads'):
                options.minthreads = None
            if not hasattr(options, 'maxthreads'):
                options.maxthreads = None
        from gluon import main
        self.server = main.HttpServer(
            ip=options.ip,
            port=options.port,
            password=options.password,
            pid_filename=options.pid_filename,
            log_filename=options.log_filename,
            profiler_filename=options.profiler_filename,
            ssl_certificate=options.ssl_certificate,
            ssl_private_key=options.ssl_private_key,
            min_threads=options.minthreads,
            max_threads=options.maxthreads,
            server_name=options.server_name,
            request_queue_size=options.request_queue_size,
            timeout=options.timeout,
            socket_timeout=options.socket_timeout,
            shutdown_timeout=options.shutdown_timeout,
            path=options.folder,
            interfaces=options.interfaces
        )
        try:
            from gluon.rewrite import load
            load()
            self.server.start()
        except:
            self.server = None
            raise

    def stop(self):
        self.log('web2py server stopping')
        if not self.chdir():
            return
        if self.server:
            self.server.stop()
        time.sleep(1)


class Web2pyCronService(Web2pyService):

    _svc_name_ = 'web2py_cron'
    _svc_display_name_ = 'web2py Cron Service'
    _svc_description_ = 'web2py Windows cron service for scheduled tasks'
    _exe_args_ = 'options'

    def start(self):
        from gluon import newcron
        import logging
        import logging.config
        from gluon.settings import global_settings
        from gluon.fileutils import abspath
        from os.path import exists, join

        self.log('web2py Cron service starting')
        if not self.chdir():
            return
        if len(sys.argv) == 2:
            opt_mod = sys.argv[1]
        else:
            opt_mod = self._exe_args_
        options = __import__(opt_mod, [], [], '')
        logpath = abspath(join(options.folder, "logging.conf"))

        if exists(logpath):
            logging.config.fileConfig(logpath)
        else:
            logging.basicConfig()
        logger = logging.getLogger("web2py.cron")
        global_settings.web2py_crontype = 'external'
        if options.scheduler:   # -K
            apps = [app.strip() for app in options.scheduler.split(
                    ',') if check_existent_app(options, app.strip())]
        else:
            apps = None

        misfire_gracetime = float(options.misfire_gracetime) if 'misfire_gracetime' in dir(options) else 0.0
        logger.info('Starting Window cron service with %0.2f secs gracetime.' % misfire_gracetime)
        self._started = True
        wait_full_min = lambda: 60 - time.time() % 60
        while True:
            try:
                if wait_full_min() >= misfire_gracetime: # an offset of max. 5 secs before full minute (e.g. time.sleep(60) == 58.99 secs)
                    self.extcron = newcron.extcron(options.folder, apps=apps)
                    self.extcron.start()
                    time.sleep(wait_full_min())
                else:
                    logger.debug('time.sleep() offset detected: %0.3f s' % wait_full_min())
                    while wait_full_min() <= misfire_gracetime:
                        pass
                if apps != None:
                    break
                if not self._started:
                    break
            except Exception, ex:
                self.extcron = None
                self.log_error('%s, restarting service.' % ex)
                logger.exception('Exception! Restarting Windows cron service.' % ex)
                self.start()

    def stop(self):
        self.log('web2py Cron service stopping')
        if not self.chdir():
            return
        if self.extcron:
            self._started = False
            self.extcron.join()

def register_service_handler(argv=None, opt_file='options', cls=Web2pyService):
    path = os.path.dirname(__file__)
    web2py_path = up(path)
    if web2py_path.endswith('.zip'):  # in case bianry distro 'library.zip'
        web2py_path = os.path.dirname(web2py_path)
    os.chdir(web2py_path)
    classstring = os.path.normpath(
        os.path.join(web2py_path, 'gluon.winservice.'+cls.__name__))
    if opt_file:
        cls._exe_args_ = opt_file
        win32serviceutil.HandleCommandLine(
            cls, serviceClassString=classstring, argv=['', 'install'])
    win32serviceutil.HandleCommandLine(
        cls, serviceClassString=classstring, argv=argv)

if __name__ == '__main__':
    register_service_handler(cls=Web2pyService)
    register_service_handler(cls=Web2pyCronService)
