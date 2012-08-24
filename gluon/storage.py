#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Provides:

- List; like list but returns None instead of IndexOutOfBounds
- Storage; like dictionary allowing also for `obj.foo` for `obj['foo']`
"""

import cPickle
import portalocker

__all__ = ['List', 'Storage', 'Settings', 'Messages',
           'StorageList', 'load_storage', 'save_storage']

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`, and setting obj.foo = None deletes item foo.

        >>> o = Storage(a=1)
        >>> print o.a
        1

        >>> o['a']
        1

        >>> o.a = 2
        >>> print o['a']
        2

        >>> del o.a
        >>> print o.a
        None
    """
    def __getattr__(self, key):
        return dict.get(self, key, None)
    def __setattr__(self, key, value):
        self[key] = value
    def __delattr__(self, key):
        del self[key]
    def __getitem__(self, key):
        return dict.get(self, key, None)
    def __repr__(self):
        return '<Storage %s>' + dict.__repr__(self)
    def __getstate__(self):
        return dict(self)
    def __setstate__(self,values):
        self.update(values)

    def getlist(self,key):
        """
        Return a Storage value as a list.

        If the value is a list it will be returned as-is.
        If object is None, an empty list will be returned.
        Otherwise, [value] will be returned.

        Example output for a query string of ?x=abc&y=abc&y=def
        >>> request = Storage()
        >>> request.vars = Storage()
        >>> request.vars.x = 'abc'
        >>> request.vars.y = ['abc', 'def']
        >>> request.vars.getlist('x')
        ['abc']
        >>> request.vars.getlist('y')
        ['abc', 'def']
        >>> request.vars.getlist('z')
        []
        """
        value = self.get(key,[])
        return value if not value else \
            value if isinstance(value,(list,tuple)) else [value]

    def getfirst(self,key,default=None):
        """
        Return the first or only value when given a request.vars-style key.

        If the value is a list, its first item will be returned;
        otherwise, the value will be returned as-is.

        Example output for a query string of ?x=abc&y=abc&y=def
        >>> request = Storage()
        >>> request.vars = Storage()
        >>> request.vars.x = 'abc'
        >>> request.vars.y = ['abc', 'def']
        >>> request.vars.getfirst('x')
        'abc'
        >>> request.vars.getfirst('y')
        'abc'
        >>> request.vars.getfirst('z')
        """
        values = self.getlist(key)
        return values[0] if values else default

    def getlast(self,key,default=None):
        """
        Returns the last or only single value when
        given a request.vars-style key.

        If the value is a list, the last item will be returned;
        otherwise, the value will be returned as-is.

        Simulated output with a query string of ?x=abc&y=abc&y=def
        >>> request = Storage()
        >>> request.vars = Storage()
        >>> request.vars.x = 'abc'
        >>> request.vars.y = ['abc', 'def']
        >>> request.vars.getlast('x')
        'abc'
        >>> request.vars.getlast('y')
        'def'
        >>> request.vars.getlast('z')
        """
        values = self.getlist(key)
        return values[-1] if values else default

PICKABLE = (str,int,long,float,bool,list,dict,tuple,set)

class StorageList(Storage):
    """
    like Storage but missing elements default to [] instead of None
    """
    def __getitem__(self,key):
        return self.__gteattr__(key)
    def __getattr__(self, key):
        if key in self:
            return getattr(self,key)
        else:
            r = []
            setattr(self,key,r)
            return r

def load_storage(filename):
    fp = None
    try:
        fp = portalocker.LockedFile(filename, 'rb')
        storage = cPickle.load(fp)
    finally:
        if fp: fp.close()
    return Storage(storage)

def save_storage(storage, filename):
    fp = None
    try:
        fp = portalocker.LockedFile(filename, 'wb')
        cPickle.dump(dict(storage), fp)
    finally:
        if fp: fp.close()

class Settings(Storage):
    def __setattr__(self, key, value):
        if key != 'lock_keys' and self['lock_keys'] and key not in self:
            raise SyntaxError, 'setting key \'%s\' does not exist' % key
        if key != 'lock_values' and self['lock_values']:
            raise SyntaxError, 'setting value cannot be changed: %s' % key
        self[key] = value

class Messages(Settings):
    def __init__(self, T):
        Storage.__init__(self,T=T)
    def __getattr__(self, key):
        value = self[key]
        if isinstance(value, str):
            return str(self.T(value))
        return value

class FastStorage(dict):
    """
    Eventually this should replace class Storage but causes memory leak 
    because of http://bugs.python.org/issue1469629

    >>> s = FastStorage()
    >>> s.a = 1
    >>> s.a
    1
    >>> s['a']
    1
    >>> s.b
    >>> s['b']
    >>> s['b']=2
    >>> s['b']
    2
    >>> s.b
    2
    >>> isinstance(s,dict)
    True
    >>> dict(s)
    {'a': 1, 'b': 2}
    >>> dict(FastStorage(s))
    {'a': 1, 'b': 2}
    >>> import pickle
    >>> s = pickle.loads(pickle.dumps(s))
    >>> dict(s)
    {'a': 1, 'b': 2}
    >>> del s.b
    >>> del s.a
    >>> s.a
    >>> s.b
    >>> s['a']
    >>> s['b']
    """
    def __init__(self, *args, **kwargs): 
        dict.__init__(self, *args, **kwargs)
        self.__dict__ = self
    def __getattr__(self,key):
        return getattr(self,key) if key in self else None
    def __getitem__(self,key):
        return dict.get(self,key,None)
    def copy(self):
        self.__dict__ = {}
        s = FastStorage(self)
        self.__dict__ = self
        return s
    def __repr__(self):
        return '<Storage %s>' % dict.__repr__(self)
    def __getstate__(self):
        return dict(self)
    def __setstate__(self, sdict):
        dict.__init__(self, sdict)
        self.__dict__=self
    def update(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__dict__=self

class List(list):
    """
    Like a regular python list but a[i] if i is out of bounds return None
    instead of IndexOutOfBounds
    """

    def __call__(self, i, default=None, cast=None, otherwise=None):
        """
        request.args(0,default=0,cast=int,otherwise='http://error_url')
        request.args(0,default=0,cast=int,otherwise=lambda:...)
        """
        n = len(self)
        if 0<=i<n or -n<=i<0:
            value = self[i]
        else:
            value = default
        if cast:
            try:
                value = cast(value)
            except (ValueError, TypeError):
                from http import HTTP, redirect
                if otherwise is None:
                    raise HTTP(404)
                elif isinstance(otherwise,str):
                    redirect(otherwise)
                elif callable(otherwise):
                    return otherwise()
                else:
                    raise RuntimeError, "invalid otherwise"
        return value


if __name__ == '__main__':
    import doctest
    doctest.testmod()






