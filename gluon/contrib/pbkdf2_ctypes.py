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

def commoncrypto_hashlib_to_crypto_map_get(hashfunc):
    hashlib_to_crypto_map = {hashlib.sha1: 1,
                             hashlib.sha224: 2,
                             hashlib.sha256: 3,
                             hashlib.sha384: 4,
                             hashlib.sha512: 5}
    crypto_hashfunc = hashlib_to_crypto_map.get(hashfunc)
    if crypto_hashfunc is None:
        raise ValueError('Unkwnown digest %s' % hashfunc)
    return crypto_hashfunc

def commoncrypto_pbkdf2(c_pass, c_passlen,
               c_salt, c_saltlen,
               c_iter, digest, c_keylen, c_buff):
    """Common Crypto compatibile wrapper
    """
    c_hashfunc = ctypes.c_int(commoncrypto_hashlib_to_crypto_map_get(digest))

    return 1 - crypto.CCKeyDerivationPBKDF(2, # hardcoded 2-> PBKDF2
                                           c_pass, c_passlen,
                                           c_salt, c_saltlen,
                                           c_hashfunc,
                                           c_iter,
                                           c_buff,
                                           c_keylen)


def openssl_hashlib_to_crypto_map_get(hashfunc):
    hashlib_to_crypto_map = {hashlib.md5: crypto.EVP_md5,
                                 hashlib.sha1: crypto.EVP_sha1,
                                 hashlib.sha256: crypto.EVP_sha256,
                                 hashlib.sha224: crypto.EVP_sha224,
                                 hashlib.sha384: crypto.EVP_sha384,
                                 hashlib.sha512: crypto.EVP_sha512}
    crypto_hashfunc = hashlib_to_crypto_map.get(hashfunc)
    if crypto_hashfunc is None:
        raise ValueError('Unkwnown digest %s' % hashfunc)
    crypto_hashfunc.restype = ctypes.c_void_p
    return crypto_hashfunc()

    
def openssl_pbkdf2(c_pass, c_passlen,
                   c_salt, c_saltlen,
                   c_iter, digest, c_keylen, c_buff):
    """OpenSSL compatibile wrapper
    """
    c_hashfunc = ctypes.c_void_p(openssl_hashlib_to_crypto_map_get(digest))

    return crypto.PKCS5_PBKDF2_HMAC(c_pass, c_passlen,
                            c_salt, c_saltlen,
                            c_iter,
                            c_hashfunc,
                            c_keylen,
                            c_buff)

try:  # check that we have proper OpenSSL or Common Crypto on the system.
    system = platform.system()
    if system == 'Windows':
        if platform.architecture()[0] == '64bit':
            crypto = ctypes.CDLL(os.path.basename(
                ctypes.util.find_library('libeay64')))
        else:
            crypto = ctypes.CDLL(os.path.basename(
                ctypes.util.find_library('libeay32')))
        _pbkdf2_hmac = openssl_pbkdf2
        crypto.PKCS5_PBKDF2_HMAC # test compatibility
    elif system == 'Darwin': # think different(TM)! i.e. break things!
        raise ImportError('Not yet available on OS X')
    else:
        crypto = ctypes.CDLL(os.path.basename(
            ctypes.util.find_library('crypto')))
        _pbkdf2_hmac = openssl_pbkdf2
        crypto.PKCS5_PBKDF2_HMAC # test compatibility

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
    c_buff = ctypes.create_string_buffer('\000' * keylen)
    err = _pbkdf2_hmac(c_pass, c_passlen,
                            c_salt, c_saltlen,
                            c_iter,
                            hashfunc,
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
    try:
        crypto.SSLeay_version.restype = ctypes.c_char_p
        print crypto.SSLeay_version(0)
    except:
        print "Not using OpenSSL"

    for h in [hashlib.sha1, hashlib.sha224, hashlib.sha256,
              hashlib.sha384, hashlib.sha512]:
        pkcs5_pbkdf2_hmac('secret' * 11, 'salt', hashfunc=h)
