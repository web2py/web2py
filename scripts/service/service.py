#!/usr/bin/env python

import sys, os, time, subprocess

class Base:
    def run_command(self, *args):
        """
        Returns the output of a command as a tuple (output, error).
        """
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.communicate()

class ServiceBase(Base):
    def __init__(self, name, label, stdout=None, stderr=None):
        self.name = name
        self.label = label
        self.stdout = stdout
        self.stderr = stderr
        self.config_file = None
        
    def load_configuration(self):
        """
        Loads the configuration required to build the command-line string
        for running web2py. Returns a tuple (command_args, config_dict).
        """
        s = os.path.sep
        
        default = dict(
            python = 'python',
            web2py = os.path.join(s.join(__file__.split(s)[:-3]), 'web2py.py'),
            http_enabled = True,
            http_ip = '0.0.0.0',
            http_port = 8000,
            https_enabled = True,
            https_ip = '0.0.0.0',
            https_port = 8001,
            https_key = '',
            https_cert = '',
            password = '<recycle>',
        )
        
        config = default
        if self.config_file:
            try:
                f = open(self.config_file, 'r')
                lines = f.readlines()
                f.close()
            
                for line in lines:
                    fields = line.split('=', 1)
                    if len(fields) == 2:
                        key, value = fields
                        key = key.strip()
                        value = value.strip()
                        config[key] = value
            except:
                pass
        
        web2py_path = os.path.dirname(config['web2py'])
        os.chdir(web2py_path)
        
        args = [config['python'], config['web2py']]
        interfaces = []
        ports = []

        if config['http_enabled']:
            ip = config['http_ip']
            port = config['http_port']
            interfaces.append('%s:%s' % (ip, port))
            ports.append(port)
        if config['https_enabled']:
            ip = config['https_ip']
            port = config['https_port']
            key = config['https_key']
            cert = config['https_cert']
            if key != '' and cert != '':
                interfaces.append('%s:%s:%s:%s' % (ip, port, cert, key))
                ports.append(ports)
        if len(interfaces) == 0:
            sys.exit('Configuration error. Must have settings for http and/or https')
        
        password = config['password']
        if not password == '<recycle>':
            from gluon import main
            for port in ports:
                main.save_password(password, port)
                
            password = '<recycle>'
            
        args.append('-a "%s"' % password)
        
        interfaces = ';'.join(interfaces)
        args.append('--interfaces=%s' % interfaces)
        
        if 'log_filename' in config.key():
            log_filename = config['log_filename']
            args.append('--log_filename=%s' % log_filename)
        
        return (args, config)
    
    def start(self):
        pass
        
    def stop(self):
        pass
        
    def restart(self):
        pass
        
    def status(self):
        pass
        
    def run(self):
        pass
        
    def install(self):
        pass
        
    def uninstall(self):
        pass
        
    def check_permissions(self):
        """
        Does the script have permissions to install, uninstall, start, and stop services?
        Return value must be a tuple (True/False, error_message_if_False).
        """
        return (False, 'Permissions check not implemented')
        
class WebServerBase(Base):
    def install(self):
        pass
        
    def uninstall(self):
        pass
        

def get_service():
    service_name = 'web2py'
    service_label = 'web2py Service'
    
    if sys.platform == 'linux2':
        from linux import LinuxService as Service            
    elif sys.platform == 'darwin':
        # from mac import MacService as Service
        sys.exit('Mac OS X is not yet supported.\n')
    elif sys.platform == 'win32':
        # from windows import WindowsService as Service
        sys.exit('Windows is not yet supported.\n')
    else:
        sys.exit('The following platform is not supported: %s.\n' % sys.platform)
    
    service = Service(service_name, service_label)
    return service
             
if __name__ == '__main__':
    service = get_service()
    is_root, error_message = service.check_permissions()
    if not is_root:
        sys.exit(error_message)
        
    if len(sys.argv) >= 2:
        command = sys.argv[1]
        if command == 'start':
            service.start()
        elif command == 'stop':
            service.stop()
        elif command == 'restart':
            service.restart()
        elif command == 'status':
            print service.status() + '\n'
        elif command == 'run':
            service.run()
        elif command == 'install':
            service.install()
        elif command == 'uninstall':
            service.uninstall()
        elif command == 'install-apache':
            # from apache import Apache
            # server = Apache()
            # server.install()
            sys.exit('Configuring Apache is not yet supported.\n')
        elif command == 'uninstall-apache':
            # from apache import Apache
            # server = Apache()
            # server.uninstall()
            sys.exit('Configuring Apache is not yet supported.\n')
        else:
            sys.exit('Unknown command: %s' % command)
    else:
        print 'Usage: %s [command] \n' % sys.argv[0] + \
            '\tCommands:\n' + \
                '\t\tstart             Starts the service\n' + \
                '\t\tstop              Stop the service\n' + \
                '\t\trestart           Restart the service\n' + \
                '\t\tstatus            Check if the service is running\n' + \
                '\t\trun               Run service is blocking mode\n' + \
                '\t\t                      (Press Ctrl + C to exit)\n' + \
                '\t\tinstall           Install the service\n' + \
                '\t\tuninstall         Uninstall the service\n' + \
                '\t\tinstall-apache    Install as an Apache site\n' + \
                '\t\tuninstall-apache  Uninstall from Apache\n'
