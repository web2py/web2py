# -*- coding: utf-8 -*-
# vim: set ts=4 sw=4 et ai:

"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

GUI widget and services start function
--------------------------------------
"""

from __future__ import print_function

import time
import sys
import os
from collections import OrderedDict
import socket
import threading
import math
import logging
import signal
import getpass

from gluon.fileutils import read_file, create_welcome_w2p
from gluon.shell import die, run, test
from gluon._compat import PY2, xrange
from gluon.utils import (getipaddrinfo, is_loopback_ip_address,
    is_valid_ip_address)
from gluon.console import is_appdir, console
from gluon import newcron
from gluon import main
from gluon.settings import global_settings


ProgramName = 'web2py Web Framework'
ProgramAuthor = 'Created by Massimo Di Pierro, Copyright 2007-' + str(
    time.localtime().tm_year)
ProgramVersion = read_file('VERSION').rstrip()

if sys.version_info < (2, 7) or (3, 0) < sys.version_info < (3, 5):
    from platform import python_version
    sys.stderr.write("Warning: web2py requires at least Python 2.7/3.5"
        " but you are running %s\n" % python_version())


def run_system_tests(options):
    """
    Runs unittests for gluon.tests
    """
    # see "python -m unittest -h" for unittest options help
    # NOTE: someone might be interested either in using the
    #       -f (--failfast) option to stop testing on first failure, or
    #       in customizing the test selection, for example to run only
    #       'gluon.tests.<module>', 'gluon.tests.<module>.<class>' (this
    #       could be shortened as 'gluon.tests.<class>'), or even
    #       'gluon.tests.<module>.<class>.<method>' (or
    #       the shorter 'gluon.tests.<class>.<method>')
    call_args = ['-m', 'unittest', '-c', 'gluon.tests']
    if options.verbose:
        call_args.insert(-1, '-v')
    if options.with_coverage:
        try:
            import coverage
        except:
            die('Coverage not installed')
    if not PY2:
        sys.stderr.write('Experimental ')
    sys.stderr.write("Python %s\n" % sys.version)
    if options.with_coverage:
        coverage_exec = 'coverage2' if PY2 else 'coverage3'
        coverage_config_file = os.path.join('gluon', 'tests', 'coverage.ini')
        coverage_config = os.environ.setdefault("COVERAGE_PROCESS_START",
                                                coverage_config_file)
        run_args = [coverage_exec, 'run', '--rcfile=%s' % coverage_config]
        # replace the current process
        os.execvpe(run_args[0], run_args + call_args, os.environ)
    else:
        run_args = [sys.executable]
        # replace the current process
        os.execv(run_args[0], run_args + call_args)


def get_url(host, path='/', proto='http', port=80):
    if ':' in host:
        host = '[%s]' % host
    elif host == '0.0.0.0':
        host = '127.0.0.1'
    if path.startswith('/'):
        path = path[1:]
    if proto.endswith(':'):
        proto = proto[:-1]
    if not port or port == 80:
        port = ''
    else:
        port = ':%s' % port
    return '%s://%s%s/%s' % (proto, host, port, path)


def start_browser(url, startup=False):
    if startup:
        print('please visit:')
        print('\t' + url)
        print('starting browser...')
    try:
        import webbrowser
        webbrowser.open(url)
    except:
        print('warning: unable to detect your browser')


class web2pyDialog(object):
    """ Main window dialog """

    def __init__(self, root, options):
        """ web2pyDialog constructor  """

        if PY2:
            import Tkinter as tkinter
            import tkMessageBox as messagebox
        else:
            import tkinter
            from tkinter import messagebox

        root.withdraw()

        bg_color = 'white'
        self.root = tkinter.Toplevel(root, bg=bg_color)
        self.root.resizable(0, 0)
        self.root.title(ProgramName)

        self.options = options
        self.scheduler_processes_lock = threading.RLock()
        self.scheduler_processes = OrderedDict()

        iconphoto = os.path.join('extras', 'icons', 'web2py.gif')
        if os.path.exists(iconphoto):
            img = tkinter.PhotoImage(file=iconphoto)
            self.root.tk.call('wm', 'iconphoto', self.root._w, img)

        # Building the Menu
        self.menu = tkinter.Menu(self.root)
        servermenu = tkinter.Menu(self.menu, tearoff=0)

        httplog = os.path.join(options.folder, options.log_filename)
        item = lambda: start_browser(httplog)
        servermenu.add_command(label='View httpserver.log',
                               command=item)

        servermenu.add_command(label='Quit (pid:%i)' % os.getpid(),
                               command=self.quit)

        self.menu.add_cascade(label='Server', menu=servermenu)

        self.pagesmenu = tkinter.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='Pages', menu=self.pagesmenu)

        self.schedmenu = tkinter.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='Scheduler', menu=self.schedmenu)
        # register and start schedulers
        self.update_schedulers(start=True)

        helpmenu = tkinter.Menu(self.menu, tearoff=0)

        # Home Page
        item = lambda: start_browser('http://www.web2py.com/')
        helpmenu.add_command(label='Home Page',
                             command=item)

        # About
        ProgramInfo = """%s
                 %s
                 %s""" % (ProgramName, ProgramAuthor, ProgramVersion)
        item = lambda: messagebox.showinfo('About web2py', ProgramInfo)
        helpmenu.add_command(label='About',
                             command=item)

        self.menu.add_cascade(label='Info', menu=helpmenu)

        self.root.config(menu=self.menu)

        if options.taskbar:
            self.root.protocol('WM_DELETE_WINDOW',
                               lambda: self.quit(True))
        else:
            self.root.protocol('WM_DELETE_WINDOW', self.quit)

        sticky = tkinter.NW

        # Prepare the logo area
        self.logoarea = tkinter.Canvas(self.root,
                                background=bg_color,
                                width=300,
                                height=300)
        self.logoarea.grid(row=0, column=0, columnspan=4, sticky=sticky)
        self.logoarea.after(1000, self.update_canvas)

        logo = os.path.join('extras', 'icons', 'splashlogo.gif')
        if os.path.exists(logo):
            img = tkinter.PhotoImage(file=logo)
            pnl = tkinter.Label(self.logoarea, image=img, background=bg_color, bd=0)
            pnl.pack(side='top', fill='both', expand='yes')
            # Prevent garbage collection of img
            pnl.image = img

        # Prepare the banner area
        self.bannerarea = tkinter.Canvas(self.root,
                                bg=bg_color,
                                width=300,
                                height=300)
        self.bannerarea.grid(row=1, column=1, columnspan=2, sticky=sticky)

        tkinter.Label(self.bannerarea, anchor=tkinter.N,
                      text=str(ProgramVersion + "\n" + ProgramAuthor),
                      font=('Helvetica', 11), justify=tkinter.CENTER,
                      foreground='#195866', background=bg_color,
                      height=3).pack(side='top',
                                     fill='both',
                                     expand='yes')

        self.bannerarea.after(1000, self.update_canvas)

        # IP
        # retrieves the list of server IP addresses
        try:
            if_ips = list(set(  # no duplicates
                [addrinfo[4][0] for addrinfo in getipaddrinfo(socket.getfqdn())
                 if not is_loopback_ip_address(addrinfo=addrinfo)]))
        except socket.gaierror:
            if_ips = []

        tkinter.Label(self.root,
                      text='Server IP:', bg=bg_color,
                      justify=tkinter.RIGHT).grid(row=4,
                                                  column=1,
                                                  sticky=sticky)
        self.ips = {}
        self.selected_ip = tkinter.StringVar()
        row = 4
        ips = [('127.0.0.1', 'Local (IPv4)')] + \
            ([('::1', 'Local (IPv6)')] if socket.has_ipv6 else []) + \
            [(ip, 'Public') for ip in if_ips] + \
            [('0.0.0.0', 'Public')]
        for ip, legend in ips:
            self.ips[ip] = tkinter.Radiobutton(
                self.root, bg=bg_color, highlightthickness=0,
                selectcolor='light grey', width=30,
                anchor=tkinter.W, text='%s (%s)' % (legend, ip),
                justify=tkinter.LEFT,
                variable=self.selected_ip, value=ip)
            self.ips[ip].grid(row=row, column=2, sticky=sticky)
            if row == 4:
                self.ips[ip].select()
            row += 1
        shift = row

        # Port
        tkinter.Label(self.root,
                      text='Server Port:', bg=bg_color,
                      justify=tkinter.RIGHT).grid(row=shift,
                                                  column=1, pady=10,
                                                  sticky=sticky)

        self.port_number = tkinter.Entry(self.root)
        self.port_number.insert(tkinter.END, options.port)
        self.port_number.grid(row=shift, column=2, sticky=sticky, pady=10)

        # Password
        tkinter.Label(self.root,
                      text='Choose Password:', bg=bg_color,
                      justify=tkinter.RIGHT).grid(row=shift + 1,
                                                  column=1,
                                                  sticky=sticky)

        self.password = tkinter.Entry(self.root, show='*')
        self.password.bind('<Return>', lambda e: self.start())
        self.password.focus_force()
        self.password.grid(row=shift + 1, column=2, sticky=sticky)

        # Prepare the canvas
        self.canvas = tkinter.Canvas(self.root,
                                     width=400,
                                     height=100,
                                     bg='black')
        self.canvas.grid(row=shift + 2, column=1, columnspan=2, pady=5,
                         sticky=sticky)
        self.canvas.after(1000, self.update_canvas)

        # Prepare the frame
        frame = tkinter.Frame(self.root)
        frame.grid(row=shift + 3, column=1, columnspan=2, pady=5,
                   sticky=sticky)

        # Start button
        self.button_start = tkinter.Button(frame,
                                           text='start server',
                                           command=self.start)

        self.button_start.grid(row=0, column=0, sticky=sticky)

        # Stop button
        self.button_stop = tkinter.Button(frame,
                                          text='stop server',
                                          command=self.stop)

        self.button_stop.grid(row=0, column=1,  sticky=sticky)
        self.button_stop.configure(state='disabled')

        if options.taskbar:
            import gluon.contrib.taskbar_widget
            self.tb = gluon.contrib.taskbar_widget.TaskBarIcon()
            self.checkTaskBar()

            if options.password != '<ask>':
                self.password.insert(0, options.password)
                self.start()
                self.root.withdraw()
        else:
            self.tb = None

    def update_schedulers(self, start=False):
        applications_folder = os.path.join(self.options.folder, 'applications')
        available_apps = [
            arq for arq in os.listdir(applications_folder)
            if os.path.isdir(os.path.join(applications_folder, arq))
        ]
        with self.scheduler_processes_lock:
            # reset the menu
            # since applications can disappear (be disinstalled) must
            # clear the menu (should use tkinter.END or tkinter.LAST)
            self.schedmenu.delete(0, 'end')
            for arq in available_apps:
                if arq not in self.scheduler_processes:
                    item = lambda a = arq: self.try_start_scheduler(a)
                    self.schedmenu.add_command(label="start %s" % arq,
                                               command=item)
                if arq in self.scheduler_processes:
                    item = lambda a = arq: self.try_stop_scheduler(a)
                    self.schedmenu.add_command(label="stop %s" % arq,
                                               command=item)

        if start and self.options.with_scheduler and self.options.schedulers:
            # the widget takes care of starting the schedulers
            apps = [ag.split(':', 1)[0] for ag in self.options.schedulers]
        else:
            apps = []
        for app in apps:
            self.try_start_scheduler(app)

    def start_schedulers(self, app):
        from multiprocessing import Process
        code = "from gluon.globals import current;current._scheduler.loop()"
        print('starting scheduler from widget for "%s"...' % app)
        args = (app, True, True, None, False, code, False, True)
        p = Process(target=run, args=args)
        with self.scheduler_processes_lock:
            self.scheduler_processes[app] = p
            self.update_schedulers()
            print("Currently running %s scheduler processes" % (
                len(self.scheduler_processes)))
        p.start()
        print("Processes started")

    def try_stop_scheduler(self, app, skip_update=False):
        p = None
        with self.scheduler_processes_lock:
            if app in self.scheduler_processes:
                p = self.scheduler_processes[app]
                del self.scheduler_processes[app]
        if p is not None:
            p.terminate()
            p.join()
        if not skip_update:
            self.update_schedulers()

    def try_start_scheduler(self, app):
        t = None
        with self.scheduler_processes_lock:
            if not is_appdir(self.options.folder, app):
                self.schedmenu.delete("start %s" % app)
                return
            if app not in self.scheduler_processes:
                t = threading.Thread(target=self.start_schedulers, args=(app,))
        if t is not None:
            t.start()

    def checkTaskBar(self):
        """ Checks taskbar status """
        tb = self.tb
        if tb.status:
            st0 = tb.status[0]
            EnumStatus = tb.EnumStatus
            if st0 == EnumStatus.QUIT:
                self.quit()
            elif st0 == EnumStatus.TOGGLE:
                if self.root.state() == 'withdrawn':
                    self.root.deiconify()
                else:
                    self.root.withdraw()
            elif st0 == EnumStatus.STOP:
                self.stop()
            elif st0 == EnumStatus.START:
                self.start()
            elif st0 == EnumStatus.RESTART:
                self.stop()
                self.start()
            del tb.status[0]

        self.root.after(1000, self.checkTaskBar)

    def connect_pages(self):
        """ Connects pages """
        # reset the menu,
        # since applications can disappear (be disinstalled) must
        # clear the menu (should use tkinter.END or tkinter.LAST)
        self.pagesmenu.delete(0, 'end')
        applications_folder = os.path.join(self.options.folder, 'applications')
        available_apps = [
            arq for arq in os.listdir(applications_folder)
            if os.path.exists(os.path.join(applications_folder, arq, '__init__.py'))
        ]
        for arq in available_apps:
            url = self.url + arq
            item = lambda a = arq: self.try_start_browser(a)
            self.pagesmenu.add_command(
                label=url, command=item)

    def try_start_browser(self, app):
        url = self.url + app
        if not is_appdir(self.options.folder, app):
            self.pagesmenu.delete(url)
            return
        start_browser(url)

    def quit(self, justHide=False):
        """ Finishes the program execution """
        if justHide:
            self.root.withdraw()
        else:
            try:
                with self.scheduler_processes_lock:
                    scheds = list(self.scheduler_processes.keys())
                for t in scheds:
                    self.try_stop_scheduler(t, skip_update=True)
            except:
                pass
            if self.options.with_cron and not self.options.soft_cron:
                # shutting down hardcron
                try:
                    newcron.stopcron()
                except:
                    pass
            try:
                # HttpServer.stop takes care of stopping softcron
                self.server.stop()
            except:
                pass
            try:
                self.tb.Destroy()
            except:
                pass

            self.root.destroy()
            sys.exit(0)

    def error(self, message):
        """ Shows error message """
        if PY2:
            import tkMessageBox as messagebox
        else:
            from tkinter import messagebox
        messagebox.showerror('web2py start server', message)

    def start(self):
        """ Starts web2py server """
        password = self.password.get()
        if not password:
            self.error('no password, no web admin interface')

        ip = self.selected_ip.get()
        if not is_valid_ip_address(ip):
            return self.error('invalid host ip address')
        try:
            port = int(self.port_number.get())
        except ValueError:
            return self.error('invalid port number')

        if self.options.server_key and self.options.server_cert:
            proto = 'https'
        else:
            proto = 'http'
        self.url = get_url(ip, proto=proto, port=port)

        self.connect_pages()
        self.update_schedulers()

        # softcron is stopped with HttpServer, thus if starting again
        # need to reset newcron._stopping to re-enable cron
        if self.options.soft_cron:
            newcron.reset()

        # FIXME: if the HttpServer is stopped, then started again,
        #        does not start because of following error:
        # WARNING:Rocket.Errors.Port8000:Listener started when not ready.

        self.button_start.configure(state='disabled')

        try:
            options = self.options
            req_queue_size = options.request_queue_size
            self.server = main.HttpServer(
                ip,
                port,
                password,
                pid_filename=options.pid_filename,
                log_filename=options.log_filename,
                profiler_dir=options.profiler_dir,
                ssl_certificate=options.server_cert,
                ssl_private_key=options.server_key,
                ssl_ca_certificate=options.ca_cert,
                min_threads=options.min_threads,
                max_threads=options.max_threads,
                server_name=options.server_name,
                request_queue_size=req_queue_size,
                timeout=options.timeout,
                shutdown_timeout=options.shutdown_timeout,
                path=options.folder,
                interfaces=options.interfaces)

            threading.Thread(target=self.server.start).start()
        except Exception as e:
            self.button_start.configure(state='normal')
            return self.error(str(e))

        if not self.server_ready():
            self.button_start.configure(state='normal')
            return

        self.button_stop.configure(state='normal')

        if not options.taskbar:
            cpt = threading.Thread(target=start_browser,
                args=(get_url(ip, proto=proto, port=port), True))
            cpt.setDaemon(True)
            cpt.start()

        self.password.configure(state='readonly')
        for ip in self.ips.values():
            ip.configure(state='disabled')
        self.port_number.configure(state='readonly')

        if self.tb:
            self.tb.SetServerRunning()

    def server_ready(self):
        for listener in self.server.server.listeners:
            if listener.ready:
                return True
        return False

    def stop(self):
        """ Stops web2py server """
        self.button_start.configure(state='normal')
        self.button_stop.configure(state='disabled')
        self.password.configure(state='normal')
        for ip in self.ips.values():
            ip.configure(state='normal')
        self.port_number.configure(state='normal')
        self.server.stop()

        if self.tb:
            self.tb.SetServerStopped()

    def update_canvas(self):
        """ Updates canvas """
        httplog = os.path.join(self.options.folder, self.options.log_filename)
        canvas = self.canvas
        try:
            t1 = os.path.getsize(httplog)
        except OSError:
            canvas.after(1000, self.update_canvas)
            return

        points = 400
        try:
            pvalues = self.p0[1:]
            with open(httplog, 'r') as fp:
                fp.seek(self.t0)
                data = fp.read(t1 - self.t0)
            self.p0 = pvalues + [10 + 90.0 / math.sqrt(1 + data.count('\n'))]

            for i in xrange(points - 1):
                c = canvas.coords(self.q0[i])
                canvas.coords(self.q0[i],
                                   (c[0], self.p0[i],
                                    c[2], self.p0[i + 1]))
            self.t0 = t1
        except AttributeError:
            self.t0 = time.time()
            self.t0 = t1
            self.p0 = [100] * points
            self.q0 = [canvas.create_line(i, 100, i + 1, 100,
                       fill='green') for i in xrange(points - 1)]

        canvas.after(1000, self.update_canvas)


def get_code_for_scheduler(applications_parent, app_groups):
    app = app_groups[0]
    if not is_appdir(applications_parent, app):
        print("Application '%s' doesn't exist, skipping" % app)
        return None, None
    code = 'from gluon.globals import current;'
    if len(app_groups) > 1:
        code += "current._scheduler.group_names=['%s'];" % "','".join(
            app_groups[1:])
    code += "current._scheduler.loop()"
    return app, code


def start_schedulers(options):
    from multiprocessing import Process
    apps = [ag.split(':') for ag in options.schedulers]
    if not options.with_scheduler and len(apps) == 1:
        app, code = get_code_for_scheduler(options.folder, apps[0])
        if not app:
            return
        print('starting single-scheduler for "%s"...' % app)
        run(app, True, True, None, False, code, False, True)
        return

    # Work around OS X problem: http://bugs.python.org/issue9405
    if PY2:
        import urllib
    else:
        import urllib.request as urllib
    urllib.getproxies()

    processes = []
    for app_groups in apps:
        app, code = get_code_for_scheduler(options.folder, app_groups)
        if not app:
            continue
        print('starting scheduler for "%s"...' % app)
        args = (app, True, True, None, False, code, False, True)
        p = Process(target=run, args=args)
        processes.append(p)
        print("Currently running %s scheduler processes" % (len(processes)))
        p.start()
        ##to avoid bashing the db at the same time
        time.sleep(0.7)
        print("Processes started")
    for p in processes:
        try:
            p.join()
        except (KeyboardInterrupt, SystemExit):
            print("Processes stopped")
        except:
            p.terminate()
            p.join()


def start():
    """ Starts server and other services """

    # get command line arguments
    options = console(version=ProgramVersion)

    if options.with_scheduler or len(options.schedulers) > 1:
        try:
            from multiprocessing import Process
        except:
            die('Sorry, -K/--scheduler only supported for Python 2.6+')

    if options.gae:
        # write app.yaml, gaehandler.py, and exit
        if not os.path.exists('app.yaml'):
            name = options.gae
            # for backward compatibility
            if name == 'configure':
                if PY2: input = raw_input
                name = input("Your GAE app name: ")
            content = open(os.path.join('examples', 'app.example.yaml'), 'rb').read()
            open('app.yaml', 'wb').write(content.replace("yourappname", name))
        else:
            print("app.yaml alreday exists in the web2py folder")
        if not os.path.exists('gaehandler.py'):
            content = open(os.path.join('handlers', 'gaehandler.py'), 'rb').read()
            open('gaehandler.py', 'wb').write(content)
        else:
            print("gaehandler.py alreday exists in the web2py folder")
        return

    logger = logging.getLogger("web2py")
    logger.setLevel(options.log_level)
    logging.getLogger().setLevel(options.log_level) # root logger

    # on new installation build the scaffolding app
    create_welcome_w2p()

    if options.run_system_tests:
        # run system test and exit
        run_system_tests(options)

    if options.quiet:
        # mute existing loggers, to do that iterate
        # over all loggers (root logger included) and remove
        # attached logging.StreamHandler instances currently
        # streaming on sys.stdout or sys.stderr
        loggers = [logging.getLogger()]
        loggers.extend(logging.Logger.manager.loggerDict.values())
        for l in loggers:
            if isinstance(l, logging.PlaceHolder): continue
            for h in l.handlers[:]:
                if isinstance(h, logging.StreamHandler) and \
                    h.stream in (sys.stdout, sys.stderr):
                    l.removeHandler(h)
        # this is to avoid the warning
        # ``No handlers could be found for logger "..."``
        # emitted by logging module when no handler is found
        logging.Logger.manager.emittedNoHandlerWarning = 1
        # to prevent writes on stdout set a null stream
        class NullFile(object):
            def write(self, x):
                pass
        sys.stdout = NullFile()
        # NOTE: stderr.write() is still working

    elif not options.no_banner:
        # banner
        print(ProgramName)
        print(ProgramAuthor)
        print(ProgramVersion)
        from pydal.drivers import DRIVERS
        print('Database drivers available: %s' % ', '.join(DRIVERS))

    if options.run_doctests:
        # run doctests and exit
        test(options.run_doctests, verbose=options.verbose)
        return

    if options.shell:
        # run interactive shell and exit
        sys.argv = [options.run or ''] + options.args
        run(options.shell, plain=options.plain, bpython=options.bpython,
            import_models=options.import_models, startfile=options.run,
            cron_job=options.cron_job, force_migrate=options.force_migrate,
            fake_migrate=options.fake_migrate)
        return

    # set size of cron thread pools
    newcron.dancer_size(options.min_threads)
    newcron.launcher_size(options.cron_threads)

    if options.cron_run:
        # run cron (extcron) and exit
        logger.debug('Running extcron...')
        global_settings.web2py_crontype = 'external'
        newcron.extcron(options.folder, apps=options.crontabs)
        return

    if not options.with_scheduler and options.schedulers:
        # run schedulers and exit
        try:
            start_schedulers(options)
        except KeyboardInterrupt:
            pass
        return

    if options.with_cron:
        if options.soft_cron:
            print('Using cron software emulation (but this is not very efficient)')
            global_settings.web2py_crontype = 'soft'
        else:
            # start hardcron thread
            logger.debug('Starting hardcron...')
            global_settings.web2py_crontype = 'hard'
            newcron.hardcron(options.folder, apps=options.crontabs).start()

    # if no password provided and have Tk library start GUI (when not
    # explicitly disabled), we also need a GUI to put in taskbar (system tray)
    # when requested
    root = None

    if (not options.no_gui and options.password == '<ask>') or options.taskbar:
        try:
            if PY2:
                import Tkinter as tkinter
            else:
                import tkinter
            root = tkinter.Tk()
        except (ImportError, OSError):
            logger.warn(
                'GUI not available because Tk library is not installed')
            options.no_gui = True
        except:
            logger.exception('cannot get Tk root window, GUI disabled')
            options.no_gui = True

    if root:
        # run GUI and exit
        root.focus_force()

        # Mac OS X - make the GUI window rise to the top
        if os.path.exists("/usr/bin/osascript"):
            applescript = """
