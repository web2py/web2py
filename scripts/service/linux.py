from service import ServiceBase
import os, sys, time, subprocess, atexit
from signal import SIGTERM

class LinuxService(ServiceBase):
    def __init__(self, name, label, stdout='/dev/null', stderr='/dev/null'):
        ServiceBase.__init__(self, name, label, stdout, stderr)
        self.pidfile = '/tmp/%s.pid' % name
        self.config_file = '/etc/%s.conf' % name
    
    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced 
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit first parent
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            return
    
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
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            return
    
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file('/dev/null', 'r')
        so = file(self.stdout or '/dev/null', 'a+')
        se = file(self.stderr or '/dev/null', 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        
    def getpid(self):
        # Check for a pidfile to see if the daemon already runs
        try:                
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
            
        return pid
        
    def status(self):
        pid = self.getpid()
        if pid:
            return 'Service running with PID %s.' % pid
        else:
            return 'Service is not running.'
            
    def check_permissions(self):
        if not os.geteuid() == 0:
            return (False, 'This script must be run with root permissions.')
        else:
            return (True, '')

    def start(self):
        """
        Start the daemon
        """
        pid = self.getpid()
    
        if pid:
            message = "Service already running under PID %s\n"
            sys.stderr.write(message % self.pidfile)
            return
        
        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        pid = self.getpid()
    
        if not pid:
            message = "Service is not running\n"
            sys.stderr.write(message)
            return # not an error in a restart

        # Try killing the daemon process    
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.5)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                return

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()
        
    def run(self):
        atexit.register(self.terminate)
        
        args = self.load_configuration()[0]
        stdout = open(self.stdout, 'a+')
        stderr = open(self.stderr, 'a+')
        process = subprocess.Popen(args, stdout=stdout, stderr=stderr)
        file(self.pidfile,'w+').write("%s\n" % process.pid)
        process.wait()
        
        self.terminate()
        
    def terminate(self):
        try:
            os.remove(self.pidfile)
        except:
            pass

    def install(self):
        env = self.detect_environment()
        src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'service.py')

        # make sure this script is executable
        self.run_command('chmod', '+x', src_path)

        # link this daemon to the service directory
        dest_path = env['rc.d-path'] + self.name
        os.symlink(src_path, dest_path)

        # start the service at boot
        install_command = self.get_service_installer_command(env)
        result = self.run_command(*install_command)
        self.start()
        
    def uninstall(self):
        self.stop()
        env = self.detect_environment()

        # stop the service from autostarting
        uninstall_command = self.get_service_uninstaller_command(env)
        result = self.run_command(*uninstall_command)

        # remove link to the script from the service directory
        path = env['rc.d-path'] + self.name
        os.remove(path)
        
    def detect_environment(self):
        """
        Returns a dictionary of command/path to the required command-line applications.
        One key is 'dist' which will either be 'debian' or 'redhat', which is the best
        guess as to which Linux distribution the current system is based on.
        """
        check_for = [
            'chkconfig',
            'service',
            'update-rc.d',
            'rpm',
            'dpkg',
        ]

        env = dict()
        for cmd in check_for:
            result = self.run_command('which', cmd)
            if result[0]:
                env[cmd] = result[0].replace('\n', '')

        if 'rpm' in env:
            env['dist'] = 'redhat'
            env['rc.d-path'] = '/etc/rc.d/init.d/'
        elif 'dpkg' in env:
            env['dist'] = 'debian'
            env['rc.d-path'] = '/etc/init.d/'
        else:
            env['dist'] = 'unknown'
            env['rc.d-path'] = '/dev/null/'

        return env
        
    def get_service_installer_command(self, env):
        """
        Returns list of args required to set a service to run on boot.
        """
        if env['dist'] == 'redhat':
            cmd = env['chkconfig']
            return [cmd, self.name, 'on']
        else:
            cmd = env['update-rc.d']
            return [cmd, self.name, 'defaults']

    def get_service_uninstaller_command(self, env):
        """
        Returns list of arge required to stop a service from running at boot.
        """
        if env['dist'] == 'redhat':
            cmd = env['chkconfig']
            return [cmd, self.name, 'off']
        else:
            cmd = env['update-rc.d']
            return [cmd, self.name, 'remove']

