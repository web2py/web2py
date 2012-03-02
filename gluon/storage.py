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


class List(list):
    """
    Like a regular python list but a[i] if i is out of bounds return None
    instead of IndexOutOfBounds
    """

    def __call__(self, i, default=None):
        if 0<=i<len(self):
            return self[i]
        else:
            return default

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
        if value is None:
            if key in self:
                del self[key]
        else:
            self[key] = value

    def __delattr__(self, key):
        if key in self:
            del self[key]
        else:
            raise AttributeError, "missing key=%s" % key

    def __getitem__(self, key):
        return dict.get(self, key, None)

    def __repr__(self):
        return '<Storage ' + dict.__repr__(self) + '>'

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, value):
        for (k, v) in value.items():
            self[k] = v

    def getlist(self, key):
        """Return a Storage value as a list.

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
        value = self.get(key, None)
        if isinstance(value, (list, tuple)):
            return value
        elif value is None:
            return []
        return [value]

    def getfirst(self, key):
        """Return the first or only value when given a request.vars-style key.

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
        value = self.getlist(key)
        if len(value):
            return value[0]
        return None

    def getlast(self, key):
        """Returns the last or only single value when given a request.vars-style key.

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
        value = self.getlist(key)
        if len(value):
            return value[-1]
        return None

PICKABLE = (str,int,long,float,bool,list,dict,tuple,set)
def PickleableStorage(data):
    return Storage(dict((k,v) for (k,v) in data.items() if isinstance(v,PICKABLE)))

class StorageList(Storage):
    """
    like Storage but missing elements default to [] instead of None
    """
    def __getattr__(self, key):
        if key in self:
            return self[key]
        else:
            self[key] = []
            return self[key]

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
        if key != 'lock_keys' and self.get('lock_keys', None)\
             and not key in self:
            raise SyntaxError, 'setting key \'%s\' does not exist' % key
        if key != 'lock_values' and self.get('lock_values', None):
            raise SyntaxError, 'setting value cannot be changed: %s' % key
        self[key] = value


class Messages(Storage):

    def __init__(self, T):
        self['T'] = T

    def __setattr__(self, key, value):
        if key != 'lock_keys' and self.get('lock_keys', None)\
             and not key in self:
            raise SyntaxError, 'setting key \'%s\' does not exist' % key
        if key != 'lock_values' and self.get('lock_values', None):
            raise SyntaxError, 'setting value cannot be changed: %s' % key
        self[key] = value

    def __getattr__(self, key):
        value = self[key]
        if isinstance(value, str):
            return str(self['T'](value))
        return value

if __name__ == '__main__':
    import doctest
    doctest.testmod()