tell application "System Events"
    set proc to first process whose unix id is %d
    set frontmost of proc to true
end tell
""" % (os.getpid())
            os.system("/usr/bin/osascript -e '%s'" % applescript)

        # web2pyDialog takes care of schedulers
        master = web2pyDialog(root, options)
        signal.signal(signal.SIGTERM, lambda a, b: master.quit())

        try:
            root.mainloop()
        except:
            master.quit()

        sys.exit()

    spt = None

    if options.with_scheduler and options.schedulers:
        # start schedulers in a separate thread
        spt = threading.Thread(target=start_schedulers, args=(options,))
        spt.start()

    # start server

    if options.password == '<ask>':
        options.password = getpass.getpass('choose a password:')

    if not options.password and not options.no_banner:
        print('no password, no web admin interface')

    # Use first interface IP and port if interfaces specified, since the
    # interfaces option overrides the IP (and related) options.
    if not options.interfaces:
        ip = options.ip
        port = options.port
    else:
        first_if = options.interfaces[0]
        ip = first_if[0]
        port = first_if[1]

    if options.server_key and options.server_cert:
        proto = 'https'
    else:
        proto = 'http'

    url = get_url(ip, proto=proto, port=port)

    if not options.no_banner:
        message = '\nplease visit:\n\t%s\n'
        if sys.platform.startswith('win'):
            message += 'use "taskkill /f /pid %i" to shutdown the web2py server\n\n'
        else:
            message += 'use "kill -SIGTERM %i" to shutdown the web2py server\n\n'
        print(message % (url, os.getpid()))

    # enhance linecache.getline (used by debugger) to look at the source file
    # if the line was not found (under py2exe & when file was modified)
    import linecache
    py2exe_getline = linecache.getline

    def getline(filename, lineno, *args, **kwargs):
        line = py2exe_getline(filename, lineno, *args, **kwargs)
        if not line:
            try:
                with open(filename, "rb") as f:
                    for i, line in enumerate(f):
                        line = line.decode('utf-8')
                        if lineno == i + 1:
                            break
                    else:
                        line = ''
            except (IOError, OSError):
                line = ''
        return line
    linecache.getline = getline

    server = main.HttpServer(ip=ip,
                             port=port,
                             password=options.password,
                             pid_filename=options.pid_filename,
                             log_filename=options.log_filename,
                             profiler_dir=options.profiler_dir,
                             ssl_certificate=options.server_cert,
                             ssl_private_key=options.server_key,
                             ssl_ca_certificate=options.ca_cert,
                             min_threads=options.min_threads,
                             max_threads=options.max_threads,
                             server_name=options.server_name,
                             request_queue_size=options.request_queue_size,
                             timeout=options.timeout,
                             socket_timeout=options.socket_timeout,
                             shutdown_timeout=options.shutdown_timeout,
                             path=options.folder,
                             interfaces=options.interfaces)

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        if spt is not None:
            try:
                spt.join()
            except:
                logger.exception('error terminating schedulers')
    logging.shutdown()
