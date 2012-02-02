#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

The widget is called from web2py.
"""

import sys
import cStringIO
import time
import thread
import re
import os
import socket
import signal
import math
import logging
import newcron
import main

from fileutils import w2p_pack, read_file, write_file
from shell import run, test
from settings import global_settings

try:
    import Tkinter, tkMessageBox
    import contrib.taskbar_widget
    from winservice import web2py_windows_service_handler
except:
    pass


try:
    BaseException
except NameError:
    BaseException = Exception

ProgramName = 'web2py Web Framework'
ProgramAuthor = 'Created by Massimo Di Pierro, Copyright 2007-2011'
ProgramVersion = read_file('VERSION').strip()

ProgramInfo = '''%s
                 %s
                 %s''' % (ProgramName, ProgramAuthor, ProgramVersion)

if not sys.version[:3] in ['2.4', '2.5', '2.6', '2.7']:
    msg = 'Warning: web2py requires Python 2.4, 2.5 (recommended), 2.6 or 2.7 but you are running:\n%s'
    msg = msg % sys.version
    sys.stderr.write(msg)

logger = logging.getLogger("web2py")

class IO(object):
    """   """

    def __init__(self):
        """   """

        self.buffer = cStringIO.StringIO()

    def write(self, data):
        """   """

        sys.__stdout__.write(data)
        if hasattr(self, 'callback'):
            self.callback(data)
        else:
            self.buffer.write(data)


def try_start_browser(url):
    """ Try to start the default browser """

    try:
        import webbrowser
        webbrowser.open(url)
    except:
        print 'warning: unable to detect your browser'


def start_browser(ip, port):
    """ Starts the default browser """
    print 'please visit:'
    print '\thttp://%s:%s' % (ip, port)
    print 'starting browser...'
    try_start_browser('http://%s:%s' % (ip, port))


def presentation(root):
    """ Draw the splash screen """

    root.withdraw()

    dx = root.winfo_screenwidth()
    dy = root.winfo_screenheight()

    dialog = Tkinter.Toplevel(root, bg='white')
    dialog.geometry('%ix%i+%i+%i' % (500, 300, dx / 2 - 200, dy / 2 - 150))

    dialog.overrideredirect(1)
    dialog.focus_force()

    canvas = Tkinter.Canvas(dialog,
                            background='white',
                            width=500,
                            height=300)
    canvas.pack()
    root.update()

    logo = 'splashlogo.gif'
    if os.path.exists(logo):
        img = Tkinter.PhotoImage(file=logo)
        pnl = Tkinter.Label(canvas, image=img, background='white', bd=0)
        pnl.pack(side='top', fill='both', expand='yes')
        # Prevent garbage collection of img
        pnl.image=img

    def add_label(text='Change Me', font_size=12, foreground='#195866', height=1):
        return Tkinter.Label(
            master=canvas,
            width=250,
            height=height,
            text=text,
            font=('Helvetica', font_size),
            anchor=Tkinter.CENTER,
            foreground=foreground,
            background='white'
            )

    add_label('Welcome to...').pack(side='top')
    add_label(ProgramName, 18, '#FF5C1F', 2).pack()
    add_label(ProgramAuthor).pack()
    add_label(ProgramVersion).pack()

    root.update()
    time.sleep(5)
    dialog.destroy()
    return


class web2pyDialog(object):
    """ Main window dialog """

    def __init__(self, root, options):
        """ web2pyDialog constructor  """

        root.title('web2py server')
        self.root = Tkinter.Toplevel(root)
        self.options = options
        self.menu = Tkinter.Menu(self.root)
        servermenu = Tkinter.Menu(self.menu, tearoff=0)
        httplog = os.path.join(self.options.folder, 'httpserver.log')

        # Building the Menu
        item = lambda: try_start_browser(httplog)
        servermenu.add_command(label='View httpserver.log',
                               command=item)

        servermenu.add_command(label='Quit (pid:%i)' % os.getpid(),
                               command=self.quit)

        self.menu.add_cascade(label='Server', menu=servermenu)

        self.pagesmenu = Tkinter.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label='Pages', menu=self.pagesmenu)

        helpmenu = Tkinter.Menu(self.menu, tearoff=0)

        # Home Page
        item = lambda: try_start_browser('http://www.web2py.com')
        helpmenu.add_command(label='Home Page',
                             command=item)

        # About
        item = lambda: tkMessageBox.showinfo('About web2py', ProgramInfo)
        helpmenu.add_command(label='About',
                             command=item)

        self.menu.add_cascade(label='Info', menu=helpmenu)

        self.root.config(menu=self.menu)

        if options.taskbar:
            self.root.protocol('WM_DELETE_WINDOW',
                               lambda: self.quit(True))
        else:
            self.root.protocol('WM_DELETE_WINDOW', self.quit)

        sticky = Tkinter.NW

        # IP
        Tkinter.Label(self.root,
                      text='Server IP:',
                      justify=Tkinter.LEFT).grid(row=0,
                                                 column=0,
                                                 sticky=sticky)
        self.ip = Tkinter.Entry(self.root)
        self.ip.insert(Tkinter.END, self.options.ip)
        self.ip.grid(row=0, column=1, sticky=sticky)

        # Port
        Tkinter.Label(self.root,
                      text='Server Port:',
                      justify=Tkinter.LEFT).grid(row=1,
                                                 column=0,
                                                 sticky=sticky)

        self.port_number = Tkinter.Entry(self.root)
        self.port_number.insert(Tkinter.END, self.options.port)
        self.port_number.grid(row=1, column=1, sticky=sticky)

        # Password
        Tkinter.Label(self.root,
                      text='Choose Password:',
                      justify=Tkinter.LEFT).grid(row=2,
                                                 column=0,
                                                 sticky=sticky)

        self.password = Tkinter.Entry(self.root, show='*')
        self.password.bind('<Return>', lambda e: self.start())
        self.password.focus_force()
        self.password.grid(row=2, column=1, sticky=sticky)

        # Prepare the canvas
        self.canvas = Tkinter.Canvas(self.root,
                                     width=300,
                                     height=100,
                                     bg='black')
        self.canvas.grid(row=3, column=0, columnspan=2)
        self.canvas.after(1000, self.update_canvas)

        # Prepare the frame
        frame = Tkinter.Frame(self.root)
        frame.grid(row=4, column=0, columnspan=2)

        # Start button
        self.button_start = Tkinter.Button(frame,
                                           text='start server',
                                           command=self.start)

        self.button_start.grid(row=0, column=0)

        # Stop button
        self.button_stop = Tkinter.Button(frame,
                                          text='stop server',
                                          command=self.stop)

        self.button_stop.grid(row=0, column=1)
        self.button_stop.configure(state='disabled')

        if options.taskbar:
            self.tb = contrib.taskbar_widget.TaskBarIcon()
            self.checkTaskBar()

            if options.password != '<ask>':
                self.password.insert(0, options.password)
                self.start()
                self.root.withdraw()
        else:
            self.tb = None

    def checkTaskBar(self):
        """ Check taskbar status """

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
        """ Update app text """

        try:
            self.text.configure(state='normal')
            self.text.insert('end', text)
            self.text.configure(state='disabled')
        except:
            pass  # ## this should only happen in case app is destroyed

    def connect_pages(self):
        """ Connect pages """

        for arq in os.listdir('applications/'):
            if os.path.exists('applications/%s/__init__.py' % arq):
                url = self.url + '/' + arq
                start_browser = lambda u = url: try_start_browser(u)
                self.pagesmenu.add_command(label=url,
                                           command=start_browser)

    def quit(self, justHide=False):
        """ Finish the program execution """

        if justHide:
            self.root.withdraw()
        else:
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
        """ Show error message """

        tkMessageBox.showerror('web2py start server', message)

    def start(self):
        """ Start web2py server """

        password = self.password.get()

        if not password:
            self.error('no password, no web admin interface')

        ip = self.ip.get()

        regexp = '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
        if ip and not re.compile(regexp).match(ip):
            return self.error('invalid host ip address')

        try:
            port = int(self.port_number.get())
        except:
            return self.error('invalid port number')

        self.url = 'http://%s:%s' % (ip, port)
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
                profiler_filename=options.profiler_filename,
                ssl_certificate=options.ssl_certificate,
                ssl_private_key=options.ssl_private_key,
                min_threads=options.minthreads,
                max_threads=options.maxthreads,
                server_name=options.server_name,
                request_queue_size=req_queue_size,
                timeout=options.timeout,
                shutdown_timeout=options.shutdown_timeout,
                path=options.folder,
                interfaces=options.interfaces)

            thread.start_new_thread(self.server.start, ())
        except Exception, e:
            self.button_start.configure(state='normal')
            return self.error(str(e))

        self.button_stop.configure(state='normal')

        if not options.taskbar:
            thread.start_new_thread(start_browser, (ip, port))

        self.password.configure(state='readonly')
        self.ip.configure(state='readonly')
        self.port_number.configure(state='readonly')

        if self.tb:
            self.tb.SetServerRunning()

    def stop(self):
        """ Stop web2py server """

        self.button_start.configure(state='normal')
        self.button_stop.configure(state='disabled')
        self.password.configure(state='normal')
        self.ip.configure(state='normal')
        self.port_number.configure(state='normal')
        self.server.stop()

        if self.tb:
            self.tb.SetServerStopped()

    def update_canvas(self):
        """ Update canvas """

        try:
            t1 = os.path.getsize('httpserver.log')
        except:
            self.canvas.after(1000, self.update_canvas)
            return

        try:
            fp = open('httpserver.log', 'r')
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
            self.p0 = [100] * 300
            self.q0 = [self.canvas.create_line(i, 100, i + 1, 100,
                       fill='green') for i in xrange(len(self.p0) - 1)]

        self.canvas.after(1000, self.update_canvas)


def console():
    """ Defines the behavior of the console web2py execution """
    import optparse
    import textwrap

    usage = "python web2py.py"

    description = """\
    web2py Web Framework startup script.
    ATTENTION: unless a password is specified (-a 'passwd') web2py will
    attempt to run a GUI. In this case command line options are ignored."""

    description = textwrap.dedent(description)

    parser = optparse.OptionParser(usage, None, optparse.Option, ProgramVersion)

    parser.description = description

    parser.add_option('-i',
                      '--ip',
                      default='127.0.0.1',
                      dest='ip',
                      help='ip address of the server (127.0.0.1)')

    parser.add_option('-p',
                      '--port',
                      default='8000',
                      dest='port',
                      type='int',
                      help='port of server (8000)')

    msg = 'password to be used for administration'
    msg += ' (use -a "<recycle>" to reuse the last password))'
    parser.add_option('-a',
                      '--password',
                      default='<ask>',
                      dest='password',
                      help=msg)

    parser.add_option('-c',
                      '--ssl_certificate',
                      default='',
                      dest='ssl_certificate',
                      help='file that contains ssl certificate')

    parser.add_option('-k',
                      '--ssl_private_key',
                      default='',
                      dest='ssl_private_key',
                      help='file that contains ssl private key')

    parser.add_option('--ca-cert',
                      action='store',
                      dest='ssl_ca_certificate',
                      default=None,
                      help='Use this file containing the CA certificate to validate X509 certificates from clients')

    parser.add_option('-d',
                      '--pid_filename',
                      default='httpserver.pid',
                      dest='pid_filename',
                      help='file to store the pid of the server')

    parser.add_option('-l',
                      '--log_filename',
                      default='httpserver.log',
                      dest='log_filename',
                      help='file to log connections')

    parser.add_option('-n',
                      '--numthreads',
                      default=None,
                      type='int',
                      dest='numthreads',
                      help='number of threads (deprecated)')

    parser.add_option('--minthreads',
                      default=None,
                      type='int',
                      dest='minthreads',
                      help='minimum number of server threads')

    parser.add_option('--maxthreads',
                      default=None,
                      type='int',
                      dest='maxthreads',
                      help='maximum number of server threads')

    parser.add_option('-s',
                      '--server_name',
                      default=socket.gethostname(),
                      dest='server_name',
                      help='server name for the web server')

    msg = 'max number of queued requests when server unavailable'
    parser.add_option('-q',
                      '--request_queue_size',
                      default='5',
                      type='int',
                      dest='request_queue_size',
                      help=msg)

    parser.add_option('-o',
                      '--timeout',
                      default='10',
                      type='int',
                      dest='timeout',
                      help='timeout for individual request (10 seconds)')

    parser.add_option('-z',
                      '--shutdown_timeout',
                      default='5',
                      type='int',
                      dest='shutdown_timeout',
                      help='timeout on shutdown of server (5 seconds)')

    parser.add_option('--socket-timeout',
                      default=5,
                      type='int',
                      dest='socket_timeout',
                      help='timeout for socket (5 second)')

    parser.add_option('-f',
                      '--folder',
                      default=os.getcwd(),
                      dest='folder',
                      help='folder from which to run web2py')

    parser.add_option('-v',
                      '--verbose',
                      action='store_true',
                      dest='verbose',
                      default=False,
                      help='increase --test verbosity')

    parser.add_option('-Q',
                      '--quiet',
                      action='store_true',
                      dest='quiet',
                      default=False,
                      help='disable all output')

    msg = 'set debug output level (0-100, 0 means all, 100 means none;'
    msg += ' default is 30)'
    parser.add_option('-D',
                      '--debug',
                      dest='debuglevel',
                      default=30,
                      type='int',
                      help=msg)

    msg = 'run web2py in interactive shell or IPython (if installed) with'
    msg += ' specified appname (if app does not exist it will be created).'
    msg += ' APPNAME like a/c/f (c,f optional)'
    parser.add_option('-S',
                      '--shell',
                      dest='shell',
                      metavar='APPNAME',
                      help=msg)

    msg = 'run web2py in interactive shell or bpython (if installed) with'
    msg += ' specified appname (if app does not exist it will be created).'
    msg += '\n Use combined with --shell'
    parser.add_option('-B',
                      '--bpython',
                      action='store_true',
                      default=False,
                      dest='bpython',
                      help=msg)

    msg = 'only use plain python shell; should be used with --shell option'
    parser.add_option('-P',
                      '--plain',
                      action='store_true',
                      default=False,
                      dest='plain',
                      help=msg)

    msg = 'auto import model files; default is False; should be used'
    msg += ' with --shell option'
    parser.add_option('-M',
                      '--import_models',
                      action='store_true',
                      default=False,
                      dest='import_models',
                      help=msg)

    msg = 'run PYTHON_FILE in web2py environment;'
    msg += ' should be used with --shell option'
    parser.add_option('-R',
                      '--run',
                      dest='run',
                      metavar='PYTHON_FILE',
                      default='',
                      help=msg)

    msg = 'run scheduled tasks for the specified apps'
    msg += '-K app1,app2,app3'
    msg += 'requires a scheduler defined in the models'
    parser.add_option('-K',
                      '--scheduler',
                      dest='scheduler',
                      default=None,
                      help=msg)

    msg = 'run doctests in web2py environment; ' +\
        'TEST_PATH like a/c/f (c,f optional)'
    parser.add_option('-T',
                      '--test',
                      dest='test',
                      metavar='TEST_PATH',
                      default=None,
                      help=msg)

    parser.add_option('-W',
                      '--winservice',
                      dest='winservice',
                      default='',
                      help='-W install|start|stop as Windows service')

    msg = 'trigger a cron run manually; usually invoked from a system crontab'
    parser.add_option('-C',
                      '--cron',
                      action='store_true',
                      dest='extcron',
                      default=False,
                      help=msg)

    msg = 'triggers the use of softcron'
    parser.add_option('--softcron',
                      action='store_true',
                      dest='softcron',
                      default=False,
                      help=msg)

    parser.add_option('-N',
                      '--no-cron',
                      action='store_true',
                      dest='nocron',
                      default=False,
                      help='do not start cron automatically')

    parser.add_option('-J',
                      '--cronjob',
                      action='store_true',
                      dest='cronjob',
                      default=False,
                      help='identify cron-initiated command')

    parser.add_option('-L',
                      '--config',
                      dest='config',
                      default='',
                      help='config file')

    parser.add_option('-F',
                      '--profiler',
                      dest='profiler_filename',
                      default=None,
                      help='profiler filename')

    parser.add_option('-t',
                      '--taskbar',
                      action='store_true',
                      dest='taskbar',
                      default=False,
                      help='use web2py gui and run in taskbar (system tray)')

    parser.add_option('',
                      '--nogui',
                      action='store_true',
                      default=False,
                      dest='nogui',
                      help='text-only, no GUI')

    parser.add_option('-A',
                      '--args',
                      action='store',
                      dest='args',
                      default=None,
                      help='should be followed by a list of arguments to be passed to script, to be used with -S, -A must be the last option')

    parser.add_option('--no-banner',
                      action='store_true',
                      default=False,
                      dest='nobanner',
                      help='Do not print header banner')


    msg = 'listen on multiple addresses: "ip:port:cert:key:ca_cert;ip2:port2:cert2:key2:ca_cert2;..." (:cert:key optional; no spaces)'
    parser.add_option('--interfaces',
                      action='store',
                      dest='interfaces',
                      default=None,
                      help=msg)

    if '-A' in sys.argv: k = sys.argv.index('-A')
    elif '--args' in sys.argv: k = sys.argv.index('--args')
    else: k=len(sys.argv)
    sys.argv, other_args = sys.argv[:k], sys.argv[k+1:]
    (options, args) = parser.parse_args()
    options.args = [options.run] + other_args
    global_settings.cmd_options = options
    global_settings.cmd_args = args

    if options.quiet:
        capture = cStringIO.StringIO()
        sys.stdout = capture
        logger.setLevel(logging.CRITICAL + 1)
    else:
        logger.setLevel(options.debuglevel)

    if options.config[-3:] == '.py':
        options.config = options.config[:-3]

    if options.cronjob:
        global_settings.cronjob = True  # tell the world
        options.nocron = True   # don't start cron jobs
        options.plain = True    # cronjobs use a plain shell

    options.folder = os.path.abspath(options.folder)

    #  accept --interfaces in the form
    #  "ip:port:cert:key;ip2:port2;ip3:port3:cert3:key3"
    #  (no spaces; optional cert:key indicate SSL)
    if isinstance(options.interfaces, str):
        options.interfaces = [
            interface.split(':') for interface in options.interfaces.split(';')]
        for interface in options.interfaces:
            interface[1] = int(interface[1])    # numeric port
        options.interfaces = [
            tuple(interface) for interface in options.interfaces]

    if options.numthreads is not None and options.minthreads is None:
        options.minthreads = options.numthreads  # legacy

    if not options.cronjob:
        # If we have the applications package or if we should upgrade
        if not os.path.exists('applications/__init__.py'):
            write_file('applications/__init__.py', '')

        if not os.path.exists('welcome.w2p') or os.path.exists('NEWINSTALL'):
            try:
                w2p_pack('welcome.w2p','applications/welcome')
                os.unlink('NEWINSTALL')
            except:
                msg = "New installation: unable to create welcome.w2p file"
                sys.stderr.write(msg)

    return (options, args)

def start_schedulers(options):
    apps = [app.strip() for app in options.scheduler.split(',')]
    try:
        from multiprocessing import Process
    except:
        sys.stderr.write('Sorry, -K only supported for python 2.6-2.7\n')
        return
    processes = []
    code = "from gluon import current; current._scheduler.loop()"
    for app in apps:
        print 'starting scheduler for "%s"...' % app
        args = (app,True,True,None,False,code)
        logging.getLogger().setLevel(logging.DEBUG)
        p = Process(target=run, args=args)
        processes.append(p)
        print "Currently running %s scheduler processes" % (len(processes))
        p.start()
        print "Processes started"
    for p in processes:
        try:
            p.join()
        except KeyboardInterrupt:
            p.terminate()
            p.join()


def start(cron=True):
    """ Start server  """

    # ## get command line arguments

    (options, args) = console()

    if not options.nobanner:
        print ProgramName
        print ProgramAuthor
        print ProgramVersion

    from dal import drivers
    if not options.nobanner:
        print 'Database drivers available: %s' % ', '.join(drivers)


    # ## if -L load options from options.config file
    if options.config:
        try:
            options2 = __import__(options.config, {}, {}, '')
        except Exception:
            try:
                # Jython doesn't like the extra stuff
                options2 = __import__(options.config)
            except Exception:
                print 'Cannot import config file [%s]' % options.config
                sys.exit(1)
        for key in dir(options2):
            if hasattr(options,key):
                setattr(options,key,getattr(options2,key))

    # ## if -T run doctests (no cron)
    if hasattr(options,'test') and options.test:
        test(options.test, verbose=options.verbose)
        return

    # ## if -K
    if options.scheduler:
        try:
            start_schedulers(options)
        except KeyboardInterrupt:
            pass
        return

    # ## if -S start interactive shell (also no cron)
    if options.shell:
        if not options.args is None:
            sys.argv[:] = options.args
        run(options.shell, plain=options.plain, bpython=options.bpython,
            import_models=options.import_models, startfile=options.run)
        return

    # ## if -C start cron run (extcron) and exit
    # ## if -N or not cron disable cron in this *process*
    # ## if --softcron use softcron
    # ## use hardcron in all other cases
    if options.extcron:
        print 'Starting extcron...'
        global_settings.web2py_crontype = 'external'
        extcron = newcron.extcron(options.folder)
        extcron.start()
        extcron.join()
        return
    elif cron and not options.nocron and options.softcron:
        print 'Using softcron (but this is not very efficient)'
        global_settings.web2py_crontype = 'soft'
    elif cron and not options.nocron:
        print 'Starting hardcron...'
        global_settings.web2py_crontype = 'hard'
        newcron.hardcron(options.folder).start()

    # ## if -W install/start/stop web2py as service
    if options.winservice:
        if os.name == 'nt':
            web2py_windows_service_handler(['', options.winservice],
                    options.config)
        else:
            print 'Error: Windows services not supported on this platform'
            sys.exit(1)
        return

    # ## if no password provided and havetk start Tk interface
    # ## or start interface if we want to put in taskbar (system tray)

    try:
        options.taskbar
    except:
        options.taskbar = False

    if options.taskbar and os.name != 'nt':
        print 'Error: taskbar not supported on this platform'
        sys.exit(1)

    root = None

    if not options.nogui:
        try:
            import Tkinter
            havetk = True
        except ImportError:
            logger.warn('GUI not available because Tk library is not installed')
            havetk = False

        if options.password == '<ask>' and havetk or options.taskbar and havetk:
            try:
                root = Tkinter.Tk()
            except:
                pass

    if root:
        root.focus_force()
        if not options.quiet:
            presentation(root)
        master = web2pyDialog(root, options)
        signal.signal(signal.SIGTERM, lambda a, b: master.quit())

        try:
            root.mainloop()
        except:
            master.quit()

        sys.exit()

    # ## if no tk and no password, ask for a password

    if not root and options.password == '<ask>':
        options.password = raw_input('choose a password:')

    if not options.password and not options.nobanner:
        print 'no password, no admin interface'

    # ## start server

    (ip, port) = (options.ip, int(options.port))

    if not options.nobanner:
        print 'please visit:'
        print '\thttp://%s:%s' % (ip, port)
        print 'use "kill -SIGTERM %i" to shutdown the web2py server' % os.getpid()

    server = main.HttpServer(ip=ip,
                             port=port,
                             password=options.password,
                             pid_filename=options.pid_filename,
                             log_filename=options.log_filename,
                             profiler_filename=options.profiler_filename,
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
    logging.shutdown()




