import weakref

DEFAULT = lambda: None

class AuthAPI(object):

    def __init__(self, auth):
        self.auth = weakref.ref(auth)
        self.settings = weakref.proxy(auth.settings)
        self.messages = weakref.proxy(auth.messages)
