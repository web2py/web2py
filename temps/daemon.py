#!/usr/bin/env python

import sys, os, time, atexit, signal, subprocess

class Daemon:
    """
    A generic daemon class.	
    Usage: subclass the Daemon class and override the run() method
    From: http://bit.ly/TnPxwp
    Developed by Sander Marechal
    Minor modifications by Massimo Di Pierro
    """
    def __init__(self,
                 pidfile, 
		 stdin='/dev/null', 
		 stdout='/dev/null', 
		 stderr=None):
	    
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
	
    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens 
        "Advanced Programming in the UNIX Environment" 
        for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit first parent
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (
                    e.errno, e.strerror))
            sys.exit(1)
	
        # decouple from parent environment
        os.chdir("/") 
        os.setsid() 
        os.umask(0) 
	
        # do second fork
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit from second parent
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (
                    e.errno, e.strerror))
            sys.exit(1) 
	
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        if self.stdin != '/dev/null':
            os.mkfifo(self.stdin)
        si = open(self.stdin, 'r')        
        if self.stdout != '/dev/null':
            os.mkfifo(self.stdout)
        so = open(self.stdout, 'a+')
        if self.stderr is None:
            se = so
        else:
            if self.stderr != '/dev/null':
                os.mkfifo(self.stderr)
            se = open(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
	
        # write pidfile
        # atexit.register(self.delpid)
        pid = str(os.getpid())
        open(self.pidfile,'w+').write("%s\n" % pid)
	
    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = open(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
	
        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)
            
        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = open(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
	
        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart
        
        # Try killing the daemon process	
        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
                else:
                    print str(err)
                    sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()
        
    def run(self):
        """
        You should override this method when you subclass Daemon.
        It will be called after the process has been
        daemonized by start() or restart().
        """
        if hasattr(self,'args'):
            subprocess.call(self.args,
                            stdin=sys.stdin,
                            stdout=sys.stdout,
                            stderr=sys.stderr,
                            shell=True)


os.system('rm t1/*')
d = Daemon(
    pidfile = '/Users/massimodipierro/Dropbox/web2py/temps/t1/process.pid',
    stdin = '/Users/massimodipierro/Dropbox/web2py/temps/t1/fifo.in',
    stdout = '/Users/massimodipierro/Dropbox/web2py/temps/t1/fifo.out',
    stderr = None)

d.args = ['python looping.py']
d.start()
