# -*- coding: utf-8 -*-
"""
    pbkdf2_ctypes
    ~~~~~~

    This module implements pbkdf2 for Python using crypto lib from
    openssl.

    Note: This module is intended as a plugin replacement of pbkdf2.py
    by Armin Ronacher.

    Git repository: 
    $ git clone https://github.com/michele-comitini/pbkdf2_ctypes.git

    :copyright: Copyright (c) 2013: Michele Comitini <mcm@glisco.it>
    :license: LGPLv3

"""

import ctypes
import ctypes.util
import hashlib
import platform
import os.path

try:  # check that we have proper OpenSSL on the system.
    system = platform.system()
    if system == 'Windows':
        if platform.architecture()[0] == '64bit':
            crypto = ctypes.CDLL(os.path.basename(
                ctypes.util.find_library('libeay64')))
        else:
            crypto = ctypes.CDLL(os.path.basename(
                ctypes.util.find_library('libeay32')))
    else:
        crypto = ctypes.CDLL(os.path.basename(
            ctypes.util.find_library('crypto')))

    PKCS5_PBKDF2_HMAC = crypto.PKCS5_PBKDF2_HMAC

    hashlib_to_crypto_map = {hashlib.md5: crypto.EVP_md5,
                             hashlib.sha1: crypto.EVP_sha1,
                             hashlib.sha256: crypto.EVP_sha256,
                             hashlib.sha224: crypto.EVP_sha224,
                             hashlib.sha384: crypto.EVP_sha384,
                             hashlib.sha512: crypto.EVP_sha512}
except (OSError, AttributeError), e:
    raise ImportError('Cannot find a compatible OpenSSL installation '
                      'on your system')


def pkcs5_pbkdf2_hmac(data, salt, iterations=1000, keylen=24, hashfunc=None):
    c_pass = ctypes.c_char_p(data)
    c_passlen = ctypes.c_int(len(data))
    c_salt = ctypes.c_char_p(salt)
    c_saltlen = ctypes.c_int(len(salt))
    c_iter = ctypes.c_int(iterations)
    c_keylen = ctypes.c_int(keylen)
    if hashfunc:
        crypto_hashfunc = hashlib_to_crypto_map.get(hashfunc)
        crypto_hashfunc.restype = ctypes.c_void_p
        if crypto_hashfunc is None:
            raise ValueError('Unknown digest' + str(hashfunc))
        c_digest = ctypes.c_void_p(crypto_hashfunc())
    else:
        crypto.EVP_sha1.restype = ctypes.c_void_p
        c_digest = ctypes.c_void_p(crypto.EVP_sha1())
    c_buff = ctypes.create_string_buffer('\000' * keylen)
    err = PKCS5_PBKDF2_HMAC(c_pass, c_passlen,
                            c_salt, c_saltlen,
                            c_iter,
                            c_digest,
                            c_keylen,
                            c_buff)

    if err == 0:
        raise ValueError('wrong parameters')
    return c_buff.raw[:keylen]


def pbkdf2_hex(data, salt, iterations=1000, keylen=24, hashfunc=None):
    return pkcs5_pbkdf2_hmac(data, salt, iterations, keylen, hashfunc).\
        encode('hex')


def pbkdf2_bin(data, salt, iterations=1000, keylen=24, hashfunc=None):
    return pkcs5_pbkdf2_hmac(data, salt, iterations, keylen, hashfunc)

if __name__ == '__main__':
    crypto.SSLeay_version.restype = ctypes.c_char_p
    print crypto.SSLeay_version(0)
    for h in hashlib_to_crypto_map:
        pkcs5_pbkdf2_hmac('secret' * 11, 'salt', hashfunc=h)
