import os

class Path(object):
    def __init__(self,s='/',sep=os.path.sep):
        self.sep = sep
        self.s = s.split(sep)
    def __str__(self):
        return self.sep.join(self.s)
    def __add__(self,other):
        if other[0]=='':
            return Path(other)
        else:
            return Path(str(self)+os.sep+str(other))
    def __getitem__(self,i):
        return self.s[i]
    def __setitem__(self,i,v):
        self.s[i] = v
    def append(self,v):
        self.s.append(v)
    @property
    def filename(self):
        return self.s[-1]
    @property
    def folder(self):
        return Path(self.sep.join(self.s[:-1]))

>>> path = Path('/this/is/an/example.png')
>>> print path[-1]
example.png
>>> print path.filename
example.png
>>> print path.folder
/this/is/an
>>> path[1]='that'
/that/is/an/example.png
>>> print path.folder + 'this'
/that/is/an/this
