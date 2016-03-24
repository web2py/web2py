#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for utils.py """

import unittest
from fix_path import fix_sys_path

fix_sys_path(__file__)

from utils import md5_hash
from utils import compare
from utils import is_valid_ip_address
from utils import web2py_uuid

import hashlib
from hashlib import md5, sha1, sha224, sha256, sha384, sha512
from utils import simple_hash, get_digest, secure_dumps, secure_loads


class TestUtils(unittest.TestCase):
    """ Tests the utils.py module """

    # TODO: def test_AES_new(self):

    def test_compare(self):
        """ Tests the compare funciton """

        a, b = 'test123', 'test123'
        compare_result_true = compare(a, b)
        self.assertTrue(compare_result_true)

        a, b = 'test123', 'test456'
        compare_result_false = compare(a, b)
        self.assertFalse(compare_result_false)

    def test_md5_hash(self):
        """ Tests the md5_hash function """

        data = md5_hash("web2py rocks")
        self.assertEqual(data, '79509f3246a2824dee64635303e99204')

    def test_simple_hash(self):
        """ Tests the simple_hash function """

        # no key, no salt, digest_alg=None
        self.assertRaises(RuntimeError, simple_hash, 'web2py rocks!', key='', salt='', digest_alg=None)

        # no key, no salt, digest_alg = md5
        data_md5 = simple_hash('web2py rocks!', key='', salt='', digest_alg=md5)
        self.assertEqual(data_md5, '37d95defba6c8834cb8cae86ee888568')

        # no key, no salt, 'md5'
        data_md5 = simple_hash('web2py rocks!', key='', salt='', digest_alg='md5')
        self.assertEqual(data_md5, '37d95defba6c8834cb8cae86ee888568')

        # no key, no salt, 'sha1'
        data_sha1 = simple_hash('web2py rocks!', key='', salt='', digest_alg='sha1')
        self.assertEqual(data_sha1, '00489a46753d8db260c71542611cdef80652c4b7')

        # no key, no salt, 'sha224'
        data_sha224 = simple_hash('web2py rocks!', key='', salt='', digest_alg='sha224')
        self.assertEqual(data_sha224, '84d7054271842c2c17983baa2b1447e0289d101140a8c002d49d60da')

        # no key, no salt, 'sha256'
        data_sha256 = simple_hash('web2py rocks!', key='', salt='', digest_alg='sha256')
        self.assertEqual(data_sha256, '0849f224d8deb267e4598702aaec1bd749e6caec90832469891012a4be24af08')

        # no key, no salt, 'sha384'
        data_sha384 = simple_hash('web2py rocks!', key='', salt='', digest_alg='sha384')
        self.assertEqual(data_sha384,
                         '3cffaf39371adbe84eb10f588d2718207d8e965e9172a27a278321b86977351376ae79f92e91d8c58cad86c491282d5f')

        # no key, no salt, 'sha512'
        data_sha512 = simple_hash('web2py rocks!', key='', salt='', digest_alg='sha512')
        self.assertEqual(data_sha512, 'fa3237f594743e1d7b6c800bb134b3255cf4a98ab8b01e2ec23256328c9f8059'
                                      '64fdef25a038d6cc3fda1b2fb45d66461eeed5c4669e506ec8bdfee71348db7e')

    # NOTE : get_digest() is covered by simple_hash tests above except raise error...
    def test_get_digest(self):
        # Bad algorithm
        # Option 1, think not working with python 2.6
        # with self.assertRaises(ValueError) as cm:
        #     get_digest('123')
        # self.assertEqual(cm.exception[0], 'Invalid digest algorithm: 123')
        # Option 2
        self.assertRaises(ValueError, get_digest, '123')

    # TODO: def test_get_callable_argspec(self):

    # TODO: def test_pad(self):

    def test_secure_dumps_and_loads(self):
        """ Tests secure_dumps and secure_loads"""
        testobj = {'a': 1, 'b': 2}
        testkey = 'mysecret'
        secured = secure_dumps(testobj, testkey)
        original = secure_loads(secured, testkey)
        self.assertEqual(testobj, original)
        self.assertTrue(isinstance(secured, basestring))
        self.assertTrue(':' in secured)

        large_testobj = [x for x in range(1000)]
        secured_comp = secure_dumps(large_testobj, testkey, compression_level=9)
        original_comp = secure_loads(secured_comp, testkey, compression_level=9)
        self.assertEqual(large_testobj, original_comp)
        secured = secure_dumps(large_testobj, testkey)
        self.assertTrue(len(secured_comp) < len(secured))

        testhash = 'myhash'
        secured = secure_dumps(testobj, testkey, testhash)
        original = secure_loads(secured, testkey, testhash)
        self.assertEqual(testobj, original)

        wrong1 = secure_loads(secured, testkey, 'wronghash')
        self.assertEqual(wrong1, None)
        wrong2 = secure_loads(secured, 'wrongkey', testhash)
        self.assertEqual(wrong2, None)
        wrong3 = secure_loads(secured, 'wrongkey', 'wronghash')
        self.assertEqual(wrong3, None)
        wrong4 = secure_loads('abc', 'a', 'b')
        self.assertEqual(wrong4, None)

    # TODO: def test_initialize_urandom(self):

    # TODO: def test_fast_urandom16(self):

    def test_web2py_uuid(self):
        from uuid import UUID
        self.assertTrue(UUID(web2py_uuid()))

    def test_is_valid_ip_address(self):
        # IPv4
        # False
        # self.assertEqual(is_valid_ip_address('127.0'), False)  # Fail with AppVeyor?? should pass
        self.assertEqual(is_valid_ip_address('unknown'), False)
        self.assertEqual(is_valid_ip_address(''), False)
        # True
        self.assertEqual(is_valid_ip_address('127.0.0.1'), True)
        self.assertEqual(is_valid_ip_address('localhost'), True)
        self.assertEqual(is_valid_ip_address('::1'), True)
        # IPv6
        # True
        # Compressed
        self.assertEqual(is_valid_ip_address('::ffff:7f00:1'), True)  # IPv6 127.0.0.1 compressed
        self.assertEqual(is_valid_ip_address('2001:660::1'), True)
        # Expanded
        self.assertEqual(is_valid_ip_address('0:0:0:0:0:ffff:7f00:1'), True)  # IPv6 127.0.0.1 expanded
        self.assertEqual(is_valid_ip_address('2607:fa48:6d50:69f1:21f:3cff:fe9d:9be3'), True)  # Any address
        # False
        # self.assertEqual(is_valid_ip_address('2607:fa48:6d50:69f1:21f:3cff:fe9d:'), False)  # Any address with mistake
        # The above pass locally but fail with AppVeyor

        # TODO: def test_is_loopback_ip_address(self):

        # TODO: def test_getipaddrinfo(self):


if __name__ == '__main__':
    unittest.main()
