#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Pythonic XML Security Library implementation"""
from __future__ import print_function
import base64
import hashlib
import os
from cStringIO import StringIO
from M2Crypto import BIO, EVP, RSA, X509, m2

# if lxml is not installed, use c14n.py native implementation
try:
    import lxml.etree
except ImportError:
    lxml = None
    
# Features:
#  * Uses M2Crypto and lxml (libxml2) but it is independent from libxmlsec1
#  * Sign, Verify, Encrypt & Decrypt XML documents

# Enveloping templates ("by reference": signature is parent):
SIGN_REF_TMPL = """
<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
  <CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" />
  <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1" />
  <Reference URI="%(ref_uri)s">
    <Transforms>
      <Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#" />
    </Transforms>
    <DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1" />
    <DigestValue>%(digest_value)s</DigestValue>
  </Reference>
</SignedInfo>
"""
SIGNED_TMPL = """
<?xml version="1.0" encoding="UTF-8"?>
<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
%(signed_info)s
<SignatureValue>%(signature_value)s</SignatureValue>
%(key_info)s
%(ref_xml)s
</Signature>
"""

# Enveloped templates (signature is child, the reference is the root object):
SIGN_ENV_TMPL = """
<SignedInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
  <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
  <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
  <Reference URI="">
    <Transforms>
       <Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
       <Transform Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
    </Transforms>
    <DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
    <DigestValue>%(digest_value)s</DigestValue>
  </Reference>
</SignedInfo>
"""
SIGNATURE_TMPL = """<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
%(signed_info)s
<SignatureValue>%(signature_value)s</SignatureValue>
%(key_info)s
</Signature>"""

KEY_INFO_RSA_TMPL = """
<KeyInfo>
  <KeyValue>
    <RSAKeyValue>
      <Modulus>%(modulus)s</Modulus>
      <Exponent>%(exponent)s</Exponent>
    </RSAKeyValue>
  </KeyValue>
</KeyInfo>
"""

KEY_INFO_X509_TMPL = """
<KeyInfo>
    <X509Data>
        <X509IssuerSerial>
            <X509IssuerName>%(issuer_name)s</X509IssuerName>
            <X509SerialNumber>%(serial_number)s</X509SerialNumber>
        </X509IssuerSerial>
    </X509Data>
</KeyInfo>
"""

def canonicalize(xml, c14n_exc=True):
    "Return the canonical (c14n) form of the xml document for hashing"
    # UTF8, normalization of line feeds/spaces, quoting, attribute ordering...
    output = StringIO()
    if lxml is not None:
        # use faster libxml2 / lxml canonicalization function if available
        et = lxml.etree.parse(StringIO(xml))
        et.write_c14n(output, exclusive=c14n_exc)
    else:
        # use pure-python implementation: c14n.py (avoid recursive import)
        from .simplexml import SimpleXMLElement
        SimpleXMLElement(xml).write_c14n(output, exclusive=c14n_exc)
    return output.getvalue()


def sha1_hash_digest(payload):
    "Create a SHA1 hash and return the base64 string"
    return base64.b64encode(hashlib.sha1(payload).digest())


def rsa_sign(xml, ref_uri, private_key, password=None, cert=None, c14n_exc=True,
             sign_template=SIGN_REF_TMPL, key_info_template=KEY_INFO_RSA_TMPL):
    "Sign an XML document usign RSA (templates: enveloped -ref- or enveloping)"

    # normalize the referenced xml (to compute the SHA1 hash)
    ref_xml = canonicalize(xml, c14n_exc)
    # create the signed xml normalized (with the referenced uri and hash value)
    signed_info = sign_template % {'ref_uri': ref_uri, 
                                   'digest_value': sha1_hash_digest(ref_xml)}
    signed_info = canonicalize(signed_info, c14n_exc)
    # Sign the SHA1 digest of the signed xml using RSA cipher
    pkey = RSA.load_key(private_key, lambda *args, **kwargs: password)
    signature = pkey.sign(hashlib.sha1(signed_info).digest())
    # build the mapping (placeholders) to create the final xml signed message
    return {
            'ref_xml': ref_xml, 'ref_uri': ref_uri,
            'signed_info': signed_info,
            'signature_value': base64.b64encode(signature),
            'key_info': key_info(pkey, cert, key_info_template),
            }


