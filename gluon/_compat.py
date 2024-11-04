import hashlib
import os
import sys

PY2 = sys.version_info[0] == 2

_identity = lambda x: x


import _thread as thread
import builtins as builtin
import configparser
import copyreg
import html  # warning, this is the python3 module and not the web2py html module
import ipaddress
import pickle
import queue as Queue
from email import encoders as Encoders
from email.charset import QP as charset_QP
from email.charset import Charset, add_charset
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import reduce
from html.entities import entitydefs, name2codepoint
from html.parser import HTMLParser
from http import cookiejar as cookielib
from http import cookies as Cookie
from importlib import reload
from io import BytesIO, StringIO
from urllib import parse as urlparse
from urllib import request as urllib2
from urllib.parse import quote as urllib_quote
from urllib.parse import quote_plus as urllib_quote_plus
from urllib.parse import unquote
from urllib.parse import unquote as urllib_unquote
from urllib.parse import urlencode
from urllib.request import FancyURLopener, urlopen
from xmlrpc.client import ProtocolError

hashlib_md5 = lambda s: hashlib.md5(bytes(s, "utf8"))
iterkeys = lambda d: iter(d.keys())
itervalues = lambda d: iter(d.values())
iteritems = lambda d: iter(d.items())
integer_types = (int,)
string_types = (str,)
text_type = str
basestring = str
xrange = range
long = int
unichr = chr
unicodeT = str
maketrans = str.maketrans
ClassType = type

implements_iterator = _identity
implements_bool = _identity


def to_bytes(obj, charset="utf-8", errors="strict"):
    if obj is None:
        return None
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return bytes(obj)
    if isinstance(obj, str):
        return obj.encode(charset, errors)
    raise TypeError("Expected bytes")


def to_native(obj, charset="utf8", errors="strict"):
    if obj is None or isinstance(obj, str):
        return obj
    return obj.decode(charset, errors)


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""

    # This requires a bit of explanation: the basic idea is to make a dummy
    # metaclass for one level of class instantiation that replaces itself with
    # the actual metaclass.
    class metaclass(meta):
        __call__ = type.__call__
        __init__ = type.__init__

        def __new__(cls, name, this_bases, d):
            if this_bases is None:
                return type.__new__(cls, name, (), d)
            return meta(name, bases, d)

    return metaclass("temporary_class", None, {})


def to_unicode(obj, charset="utf-8", errors="strict"):
    if obj is None:
        return None
    if not hasattr(obj, "decode") or not callable(obj.decode):
        return text_type(obj)
    return obj.decode(charset, errors)


# shortcuts
pjoin = os.path.join
exists = os.path.exists
