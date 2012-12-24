import os
import subprocess
import pickle

class Process(object):
    def __init__(self,path):
        self.path = path
        self.fifo_in_filename = os.path.join(self.path,'fifo.in')
        self.fifo_out_filename = os.path.join(self.path,'fifo.out')
        self.process_filename = os.path.join(self.path,'process.pickle')
        if not os.path.exists(path):
            os.mkdir(path)
    def run(self,command):        
        if os.path.exists(self.fifo_in_filename):
            os.unlink(self.fifo_in_filename)
        if os.path.exists(self.fifo_out_filename):
            os.unlink(self.fifo_out_filename)
        fifo_in = os.mkfifo(self.fifo_in_filename)
        fifo_out = os.mkfifo(self.fifo_out_filename)
        s = subprocess.Popen(command, shell=True,
                             stdin=fifo_in,
                             stdout=fifo_out,
                             stderr=fifo_out,
                             close_fds=True)
        pickle.dump(s,open(self.process_filename,'wb'))
    def interact(self):
        fifo_out = open(self.fifo_out_filename,'rb')
        while True:
            print 'x',fifo_out.read(1)

p = Process('t1').run('python looping.py')
q = Process('t1').interact()
