#!/usr/bin/env python

import sys, os
import subprocess
import threading
import socket
import tempfile

def daemonize():
    sys.stdout.flush()
    sys.stderr.flush()
    pid = os.fork()
    if pid<0:
        raise RuntimeError, "cannot fork"
    elif pid>0:
        (pid,status) = os.wait()
        sys.exit(status)
    os.chdir("/")
    os.setsid()
    os.umask(0)
    pid = os.fork()
    if pid<0:
        raise RuntimeError, "cannot fork"
    elif pid>0:
        sys.exit(0)
    os.dup2(os.open('/dev/null',os.O_RDONLY),sys.stdin.fileno())
    os.dup2(os.open('/dev/null',os.O_WRONLY),sys.stdout.fileno())
    os.dup2(os.open('/dev/null',os.O_WRONLY),sys.stderr.fileno())

class SmokingDaemon(threading.Thread):
    def __init__(self, 
                 cmd,
                 path,
                 tempdir = None):
        self.cmd = cmd
        self.path = path
        self.tempdir = tempdir or tempfile.mkdtemp()
        self.fifo_in_name = os.path.join(self.tempdir,'in.fifo')
        self.fifo_out_name = os.path.join(self.tempdir,'out.fifo')
        self.fifo_err_name = os.path.join(self.tempdir,'err.fifo')
        daemonize(path)
        threading.Thread.__init__(self)
    
    def run(self):
        try: os.unlink(self.fifo_in_name)
        except: pass
        try: os.unlink(self.fifo_out_name)
        except: pass
        os.mkfifo(self.fifo_in_name)
        os.mkfifo(self.fifo_out_name)
        fifo_in_read = os.fdopen(
            os.open(self.fifo_in_name,os.O_RDONLY|os.O_NONBLOCK))
        self.output = os.fdopen(
            os.open(self.fifo_out_name,os.O_RDONLY|os.O_NONBLOCK))
        self.input = open(self.fifo_in_name,'a+')
        fifo_out_write = open(self.fifo_out_name,'a+')
        process = subprocess.call(self.cmd,
                                  shell=True,
                                  stdin=fifo_in_read,
                                  stdout=fifo_out_write,
                                  stderr=fifo_out_write)

sd = SmokingDaemon('ls -l','fifo.in','fifo.out')
sd.start()
sd.server()
sd.join()
open(sd.output.read()

sd = SmokingDaemon(id)
sd.start(command)
sd.stop()
sd.kill()
sd.seek()
sd.read(bytes)
sd.readline()
sd.write('hello world')
