import threading
import logging

GLOBAL_LOCKER = threading.RLock()
THREAD_LOCAL = threading.local()

LOGGER = logging.getLogger("web2py.dal")

DEFAULT = lambda: None

def IDENTITY(x): return x
def OR(a,b): return a|b
def AND(a,b): return a&b
