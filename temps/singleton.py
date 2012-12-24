import threading

class SingletonPool(object):

    thread_local = threading.local
    locker = threadling.RLock()
    pool = dict()
    
    def __new__(cls, uri, *args, **kwargs):
        print 'in new'
        if not hasattr(thread_local,'db_instances'):
            thread_local.db_instances = {}
        try:
            instance = thread_local.db_instances[uri]
            print 'found existing instance'
        except KeyError:
            instance = super(DAL, cls).__new__(cls, uri, *args, **kwargs)
            thread_local.db_instances[uri] = instance
        return instance

    def __init__(self,uri,*args, **kwargs):
        print "INIT"
        try:
            self.uri
            print 'have self.uri',self.uri
        except:
            self.uri = uri

db=DAL('test')
print 'here'
db=DAL('test')
