#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

This file specifically includes utilities for security.
"""

import hashlib
import hmac
import uuid
import random
import time
import os
import logging

logger = logging.getLogger("web2py")

def md5_hash(text):
    """ Generate a md5 hash with the given text """
    return hashlib.md5(text).hexdigest()

def simple_hash(text, digest_alg = 'md5'):
    """
    Generates hash with the given text using the specified
    digest hashing algorithm
    """
    if not digest_alg:
        raise RuntimeError, "simple_hash with digest_alg=None"
    elif not isinstance(digest_alg,str):
        h = digest_alg(text)
    else:
        h = hashlib.new(digest_alg)
        h.update(text)
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
        raise ValueError("Invalid digest algorithm")

def hmac_hash(value, key, digest_alg='md5', salt=None):
    if ':' in key:
        digest_alg, key = key.split(':')
    digest_alg = get_digest(digest_alg)
    d = hmac.new(key,value,digest_alg)
    if salt:
        d.update(str(salt))
    return d.hexdigest()


### compute constant ctokens
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
        logger.warning(
"""Cryptographically secure session management is not possible on your system because
your system does not provide a cryptographically secure entropy source.
This is not specific to web2py; consider deploying on a different operating system.""")
    return ctokens
ctokens = initialize_urandom()

def web2py_uuid():
    """
    This function follows from the following discussion:
    http://groups.google.com/group/web2py-developers/browse_thread/thread/7fd5789a7da3f09

    It works like uuid.uuid4 except that tries to use os.urandom() if possible
    and it XORs the output with the tokens uniquely associated with this machine.
    """
    bytes = [random.randrange(256) for i in range(16)]
    try:
        ubytes = [ord(c) for c in os.urandom(16)] # use /dev/urandom if possible
        bytes = [bytes[i] ^ ubytes[i] for i in range(16)]
    except NotImplementedError:
        pass
    ## xor bytes with constant ctokens
    bytes = ''.join(chr(c ^ ctokens[i]) for i,c in enumerate(bytes))
    return str(uuid.UUID(bytes=bytes, version=4))




