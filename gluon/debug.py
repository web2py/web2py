#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>,
limodou <limodou@gmail.com> and srackham <srackham@gmail.com>.
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

"""

import logging
import pdb
import Queue
import sys

logger = logging.getLogger("web2py")

class Pipe(Queue.Queue):
    def __init__(self, name, mode='r', *args, **kwargs):
        self.__name = name
        Queue.Queue.__init__(self, *args, **kwargs)

    def write(self, data):
        logger.debug("debug %s writting %s" % (self.__name, data))
        self.put(data)

    def flush(self):
        # mark checkpoint (complete message)
        logger.debug("debug %s flushing..." % self.__name)
        self.put(None)
        # wait until it is processed
        self.join()
        logger.debug("debug %s flush done" % self.__name)

    def read(self, count=None, timeout=None):
        logger.debug("debug %s reading..." % (self.__name, ))
        data = self.get(block=True, timeout=timeout)
        # signal that we are ready
        self.task_done()
        logger.debug("debug %s read %s" % (self.__name, data))
        return data

    def readline(self):
        logger.debug("debug %s readline..." % (self.__name, ))
        return self.read()


pipe_in = Pipe('in')
pipe_out = Pipe('out')

debugger = pdb.Pdb(completekey=None, stdin=pipe_in, stdout=pipe_out,)

def set_trace():
    "breakpoint shortcut (like pdb)"
    logger.info("DEBUG: set_trace!")
    debugger.set_trace(sys._getframe().f_back)


def stop_trace():
    "stop waiting for the debugger (called atexit)"
    # this should prevent communicate is wait forever a command result
    # and the main thread has finished
    logger.info("DEBUG: stop_trace!")
    pipe_out.write("debug finished!")
    pipe_out.write(None)
    #pipe_out.flush()

def communicate(command=None):
    "send command to debbuger, wait result"
    if command is not None:
        logger.info("DEBUG: sending command %s" % command)
        pipe_in.write(command)
        #pipe_in.flush()
    result = []
    while True:
        data = pipe_out.read()
        if data is None:
            break
        result.append(data)
    logger.info("DEBUG: result %s" % repr(result))
    return ''.join(result)





