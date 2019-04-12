# -*- coding: utf-8 -*-

"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

The widget is called from web2py
----------------------------------
"""

import sys
from gluon._compat import thread, xrange, PY2
import time
import threading
import os
import copy
import socket
import signal
import math
import logging
import getpass
from gluon import main, newcron

from gluon.fileutils import read_file, write_file, create_welcome_w2p
from gluon.settings import global_settings
from gluon.shell import die, run, test
from gluon.utils import is_valid_ip_address, is_loopback_ip_address, getipaddrinfo


ProgramName = 'web2py Web Framework'
ProgramAuthor = 'Created by Massimo Di Pierro, Copyright 2007-' + str(
    time.localtime().tm_year)
ProgramVersion = read_file('VERSION').rstrip()

if sys.version_info < (2, 7) or (3, 0) < sys.version_info < (3, 5):
    from platform import python_version
    sys.stderr.write("Warning: web2py requires at least Python 2.7/3.5"
        " but you are running %s\n" % python_version())

logger = logging.getLogger("web2py")


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
        print('\t', url)
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


        bg_color = 'white'
        root.withdraw()

        self.root = tkinter.Toplevel(root, bg=bg_color)
        self.root.resizable(0, 0)
        self.root.title(ProgramName)

        self.options = options
        self.scheduler_processes = {}
        self.menu = tkinter.Menu(self.root)
        servermenu = tkinter.Menu(self.menu, tearoff=0)
        httplog = os.path.join(self.options.folder, self.options.log_filename)
        iconphoto = os.path.join('extras', 'icons', 'web2py.gif')
        if os.path.exists(iconphoto):
            img = tkinter.PhotoImage(file=iconphoto)
            self.root.tk.call('wm', 'iconphoto', self.root._w, img)
        # Building the Menu
        item = lambda: start_browser(httplog)
        servermenu.add_command(label='View httpserver.log',
                               command=item)

        servermenu.add_command(label='Quit (pid:%i)' % os.getpid(),
                               command=self.quit)

        self.menu.add_cascade(label='Server', menu=servermenu)

        self.pagesmenu = tkinter.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='Pages', menu=self.pagesmenu)

        #scheduler menu
        self.schedmenu = tkinter.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='Scheduler', menu=self.schedmenu)
        #start and register schedulers from options
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
            [(ip, 'Public') for ip in options.ips] + \
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
        self.port_number.insert(tkinter.END, self.options.port)
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
        apps = []
        available_apps = [
            arq for arq in os.listdir(applications_folder)
            if os.path.exists(os.path.join(applications_folder, arq, 'models', 'scheduler.py'))
        ]
        if start:
            # the widget takes care of starting the scheduler
            if self.options.scheduler and self.options.with_scheduler:
                apps = [app.strip() for app
                        in self.options.scheduler.split(',')
                        if app in available_apps]
        for app in apps:
            self.try_start_scheduler(app)

        # reset the menu
        self.schedmenu.delete(0, len(available_apps))

        for arq in available_apps:
            if arq not in self.scheduler_processes:
                item = lambda u = arq: self.try_start_scheduler(u)
                self.schedmenu.add_command(label="start %s" % arq,
                                           command=item)
            if arq in self.scheduler_processes:
                item = lambda u = arq: self.try_stop_scheduler(u)
                self.schedmenu.add_command(label="stop %s" % arq,
                                           command=item)

    def start_schedulers(self, app):
        try:
            from multiprocessing import Process
        except:
            sys.stderr.write('Sorry, -K only supported for Python 2.6+\n')
            return
        code = "from gluon.globals import current;current._scheduler.loop()"
        print('starting scheduler from widget for "%s"...' % app)
        args = (app, True, True, None, False, code)
        logging.getLogger().setLevel(self.options.debuglevel)
        p = Process(target=run, args=args)
        self.scheduler_processes[app] = p
        self.update_schedulers()
        print("Currently running %s scheduler processes" % (
            len(self.scheduler_processes)))
        p.start()
        print("Processes started")

    def try_stop_scheduler(self, app):
        if app in self.scheduler_processes:
            p = self.scheduler_processes[app]
            del self.scheduler_processes[app]
            p.terminate()
            p.join()
        self.update_schedulers()

    def try_start_scheduler(self, app):
        if app not in self.scheduler_processes:
            t = threading.Thread(target=self.start_schedulers, args=(app,))
            t.start()

    def checkTaskBar(self):
        """ Checks taskbar status """

        if self.tb.status:
            if self.tb.status[0] == self.tb.EnumStatus.QUIT:
                self.quit()
            elif self.tb.status[0] == self.tb.EnumStatus.TOGGLE:
                if self.root.state() == 'withdrawn':
                    self.root.deiconify()
                else:
                    self.root.withdraw()
            elif self.tb.status[0] == self.tb.EnumStatus.STOP:
                self.stop()
            elif self.tb.status[0] == self.tb.EnumStatus.START:
                self.start()
            elif self.tb.status[0] == self.tb.EnumStatus.RESTART:
                self.stop()
                self.start()
            del self.tb.status[0]

        self.root.after(1000, self.checkTaskBar)

    def update(self, text):
        """ Updates app text """

        try:
            self.text.configure(state='normal')
            self.text.insert('end', text)
            self.text.configure(state='disabled')
        except:
            pass  # ## this should only happen in case app is destroyed

    def connect_pages(self):
        """ Connects pages """
        # reset the menu
        applications_folder = os.path.join(self.options.folder, 'applications')
        available_apps = [
            arq for arq in os.listdir(applications_folder)
            if os.path.exists(os.path.join(applications_folder, arq, '__init__.py'))
        ]
        self.pagesmenu.delete(0, len(available_apps))
        for arq in available_apps:
            url = self.url + arq
            self.pagesmenu.add_command(
                label=url, command=lambda u=url: start_browser(u))

    def quit(self, justHide=False):
        """ Finishes the program execution """
        if justHide:
            self.root.withdraw()
        else:
            try:
                scheds = self.scheduler_processes.keys()
                for t in scheds:
                    self.try_stop_scheduler(t)
            except:
                pass
            try:
                newcron.stopcron()
            except:
                pass
            try:
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
        except:
            return self.error('invalid port number')

        if self.options.ssl_certificate and self.options.ssl_private_key:
            proto = 'https'
        else:
            proto = 'http'

        self.url = get_url(ip, proto=proto, port=port)
        self.connect_pages()
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
                ssl_certificate=options.ssl_certificate,
                ssl_private_key=options.ssl_private_key,
                ssl_ca_certificate=options.ssl_ca_certificate,
                min_threads=options.minthreads,
                max_threads=options.maxthreads,
                server_name=options.server_name,
                request_queue_size=req_queue_size,
                timeout=options.timeout,
                shutdown_timeout=options.shutdown_timeout,
                path=options.folder,
                interfaces=options.interfaces)

            thread.start_new_thread(self.server.start, ())
        except Exception as e:
            self.button_start.configure(state='normal')
            return self.error(str(e))

        if not self.server_ready():
            self.button_start.configure(state='normal')
            return

        self.button_stop.configure(state='normal')

        if not options.taskbar:
            thread.start_new_thread(
                start_browser, (get_url(ip, proto=proto, port=port), True))

        self.password.configure(state='readonly')
        [ip.configure(state='disabled') for ip in self.ips.values()]
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
        [ip.configure(state='normal') for ip in self.ips.values()]
        self.port_number.configure(state='normal')
        self.server.stop()

        if self.tb:
            self.tb.SetServerStopped()

    def update_canvas(self):
        """ Updates canvas """

        httplog = os.path.join(self.options.folder, self.options.log_filename)
        try:
            t1 = os.path.getsize(httplog)
        except:
            self.canvas.after(1000, self.update_canvas)
            return

        try:
            fp = open(httplog, 'r')
            fp.seek(self.t0)
            data = fp.read(t1 - self.t0)
            fp.close()
            value = self.p0[1:] + [10 + 90.0 / math.sqrt(1 + data.count('\n'))]
            self.p0 = value

            for i in xrange(len(self.p0) - 1):
                c = self.canvas.coords(self.q0[i])
                self.canvas.coords(self.q0[i],
                                   (c[0],
                                    self.p0[i],
                                    c[2],
                                    self.p0[i + 1]))
            self.t0 = t1
        except BaseException:
            self.t0 = time.time()
            self.t0 = t1
            self.p0 = [100] * 400
            self.q0 = [self.canvas.create_line(i, 100, i + 1, 100,
                       fill='green') for i in xrange(len(self.p0) - 1)]

        self.canvas.after(1000, self.update_canvas)


def console():
    """ Defines the behavior of the console web2py execution """
    import optparse

    parser = optparse.OptionParser(
        usage='python %prog [options]',
        version=ProgramVersion,
        description='web2py Web Framework startup script.',
        epilog='''NOTE: unless a password is specified (-a 'passwd')
web2py will attempt to run a GUI to ask for it when starting the web server
(if not disabled with --nogui).''')

    parser.add_option('-i', '--ip',
                      default='127.0.0.1',
                      metavar='IP_ADDR', help=\
        'IP address of the server (e.g., 127.0.0.1 or ::1); ' \
        'Note: This value is ignored when using the --interfaces option')

    parser.add_option('-p', '--port',
                      default=8000,
                      type='int', metavar='NUM', help=\
        'port of server (%default); ' \
        'Note: This value is ignored when using the --interfaces option')

    parser.add_option('-G', '--GAE', dest='gae',
                      default=None,
                      metavar='APP_NAME', help=\
        'will create app.yaml and gaehandler.py and exit')

    parser.add_option('-a', '--password',
                      default='<ask>',
                      help=\
        'password to be used for administration ' \
        '(use "<recycle>" to reuse the last password), ' \
        'when no password is available the administrative ' \
        'interface will be disabled')

    parser.add_option('-c', '--ssl_certificate',
                      default=None,
                      metavar='FILE', help='server certificate file')

    parser.add_option('-k', '--ssl_private_key',
                      default=None,
                      metavar='FILE', help='server private key file')

    parser.add_option('--ca-cert', dest='ssl_ca_certificate',
                      default=None,
                      metavar='FILE', help='CA certificate file')

    parser.add_option('-d', '--pid_filename',
                      default='httpserver.pid',
                      metavar='FILE', help='server pid file (%default)')

    parser.add_option('-l', '--log_filename',
                      default='httpserver.log',
                      metavar='FILE', help='server log file (%default)')

    parser.add_option('-n', '--numthreads',
                      default=None,
                      type='int', metavar='NUM',
                      help='number of threads (deprecated)')

    parser.add_option('--minthreads',
                      default=None,
                      type='int', metavar='NUM',
                      help='minimum number of server threads')

    parser.add_option('--maxthreads',
                      default=None,
                      type='int', metavar='NUM',
                      help='maximum number of server threads')

    parser.add_option('-s', '--server_name',
                      default=socket.gethostname(),
                      help='web server name (%default)')

    parser.add_option('-q', '--request_queue_size',
                      default=5,
                      type='int', metavar='NUM',
                      help=\
        'max number of queued requests when server unavailable (%default)')

    parser.add_option('-o', '--timeout',
                      default=10,
                      type='int', metavar='SECONDS',
                      help='timeout for individual request (%default seconds)')

    parser.add_option('-z', '--shutdown_timeout',
                      default=None,
                      type='int', metavar='SECONDS',
                      help=\
        'timeout on server shutdown; this value is not used by ' \
        'Rocket web server')

    parser.add_option('--socket-timeout', dest='socket_timeout', # not needed
                      default=5,
                      type='int', metavar='SECONDS',
                      help='timeout for socket (%default seconds)')

    parser.add_option('-f', '--folder',
                      default=os.getcwd(), metavar='WEB2PY_DIR',
                      help='folder from which to run web2py')

    parser.add_option('-v', '--verbose',
                      default=False,
                      action='store_true',
                      help='increase --test and --run_system_tests verbosity')

    parser.add_option('-Q', '--quiet',
                      default=False,
                      action='store_true',
                      help='disable all output')

    parser.add_option('-e', '--errors_to_console', dest='print_errors',
                      default=False,
                      action='store_true',
                      help='log all errors to console')

    parser.add_option('-D', '--debug', dest='debuglevel',
                      default=30,
                      type='int',
                      metavar='LOG_LEVEL', help=\
        'set log level (0-100, 0 means all, 100 means none; ' \
        'default is %default)')

    parser.add_option('-S', '--shell',
                      default=None,
                      metavar='APPNAME', help=\
        'run web2py in interactive shell or IPython (if installed) with ' \
        'specified appname (if app does not exist it will be created). ' \
        'APPNAME like a/c/f?x=y (c,f and vars x,y optional)')

    parser.add_option('-B', '--bpython',
                      default=False,
                      action='store_true',
                      help=\
        'run web2py in interactive shell or bpython (if installed) with ' \
        'specified appname (if app does not exist it will be created). ' \
        'Use combined with --shell')

    parser.add_option('-P', '--plain',
                      default=False,
                      action='store_true',
                      help=\
        'only use plain python shell; should be used with --shell option')

    parser.add_option('-M', '--import_models',
                      default=False,
                      action='store_true',
                      help=\
        'auto import model files (default is %default); should be used ' \
        'with --shell option')

    parser.add_option('-R', '--run',
                      default='', # NOTE: used for sys.argv[0] if --shell
                      metavar='PYTHON_FILE', help=\
        'run PYTHON_FILE in web2py environment; ' \
        'should be used with --shell option')

    parser.add_option('-K', '--scheduler',
                      default=None,
                      metavar='APP_LIST', help=\
        'run scheduled tasks for the specified apps: expects a list of ' \
        'app names as app1,app2,app3 ' \
        'or a list of app:groups as app1:group1:group2,app2:group1 ' \
        '(only strings, no spaces allowed). NOTE: ' \
        'Requires a scheduler defined in the models')

    parser.add_option('-X', '--with-scheduler', dest='with_scheduler', # not needed
                      default=False,
                      action='store_true',
                      help=\
        'run schedulers alongside webserver, needs -K')

    parser.add_option('-T', '--test',
                      default=None,
                      metavar='TEST_PATH', help=\
        'run doctests in web2py environment; ' \
        'TEST_PATH like a/c/f (c,f optional)')

    parser.add_option('-C', '--cron', dest='extcron',
                      default=False,
                      action='store_true',
                      help=\
        'trigger a cron run and exit; usually used when invoked ' \
        'from a system crontab')

    parser.add_option('--softcron',
                      default=False,
                      action='store_true',
                      help=\
        'use software cron emulation instead of separate cron process, '\
        'needs -Y; NOTE: use of software cron emulation is strongly '
        'discouraged')

    parser.add_option('-Y', '--run-cron', dest='runcron',
                      default=False,
                      action='store_true',
                      help='start the background cron process')

    parser.add_option('-J', '--cronjob',
                      default=False,
                      action='store_true',
                      help='identify cron-initiated command')

    parser.add_option('-L', '--config',
                      default='',
                      help='config file')

    parser.add_option('-F', '--profiler', dest='profiler_dir',
                      default=None,
                      help='profiler dir')

    parser.add_option('-t', '--taskbar',
                      default=False,
                      action='store_true',
                      help='use web2py GUI and run in taskbar (system tray)')

    parser.add_option('--nogui',
                      default=False,
                      action='store_true',
                      help='do not run GUI')

    parser.add_option('-A', '--args',
                      default=None,
                      help=\
        'should be followed by a list of arguments to be passed to script, ' \
        'to be used with -S; NOTE: must be the last option because eat all ' \
        'remaining arguments')

    parser.add_option('--no-banner', dest='nobanner',
                      default=False,
                      action='store_true',
                      help='do not print header banner')

    parser.add_option('--interfaces',
                      default=None,
                      help=\
        'listen on multiple addresses: ' \
        '"ip1:port1:key1:cert1:ca_cert1;ip2:port2:key2:cert2:ca_cert2;..." ' \
        '(:key:cert:ca_cert optional; no spaces; IPv6 addresses must be in ' \
        'square [] brackets)')

    parser.add_option('--run_system_tests',
                      default=False,
                      action='store_true',
                      help='run web2py tests')

    parser.add_option('--with_coverage',
                      default=False,
                      action='store_true',
                      help=\
        'adds coverage reporting (should be used with --run_system_tests), ' \
        'needs Python 2.7+ and the coverage module installed. ' \
        'You can alter the default path setting the environment ' \
        'variable "COVERAGE_PROCESS_START" ' \
        '(by default it takes gluon/tests/coverage.ini)')

    if '-A' in sys.argv:
        k = sys.argv.index('-A')
    elif '--args' in sys.argv:
        k = sys.argv.index('--args')
    else:
        k = len(sys.argv)
    sys.argv, other_args = sys.argv[:k], sys.argv[k + 1:]
    (options, args) = parser.parse_args()
    # TODO: warn or error if args (should be no unparsed arguments)
    options.args = other_args

    if options.config.endswith('.py'):
        options.config = options.config[:-3]
    if options.config:
        # import options from options.config file
        try:
            # FIXME: avoid __import__
            options2 = __import__(options.config)
        except:
            die("cannot import config file %s" % options.config)
        for key in dir(options2):
            if hasattr(options, key):
                setattr(options, key, getattr(options2, key))

    # store in options.ips the list of server IP addresses
    try:
        options.ips = list(set(  # no duplicates
            [addrinfo[4][0] for addrinfo in getipaddrinfo(socket.getfqdn())
             if not is_loopback_ip_address(addrinfo=addrinfo)]))
    except socket.gaierror:
        options.ips = []

    if options.cronjob:
        global_settings.cronjob = True  # tell the world
        options.plain = True    # cronjobs use a plain shell
        options.nobanner = True
        options.nogui = True

    # transform options.interfaces, in the form
    # "ip1:port1:key1:cert1:ca_cert1;[ip2]:port2;ip3:port3:key3:cert3"
    # (no spaces; optional key:cert:ca_cert indicate SSL), into
    # a list of tuples
    if options.interfaces:
        interfaces = options.interfaces.split(';')
        options.interfaces = []
        for interface in interfaces:
            if interface.startswith('['):
                # IPv6
                ip, if_remainder = interface.split(']', 1)
                ip = ip[1:]
                interface = if_remainder[1:].split(':')
                interface.insert(0, ip)
            else:
                # IPv4
                interface = interface.split(':')
            interface[1] = int(interface[1])  # numeric port
            options.interfaces.append(tuple(interface))

    # strip group infos from options.scheduler, in the form
    # "app:group1:group2,app2:group1", and put into a list of lists
    # in options.scheduler_groups
    if options.scheduler and ':' in options.scheduler:
        sg = options.scheduler_groups = []
        for awg in options.scheduler.split(','):
            sg.append(awg.split(':'))
        options.scheduler = ','.join([app[0] for app in sg])
    else:
        options.scheduler_groups = None

    if options.numthreads is not None and options.minthreads is None:
        options.minthreads = options.numthreads  # legacy

    copy_options = copy.deepcopy(options)
    copy_options.password = '******'
    global_settings.cmd_options = copy_options

    return options, args


def check_existent_app(options, appname):
    if os.path.isdir(os.path.join(options.folder, 'applications', appname)):
        return True


def get_code_for_scheduler(app, options):
    if len(app) == 1 or app[1] is None:
        code = "from gluon.globals import current;current._scheduler.loop()"
    else:
        code = "from gluon.globals import current;current._scheduler.group_names = ['%s'];"
        code += "current._scheduler.loop()"
        code = code % ("','".join(app[1:]))
    app_ = app[0]
    if not check_existent_app(options, app_):
        print("Application '%s' doesn't exist, skipping" % app_)
        return None, None
    return app_, code


def start_schedulers(options):
    try:
        from multiprocessing import Process
    except:
        sys.stderr.write('Sorry, -K only supported for Python 2.6+\n')
        return
    processes = []
    apps = options.scheduler_groups or \
        [(app.strip(), None) for app in options.scheduler.split(',')]
    code = "from gluon.globals import current;current._scheduler.loop()"
    logging.getLogger().setLevel(options.debuglevel)
    if len(apps) == 1 and not options.with_scheduler:
        app_, code = get_code_for_scheduler(apps[0], options)
        if not app_:
            return
        print('starting single-scheduler for "%s"...' % app_)
        run(app_, True, True, None, False, code)
        return

    # Work around OS X problem: http://bugs.python.org/issue9405
    if PY2:
        import urllib
    else:
        import urllib.request as urllib
    urllib.getproxies()

    for app in apps:
        app_, code = get_code_for_scheduler(app, options)
        if not app_:
            continue
        print('starting scheduler for "%s"...' % app_)
        args = (app_, True, True, None, False, code)
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


def start(cron=True):
    """ Starts server and other services """

    # get command line arguments
    (options, args) = console()

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

    create_welcome_w2p()

    if options.run_system_tests:
        # run system test and exit
        run_system_tests(options)

    if options.quiet:
        # to prevent writes on stdout set a null stream
        class NullFile(object):
            def write(self, x):
                pass
        sys.stdout = NullFile()
        # but still has to mute existing loggers, to do that iterate
        # over all existing loggers (root logger included) and remove
        # all attached logging.StreamHandler instances currently
        # streaming on sys.stdout or sys.stderr
        loggers = [logging.getLogger()]
        loggers.extend(logging.Logger.manager.loggerDict.values())
        for l in loggers:
            if isinstance(l, logging.PlaceHolder): continue
            for h in l.handlers[:]:
                if isinstance(h, logging.StreamHandler) and \
                    h.stream in (sys.stdout, sys.stderr):
                    l.removeHandler(h)
        # NOTE: stderr.write() is still working

    logger.setLevel(options.debuglevel)

    if not options.nobanner:
        # banner
        print(ProgramName)
        print(ProgramAuthor)
        print(ProgramVersion)
        from pydal.drivers import DRIVERS
        print('Database drivers available: %s' % ', '.join(DRIVERS))

    if options.test:
        # run doctests and exit
        test(options.test, verbose=options.verbose)
        return

    if options.shell:
        # run interactive shell and exit
        sys.argv = [options.run] + options.args
        run(options.shell, plain=options.plain, bpython=options.bpython,
            import_models=options.import_models, startfile=options.run,
            cronjob=options.cronjob)
        return

    if options.extcron:
        # run cron (extcron) and exit
        logger.debug('Starting extcron...')
        global_settings.web2py_crontype = 'external'
        if options.scheduler:
            # run cron for applications listed with --scheduler (-K)
            apps = [app.strip() for app in options.scheduler.split(
                ',') if check_existent_app(options, app.strip())]
        else:
            apps = None
        extcron = newcron.extcron(options.folder, apps=apps)
        extcron.start()
        extcron.join()
        return

    if options.scheduler and not options.with_scheduler:
        # run schedulers and exit
        try:
            start_schedulers(options)
        except KeyboardInterrupt:
            pass
        return

    if cron and options.runcron:
        if options.softcron:
            print('Using softcron (but this is not very efficient)')
            global_settings.web2py_crontype = 'soft'
        else:
            # start hardcron thread
            logger.debug('Starting hardcron...')
            global_settings.web2py_crontype = 'hard'
            newcron.hardcron(options.folder).start()

    # if no password provided and have Tk library start GUI (when not
    # explicitly disabled), we also need a GUI to put in taskbar (system tray)
    # when requested

    # FIXME: this check should be done first
    if options.taskbar and os.name != 'nt':
        die('taskbar not supported on this platform')

    root = None

    if (not options.nogui and options.password == '<ask>') or options.taskbar:
        try:
            if PY2:
                import Tkinter as tkinter
            else:
                import tkinter
            root = tkinter.Tk()
        except (ImportError, OSError):
            logger.warn(
                'GUI not available because Tk library is not installed')
            options.nogui = True
        except:
            logger.exception('cannot get Tk root window, GUI disabled')
            options.nogui = True

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

    if options.password == '<ask>':
        options.password = getpass.getpass('choose a password:')

    if not options.password and not options.nobanner:
        print('no password, disable admin interface')

    spt = None

    if options.scheduler and options.with_scheduler:
        # start schedulers in a separate thread
        spt = threading.Thread(target=start_schedulers, args=(options,))
        spt.start()

    # start server

    # Use first interface IP and port if interfaces specified, since the
    # interfaces option overrides the IP (and related) options.
    if not options.interfaces:
        ip = options.ip
        port = options.port
    else:
        first_if = options.interfaces[0]
        ip = first_if[0]
        port = first_if[1]

    if options.ssl_certificate and options.ssl_private_key:
        proto = 'https'
    else:
        proto = 'http'

    url = get_url(ip, proto=proto, port=port)

    if not options.nobanner:
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
                             ssl_certificate=options.ssl_certificate,
                             ssl_private_key=options.ssl_private_key,
                             ssl_ca_certificate=options.ssl_ca_certificate,
                             min_threads=options.minthreads,
                             max_threads=options.maxthreads,
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
                pass
    logging.shutdown()
