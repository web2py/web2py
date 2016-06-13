#!/usr/bin/env python
# -*- coding: utf-8 -*-

"Special module to handle differences between Python 2 and 3 versions"

import sys

PY3K = sys.version_info >= (3, 0)

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
	from urllib import urlopen
except ImportError:
	from urllib.request import urlopen

try:
    from io import BytesIO
except ImportError:
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO

try:
    from hashlib import md5
except ImportError:
    try:
        from md5 import md5
    except ImportError:
        md5 = None
def hashpath(fn):
    h = md5()
    if PY3K:
        h.update(fn.encode("UTF-8"))
    else:
        h.update(fn)
    return h.hexdigest()

# Check if PIL is available (tries importing both pypi version and corrected or manually installed versions).
# Necessary for JPEG and GIF support.
# TODO: Pillow support
try:
    from PIL import Image
except ImportError:
    try:
        import Image
    except ImportError:
        Image = None

try:
	from HTMLParser import HTMLParser
except ImportError:
	from html.parser import HTMLParser

if PY3K:
    basestring = str
    unicode = str
    ord = lambda x: x
else:
    basestring = basestring
    unicode = unicode
    ord = ord

# shortcut to bytes conversion (b prefix)
def b(s): 
    if isinstance(s, basestring):
        return s.encode("latin1")
    elif isinstance(s, int):
        if PY3K:
            return bytes([s])       # http://bugs.python.org/issue4588
        else:
            return chr(s)

def exception():
    "Return the current the exception instance currently being handled"
    # this is needed to support Python 2.5 that lacks "as" syntax
    return sys.exc_info()[1]


