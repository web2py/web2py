
class MulticastDelegate(object):
    def __init__(self):
        self.delegates = []

    def __iadd__(self, delegate):
        self.add(delegate)
        return self

    def add(self, delegate):
        self.delegates.append(delegate)

    def __isub__(self, delegate):
        self.delegates.remove(delegate)
        return self

    def __call__(self, *args, **kwargs):
        for d in self.delegates:
            d(*args, **kwargs)

