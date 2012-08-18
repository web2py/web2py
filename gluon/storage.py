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

__all__ = ['List', 'Storage', 'Settings', 'Messages', 'PickleableStorage',
           'StorageList', 'load_storage', 'save_storage']


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

class Storage(object):

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

    def __init__(self,d=None,**values):
        self.__dict__.update(d or {},**values)
    def __getattr__(self,key):        
        return getattr(self,key) if key in self else None
    def __getitem__(self,key):
        return getattr(self,key) if key in self else None
    def __setitem__(self,key,value):
        setattr(self,key,value)
    def __delitem__(self,key):
        delattr(self,key)
    def pop(self,key,default=None):
        if key in self:
            default = getattr(self,key)
            delattr(self,key)
        return default
    def clear(self):
        self.__dict__.clear()
    def __repr__(self):
        return '<Storage %s>' % self.__dict__ 
    def keys(self):
        return self.__dict__.keys()
    def items(self):
        return self.__dict__.items()
    def __iter__(self):
        return self.__dict__.__iter__()
    def has_key(self,key):
        return key in self.__dict__
    def __contains__(self,key):
        return key in self.__dict__
    def update(self,*args,**kargs):
        self.__dict__.update(*args,**kargs)
    def get(self,key,default=None):
        return getattr(self,key) if key in self else default
    def __getstate__(self):
        return self.__dict__
    def __setstate__(self, values):
        for key, value in values.items():
            setattr(self,key,value)
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
        value = getattr(self,key,[])
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
        values = self.getlist(default)
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
        values = self.getlist(default)
        return values[0] if values else default

PICKABLE = (str,int,long,float,bool,list,dict,tuple,set)
def PickleableStorage(data):
    return Storage(dict((k,v) for (k,v) in data.items() if isinstance(v,PICKABLE)))

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
        if key != 'lock_keys' and self.lock_keys and not key in self:
            raise SyntaxError, 'setting key \'%s\' does not exist' % key
        if key != 'lock_values' and self.lock_values:
            raise SyntaxError, 'setting value cannot be changed: %s' % key
        Storage.__setattr__(self,key,value)


class Messages(Storage):
    def __init__(self, T):
        self.T = T

    def __setattr__(self, key, value):
        if key != 'lock_keys' and self.lock_keys and not key in self:
            raise SyntaxError, 'setting key \'%s\' does not exist' % key
        if key != 'lock_values' and self.lock_values:
            raise SyntaxError, 'setting value cannot be changed: %s' % key
        Storage.__setattr__(self,key,value)

    def __getattr__(self, key):
        value = Storage.__getattr__(self,key)
        if isinstance(value, str):
            return str(self.T(value))
        return value


if __name__ == '__main__':
    import doctest
    doctest.testmod()






