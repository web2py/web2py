#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

This file specifically includes utilities for security.
"""

import string
import threading
import struct
import hashlib
import hmac
import uuid
import random
import time
import os
import re
import logging
import socket
try:
    from contrib.pbkdf2 import pbkdf2_hex
    HAVE_PBKDF2 = True
except ImportError:
    HAVE_PBKDF2 = False

logger = logging.getLogger("web2py")

def compare(a,b):
    """ compares two strings and not vulnerable to timing attacks """
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0

def md5_hash(text):
    """ Generate a md5 hash with the given text """
    return hashlib.md5(text).hexdigest()

def simple_hash(text, key='', salt = '', digest_alg = 'md5'):
    """
    Generates hash with the given text using the specified
    digest hashing algorithm
    """
    if not digest_alg:
        raise RuntimeError, "simple_hash with digest_alg=None"
    elif not isinstance(digest_alg,str): # manual approach
        h = digest_alg(text+key+salt)
    elif digest_alg.startswith('pbkdf2'): # latest and coolest!
        iterations, keylen, alg = digest_alg[7:-1].split(',')
        return pbkdf2_hex(text, salt, int(iterations),
                          int(keylen),get_digest(alg))
    elif key: # use hmac
        digest_alg = get_digest(digest_alg)
        h = hmac.new(key+salt,text,digest_alg)
    else: # compatible with third party systems
        h = hashlib.new(digest_alg)
        h.update(text+salt)
    return h.hexdigest()

def get_digest(value):
    """
    Returns a hashlib digest algorithm from a string
    """
    if not isinstance(value,str):
        return value
    value = value.lower()
    if value == "md5":
        return hashlib.md5
    elif value == "sha1":
        return hashlib.sha1
    elif value == "sha224":
        return hashlib.sha224
    elif value == "sha256":
        return hashlib.sha256
    elif value == "sha384":
        return hashlib.sha384
    elif value == "sha512":
        return hashlib.sha512
    else:
        raise ValueError("Invalid digest algorithm: %s" % value)

DIGEST_ALG_BY_SIZE = {
    128/4: 'md5',
    160/4: 'sha1',
    224/4: 'sha224',
    256/4: 'sha256',
    384/4: 'sha384',
    512/4: 'sha512',
    }


### compute constant CTOKENS
def initialize_urandom():
    """
    This function and the web2py_uuid follow from the following discussion:
    http://groups.google.com/group/web2py-developers/browse_thread/thread/7fd5789a7da3f09

    At startup web2py compute a unique ID that identifies the machine by adding
    uuid.getnode() + int(time.time() * 1e3)

    This is a 48-bit number. It converts the number into 16 8-bit tokens.
    It uses this value to initialize the entropy source ('/dev/urandom') and to seed random.

    If os.random() is not supported, it falls back to using random and issues a warning.
    """
    node_id = uuid.getnode()
    microseconds = int(time.time() * 1e6)
    ctokens = [((node_id + microseconds) >> ((i%6)*8)) % 256 for i in range(16)]
    random.seed(node_id + microseconds)
    try:
        os.urandom(1)
        have_urandom = True
        try:
            # try to add process-specific entropy
            frandom = open('/dev/urandom','wb')
            try:
                frandom.write(''.join(chr(t) for t in ctokens))
            finally:
                frandom.close()
        except IOError:
            # works anyway
            pass
    except NotImplementedError:
        have_urandom = False
        logger.warning(
"""Cryptographically secure session management is not possible on your system because
your system does not provide a cryptographically secure entropy source.
This is not specific to web2py; consider deploying on a different operating system.""")
    unpacked_ctokens = struct.unpack('=QQ',string.join(
            (chr(x) for x in ctokens),''))
    return unpacked_ctokens, have_urandom
UNPACKED_CTOKENS, HAVE_URANDOM = initialize_urandom()

def fast_urandom16(urandom=[], locker = threading.RLock()):
    """
    this is 4x faster than calling os.urandom(16) and prevents
    the "too many files open" issue with concurrent access to os.urandom()
    """
    try:
        return urandom.pop()
    except IndexError:
        try:
            locker.acquire()
            ur = os.urandom(16*1024)
            urandom += [ur[i:i+16] for i in xrange(16,1024*16,16)]
            return ur[0:16]
        finally:
            locker.release()

def web2py_uuid(ctokens=UNPACKED_CTOKENS):
    """
    This function follows from the following discussion:
    http://groups.google.com/group/web2py-developers/browse_thread/thread/7fd5789a7da3f09

    It works like uuid.uuid4 except that tries to use os.urandom() if possible
    and it XORs the output with the tokens uniquely associated with this machine.
    """
    rand_longs = struct.unpack('=QQ', string.join(
            (chr(random.randrange(256)) for i in xrange(16)),''))
    if HAVE_URANDOM:
        urand_longs = struct.unpack('=QQ', fast_urandom16())
        byte_s = struct.pack('=QQ',
                             rand_longs[0]^urand_longs[0]^ctokens[0], 
                             rand_longs[1]^urand_longs[1]^ctokens[1])
    else:
        byte_s = struct.pack('=QQ', 
                             rand_longs[0]^ctokens[0], 
                             rand_longs[1]^ctokens[1])
    return str(uuid.UUID(bytes=byte_s, version=4))

REGEX_IPv4 = re.compile('(\d+)\.(\d+)\.(\d+)\.(\d+)')

def is_valid_ip_address(address):
    """
    >>> is_valid_ip_address('127.0')
    False
    >>> is_valid_ip_address('127.0.0.1')
    True
    >>> is_valid_ip_address('2001:660::1')
    True
    """
    # deal with special cases
    if address.lower() in ('127.0.0.1','localhost','::1','::ffff:127.0.0.1'):
        return True
    elif address.lower() in ('unkown',''):
        return False
    elif address.count('.')==3: # assume IPv4
        if hasattr(socket,'inet_aton'): # try validate using the OS
            try:
                addr = socket.inet_aton(address)
                return True
            except socket.error: # invalid address
                return False
        else: # try validate using Regex
            match = REGEX_IPv4.match(address)
            if match and all(0<=int(match.group(i))<256 for i in (1,2,3,4)):
                return True
            return False
    elif hasattr(socket,'inet_pton'): # assume IPv6, try using the OS
        try:
            addr = socket.inet_pton(socket.AF_INET6, address)
            return True
        except socket.error: # invalid address
            return False
    else: # do not know what to do? assume it is a valid address
        return True







