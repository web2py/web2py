#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

This file specifically includes utilities for security.
--------------------------------------------------------
"""

import hashlib
import hmac
from gluon._compat import basestring, pickle, PY2, xrange, to_bytes, to_native

def pbkdf2_hex(data, salt, iterations=1000, keylen=24, hashfunc=None):
    hashfunc = hashfunc or sha1
    hmac = hashlib.pbkdf2_hmac(hashfunc().name, to_bytes(data),
                               to_bytes(salt), iterations, keylen)
    return binascii.hexlify(hmac)


def simple_hash(text, key='', salt='', digest_alg='md5'):
    """Generate hash with the given text using the specified digest algorithm."""
    text = to_bytes(text)
    key = to_bytes(key)
    salt = to_bytes(salt)
    if not digest_alg:
        raise RuntimeError("simple_hash with digest_alg=None")
    elif not isinstance(digest_alg, str):  # manual approach
        h = digest_alg(text + key + salt)
    elif digest_alg.startswith('pbkdf2'):  # latest and coolest!
        iterations, keylen, alg = digest_alg[7:-1].split(',')
        return to_native(pbkdf2_hex(text, salt, int(iterations),
                                    int(keylen), get_digest(alg)))
    elif key:  # use hmac
        digest_alg = get_digest(digest_alg)
        h = hmac.new(key + salt, text, digest_alg)
    else:  # compatible with third party systems
        h = get_digest(digest_alg)()
        h.update(text + salt)
    return h.hexdigest()


def get_digest(value):
    """Return a hashlib digest algorithm from a string."""
    if isinstance(value, str):
        value = value.lower()
        if value not in ('md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512'):
            raise ValueError("Invalid digest algorithm: %s" % value)
        value = getattr(hashlib, value)
    return value

DIGEST_ALG_BY_SIZE = {
    128 // 4: 'md5',
    160 // 4: 'sha1',
    224 // 4: 'sha224',
    256 // 4: 'sha256',
    384 // 4: 'sha384',
    512 // 4: 'sha512',
}