def rsa_verify(xml, signature, key, c14n_exc=True):
    "Verify a XML document signature usign RSA-SHA1, return True if valid"

    # load the public key (from buffer or filename)
    if key.startswith("-----BEGIN PUBLIC KEY-----"):
        bio = BIO.MemoryBuffer(key)
        rsa = RSA.load_pub_key_bio(bio)
    else:
        rsa = RSA.load_pub_key(certificate)
    # create the digital envelope
    pubkey = EVP.PKey()
    pubkey.assign_rsa(rsa)
    # do the cryptographic validation (using the default sha1 hash digest)
    pubkey.reset_context(md='sha1')
    pubkey.verify_init()
    # normalize and feed the signed xml to be verified
    pubkey.verify_update(canonicalize(xml, c14n_exc))
    ret = pubkey.verify_final(base64.b64decode(signature))
    return ret == 1


def key_info(pkey, cert, key_info_template):
    "Convert private key (PEM) to XML Signature format (RSAKeyValue/X509Data)"
    exponent = base64.b64encode(pkey.e[4:])
    modulus = m2.bn_to_hex(m2.mpi_to_bn(pkey.n)).decode("hex").encode("base64")
    x509 = x509_parse_cert(cert) if cert else None
    return key_info_template % {
        'modulus': modulus,
        'exponent': exponent,
        'issuer_name': x509.get_issuer().as_text() if x509 else "",
        'serial_number': x509.get_serial_number() if x509 else "",
        }


# Miscellaneous certificate utility functions:


def x509_parse_cert(cert, binary=False):
    "Create a X509 certificate from binary DER, plain text PEM or filename"
    if binary:
        bio = BIO.MemoryBuffer(cert)
        x509 = X509.load_cert_bio(bio, X509.FORMAT_DER)
    elif cert.startswith("-----BEGIN CERTIFICATE-----"):
        bio = BIO.MemoryBuffer(cert)
        x509 = X509.load_cert_bio(bio, X509.FORMAT_PEM)
    else:
        x509 = X509.load_cert(cert, 1)
    return x509


def x509_extract_rsa_public_key(cert, binary=False):
    "Return the public key (PEM format) from a X509 certificate"
    x509 = x509_parse_cert(cert, binary)
    return x509.get_pubkey().get_rsa().as_pem()


def x509_verify(cacert, cert, binary=False):
    "Validate the certificate's authenticity using a certification authority"
    ca = x509_parse_cert(cacert)
    crt = x509_parse_cert(cert, binary)
    return crt.verify(ca.get_pubkey())


if __name__ == "__main__":
    # basic test of enveloping signature (the reference is a part of the xml)
    sample_xml = """<Object xmlns="http://www.w3.org/2000/09/xmldsig#" Id="object">data</Object>"""
    output = canonicalize(sample_xml)
    print (output)
    vars = rsa_sign(sample_xml, '#object', "no_encriptada.key", "password")
    print (SIGNED_TMPL % vars)

    # basic test of enveloped signature (the reference is the document itself)
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?><Object>data%s</Object>"""
    vars = rsa_sign(sample_xml % "", '', "no_encriptada.key", "password",
                    sign_template=SIGN_ENV_TMPL, c14n_exc=False)
    print (sample_xml % (SIGNATURE_TMPL % vars))

    # basic signature verification:
    public_key = x509_extract_rsa_public_key(open("zunimercado.crt").read())
    assert rsa_verify(vars['signed_info'], vars['signature_value'], public_key,
                      c14n_exc=False)
