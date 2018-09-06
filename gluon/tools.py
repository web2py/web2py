#!/bin/python
# -*- coding: utf-8 -*-

"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Auth, Mail, PluginManager and various utilities
------------------------------------------------
"""

import base64
from functools import reduce
from gluon._compat import pickle, thread, urllib2, Cookie, StringIO, urlencode
from gluon._compat import configparser, MIMEBase, MIMEMultipart, MIMEText, Header
from gluon._compat import Encoders, Charset, long, urllib_quote, iteritems
from gluon._compat import to_bytes, to_native, add_charset
from gluon._compat import charset_QP, basestring, unicodeT, to_unicode
import datetime
import logging
import sys
import glob
import os
import re
import time
import fnmatch
import traceback
import smtplib
import email.utils
import random
import hmac
import hashlib
import json

from email import message_from_string

from gluon.authapi import AuthAPI
from gluon.contenttype import contenttype
from gluon.storage import Storage, StorageList, Settings, Messages
from gluon.utils import web2py_uuid, compare
from gluon.fileutils import read_file, check_credentials
from gluon import *
from gluon.contrib.autolinks import expand_one
from gluon.contrib.markmin.markmin2html import replace_at_urls
from gluon.contrib.markmin.markmin2html import replace_autolinks
from gluon.contrib.markmin.markmin2html import replace_components
from pydal.objects import Row, Set, Query

import gluon.serializers as serializers

Table = DAL.Table
Field = DAL.Field

__all__ = ['Mail', 'Auth', 'Recaptcha2', 'Crud', 'Service', 'Wiki',
           'PluginManager', 'fetch', 'geocode', 'reverse_geocode', 'prettydate']

# mind there are two loggers here (logger and crud.settings.logger)!
logger = logging.getLogger("web2py")

DEFAULT = lambda: None


def getarg(position, default=None):
    args = current.request.args
    if position < 0 and len(args) >= -position:
        return args[position]
    elif position >= 0 and len(args) > position:
        return args[position]
    else:
        return default


def callback(actions, form, tablename=None):
    if actions:
        if tablename and isinstance(actions, dict):
            actions = actions.get(tablename, [])
        if not isinstance(actions, (list, tuple)):
            actions = [actions]
        [action(form) for action in actions]


def validators(*a):
    b = []
    for item in a:
        if isinstance(item, (list, tuple)):
            b = b + list(item)
        else:
            b.append(item)
    return b


def call_or_redirect(f, *args):
    if callable(f):
        redirect(f(*args))
    else:
        redirect(f)


def replace_id(url, form):
    if url:
        url = url.replace('[id]', str(form.vars.id))
        if url[0] == '/' or url[:4] == 'http':
            return url
    return URL(url)


class Mail(object):
    """
    Class for configuring and sending emails with alternative text / html
    body, multiple attachments and encryption support

    Works with SMTP and Google App Engine.

    Args:
        server: SMTP server address in address:port notation
        sender: sender email address
        login: sender login name and password in login:password notation
            or None if no authentication is required
        tls: enables/disables encryption (True by default)

    In Google App Engine use ::

        server='gae'

    For sake of backward compatibility all fields are optional and default
    to None, however, to be able to send emails at least server and sender
    must be specified. They are available under following fields::

        mail.settings.server
        mail.settings.sender
        mail.settings.login
        mail.settings.timeout = 60 # seconds (default)

    When server is 'logging', email is logged but not sent (debug mode)

    Optionally you can use PGP encryption or X509::

        mail.settings.cipher_type = None
        mail.settings.gpg_home = None
        mail.settings.sign = True
        mail.settings.sign_passphrase = None
        mail.settings.encrypt = True
        mail.settings.x509_sign_keyfile = None
        mail.settings.x509_sign_certfile = None
        mail.settings.x509_sign_chainfile = None
        mail.settings.x509_nocerts = False
        mail.settings.x509_crypt_certfiles = None

        cipher_type       : None
                            gpg - need a python-pyme package and gpgme lib
                            x509 - smime
        gpg_home          : you can set a GNUPGHOME environment variable
                            to specify home of gnupg
        sign              : sign the message (True or False)
        sign_passphrase   : passphrase for key signing
        encrypt           : encrypt the message (True or False). It defaults
                            to True
                         ... x509 only ...
        x509_sign_keyfile : the signers private key filename or
                            string containing the key. (PEM format)
        x509_sign_certfile: the signers certificate filename or
                            string containing the cert. (PEM format)
        x509_sign_chainfile: sets the optional all-in-one file where you
                             can assemble the certificates of Certification
                             Authorities (CA) which form the certificate
                             chain of email certificate. It can be a
                             string containing the certs to. (PEM format)
        x509_nocerts      : if True then no attached certificate in mail
        x509_crypt_certfiles: the certificates file or strings to encrypt
                              the messages with can be a file name /
                              string or a list of file names /
                              strings (PEM format)

    Examples:
        Create Mail object with authentication data for remote server::

            mail = Mail('example.com:25', 'me@example.com', 'me:password')

    Notice for GAE users:
        attachments have an automatic content_id='attachment-i' where i is progressive number
        in this way the can be referenced from the HTML as <img src="cid:attachment-0" /> etc.
    """

    class Attachment(MIMEBase):
        """
        Email attachment

        Args:
            payload: path to file or file-like object with read() method
            filename: name of the attachment stored in message; if set to
                None, it will be fetched from payload path; file-like
                object payload must have explicit filename specified
            content_id: id of the attachment; automatically contained within
                `<` and `>`
            content_type: content type of the attachment; if set to None,
                it will be fetched from filename using gluon.contenttype
                module
            encoding: encoding of all strings passed to this function (except
                attachment body)

        Content ID is used to identify attachments within the html body;
        in example, attached image with content ID 'photo' may be used in
        html message as a source of img tag `<img src="cid:photo" />`.

        Example::
            Create attachment from text file::

                attachment = Mail.Attachment('/path/to/file.txt')

                Content-Type: text/plain
                MIME-Version: 1.0
                Content-Disposition: attachment; filename="file.txt"
                Content-Transfer-Encoding: base64

                SOMEBASE64CONTENT=

            Create attachment from image file with custom filename and cid::

                attachment = Mail.Attachment('/path/to/file.png',
                                                 filename='photo.png',
                                                 content_id='photo')

                Content-Type: image/png
                MIME-Version: 1.0
                Content-Disposition: attachment; filename="photo.png"
                Content-Id: <photo>
                Content-Transfer-Encoding: base64

                SOMEOTHERBASE64CONTENT=
        """

        def __init__(
            self,
            payload,
            filename=None,
            content_id=None,
            content_type=None,
                encoding='utf-8'):
            if isinstance(payload, str):
                if filename is None:
                    filename = os.path.basename(payload)
                payload = read_file(payload, 'rb')
            else:
                if filename is None:
                    raise Exception('Missing attachment name')
                payload = payload.read()
            # FIXME PY3 can be used to_native?
            filename = filename.encode(encoding)
            if content_type is None:
                content_type = contenttype(filename)
            self.my_filename = filename
            self.my_payload = payload
            MIMEBase.__init__(self, *content_type.split('/', 1))
            self.set_payload(payload)
            self['Content-Disposition'] = 'attachment; filename="%s"' % to_native(filename, encoding)
            if content_id is not None:
                self['Content-Id'] = '<%s>' % to_native(content_id, encoding)
            Encoders.encode_base64(self)

    def __init__(self, server=None, sender=None, login=None, tls=True):

        settings = self.settings = Settings()
        settings.server = server
        settings.sender = sender
        settings.login = login
        settings.tls = tls
        settings.timeout = 5  # seconds
        settings.hostname = None
        settings.ssl = False
        settings.cipher_type = None
        settings.gpg_home = None
        settings.sign = True
        settings.sign_passphrase = None
        settings.encrypt = True
        settings.x509_sign_keyfile = None
        settings.x509_sign_certfile = None
        settings.x509_sign_chainfile = None
        settings.x509_nocerts = False
        settings.x509_crypt_certfiles = None
        settings.debug = False
        settings.lock_keys = True
        self.result = {}
        self.error = None

    def send(self,
             to,
             subject='[no subject]',
             message='[no message]',
             attachments=None,
             cc=None,
             bcc=None,
             reply_to=None,
             sender=None,
             encoding='utf-8',
             raw=False,
             headers={},
             from_address=None,
             cipher_type=None,
             sign=None,
             sign_passphrase=None,
             encrypt=None,
             x509_sign_keyfile=None,
             x509_sign_chainfile=None,
             x509_sign_certfile=None,
             x509_crypt_certfiles=None,
             x509_nocerts=None
             ):
        """
        Sends an email using data specified in constructor

        Args:
            to: list or tuple of receiver addresses; will also accept single
                object
            subject: subject of the email
            message: email body text; depends on type of passed object:

                - if 2-list or 2-tuple is passed: first element will be
                  source of plain text while second of html text;
                - otherwise: object will be the only source of plain text
                  and html source will be set to None

                If text or html source is:

                - None: content part will be ignored,
                - string: content part will be set to it,
                - file-like object: content part will be fetched from it using
                  it's read() method
            attachments: list or tuple of Mail.Attachment objects; will also
                accept single object
            cc: list or tuple of carbon copy receiver addresses; will also
                accept single object
            bcc: list or tuple of blind carbon copy receiver addresses; will
                also accept single object
            reply_to: address to which reply should be composed
            encoding: encoding of all strings passed to this method (including
                message bodies)
            headers: dictionary of headers to refine the headers just before
                sending mail, e.g. `{'X-Mailer' : 'web2py mailer'}`
            from_address: address to appear in the 'From:' header, this is not
                the envelope sender. If not specified the sender will be used

            cipher_type :
                gpg - need a python-pyme package and gpgme lib
                x509 - smime
            gpg_home : you can set a GNUPGHOME environment variable
                to specify home of gnupg
            sign : sign the message (True or False)
            sign_passphrase  : passphrase for key signing
            encrypt : encrypt the message (True or False). It defaults to True.
                         ... x509 only ...
            x509_sign_keyfile : the signers private key filename or
                string containing the key. (PEM format)
            x509_sign_certfile: the signers certificate filename or
                string containing the cert. (PEM format)
            x509_sign_chainfile: sets the optional all-in-one file where you
                can assemble the certificates of Certification
                Authorities (CA) which form the certificate
                chain of email certificate. It can be a
                string containing the certs to. (PEM format)
            x509_nocerts : if True then no attached certificate in mail
            x509_crypt_certfiles: the certificates file or strings to encrypt
                the messages with can be a file name / string or
                a list of file names / strings (PEM format)
        Examples:
            Send plain text message to single address::

                mail.send('you@example.com',
                          'Message subject',
                          'Plain text body of the message')

            Send html message to single address::

                mail.send('you@example.com',
                          'Message subject',
                          '<html>Plain text body of the message</html>')

            Send text and html message to three addresses (two in cc)::

                mail.send('you@example.com',
                          'Message subject',
                          ('Plain text body', '<html>html body</html>'),
                          cc=['other1@example.com', 'other2@example.com'])

            Send html only message with image attachment available from the
            message by 'photo' content id::

                mail.send('you@example.com',
                          'Message subject',
                          (None, '<html><img src="cid:photo" /></html>'),
                          Mail.Attachment('/path/to/photo.jpg'
                                          content_id='photo'))

            Send email with two attachments and no body text::

                mail.send('you@example.com,
                          'Message subject',
                          None,
                          [Mail.Attachment('/path/to/fist.file'),
                           Mail.Attachment('/path/to/second.file')])

        Returns:
            True on success, False on failure.

        Before return, method updates two object's fields:

            - self.result: return value of smtplib.SMTP.sendmail() or GAE's
              mail.send_mail() method
            - self.error: Exception message or None if above was successful
        """

        # We don't want to use base64 encoding for unicode mail
        add_charset('utf-8', charset_QP, charset_QP, 'utf-8')

        def encode_header(key):
            if [c for c in key if 32 > ord(c) or ord(c) > 127]:
                return Header(key.encode('utf-8'), 'utf-8')
            else:
                return key

        # encoded or raw text
        def encoded_or_raw(text):
            if raw:
                text = encode_header(text)
            return text

        sender = sender or self.settings.sender

        if not isinstance(self.settings.server, str):
            raise Exception('Server address not specified')
        if not isinstance(sender, str):
            raise Exception('Sender address not specified')

        if not raw and attachments:
            # Use multipart/mixed if there is attachments
            payload_in = MIMEMultipart('mixed')
        elif raw:
            # no encoding configuration for raw messages
            if not isinstance(message, basestring):
                message = message.read()
            if isinstance(message, unicodeT):
                text = message.encode('utf-8')
            elif not encoding == 'utf-8':
                text = message.decode(encoding).encode('utf-8')
            else:
                text = message
            # No charset passed to avoid transport encoding
            # NOTE: some unicode encoded strings will produce
            # unreadable mail contents.
            payload_in = MIMEText(text)
        if to:
            if not isinstance(to, (list, tuple)):
                to = [to]
        else:
            raise Exception('Target receiver address not specified')
        if cc:
            if not isinstance(cc, (list, tuple)):
                cc = [cc]
        if bcc:
            if not isinstance(bcc, (list, tuple)):
                bcc = [bcc]
        if message is None:
            text = html = None
        elif isinstance(message, (list, tuple)):
            text, html = message
        elif message.strip().startswith('<html') and \
                message.strip().endswith('</html>'):
            text = self.settings.server == 'gae' and message or None
            html = message
        else:
            text = message
            html = None

        if (text is not None or html is not None) and (not raw):

            if text is not None:
                if not isinstance(text, basestring):
                    text = text.read()
                if isinstance(text, unicodeT):
                    text = text.encode('utf-8')
                elif not encoding == 'utf-8':
                    text = text.decode(encoding).encode('utf-8')
            if html is not None:
                if not isinstance(html, basestring):
                    html = html.read()
                if isinstance(html, unicodeT):
                    html = html.encode('utf-8')
                elif not encoding == 'utf-8':
                    html = html.decode(encoding).encode('utf-8')

            # Construct mime part only if needed
            if text is not None and html:
                # We have text and html we need multipart/alternative
                attachment = MIMEMultipart('alternative')
                attachment.attach(MIMEText(text, _charset='utf-8'))
                attachment.attach(MIMEText(html, 'html', _charset='utf-8'))
            elif text is not None:
                attachment = MIMEText(text, _charset='utf-8')
            elif html:
                attachment = MIMEText(html, 'html', _charset='utf-8')

            if attachments:
                # If there is attachments put text and html into
                # multipart/mixed
                payload_in.attach(attachment)
            else:
                # No attachments no multipart/mixed
                payload_in = attachment

        if (attachments is None) or raw:
            pass
        elif isinstance(attachments, (list, tuple)):
            for attachment in attachments:
                payload_in.attach(attachment)
        else:
            payload_in.attach(attachments)
            attachments = [attachments]

        #######################################################
        #                      CIPHER                         #
        #######################################################
        cipher_type = cipher_type or self.settings.cipher_type
        sign = sign if sign is not None else self.settings.sign
        sign_passphrase = sign_passphrase or self.settings.sign_passphrase
        encrypt = encrypt if encrypt is not None else self.settings.encrypt
        #######################################################
        #                       GPGME                         #
        #######################################################
        if cipher_type == 'gpg':
            if self.settings.gpg_home:
                # Set GNUPGHOME environment variable to set home of gnupg
                import os
                os.environ['GNUPGHOME'] = self.settings.gpg_home
            if not sign and not encrypt:
                self.error = "No sign and no encrypt is set but cipher type to gpg"
                return False

            # need a python-pyme package and gpgme lib
            from pyme import core, errors
            from pyme.constants.sig import mode
            ############################################
            #                   sign                   #
            ############################################
            if sign:
                import string
                core.check_version(None)
                pin = string.replace(payload_in.as_string(), '\n', '\r\n')
                plain = core.Data(pin)
                sig = core.Data()
                c = core.Context()
                c.set_armor(1)
                c.signers_clear()
                # search for signing key for From:
                for sigkey in c.op_keylist_all(sender, 1):
                    if sigkey.can_sign:
                        c.signers_add(sigkey)
                if not c.signers_enum(0):
                    self.error = 'No key for signing [%s]' % sender
                    return False
                c.set_passphrase_cb(lambda x, y, z: sign_passphrase)
                try:
                    # make a signature
                    c.op_sign(plain, sig, mode.DETACH)
                    sig.seek(0, 0)
                    # make it part of the email
                    payload = MIMEMultipart('signed',
                                            boundary=None,
                                            _subparts=None,
                                            **dict(micalg="pgp-sha1",
                                                   protocol="application/pgp-signature"))
                    # insert the origin payload
                    payload.attach(payload_in)
                    # insert the detached signature
                    p = MIMEBase("application", 'pgp-signature')
                    p.set_payload(sig.read())
                    payload.attach(p)
                    # it's just a trick to handle the no encryption case
                    payload_in = payload
                except errors.GPGMEError as ex:
                    self.error = "GPG error: %s" % ex.getstring()
                    return False
            ############################################
            #                  encrypt                 #
            ############################################
            if encrypt:
                core.check_version(None)
                plain = core.Data(payload_in.as_string())
                cipher = core.Data()
                c = core.Context()
                c.set_armor(1)
                # collect the public keys for encryption
                recipients = []
                rec = to[:]
                if cc:
                    rec.extend(cc)
                if bcc:
                    rec.extend(bcc)
                for addr in rec:
                    c.op_keylist_start(addr, 0)
                    r = c.op_keylist_next()
                    if r is None:
                        self.error = 'No key for [%s]' % addr
                        return False
                    recipients.append(r)
                try:
                    # make the encryption
                    c.op_encrypt(recipients, 1, plain, cipher)
                    cipher.seek(0, 0)
                    # make it a part of the email
                    payload = MIMEMultipart('encrypted',
                                            boundary=None,
                                            _subparts=None,
                                            **dict(protocol="application/pgp-encrypted"))
                    p = MIMEBase("application", 'pgp-encrypted')
                    p.set_payload("Version: 1\r\n")
                    payload.attach(p)
                    p = MIMEBase("application", 'octet-stream')
                    p.set_payload(cipher.read())
                    payload.attach(p)
                except errors.GPGMEError as ex:
                    self.error = "GPG error: %s" % ex.getstring()
                    return False
        #######################################################
        #                       X.509                         #
        #######################################################
        elif cipher_type == 'x509':
            if not sign and not encrypt:
                self.error = "No sign and no encrypt is set but cipher type to x509"
                return False
            import os
            x509_sign_keyfile = x509_sign_keyfile or self.settings.x509_sign_keyfile

            x509_sign_chainfile = x509_sign_chainfile or self.settings.x509_sign_chainfile

            x509_sign_certfile = x509_sign_certfile or self.settings.x509_sign_certfile or \
                x509_sign_keyfile or self.settings.x509_sign_certfile

            # crypt certfiles could be a string or a list
            x509_crypt_certfiles = x509_crypt_certfiles or self.settings.x509_crypt_certfiles

            x509_nocerts = x509_nocerts or\
                self.settings.x509_nocerts

            # need m2crypto
            try:
                from M2Crypto import BIO, SMIME, X509
            except Exception as e:
                self.error = "Can't load M2Crypto module"
                return False
            msg_bio = BIO.MemoryBuffer(payload_in.as_string())
            s = SMIME.SMIME()

            # SIGN
            if sign:
                # key for signing
                try:
                    keyfile_bio = BIO.openfile(x509_sign_keyfile)\
                        if os.path.isfile(x509_sign_keyfile)\
                        else BIO.MemoryBuffer(x509_sign_keyfile)
                    sign_certfile_bio = BIO.openfile(x509_sign_certfile)\
                        if os.path.isfile(x509_sign_certfile)\
                        else BIO.MemoryBuffer(x509_sign_certfile)
                    s.load_key_bio(keyfile_bio, sign_certfile_bio,
                                   callback=lambda x: sign_passphrase)
                    if x509_sign_chainfile:
                        sk = X509.X509_Stack()
                        chain = X509.load_cert(x509_sign_chainfile)\
                            if os.path.isfile(x509_sign_chainfile)\
                            else X509.load_cert_string(x509_sign_chainfile)
                        sk.push(chain)
                        s.set_x509_stack(sk)
                except Exception as e:
                    self.error = "Something went wrong on certificate / private key loading: <%s>" % str(e)
                    return False
                try:
                    if x509_nocerts:
                        flags = SMIME.PKCS7_NOCERTS
                    else:
                        flags = 0
                    if not encrypt:
                        flags += SMIME.PKCS7_DETACHED
                    p7 = s.sign(msg_bio, flags=flags)
                    msg_bio = BIO.MemoryBuffer(payload_in.as_string(
                    ))  # Recreate coz sign() has consumed it.
                except Exception as e:
                    self.error = "Something went wrong on signing: <%s> %s" % (
                        str(e), str(flags))
                    return False

            # ENCRYPT
            if encrypt:
                try:
                    sk = X509.X509_Stack()
                    if not isinstance(x509_crypt_certfiles, (list, tuple)):
                        x509_crypt_certfiles = [x509_crypt_certfiles]

                    # make an encryption cert's stack
                    for crypt_certfile in x509_crypt_certfiles:
                        certfile = X509.load_cert(crypt_certfile)\
                            if os.path.isfile(crypt_certfile)\
                            else X509.load_cert_string(crypt_certfile)
                        sk.push(certfile)
                    s.set_x509_stack(sk)

                    s.set_cipher(SMIME.Cipher('des_ede3_cbc'))
                    tmp_bio = BIO.MemoryBuffer()
                    if sign:
                        s.write(tmp_bio, p7)
                    else:
                        tmp_bio.write(payload_in.as_string())
                    p7 = s.encrypt(tmp_bio)
                except Exception as e:
                    self.error = "Something went wrong on encrypting: <%s>" % str(e)
                    return False

            # Final stage in sign and encryption
            out = BIO.MemoryBuffer()
            if encrypt:
                s.write(out, p7)
            else:
                if sign:
                    s.write(out, p7, msg_bio, SMIME.PKCS7_DETACHED)
                else:
                    out.write('\r\n')
                    out.write(payload_in.as_string())
            out.close()
            st = str(out.read())
            payload = message_from_string(st)
        else:
            # no cryptography process as usual
            payload = payload_in

        if from_address:
            payload['From'] = encoded_or_raw(to_unicode(from_address, encoding))
        else:
            payload['From'] = encoded_or_raw(to_unicode(sender, encoding))
        origTo = to[:]
        if to:
            payload['To'] = encoded_or_raw(to_unicode(', '.join(to), encoding))
        if reply_to:
            payload['Reply-To'] = encoded_or_raw(to_unicode(reply_to, encoding))
        if cc:
            payload['Cc'] = encoded_or_raw(to_unicode(', '.join(cc), encoding))
            to.extend(cc)
        if bcc:
            to.extend(bcc)
        payload['Subject'] = encoded_or_raw(to_unicode(subject, encoding))
        payload['Date'] = email.utils.formatdate()
        for k, v in iteritems(headers):
            payload[k] = encoded_or_raw(to_unicode(v, encoding))
        result = {}
        try:
            if self.settings.server == 'logging':
                entry = 'email not sent\n%s\nFrom: %s\nTo: %s\nSubject: %s\n\n%s\n%s\n' % \
                    ('-' * 40, sender, ', '.join(to), subject, text or html, '-' * 40)
                logger.warning(entry)
            elif self.settings.server.startswith('logging:'):
                entry = 'email not sent\n%s\nFrom: %s\nTo: %s\nSubject: %s\n\n%s\n%s\n' % \
                    ('-' * 40, sender, ', '.join(to), subject, text or html, '-' * 40)
                open(self.settings.server[8:], 'a').write(entry)
            elif self.settings.server == 'gae':
                xcc = dict()
                if cc:
                    xcc['cc'] = cc
                if bcc:
                    xcc['bcc'] = bcc
                if reply_to:
                    xcc['reply_to'] = reply_to
                from google.appengine.api import mail
                attachments = attachments and [mail.Attachment(
                    a.my_filename,
                    a.my_payload,
                    content_id='<attachment-%s>' % k
                ) for k, a in enumerate(attachments) if not raw]
                if attachments:
                    result = mail.send_mail(
                        sender=sender, to=origTo,
                        subject=to_unicode(subject, encoding),
                        body=to_unicode(text or '', encoding),
                        html=html,
                        attachments=attachments, **xcc)
                elif html and (not raw):
                    result = mail.send_mail(
                        sender=sender, to=origTo,
                        subject=to_unicode(subject, encoding), body=to_unicode(text or '', encoding), html=html, **xcc)
                else:
                    result = mail.send_mail(
                        sender=sender, to=origTo,
                        subject=to_unicode(subject, encoding), body=to_unicode(text or '', encoding), **xcc)
            elif self.settings.server == 'aws':
                import boto3
                from botocore.exceptions import ClientError
                client = boto3.client('ses')
                try:
                    raw = {'Data': payload.as_string()}
                    response = client.send_raw_email(RawMessage=raw,
                                                     Source=sender,
                                                     Destinations=to)
                    return True
                except ClientError as e:
                    # we should log this error:
                    # print e.response['Error']['Message']
                    return False
            else:
                smtp_args = self.settings.server.split(':')
                kwargs = dict(timeout=self.settings.timeout)
                func = smtplib.SMTP_SSL if self.settings.ssl else smtplib.SMTP
                server = func(*smtp_args, **kwargs)
                try:
                    if self.settings.tls and not self.settings.ssl:
                        server.ehlo(self.settings.hostname)
                        server.starttls()
                        server.ehlo(self.settings.hostname)
                    if self.settings.login:
                        server.login(*self.settings.login.split(':', 1))
                    result = server.sendmail(sender, to, payload.as_string())
                finally:
                    server.quit()
        except Exception as e:
            logger.warning('Mail.send failure:%s' % e)
            self.result = result
            self.error = e
            return False
        self.result = result
        self.error = None
        return True


class Recaptcha2(DIV):
    """
    Experimental:
    Creates a DIV holding the newer Recaptcha from Google (v2)

    Args:
        request : the request. If not passed, uses current request
        public_key : the public key Google gave you
        private_key : the private key Google gave you
        error_message : the error message to show if verification fails
        label : the label to use
        options (dict) : takes these parameters

            - hl
            - theme
            - type
            - tabindex
            - callback
            - expired-callback

            see https://developers.google.com/recaptcha/docs/display for docs about those

        comment : the comment

    Examples:
        Use as::

            form = FORM(Recaptcha2(public_key='...', private_key='...'))

        or::

            form = SQLFORM(...)
            form.append(Recaptcha2(public_key='...', private_key='...'))

        to protect the login page instead, use::

            from gluon.tools import Recaptcha2
            auth.settings.captcha = Recaptcha2(request, public_key='...', private_key='...')

    """

    API_URI = 'https://www.google.com/recaptcha/api.js'
    VERIFY_SERVER = 'https://www.google.com/recaptcha/api/siteverify'

    def __init__(self,
                 request=None,
                 public_key='',
                 private_key='',
                 error_message='invalid',
                 label='Verify:',
                 options=None,
                 comment='',
                 ):
        request = request or current.request
        self.request_vars = request and request.vars or current.request.vars
        self.remote_addr = request.env.remote_addr
        self.public_key = public_key
        self.private_key = private_key
        self.errors = Storage()
        self.error_message = error_message
        self.components = []
        self.attributes = {}
        self.label = label
        self.options = options or {}
        self.comment = comment

    def _validate(self):
        recaptcha_response_field = self.request_vars.pop('g-recaptcha-response', None)
        remoteip = self.remote_addr
        if not recaptcha_response_field:
            self.errors['captcha'] = self.error_message
            return False
        params = urlencode({
            'secret': self.private_key,
            'remoteip': remoteip,
            'response': recaptcha_response_field,
        })
        request = urllib2.Request(
            url=self.VERIFY_SERVER,
            data=params,
            headers={'Content-type': 'application/x-www-form-urlencoded',
                     'User-agent': 'reCAPTCHA Python'})
        httpresp = urllib2.urlopen(request)
        content = httpresp.read()
        httpresp.close()
        try:
            response_dict = json.loads(content)
        except:
            self.errors['captcha'] = self.error_message
            return False
        if response_dict.get('success', False):
            self.request_vars.captcha = ''
            return True
        else:
            self.errors['captcha'] = self.error_message
            return False

    def xml(self):
        api_uri = self.API_URI
        hl = self.options.pop('hl', None)
        if hl:
            api_uri = self.API_URI + '?hl=%s' % hl
        public_key = self.public_key
        self.options['sitekey'] = public_key
        captcha = DIV(
            SCRIPT(_src=api_uri, _async='', _defer=''),
            DIV(_class="g-recaptcha", data=self.options),
            TAG.noscript(XML("""
<div style="width: 302px; height: 352px;">
<div style="width: 302px; height: 352px; position: relative;">
  <div style="width: 302px; height: 352px; position: absolute;">
    <iframe src="https://www.google.com/recaptcha/api/fallback?k=%(public_key)s"
            frameborder="0" scrolling="no"
            style="width: 302px; height:352px; border-style: none;">
    </iframe>
  </div>
  <div style="width: 250px; height: 80px; position: absolute; border-style: none;
              bottom: 21px; left: 25px; margin: 0px; padding: 0px; right: 25px;">
    <textarea id="g-recaptcha-response" name="g-recaptcha-response"
              class="g-recaptcha-response"
              style="width: 250px; height: 80px; border: 1px solid #c1c1c1;
                     margin: 0px; padding: 0px; resize: none;" value="">
    </textarea>
  </div>
</div>
</div>""" % dict(public_key=public_key))
            )
        )
        if not self.errors.captcha:
            return XML(captcha).xml()
        else:
            captcha.append(DIV(self.errors['captcha'], _class='error'))
            return XML(captcha).xml()


# this should only be used for captcha and perhaps not even for that
def addrow(form, a, b, c, style, _id, position=-1):
    if style == "divs":
        form[0].insert(position, DIV(DIV(LABEL(a), _class='w2p_fl'),
                                     DIV(b, _class='w2p_fw'),
                                     DIV(c, _class='w2p_fc'),
                                     _id=_id))
    elif style == "table2cols":
        form[0].insert(position, TR(TD(LABEL(a), _class='w2p_fl'),
                                    TD(c, _class='w2p_fc')))
        form[0].insert(position + 1, TR(TD(b, _class='w2p_fw'),
                                        _colspan=2, _id=_id))
    elif style == "ul":
        form[0].insert(position, LI(DIV(LABEL(a), _class='w2p_fl'),
                                    DIV(b, _class='w2p_fw'),
                                    DIV(c, _class='w2p_fc'),
                                    _id=_id))
    elif style == "bootstrap":
        form[0].insert(position, DIV(LABEL(a, _class='control-label'),
                                     DIV(b, SPAN(c, _class='inline-help'),
                                         _class='controls'),
                                     _class='control-group', _id=_id))
    elif style == "bootstrap3_inline":
        form[0].insert(position, DIV(LABEL(a, _class='control-label col-sm-3'),
                                     DIV(b, SPAN(c, _class='help-block'),
                                         _class='col-sm-9'),
                                     _class='form-group', _id=_id))
    elif style == "bootstrap3_stacked":
        form[0].insert(position, DIV(LABEL(a, _class='control-label'),
                                     b, SPAN(c, _class='help-block'),
                                     _class='form-group', _id=_id))
    else:
        form[0].insert(position, TR(TD(LABEL(a), _class='w2p_fl'),
                                    TD(b, _class='w2p_fw'),
                                    TD(c, _class='w2p_fc'), _id=_id))


class AuthJWT(object):
    """
    Experimental!

    Args:
     - secret_key: the secret. Without salting, an attacker knowing this can impersonate
                   any user
     - algorithm : uses as they are in the JWT specs, HS256, HS384 or HS512 basically means
                   signing with HMAC with a 256, 284 or 512bit hash
     - verify_expiration : verifies the expiration checking the exp claim
     - leeway: allow n seconds of skew when checking for token expiration
     - expiration : how many seconds a token may be valid
     - allow_refresh: enable the machinery to get a refreshed token passing a not-already-expired
                      token
     - refresh_expiration_delta: to avoid continous refresh of the token
     - header_prefix : self-explanatory. "JWT" and "Bearer" seems to be the emerging standards
     - jwt_add_header: a dict holding additional mappings to the header. by default only alg and typ are filled
     - user_param: the name of the parameter holding the username when requesting a token. Can be useful, e.g, for
                   email-based authentication, with "email" as a parameter
     - pass_param: same as above, but for the password
     - realm: self-explanatory
     - salt: can be static or a function that takes the payload as an argument.
             Example:
             def mysalt(payload):
                return payload['hmac_key'].split('-')[0]
     - additional_payload: can be a dict to merge with the payload or a function that takes
                           the payload as input and returns the modified payload
                           Example:
                           def myadditional_payload(payload):
                               payload['my_name_is'] = 'bond,james bond'
                               return payload
     - before_authorization: can be a callable that takes the deserialized token (a dict) as input.
                             Gets called right after signature verification but before the actual
                             authorization takes place. It may be use to cast
                             the extra auth_user fields to their actual types.
                             You can raise with HTTP a proper error message
                             Example:
                             def mybefore_authorization(tokend):
                                 if not tokend['my_name_is'] == 'bond,james bond':
                                     raise HTTP(400, u'Invalid JWT my_name_is claim')
     - max_header_length: check max length to avoid load()ing unusually large tokens (could mean crafted, e.g. in a DDoS.)

    Basic Usage:
    in models (or the controller needing it)

        myjwt = AuthJWT(auth, secret_key='secret')

    in the controller issuing tokens

        def login_and_take_token():
            return myjwt.jwt_token_manager()

    A call then to /app/controller/login_and_take_token with username and password returns the token
    A call to /app/controller/login_and_take_token with the original token returns the refreshed token

    To protect a function with JWT

        @myjwt.allows_jwt()
        @auth.requires_login()
        def protected():
            return '%s$%s' % (request.now, auth.user_id)

    To inject optional auth info into the action with JWT
        @myjwt.allows_jwt()
        def unprotected():
            if auth.user:
                return '%s$%s' % (request.now, auth.user_id)

            return "No auth info!"


    """

    def __init__(self,
                 auth,
                 secret_key,
                 algorithm='HS256',
                 verify_expiration=True,
                 leeway=30,
                 expiration=60 * 5,
                 allow_refresh=True,
                 refresh_expiration_delta=60 * 60,
                 header_prefix='Bearer',
                 jwt_add_header=None,
                 user_param='username',
                 pass_param='password',
                 realm='Login required',
                 salt=None,
                 additional_payload=None,
                 before_authorization=None,
                 max_header_length=4 * 1024,
                 ):
        self.secret_key = secret_key
        self.auth = auth
        self.algorithm = algorithm
        if self.algorithm not in ('HS256', 'HS384', 'HS512'):
            raise NotImplementedError('Algorithm %s not allowed' % algorithm)
        self.verify_expiration = verify_expiration
        self.leeway = leeway
        self.expiration = expiration
        self.allow_refresh = allow_refresh
        self.refresh_expiration_delta = refresh_expiration_delta
        self.header_prefix = header_prefix
        self.jwt_add_header = jwt_add_header or {}
        base_header = {'alg': self.algorithm, 'typ': 'JWT'}
        for k, v in iteritems(self.jwt_add_header):
            base_header[k] = v
        self.cached_b64h = self.jwt_b64e(json.dumps(base_header))
        digestmod_mapping = {
            'HS256': hashlib.sha256,
            'HS384': hashlib.sha384,
            'HS512': hashlib.sha512
        }
        self.digestmod = digestmod_mapping[algorithm]
        self.user_param = user_param
        self.pass_param = pass_param
        self.realm = realm
        self.salt = salt
        self.additional_payload = additional_payload
        self.before_authorization = before_authorization
        self.max_header_length = max_header_length
        self.recvd_token = None

    @staticmethod
    def jwt_b64e(string):
        string = to_bytes(string)
        return base64.urlsafe_b64encode(string).strip(b'=')

    @staticmethod
    def jwt_b64d(string):
        """base64 decodes a single bytestring (and is tolerant to getting
        called with a unicode string).
        The result is also a bytestring.
        """
        string = to_bytes(string, 'ascii', 'ignore')
        return base64.urlsafe_b64decode(string + b'=' * (-len(string) % 4))

    def generate_token(self, payload):
        secret = to_bytes(self.secret_key)
        if self.salt:
            if callable(self.salt):
                secret = "%s$%s" % (secret, self.salt(payload))
            else:
                secret = "%s$%s" % (secret, self.salt)
            if isinstance(secret, unicodeT):
                secret = secret.encode('ascii', 'ignore')
        b64h = self.cached_b64h
        b64p = self.jwt_b64e(serializers.json(payload))
        jbody = b64h + b'.' + b64p
        mauth = hmac.new(key=secret, msg=jbody, digestmod=self.digestmod)
        jsign = self.jwt_b64e(mauth.digest())
        return to_native(jbody + b'.' + jsign)

    def verify_signature(self, body, signature, secret):
        mauth = hmac.new(key=secret, msg=body, digestmod=self.digestmod)
        return compare(self.jwt_b64e(mauth.digest()), signature)

    def load_token(self, token):
        token = to_bytes(token, 'utf-8', 'strict')
        body, sig = token.rsplit(b'.', 1)
        b64h, b64b = body.split(b'.', 1)
        if b64h != self.cached_b64h:
            # header not the same
            raise HTTP(400, u'Invalid JWT Header')
        secret = self.secret_key
        tokend = serializers.loads_json(to_native(self.jwt_b64d(b64b)))
        if self.salt:
            if callable(self.salt):
                secret = "%s$%s" % (secret, self.salt(tokend))
            else:
                secret = "%s$%s" % (secret, self.salt)
        secret = to_bytes(secret, 'ascii', 'ignore')
        if not self.verify_signature(body, sig, secret):
            # signature verification failed
            raise HTTP(400, u'Token signature is invalid')
        if self.verify_expiration:
            now = time.mktime(datetime.datetime.utcnow().timetuple())
            if tokend['exp'] + self.leeway < now:
                raise HTTP(400, u'Token is expired')
        if callable(self.before_authorization):
            self.before_authorization(tokend)
        return tokend

    def serialize_auth_session(self, session_auth):
        """
        As bad as it sounds, as long as this is rarely used (vs using the token)
        this is the faster method, even if we ditch session in jwt_token_manager().
        We (mis)use the heavy default auth mechanism to avoid any further computation,
        while sticking to a somewhat-stable Auth API.
        """
        # TODO: Check the following comment
        # is the following safe or should we use
        # calendar.timegm(datetime.datetime.utcnow().timetuple())
        # result seem to be the same (seconds since epoch, in UTC)
        now = time.mktime(datetime.datetime.utcnow().timetuple())
        expires = now + self.expiration
        payload = dict(
            hmac_key=session_auth['hmac_key'],
            user_groups=session_auth['user_groups'],
            user=session_auth['user'].as_dict(),
            iat=now,
            exp=expires
        )
        return payload

    def refresh_token(self, orig_payload):
        now = time.mktime(datetime.datetime.utcnow().timetuple())
        if self.verify_expiration:
            orig_exp = orig_payload['exp']
            if orig_exp + self.leeway < now:
                # token already expired, can't be used for refresh
                raise HTTP(400, u'Token already expired')
        orig_iat = orig_payload.get('orig_iat') or orig_payload['iat']
        if orig_iat + self.refresh_expiration_delta < now:
            # refreshed too long ago
            raise HTTP(400, u'Token issued too long ago')
        expires = now + self.expiration
        orig_payload.update(
            orig_iat=orig_iat,
            iat=now,
            exp=expires,
            hmac_key=web2py_uuid()
        )
        self.alter_payload(orig_payload)
        return orig_payload

    def alter_payload(self, payload):
        if self.additional_payload:
            if callable(self.additional_payload):
                payload = self.additional_payload(payload)
            elif isinstance(self.additional_payload, dict):
                payload.update(self.additional_payload)
        return payload

    def jwt_token_manager(self, token_param='_token'):
        """
        The part that issues (and refreshes) tokens.
        Used in a controller, given myjwt is the istantiated class, as

            @myjwt.allow_jwt(required=False, verify_expiration=False)
            def api_auth():
                return myjwt.jwt_token_manager()

        Then, a call to /app/c/api_auth with username and password
        returns a token, while /app/c/api_auth with the current token
        issues another token (expired, but within grace time)
        """
        request = current.request
        response = current.response
        session = current.session
        # forget and unlock response
        session.forget(response)
        valid_user = None
        ret = None
        token = None
        try:
            token = self.recvd_token or self.get_jwt_token_from_request(token_param)
        except HTTP:
            pass
        if token:
            if not self.allow_refresh:
                raise HTTP(403, u'Refreshing token is not allowed')
            tokend = self.load_token(token)
            # verification can fail here
            refreshed = self.refresh_token(tokend)
            ret = {'token': self.generate_token(refreshed)}
        elif self.user_param in request.vars and self.pass_param in request.vars:
            username = request.vars[self.user_param]
            password = request.vars[self.pass_param]
            valid_user = self.auth.login_bare(username, password)
        else:
            valid_user = self.auth.user
            self.auth.login_user(valid_user)
        if valid_user:
            payload = self.serialize_auth_session(session.auth)
            self.alter_payload(payload)
            ret = {'token': self.generate_token(payload)}
        elif ret is None:
            raise HTTP(401,
                       u'Not Authorized - need to be logged in, to pass a token '
                       u'for refresh or username and password for login',
                       **{'WWW-Authenticate': u'JWT realm="%s"' % self.realm})
        response.headers['Content-Type'] = 'application/json'
        return serializers.json(ret)

    def inject_token(self, tokend):
        """
        The real deal, not touching the db but still logging-in the user
        """
        self.auth.user = Storage(tokend['user'])
        self.auth.user_groups = tokend['user_groups']
        self.auth.hmac_key = tokend['hmac_key']

    def get_jwt_token_from_request(self, token_param='_token'):
        """
        The method that extracts and validates the token, either
        from the header or the _token var

        token_param: request.vars attribute with the token used only if the http authorization header is not present.
        """
        token = None
        token_in_header = current.request.env.http_authorization
        if token_in_header:
            parts = token_in_header.split()
            if parts[0].lower() != self.header_prefix.lower():
                raise HTTP(400, u'Invalid JWT header')
            elif len(parts) == 1:
                raise HTTP(400, u'Invalid JWT header, missing token')
            elif len(parts) > 2:
                raise HTTP(400, 'Invalid JWT header, token contains spaces')
            token = parts[1]
        else:
            token = current.request.vars.get(token_param)
            if token is None:
                raise HTTP(400, 'JWT header not found and JWT parameter {} missing in request'.format(token_param))

        self.recvd_token = token
        return token

    def allows_jwt(self, otherwise=None, required=True, verify_expiration=True, token_param='_token'):
        """
        The decorator that takes care of injecting auth info in the decorated action.
        Works w/o resorting to session.

        Args:

            required: the token is mandatory (either in request.var._token or in the HTTP hearder Authorization Bearer)
            verify_expiration: allows to bypass expiration check.  Useful to manage token renewal.
            token_param: request.vars attribute with the token used only if the http authorization header is not present (default: "_token").

        """
        def decorator(action):
            def f(*args, **kwargs):
                try:
                    token = self.get_jwt_token_from_request(token_param=token_param)
                except HTTP as e:
                    if required:
                        raise e
                    token = None
                if token and len(token) < self.max_header_length:
                    old_verify_expiration = self.verify_expiration
                    try:
                        self.verify_expiration = verify_expiration
                        tokend = self.load_token(token)
                    except ValueError:
                        raise HTTP(400, 'Invalid JWT header, wrong token format')
                    finally:
                        self.verify_expiration = old_verify_expiration
                    self.inject_token(tokend)

                return action(*args, **kwargs)

            f.__doc__ = action.__doc__
            f.__name__ = action.__name__
            f.__dict__.update(action.__dict__)
            return f

        return decorator


class Auth(AuthAPI):

    default_settings = dict(AuthAPI.default_settings,
                            allow_basic_login=False,
                            allow_basic_login_only=False,
                            allow_delete_accounts=False,
                            alternate_requires_registration=False,
                            auth_manager_role=None,
                            auth_two_factor_enabled=False,
                            auth_two_factor_tries_left=3,
                            bulk_register_enabled=False,
                            captcha=None,
                            cas_maps=None,
                            client_side=True,
                            formstyle=None,
                            hideerror=False,
                            label_separator=None,
                            login_after_password_change=True,
                            login_after_registration=False,
                            login_captcha=None,
                            long_expiration=3600 * 30 * 24,  # one month
                            mailer=None,
                            manager_actions={},
                            multi_login=False,
                            on_failed_authentication=lambda x: redirect(x),
                            pre_registration_div=None,
                            prevent_open_redirect_attacks=True,
                            prevent_password_reset_attacks=True,
                            profile_fields=None,
                            register_captcha=None,
                            register_fields=None,
                            register_verify_password=True,
                            remember_me_form=True,
                            reset_password_requires_verification=False,
                            retrieve_password_captcha=None,
                            retrieve_username_captcha=None,
                            showid=False,
                            table_cas=None,
                            table_cas_name='auth_cas',
                            table_event=None,
                            table_group=None,
                            table_membership=None,
                            table_permission=None,
                            table_token_name='auth_token',
                            table_user=None,
                            two_factor_authentication_group=None,
                            update_fields=['email'],
                            wiki=Settings()
                            )
    # ## these are messages that can be customized
    default_messages = dict(AuthAPI.default_messages,
                            access_denied='Insufficient privileges',
                            bulk_invite_body='You have been invited to join %(site)s, click %(link)s to complete '
                                             'the process',
                            bulk_invite_subject='Invitation to join %(site)s',
                            delete_label='Check to delete',
                            email_sent='Email sent',
                            email_verified='Email verified',
                            function_disabled='Function disabled',
                            impersonate_log='User %(id)s is impersonating %(other_id)s',
                            invalid_reset_password='Invalid reset password',
                            invalid_two_factor_code='Incorrect code. {0} more attempt(s) remaining.',
                            is_empty="Cannot be empty",
                            label_client_ip='Client IP',
                            label_description='Description',
                            label_email='E-mail',
                            label_first_name='First name',
                            label_group_id='Group ID',
                            label_last_name='Last name',
                            label_name='Name',
                            label_origin='Origin',
                            label_password='Password',
                            label_record_id='Record ID',
                            label_registration_id='Registration identifier',
                            label_registration_key='Registration key',
                            label_remember_me="Remember me (for 30 days)",
                            label_reset_password_key='Reset Password key',
                            label_role='Role',
                            label_table_name='Object or table name',
                            label_time_stamp='Timestamp',
                            label_two_factor='Authentication code',
                            label_user_id='User ID',
                            label_username='Username',
                            login_button='Log In',
                            login_disabled='Login disabled by administrator',
                            new_password='New password',
                            new_password_sent='A new password was emailed to you',
                            old_password='Old password',
                            password_change_button='Change password',
                            password_reset_button='Request reset password',
                            profile_save_button='Apply changes',
                            register_button='Sign Up',
                            reset_password='Click on the link %(link)s to reset your password',
                            reset_password_log='User %(id)s Password reset',
                            reset_password_subject='Password reset',
                            retrieve_password='Your password is: %(password)s',
                            retrieve_password_log='User %(id)s Password retrieved',
                            retrieve_password_subject='Password retrieve',
                            retrieve_two_factor_code='Your temporary login code is {0}',
                            retrieve_two_factor_code_subject='Two-step Login Authentication Code',
                            retrieve_username='Your username is: %(username)s',
                            retrieve_username_log='User %(id)s Username retrieved',
                            retrieve_username_subject='Username retrieve',
                            submit_button='Submit',
                            two_factor_comment='This code was emailed to you and is required for login.',
                            unable_send_email='Unable to send email',
                            username_sent='Your username was emailed to you',
                            verify_email='Welcome %(username)s! Click on the link %(link)s to verify your email',
                            verify_email_log='User %(id)s Verification email sent',
                            verify_email_subject='Email verification',
                            verify_password='Verify Password',
                            verify_password_comment='please input your password again'
                            )
    """
    Class for authentication, authorization, role based access control.

    Includes:

    - registration and profile
    - login and logout
    - username and password retrieval
    - event logging
    - role creation and assignment
    - user defined group/role based permission

    Args:

        environment: is there for legacy but unused (awful)
        db: has to be the database where to create tables for authentication
        mailer: `Mail(...)` or None (no mailer) or True (make a mailer)
        hmac_key: can be a hmac_key or hmac_key=Auth.get_or_create_key()
        controller: (where is the user action?)
        cas_provider: (delegate authentication to the URL, CAS2)

    Authentication Example::

        from gluon.contrib.utils import *
        mail=Mail()
        mail.settings.server='smtp.gmail.com:587'
        mail.settings.sender='you@somewhere.com'
        mail.settings.login='username:password'
        auth=Auth(db)
        auth.settings.mailer=mail
        # auth.settings....=...
        auth.define_tables()
        def authentication():
            return dict(form=auth())

    Exposes:

    - `http://.../{application}/{controller}/authentication/login`
    - `http://.../{application}/{controller}/authentication/logout`
    - `http://.../{application}/{controller}/authentication/register`
    - `http://.../{application}/{controller}/authentication/verify_email`
    - `http://.../{application}/{controller}/authentication/retrieve_username`
    - `http://.../{application}/{controller}/authentication/retrieve_password`
    - `http://.../{application}/{controller}/authentication/reset_password`
    - `http://.../{application}/{controller}/authentication/profile`
    - `http://.../{application}/{controller}/authentication/change_password`

    On registration a group with role=new_user.id is created
    and user is given membership of this group.

    You can create a group with::

        group_id=auth.add_group('Manager', 'can access the manage action')
        auth.add_permission(group_id, 'access to manage')

    Here "access to manage" is just a user defined string.
    You can give access to a user::

        auth.add_membership(group_id, user_id)

    If user id is omitted, the logged in user is assumed

    Then you can decorate any action::

        @auth.requires_permission('access to manage')
        def manage():
            return dict()

    You can restrict a permission to a specific table::

        auth.add_permission(group_id, 'edit', db.sometable)
        @auth.requires_permission('edit', db.sometable)

    Or to a specific record::

        auth.add_permission(group_id, 'edit', db.sometable, 45)
        @auth.requires_permission('edit', db.sometable, 45)

    If authorization is not granted calls::

        auth.settings.on_failed_authorization

    Other options::

        auth.settings.mailer=None
        auth.settings.expiration=3600 # seconds

        ...

        ### these are messages that can be customized
        ...

    """

    @staticmethod
    def get_or_create_key(filename=None, alg='sha512'):
        request = current.request
        if not filename:
            filename = os.path.join(request.folder, 'private', 'auth.key')
        if os.path.exists(filename):
            key = open(filename, 'r').read().strip()
        else:
            key = alg + ':' + web2py_uuid()
            open(filename, 'w').write(key)
        return key

    def url(self, f=None, args=None, vars=None, scheme=False):
        if args is None:
            args = []
        if vars is None:
            vars = {}
        host = scheme and self.settings.host
        return URL(c=self.settings.controller,
                   f=f, args=args, vars=vars, scheme=scheme, host=host)

    def here(self):
        return URL(args=current.request.args, vars=current.request.get_vars)

    def select_host(self, host, host_names=None):
        """
        checks that host is valid, i.e. in the list of glob host_names
        if the host is missing, then is it selects the first entry from host_names
        read more here: https://github.com/web2py/web2py/issues/1196
        """
        if host:
            if host_names:
                for item in host_names:
                    if fnmatch.fnmatch(host, item):
                        break
                else:
                    raise HTTP(403, "Invalid Hostname")
        elif host_names:
            host = host_names[0]
        else:
            host = 'localhost'
        return host

    def __init__(self, environment=None, db=None, mailer=True,
                 hmac_key=None, controller='default', function='user',
                 cas_provider=None, signature=True, secure=False,
                 csrf_prevention=True, propagate_extension=None,
                 url_index=None, jwt=None, host_names=None):

        # next two lines for backward compatibility
        if not db and environment and isinstance(environment, DAL):
            db = environment
        self.db = db
        self.environment = current
        self.csrf_prevention = csrf_prevention
        request = current.request
        session = current.session
        auth = session.auth
        self.user_groups = auth and auth.user_groups or {}
        if secure:
            request.requires_https()
        now = request.now
        # if we have auth info
        #    if not expired it, used it
        #    if expired, clear the session
        # else, only clear auth info in the session
        if auth:
            delta = datetime.timedelta(days=0, seconds=auth.expiration)
            if auth.last_visit and auth.last_visit + delta > now:
                self.user = auth.user
                # this is a trick to speed up sessions to avoid many writes
                if (now - auth.last_visit).seconds > (auth.expiration // 10):
                    auth.last_visit = now
            else:
                self.user = None
                if session.auth:
                    del session.auth
                session.renew(clear_session=True)
        else:
            self.user = None
            if session.auth:
                del session.auth
        # ## what happens after login?

        url_index = url_index or URL(controller, 'index')
        url_login = URL(controller, function, args='login',
                        extension=propagate_extension)
        # ## what happens after registration?

        settings = self.settings = Settings()
        settings.update(Auth.default_settings)
        host = self.select_host(request.env.http_host, host_names)
        settings.update(
            cas_domains=[host],
            enable_tokens=False,
            cas_provider=cas_provider,
            cas_actions=dict(login='login',
                             validate='validate',
                             servicevalidate='serviceValidate',
                             proxyvalidate='proxyValidate',
                             logout='logout'),
            cas_create_user=True,
            extra_fields={},
            actions_disabled=[],
            controller=controller,
            function=function,
            login_url=url_login,
            logged_url=URL(controller, function, args='profile'),
            download_url=URL(controller, 'download'),
            mailer=(mailer is True) and Mail() or mailer,
            on_failed_authorization=URL(controller, function, args='not_authorized'),
            login_next=url_index,
            login_onvalidation=[],
            login_onaccept=[],
            login_onfail=[],
            login_methods=[self],
            login_form=self,
            logout_next=url_index,
            logout_onlogout=None,
            register_next=url_index,
            register_onvalidation=[],
            register_onaccept=[],
            verify_email_next=url_login,
            verify_email_onaccept=[],
            profile_next=url_index,
            profile_onvalidation=[],
            profile_onaccept=[],
            retrieve_username_next=url_index,
            retrieve_password_next=url_index,
            request_reset_password_next=url_login,
            reset_password_next=url_index,
            change_password_next=url_index,
            change_password_onvalidation=[],
            change_password_onaccept=[],
            retrieve_password_onvalidation=[],
            request_reset_password_onvalidation=[],
            request_reset_password_onaccept=[],
            reset_password_onvalidation=[],
            reset_password_onaccept=[],
            hmac_key=hmac_key,
            formstyle=current.response.formstyle,
            label_separator=current.response.form_label_separator,
            two_factor_methods=[],
            two_factor_onvalidation=[],
            host=host,
        )
        settings.lock_keys = True
        # ## these are messages that can be customized
        messages = self.messages = Messages(current.T)
        messages.update(Auth.default_messages)
        messages.update(ajax_failed_authentication=
                        DIV(H4('NOT AUTHORIZED'),
                            'Please ',
                            A('login',
                              _href=self.settings.login_url +
                                    ('?_next=' + urllib_quote(current.request.env.http_web2py_component_location))
                              if current.request.env.http_web2py_component_location else ''),
                            ' to view this content.',
                            _class='not-authorized alert alert-block'))
        messages.lock_keys = True

        # for "remember me" option
        response = current.response
        if auth and auth.remember_me:
            # when user wants to be logged in for longer
            response.session_cookie_expires = auth.expiration
        if signature:
            self.define_signature()
        else:
            self.signature = None
        self.jwt_handler = jwt and AuthJWT(self, **jwt)

    def get_vars_next(self):
        next = current.request.vars._next
        host = current.request.env.http_host
        if isinstance(next, (list, tuple)):
            next = next[0]
        if next and self.settings.prevent_open_redirect_attacks:
            return self.prevent_open_redirect(next, host)
        return next or None

    @staticmethod
    def prevent_open_redirect(next, host):
        # Prevent an attacker from adding an arbitrary url after the
        # _next variable in the request.
        if next:
            parts = next.split('/')
            if ':' not in parts[0]:
                return next
            elif len(parts) > 2 and parts[0].endswith(':') and parts[1:3] == ['', host]:
                return next
        return None

    def table_cas(self):
        return self.db[self.settings.table_cas_name]

    def table_token(self):
        return self.db[self.settings.table_token_name]

    def _HTTP(self, *a, **b):
        """
        only used in lambda: self._HTTP(404)
        """

        raise HTTP(*a, **b)

    def __call__(self):
        """
        Example:
            Use as::

                def authentication():
                    return dict(form=auth())

        """

        request = current.request
        args = request.args
        if not args:
            redirect(self.url(args='login', vars=request.vars))
        elif args[0] in self.settings.actions_disabled:
            raise HTTP(404)
        if args[0] in ('login', 'logout', 'register', 'verify_email',
                       'retrieve_username', 'retrieve_password',
                       'reset_password', 'request_reset_password',
                       'change_password', 'profile', 'groups',
                       'impersonate', 'not_authorized', 'confirm_registration',
                       'bulk_register', 'manage_tokens', 'jwt'):
            if len(request.args) >= 2 and args[0] == 'impersonate':
                return getattr(self, args[0])(request.args[1])
            else:
                return getattr(self, args[0])()
        elif args[0] == 'cas' and not self.settings.cas_provider:
            if args(1) == self.settings.cas_actions['login']:
                return self.cas_login(version=2)
            elif args(1) == self.settings.cas_actions['validate']:
                return self.cas_validate(version=1)
            elif args(1) == self.settings.cas_actions['servicevalidate']:
                return self.cas_validate(version=2, proxy=False)
            elif args(1) == self.settings.cas_actions['proxyvalidate']:
                return self.cas_validate(version=2, proxy=True)
            elif (args(1) == 'p3'
                  and args(2) == self.settings.cas_actions['servicevalidate']):
                return self.cas_validate(version=3, proxy=False)
            elif (args(1) == 'p3'
                  and args(2) == self.settings.cas_actions['proxyvalidate']):
                return self.cas_validate(version=3, proxy=True)
            elif args(1) == self.settings.cas_actions['logout']:
                return self.logout(next=request.vars.service or DEFAULT)
        else:
            raise HTTP(404)

    def navbar(self, prefix='Welcome', action=None,
               separators=(' [ ', ' | ', ' ] '), user_identifier=DEFAULT,
               referrer_actions=DEFAULT, mode='default'):
        """ Navbar with support for more templates
        This uses some code from the old navbar.

        Args:
            mode: see options for list of

        """
        items = []  # Hold all menu items in a list
        self.bar = ''  # The final
        T = current.T
        referrer_actions = [] if not referrer_actions else referrer_actions
        if not action:
            action = self.url(self.settings.function)

        request = current.request
        if URL() == action:
            next = ''
        else:
            next = '?_next=' + urllib_quote(URL(args=request.args,
                                                vars=request.get_vars))
        href = lambda function: \
            '%s/%s%s' % (action, function, next if referrer_actions is DEFAULT or function in referrer_actions else '')
        if isinstance(prefix, str):
            prefix = T(prefix)
        if prefix:
            prefix = prefix.strip() + ' '

        def Anr(*a, **b):
            b['_rel'] = 'nofollow'
            return A(*a, **b)

        if self.user_id:  # User is logged in
            logout_next = self.settings.logout_next
            items.append({'name': T('Log Out'),
                          'href': '%s/logout?_next=%s' % (action, urllib_quote(logout_next)),
                          'icon': 'icon-off'})
            if 'profile' not in self.settings.actions_disabled:
                items.append({'name': T('Profile'), 'href': href('profile'),
                              'icon': 'icon-user'})
            if 'change_password' not in self.settings.actions_disabled:
                items.append({'name': T('Password'),
                              'href': href('change_password'),
                              'icon': 'icon-lock'})

            if user_identifier is DEFAULT:
                user_identifier = '%(first_name)s'
            if callable(user_identifier):
                user_identifier = user_identifier(self.user)
            elif ((isinstance(user_identifier, str) or
                   type(user_identifier).__name__ == 'lazyT') and
                  re.search(r'%\(.+\)s', user_identifier)):
                user_identifier = user_identifier % self.user
            if not user_identifier:
                user_identifier = ''
        else:  # User is not logged in
            items.append({'name': T('Log In'), 'href': href('login'),
                          'icon': 'icon-off'})
            if 'register' not in self.settings.actions_disabled:
                items.append({'name': T('Sign Up'), 'href': href('register'),
                              'icon': 'icon-user'})
            if 'request_reset_password' not in self.settings.actions_disabled:
                items.append({'name': T('Lost password?'),
                              'href': href('request_reset_password'),
                              'icon': 'icon-lock'})
            if self.settings.use_username and 'retrieve_username' not in self.settings.actions_disabled:
                items.append({'name': T('Forgot username?'),
                              'href': href('retrieve_username'),
                              'icon': 'icon-edit'})

        def menu():  # For inclusion in MENU
            self.bar = [(items[0]['name'], False, items[0]['href'], [])]
            del items[0]
            for item in items:
                self.bar[0][3].append((item['name'], False, item['href']))

        def bootstrap3():  # Default web2py scaffolding
            def rename(icon): return icon + ' ' + icon.replace('icon', 'glyphicon')
            self.bar = UL(LI(Anr(I(_class=rename('icon ' + items[0]['icon'])),
                                 ' ' + items[0]['name'],
                                 _href=items[0]['href'])), _class='dropdown-menu')
            del items[0]
            for item in items:
                self.bar.insert(-1, LI(Anr(I(_class=rename('icon ' + item['icon'])),
                                           ' ' + item['name'],
                                           _href=item['href'])))
            self.bar.insert(-1, LI('', _class='divider'))
            if self.user_id:
                self.bar = LI(Anr(prefix, user_identifier,
                                  _href='#', _class="dropdown-toggle",
                                  data={'toggle': 'dropdown'}),
                              self.bar, _class='dropdown')
            else:
                self.bar = LI(Anr(T('Log In'),
                                  _href='#', _class="dropdown-toggle",
                                  data={'toggle': 'dropdown'}), self.bar,
                              _class='dropdown')

        def bare():
            """ In order to do advanced customization we only need the
            prefix, the user_identifier and the href attribute of items

            Examples:
                Use as::

                # in module custom_layout.py
                from gluon import *
                def navbar(auth_navbar):
                    bar = auth_navbar
                    user = bar["user"]

                    if not user:
                        btn_login = A(current.T("Login"),
                                      _href=bar["login"],
                                      _class="btn btn-success",
                                      _rel="nofollow")
                        btn_register = A(current.T("Sign up"),
                                         _href=bar["register"],
                                         _class="btn btn-primary",
                                         _rel="nofollow")
                        return DIV(btn_register, btn_login, _class="btn-group")
                    else:
                        toggletext = "%s back %s" % (bar["prefix"], user)
                        toggle = A(toggletext,
                                   _href="#",
                                   _class="dropdown-toggle",
                                   _rel="nofollow",
                                   **{"_data-toggle": "dropdown"})
                        li_profile = LI(A(I(_class="icon-user"), ' ',
                                          current.T("Account details"),
                                          _href=bar["profile"], _rel="nofollow"))
                        li_custom = LI(A(I(_class="icon-book"), ' ',
                                         current.T("My Agenda"),
                                         _href="#", rel="nofollow"))
                        li_logout = LI(A(I(_class="icon-off"), ' ',
                                         current.T("logout"),
                                         _href=bar["logout"], _rel="nofollow"))
                        dropdown = UL(li_profile,
                                      li_custom,
                                      LI('', _class="divider"),
                                      li_logout,
                                      _class="dropdown-menu", _role="menu")

                        return LI(toggle, dropdown, _class="dropdown")

                # in models db.py
                import custom_layout as custom

                # in layout.html
                <ul id="navbar" class="nav pull-right">
                    {{='auth' in globals() and \
                      custom.navbar(auth.navbar(mode='bare')) or ''}}</ul>

            """
            bare = {'prefix': prefix, 'user': user_identifier if self.user_id else None}

            for i in items:
                if i['name'] == T('Log In'):
                    k = 'login'
                elif i['name'] == T('Sign Up'):
                    k = 'register'
                elif i['name'] == T('Lost password?'):
                    k = 'request_reset_password'
                elif i['name'] == T('Forgot username?'):
                    k = 'retrieve_username'
                elif i['name'] == T('Log Out'):
                    k = 'logout'
                elif i['name'] == T('Profile'):
                    k = 'profile'
                elif i['name'] == T('Password'):
                    k = 'change_password'

                bare[k] = i['href']

            self.bar = bare

        options = {'asmenu': menu,
                   'dropdown': bootstrap3,
                   'bare': bare
                   }  # Define custom modes.

        if mode in options and callable(options[mode]):
            options[mode]()
        else:
            s1, s2, s3 = separators
            if self.user_id:
                self.bar = SPAN(prefix, user_identifier, s1,
                                Anr(items[0]['name'],
                                    _href=items[0]['href']), s3,
                                _class='auth_navbar')
            else:
                self.bar = SPAN(s1, Anr(items[0]['name'],
                                        _href=items[0]['href']), s3,
                                _class='auth_navbar')
            for item in items[1:]:
                self.bar.insert(-1, s2)
                self.bar.insert(-1, Anr(item['name'], _href=item['href']))

        return self.bar

    def enable_record_versioning(self,
                                 tables,
                                 archive_db=None,
                                 archive_names='%(tablename)s_archive',
                                 current_record='current_record',
                                 current_record_label=None):
        """
        Used to enable full record versioning (including auth tables)::

            auth = Auth(db)
            auth.define_tables(signature=True)
            # define our own tables
            db.define_table('mything',Field('name'),auth.signature)
            auth.enable_record_versioning(tables=db)

        tables can be the db (all table) or a list of tables.
        only tables with modified_by and modified_on fiels (as created
        by auth.signature) will have versioning. Old record versions will be
        in table 'mything_archive' automatically defined.

        when you enable enable_record_versioning, records are never
        deleted but marked with is_active=False.

        enable_record_versioning enables a common_filter for
        every table that filters out records with is_active = False

        Note:
            If you use auth.enable_record_versioning,
            do not use auth.archive or you will end up with duplicates.
            auth.archive does explicitly what enable_record_versioning
            does automatically.

        """
        current_record_label = current_record_label or current.T(
            current_record.replace('_', ' ').title())
        for table in tables:
            fieldnames = table.fields()
            if 'id' in fieldnames and 'modified_on' in fieldnames and current_record not in fieldnames:
                table._enable_record_versioning(archive_db=archive_db,
                                                archive_name=archive_names,
                                                current_record=current_record,
                                                current_record_label=current_record_label)

    def define_tables(self, username=None, signature=None, enable_tokens=False,
                      migrate=None, fake_migrate=None):
        """
        To be called unless tables are defined manually

        Examples:
            Use as::

                # defines all needed tables and table files
                # 'myprefix_auth_user.table', ...
                auth.define_tables(migrate='myprefix_')

                # defines all needed tables without migration/table files
                auth.define_tables(migrate=False)

        """

        db = self.db
        if migrate is None:
            migrate = db._migrate
        if fake_migrate is None:
            fake_migrate = db._fake_migrate
        settings = self.settings
        settings.enable_tokens = enable_tokens
        signature_list = \
            super(Auth, self).define_tables(username, signature, migrate, fake_migrate)._table_signature_list

        now = current.request.now
        reference_table_user = 'reference %s' % settings.table_user_name
        if settings.cas_domains:
            if settings.table_cas_name not in db.tables:
                db.define_table(
                    settings.table_cas_name,
                    Field('user_id', reference_table_user, default=None,
                          label=self.messages.label_user_id),
                    Field('created_on', 'datetime', default=now),
                    Field('service', requires=IS_URL()),
                    Field('ticket'),
                    Field('renew', 'boolean', default=False),
                    *settings.extra_fields.get(settings.table_cas_name, []),
                    **dict(
                        migrate=self._get_migrate(
                            settings.table_cas_name, migrate),
                        fake_migrate=fake_migrate))
        if settings.enable_tokens:
            extra_fields = settings.extra_fields.get(
                settings.table_token_name, []) + signature_list
            if settings.table_token_name not in db.tables:
                db.define_table(
                    settings.table_token_name,
                    Field('user_id', reference_table_user, default=None,
                          label=self.messages.label_user_id),
                    Field('expires_on', 'datetime', default=datetime.datetime(2999, 12, 31)),
                    Field('token', writable=False, default=web2py_uuid, unique=True),
                    *extra_fields,
                    **dict(migrate=self._get_migrate(settings.table_token_name, migrate),
                           fake_migrate=fake_migrate))
        if not db._lazy_tables:
            settings.table_user = db[settings.table_user_name]
            settings.table_group = db[settings.table_group_name]
            settings.table_membership = db[settings.table_membership_name]
            settings.table_permission = db[settings.table_permission_name]
            settings.table_event = db[settings.table_event_name]
            if settings.cas_domains:
                settings.table_cas = db[settings.table_cas_name]

        if settings.cas_provider:  # THIS IS NOT LAZY
            settings.actions_disabled = \
                ['profile', 'register', 'change_password',
                 'request_reset_password', 'retrieve_username']
            from gluon.contrib.login_methods.cas_auth import CasAuth
            maps = settings.cas_maps
            if not maps:
                table_user = self.table_user()
                maps = dict((name, lambda v, n=name: v.get(n, None)) for name in
                            table_user.fields if name != 'id'
                            and table_user[name].readable)
                maps['registration_id'] = \
                    lambda v, p=settings.cas_provider: '%s/%s' % (p, v['user'])
            actions = [settings.cas_actions['login'],
                       settings.cas_actions['servicevalidate'],
                       settings.cas_actions['logout']]
            settings.login_form = CasAuth(
                casversion=2,
                urlbase=settings.cas_provider,
                actions=actions,
                maps=maps)
        return self

    def get_or_create_user(self, keys, update_fields=['email'],
                           login=True, get=True):
        """
        Used for alternate login methods:
        If the user exists already then password is updated.
        If the user doesn't yet exist, then they are created.
        """
        table_user = self.table_user()
        create_user = self.settings.cas_create_user
        user = None
        checks = []
        # make a guess about who this user is
        guess_fields = ['registration_id', 'username', 'email']
        if self.settings.login_userfield:
            guess_fields.append(self.settings.login_userfield)
        for fieldname in guess_fields:
            if fieldname in table_user.fields() and \
                    keys.get(fieldname, None):
                checks.append(fieldname)
                value = keys[fieldname]
                user = table_user(**{fieldname: value})
                if user:
                    break
        if not checks:
            return None
        if 'registration_id' not in keys:
            keys['registration_id'] = keys[checks[0]]
        # if we think we found the user but registration_id does not match,
        # make new user
        if 'registration_id' in checks \
                and user \
                and user.registration_id \
                and ('registration_id' not in keys or user.registration_id != str(keys['registration_id'])):
            user = None  # THINK MORE ABOUT THIS? DO WE TRUST OPENID PROVIDER?
        if user:
            if not get:
                # added for register_bare to avoid overwriting users
                return None
            update_keys = dict(registration_id=keys['registration_id'])
            for key in update_fields:
                if key in keys:
                    update_keys[key] = keys[key]
            user.update_record(**update_keys)
        elif checks:
            if create_user is False:
                # Remove current open session a send message
                self.logout(next=None, onlogout=None, log=None)
                raise HTTP(403, "Forbidden. User need to be created first.")

            if 'first_name' not in keys and 'first_name' in table_user.fields:
                guess = keys.get('email', 'anonymous').split('@')[0]
                keys['first_name'] = keys.get('username', guess)
            vars = table_user._filter_fields(keys)
            user_id = table_user.insert(**vars)
            user = table_user[user_id]
            if self.settings.create_user_groups:
                group_id = self.add_group(self.settings.create_user_groups % user)
                self.add_membership(group_id, user_id)
            if self.settings.everybody_group_id:
                self.add_membership(self.settings.everybody_group_id, user_id)
            if login:
                self.user = user
            if self.settings.register_onaccept:
                callback(self.settings.register_onaccept, Storage(vars=user))
        return user

    def basic(self, basic_auth_realm=False):
        """
        Performs basic login.

        Args:
            basic_auth_realm: optional basic http authentication realm. Can take
                str or unicode or function or callable or boolean.

        reads current.request.env.http_authorization
        and returns basic_allowed,basic_accepted,user.

        if basic_auth_realm is defined is a callable it's return value
        is used to set the basic authentication realm, if it's a string
        its content is used instead.  Otherwise basic authentication realm
        is set to the application name.
        If basic_auth_realm is None or False (the default) the behavior
        is to skip sending any challenge.

        """
        if not self.settings.allow_basic_login:
            return (False, False, False)
        basic = current.request.env.http_authorization
        if basic_auth_realm:
            if callable(basic_auth_realm):
                basic_auth_realm = basic_auth_realm()
            elif isinstance(basic_auth_realm, (unicode, str)):
                basic_realm = unicode(basic_auth_realm)  # Warning python 3.5 does not have method unicod
            elif basic_auth_realm is True:
                basic_realm = u'' + current.request.application
            http_401 = HTTP(401, u'Not Authorized', **{'WWW-Authenticate': u'Basic realm="' + basic_realm + '"'})
        if not basic or not basic[:6].lower() == 'basic ':
            if basic_auth_realm:
                raise http_401
            return (True, False, False)
        (username, sep, password) = base64.b64decode(basic[6:]).partition(':')
        is_valid_user = sep and self.login_bare(username, password)
        if not is_valid_user and basic_auth_realm:
            raise http_401
        return (True, True, is_valid_user)

    def _get_login_settings(self):
        table_user = self.table_user()
        userfield = self.settings.login_userfield or 'username' \
            if self.settings.login_userfield or 'username' \
            in table_user.fields else 'email'
        passfield = self.settings.password_field
        return Storage({'table_user': table_user,
                        'userfield': userfield,
                        'passfield': passfield})

    def login_bare(self, username, password):
        """
        Logins user as specified by username (or email) and password
        """
        settings = self._get_login_settings()
        user = settings.table_user(**{settings.userfield: username})
        if user and user.get(settings.passfield, False):
            password = settings.table_user[
                settings.passfield].validate(password)[0]
            if ((user.registration_key is None or
                 not user.registration_key.strip()) and
                    password == user[settings.passfield]):
                self.login_user(user)
                return user
        else:
            # user not in database try other login methods
            for login_method in self.settings.login_methods:
                if login_method != self and login_method(username, password):
                    self.user = user
                    return user
        return False

    def register_bare(self, **fields):
        """
        Registers a user as specified by username (or email)
        and a raw password.
        """
        settings = self._get_login_settings()
        # users can register_bare even if no password is provided,
        # in this case they will have to reset their password to login
        if fields.get(settings.passfield):
            fields[settings.passfield] = \
                settings.table_user[settings.passfield].validate(fields[settings.passfield])[0]
        if not fields.get(settings.userfield):
            raise ValueError('register_bare: userfield not provided or invalid')
        user = self.get_or_create_user(fields, login=False, get=False,
                                       update_fields=self.settings.update_fields)
        if not user:
            # get or create did not create a user (it ignores duplicate records)
            return False
        return user

    def cas_login(self,
                  next=DEFAULT,
                  onvalidation=DEFAULT,
                  onaccept=DEFAULT,
                  log=DEFAULT,
                  version=2,
                  ):
        request = current.request
        response = current.response
        session = current.session
        db, table = self.db, self.table_cas()
        session._cas_service = request.vars.service or session._cas_service
        if request.env.http_host not in self.settings.cas_domains or \
                not session._cas_service:
            raise HTTP(403, 'not authorized')

        def allow_access(interactivelogin=False):
            row = table(service=session._cas_service, user_id=self.user.id)
            if row:
                ticket = row.ticket
            else:
                ticket = 'ST-' + web2py_uuid()
                table.insert(service=session._cas_service,
                             user_id=self.user.id,
                             ticket=ticket,
                             created_on=request.now,
                             renew=interactivelogin)
            service = session._cas_service
            query_sep = '&' if '?' in service else '?'
            del session._cas_service
            if 'warn' in request.vars and not interactivelogin:
                response.headers[
                    'refresh'] = "5;URL=%s" % service + query_sep + "ticket=" + ticket
                return A("Continue to %s" % service,
                         _href=service + query_sep + "ticket=" + ticket)
            else:
                redirect(service + query_sep + "ticket=" + ticket)
        if self.is_logged_in() and 'renew' not in request.vars:
            return allow_access()
        elif not self.is_logged_in() and 'gateway' in request.vars:
            redirect(session._cas_service)

        def cas_onaccept(form, onaccept=onaccept):
            if onaccept is not DEFAULT:
                onaccept(form)
            return allow_access(interactivelogin=True)
        return self.login(next, onvalidation, cas_onaccept, log)

    def cas_validate(self, version=2, proxy=False):
        request = current.request
        db, table = self.db, self.table_cas()
        current.response.headers['Content-Type'] = 'text'
        ticket = request.vars.ticket
        renew = 'renew' in request.vars
        row = table(ticket=ticket)
        success = False
        if row:
            userfield = self.settings.login_userfield or 'username' \
                if 'username' in table.fields else 'email'
            # If ticket is a service Ticket and RENEW flag respected
            if ticket[0:3] == 'ST-' and \
                    not ((row.renew and renew) ^ renew):
                user = self.table_user()(row.user_id)
                row.delete_record()
                success = True

        def build_response(body):
            xml_body = to_native(TAG['cas:serviceResponse'](
                    body, **{'_xmlns:cas': 'http://www.yale.edu/tp/cas'}).xml())
            return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_body
        if success:
            if version == 1:
                message = 'yes\n%s' % user[userfield]
            elif version == 3:
                username = user.get('username', user[userfield])
                message = build_response(
                    TAG['cas:authenticationSuccess'](
                        TAG['cas:user'](username),
                        TAG['cas:attributes'](
                            *[TAG['cas:' + field.name](user[field.name])
                              for field in self.table_user()
                              if field.readable])))
            else:  # assume version 2
                username = user.get('username', user[userfield])
                message = build_response(
                    TAG['cas:authenticationSuccess'](
                        TAG['cas:user'](username),
                        *[TAG['cas:' + field.name](user[field.name])
                          for field in self.table_user()
                          if field.readable]))
        else:
            if version == 1:
                message = 'no\n'
            elif row:
                message = build_response(TAG['cas:authenticationFailure']())
            else:
                message = build_response(
                    TAG['cas:authenticationFailure'](
                        'Ticket %s not recognized' % ticket,
                        _code='INVALID TICKET'))
        raise HTTP(200, message)

    def _reset_two_factor_auth(self, session):
        """
        When two-step authentication is enabled, this function is used to
        clear the session after successfully completing second challenge
        or when the maximum number of tries allowed has expired.
        """
        session.auth_two_factor_user = None
        session.auth_two_factor = None
        session.auth_two_factor_enabled = False
        # Set the number of attempts. It should be more than 1.
        session.auth_two_factor_tries_left = self.settings.auth_two_factor_tries_left

    def when_is_logged_in_bypass_next_in_url(self, next, session):
        """
        This function should be use when someone want to avoid asking for user
        credentials when loaded page contains "user/login?_next=NEXT_COMPONENT"
        in the URL is refresh but user is already authenticated.
        """
        if self.is_logged_in():
            if next == session._auth_next:
                del session._auth_next
            redirect(next, client_side=self.settings.client_side)

    def login(self,
              next=DEFAULT,
              onvalidation=DEFAULT,
              onaccept=DEFAULT,
              log=DEFAULT,
              ):
        """
        Returns a login form
        """
        settings = self.settings
        request = current.request
        response = current.response
        session = current.session

        # use session for federated login
        snext = self.get_vars_next()

        if snext:
            session._auth_next = snext
        elif session._auth_next:
            snext = session._auth_next
        # pass

        if next is DEFAULT:
            # important for security
            next = settings.login_next
            if callable(next):
                next = next()
            user_next = snext
            if user_next:
                external = user_next.split('://')
                if external[0].lower() in ['http', 'https', 'ftp']:
                    host_next = user_next.split('//', 1)[-1].split('/')[0]
                    if host_next in settings.cas_domains:
                        next = user_next
                else:
                    next = user_next
                    # Avoid asking unnecessary user credentials when user is logged in
                    self.when_is_logged_in_bypass_next_in_url(next=next, session=session)

        # Moved here to avoid unnecessary execution in case of redirection to next in case of logged in user
        table_user = self.table_user()
        if 'username' in table_user.fields or \
                not settings.login_email_validate:
            tmpvalidator = IS_NOT_EMPTY(error_message=self.messages.is_empty)
            if not settings.username_case_sensitive:
                tmpvalidator = [IS_LOWER(), tmpvalidator]
        else:
            tmpvalidator = IS_EMAIL(error_message=self.messages.invalid_email)
            if not settings.email_case_sensitive:
                tmpvalidator = [IS_LOWER(), tmpvalidator]

        passfield = settings.password_field
        try:
            table_user[passfield].requires[-1].min_length = 0
        except:
            pass

        if onvalidation is DEFAULT:
            onvalidation = settings.login_onvalidation
        if onaccept is DEFAULT:
            onaccept = settings.login_onaccept
        if log is DEFAULT:
            log = self.messages['login_log']

        onfail = settings.login_onfail

        user = None  # default

        # Setup the default field used for the form
        multi_login = False
        if self.settings.login_userfield:
            username = self.settings.login_userfield
        else:
            if 'username' in table_user.fields:
                username = 'username'
            else:
                username = 'email'
            if self.settings.multi_login:
                multi_login = True
        old_requires = table_user[username].requires
        table_user[username].requires = tmpvalidator

        # If two-factor authentication is enabled, and the maximum
        # number of tries allowed is used up, reset the session to
        # pre-login state with two-factor auth
        if session.auth_two_factor_enabled and session.auth_two_factor_tries_left < 1:
            # Exceeded maximum allowed tries for this code. Require user to enter
            # username and password again.
            user = None
            accepted_form = False
            self._reset_two_factor_auth(session)
            # Redirect to the default 'next' page without logging
            # in. If that page requires login, user will be redirected
            # back to the main login form
            redirect(next, client_side=settings.client_side)

        # Before showing the default login form, check whether
        # we are already on the second step of two-step authentication.
        # If we are, then skip this login form and use the form for the
        # second challenge instead.
        # Note to devs: The code inside the if-block is unchanged from the
        # previous version of this file, other than for indentation inside
        # to put it inside the if-block
        if session.auth_two_factor_user is None:

            if settings.remember_me_form:
                extra_fields = [
                    Field('remember_me', 'boolean', default=False,
                          label=self.messages.label_remember_me)]
            else:
                extra_fields = []

            # do we use our own login form, or from a central source?
            if settings.login_form == self:
                form = SQLFORM(table_user,
                               fields=[username, passfield],
                               hidden=dict(_next=next),
                               showid=settings.showid,
                               submit_button=self.messages.login_button,
                               delete_label=self.messages.delete_label,
                               formstyle=settings.formstyle,
                               separator=settings.label_separator,
                               extra_fields=extra_fields,
                               )

                captcha = settings.login_captcha or \
                    (settings.login_captcha is not False and settings.captcha)
                if captcha:
                    addrow(form, captcha.label, captcha, captcha.comment,
                           settings.formstyle, 'captcha__row')
                accepted_form = False

                if form.accepts(request, session if self.csrf_prevention else None,
                                formname='login', dbio=False,
                                onvalidation=onvalidation,
                                hideerror=settings.hideerror):

                    accepted_form = True
                    # check for username in db
                    entered_username = form.vars[username]
                    if multi_login and '@' in entered_username:
                        # if '@' in username check for email, not username
                        user = table_user(email=entered_username)
                    else:
                        user = table_user(**{username: entered_username})
                    if user:
                        # user in db, check if registration pending or disabled
                        temp_user = user
                        if (temp_user.registration_key or '').startswith('pending'):
                            response.flash = self.messages.registration_pending
                            return form
                        elif temp_user.registration_key in ('disabled', 'blocked'):
                            response.flash = self.messages.login_disabled
                            return form
                        elif (temp_user.registration_key is not None and temp_user.registration_key.strip()):
                            response.flash = \
                                self.messages.registration_verifying
                            return form
                        # try alternate logins 1st as these have the
                        # current version of the password
                        user = None
                        for login_method in settings.login_methods:
                            if login_method != self and \
                                    login_method(request.vars[username],
                                                 request.vars[passfield]):
                                if self not in settings.login_methods:
                                    # do not store password in db
                                    form.vars[passfield] = None
                                user = self.get_or_create_user(
                                    form.vars, settings.update_fields)
                                break
                        if not user:
                            # alternates have failed, maybe because service inaccessible
                            if settings.login_methods[0] == self:
                                # try logging in locally using cached credentials
                                if form.vars.get(passfield, '') == temp_user[passfield]:
                                    # success
                                    user = temp_user
                    else:
                        # user not in db
                        if not settings.alternate_requires_registration:
                            # we're allowed to auto-register users from external systems
                            for login_method in settings.login_methods:
                                if login_method != self and \
                                        login_method(request.vars[username],
                                                     request.vars[passfield]):
                                    if self not in settings.login_methods:
                                        # do not store password in db
                                        form.vars[passfield] = None
                                    user = self.get_or_create_user(
                                        form.vars, settings.update_fields)
                                    break
                    if not user:
                        self.log_event(self.messages['login_failed_log'],
                                       request.post_vars)
                        # invalid login
                        session.flash = self.messages.invalid_login
                        callback(onfail, None)
                        redirect(
                            self.url(args=request.args, vars=request.get_vars),
                            client_side=settings.client_side)

            else:  # use a central authentication server
                cas = settings.login_form
                cas_user = cas.get_user()

                if cas_user:
                    cas_user[passfield] = None
                    user = self.get_or_create_user(
                        table_user._filter_fields(cas_user),
                        settings.update_fields)
                elif hasattr(cas, 'login_form'):
                    return cas.login_form()
                else:
                    # we need to pass through login again before going on
                    next = self.url(settings.function, args='login')
                    redirect(cas.login_url(next),
                             client_side=settings.client_side)

        # Extra login logic for two-factor authentication
        #################################################
        # If the 'user' variable has a value, this means that the first
        # authentication step was successful (i.e. user provided correct
        # username and password at the first challenge).
        # Check if this user is signed up for two-factor authentication
        # If auth.settings.auth_two_factor_enabled it will enable two factor
        # for all the app. Another way to anble two factor is that the user
        # must be part of a group that is called auth.settings.two_factor_authentication_group
        if user and self.settings.auth_two_factor_enabled is True:
            session.auth_two_factor_enabled = True
        elif user and self.settings.two_factor_authentication_group:
            role = self.settings.two_factor_authentication_group
            session.auth_two_factor_enabled = self.has_membership(user_id=user.id, role=role)
        # challenge
        if session.auth_two_factor_enabled:
            form = SQLFORM.factory(
                Field('authentication_code',
                      label=self.messages.label_two_factor,
                      required=True,
                      comment=self.messages.two_factor_comment),
                hidden=dict(_next=next),
                formstyle=settings.formstyle,
                separator=settings.label_separator
            )
            # accepted_form is used by some default web2py code later in the
            # function that handles running specified functions before redirect
            # Set it to False until the challenge form is accepted.
            accepted_form = False
            # Handle the case when a user has submitted the login/password
            # form successfully, and the password has been validated, but
            # the two-factor form has not been displayed or validated yet.
            if session.auth_two_factor_user is None and user is not None:
                session.auth_two_factor_user = user  # store the validated user and associate with this session
                session.auth_two_factor = random.randint(100000, 999999)
                session.auth_two_factor_tries_left = self.settings.auth_two_factor_tries_left
                # Set the way we generate the code or we send the code. For example using SMS...
                two_factor_methods = self.settings.two_factor_methods

                if not two_factor_methods:
                    # TODO: Add some error checking to handle cases where email cannot be sent
                    self.settings.mailer.send(
                        to=user.email,
                        subject=self.messages.retrieve_two_factor_code_subject,
                        message=self.messages.retrieve_two_factor_code.format(session.auth_two_factor))
                else:
                    # Check for all method. It is possible to have multiples
                    for two_factor_method in two_factor_methods:
                        try:
                            # By default we use session.auth_two_factor generated before.
                            session.auth_two_factor = two_factor_method(user, session.auth_two_factor)
                        except:
                            pass
                        else:
                            break

            if form.accepts(request, session if self.csrf_prevention else None,
                            formname='login', dbio=False,
                            onvalidation=onvalidation,
                            hideerror=settings.hideerror):
                accepted_form = True

                """
                The lists is executed after form validation for each of the corresponding action.
                For example, in your model:

                In your models copy and paste:

                # Before define tables, we add some extra field to auth_user
                auth.settings.extra_fields['auth_user'] = [
                    Field('motp_secret', 'password', length=512, default='', label='MOTP Secret'),
                    Field('motp_pin', 'string', length=128, default='', label='MOTP PIN')]

                OFFSET = 60  # Be sure is the same in your OTP Client

                # Set session.auth_two_factor to None. Because the code is generated by external app.
                # This will avoid to use the default setting and send a code by email.
                def _set_two_factor(user, auth_two_factor):
                    return None

                def verify_otp(user, otp):
                    import time
                    from hashlib import md5
                    epoch_time = int(time.time())
                    time_start = int(str(epoch_time - OFFSET)[:-1])
                    time_end = int(str(epoch_time + OFFSET)[:-1])
                    for t in range(time_start - 1, time_end + 1):
                        to_hash = str(t) + user.motp_secret + user.motp_pin
                        hash = md5(to_hash).hexdigest()[:6]
                        if otp == hash:
                        return hash

                auth.settings.auth_two_factor_enabled = True
                auth.messages.two_factor_comment = "Verify your OTP Client for the code."
                auth.settings.two_factor_methods = [lambda user,
                                                           auth_two_factor: _set_two_factor(user, auth_two_factor)]
                auth.settings.two_factor_onvalidation = [lambda user, otp: verify_otp(user, otp)]

                """
                if self.settings.two_factor_onvalidation:

                    for two_factor_onvalidation in self.settings.two_factor_onvalidation:
                        try:
                            session.auth_two_factor = \
                                two_factor_onvalidation(session.auth_two_factor_user, form.vars['authentication_code'])
                        except:
                            pass
                        else:
                            break

                if form.vars['authentication_code'] == str(session.auth_two_factor):
                    # Handle the case when the two-factor form has been successfully validated
                    # and the user was previously stored (the current user should be None because
                    # in this case, the previous username/password login form should not be displayed.
                    # This will allow the code after the 2-factor authentication block to proceed as
                    # normal.
                    if user is None or user == session.auth_two_factor_user:
                        user = session.auth_two_factor_user
                    # For security, because the username stored in the
                    # session somehow does not match the just validated
                    # user. Should not be possible without session stealing
                    # which is hard with SSL.
                    elif user != session.auth_two_factor_user:
                        user = None
                    # Either way, the user and code associated with this session should
                    # be removed. This handles cases where the session login may have
                    # expired but browser window is open, so the old session key and
                    # session usernamem will still exist
                    self._reset_two_factor_auth(session)
                else:
                    session.auth_two_factor_tries_left -= 1
                    # If the number of retries are higher than auth_two_factor_tries_left
                    # Require user to enter username and password again.
                    if session.auth_two_factor_enabled and session.auth_two_factor_tries_left < 1:
                        # Exceeded maximum allowed tries for this code. Require user to enter
                        # username and password again.
                        user = None
                        accepted_form = False
                        self._reset_two_factor_auth(session)
                        # Redirect to the default 'next' page without logging
                        # in. If that page requires login, user will be redirected
                        # back to the main login form
                        redirect(next, client_side=settings.client_side)
                    response.flash = self.messages.invalid_two_factor_code.format(session.auth_two_factor_tries_left)
                    return form
            else:
                return form
        # End login logic for two-factor authentication

        # process authenticated users
        if user:
            user = Row(table_user._filter_fields(user, id=True))
            # process authenticated users
            # user wants to be logged in for longer
            self.login_user(user)
            session.auth.expiration = \
                request.post_vars.remember_me and \
                settings.long_expiration or \
                settings.expiration
            session.auth.remember_me = 'remember_me' in request.post_vars
            self.log_event(log, user)
            session.flash = self.messages.logged_in

        # how to continue
        if settings.login_form == self:
            if accepted_form:
                callback(onaccept, form)
                if next == session._auth_next:
                    session._auth_next = None
                next = replace_id(next, form)
                redirect(next, client_side=settings.client_side)

            table_user[username].requires = old_requires
            return form
        elif user:
            callback(onaccept, None)

        if next == session._auth_next:
            del session._auth_next
        redirect(next, client_side=settings.client_side)

    def logout(self, next=DEFAULT, onlogout=DEFAULT, log=DEFAULT):
        """
        Logouts and redirects to login
        """

        # Clear out 2-step authentication information if user logs
        # out. This information is also cleared on successful login.
        self._reset_two_factor_auth(current.session)

        if next is DEFAULT:
            next = self.get_vars_next() or self.settings.logout_next
        if onlogout is DEFAULT:
            onlogout = self.settings.logout_onlogout
        if onlogout:
            onlogout(self.user)
        if log is DEFAULT:
            log = self.messages['logout_log']
        if self.user:
            self.log_event(log, self.user)
        if self.settings.login_form != self:
            cas = self.settings.login_form
            cas_user = cas.get_user()
            if cas_user:
                next = cas.logout_url(next)

        current.session.auth = None
        self.user = None
        if self.settings.renew_session_onlogout:
            current.session.renew(clear_session=not self.settings.keep_session_onlogout)
        current.session.flash = self.messages.logged_out
        if next is not None:
            redirect(next)

    def logout_bare(self):
        self.logout(next=None, onlogout=None, log=None)

    def register(self,
                 next=DEFAULT,
                 onvalidation=DEFAULT,
                 onaccept=DEFAULT,
                 log=DEFAULT,
                 ):
        """
        Returns a registration form
        """

        table_user = self.table_user()
        request = current.request
        response = current.response
        session = current.session
        if self.is_logged_in():
            redirect(self.settings.logged_url,
                     client_side=self.settings.client_side)
        if next is DEFAULT:
            next = self.get_vars_next() or self.settings.register_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.register_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.register_onaccept
        if log is DEFAULT:
            log = self.messages['register_log']

        table_user = self.table_user()
        if self.settings.login_userfield:
            username = self.settings.login_userfield
        elif 'username' in table_user.fields:
            username = 'username'
        else:
            username = 'email'

        # Ensure the username field is unique.
        unique_validator = IS_NOT_IN_DB(self.db, table_user[username])
        if not table_user[username].requires:
            table_user[username].requires = unique_validator
        elif isinstance(table_user[username].requires, (list, tuple)):
            if not any([isinstance(validator, IS_NOT_IN_DB) for validator in
                        table_user[username].requires]):
                if isinstance(table_user[username].requires, list):
                    table_user[username].requires.append(unique_validator)
                else:
                    table_user[username].requires += (unique_validator, )
        elif not isinstance(table_user[username].requires, IS_NOT_IN_DB):
            table_user[username].requires = [table_user[username].requires,
                                             unique_validator]

        passfield = self.settings.password_field
        formstyle = self.settings.formstyle
        try:  # Make sure we have our original minimum length as other auth forms change it
            table_user[passfield].requires[-1].min_length = self.settings.password_min_length
        except:
            pass

        if self.settings.register_verify_password:
            if self.settings.register_fields is None:
                self.settings.register_fields = [f.name for f in table_user if f.writable and not f.compute]
                k = self.settings.register_fields.index(passfield)
                self.settings.register_fields.insert(k + 1, "password_two")
            extra_fields = [
                Field("password_two", "password",
                      requires=IS_EQUAL_TO(request.post_vars.get(passfield, None),
                                           error_message=self.messages.mismatched_password),
                      label=current.T("Confirm Password"))]
        else:
            extra_fields = []
        form = SQLFORM(table_user,
                       fields=self.settings.register_fields,
                       hidden=dict(_next=next),
                       showid=self.settings.showid,
                       submit_button=self.messages.register_button,
                       delete_label=self.messages.delete_label,
                       formstyle=formstyle,
                       separator=self.settings.label_separator,
                       extra_fields=extra_fields
                       )

        captcha = self.settings.register_captcha or self.settings.captcha
        if captcha:
            addrow(form, captcha.label, captcha,
                   captcha.comment, self.settings.formstyle, 'captcha__row')

        # Add a message if specified
        if self.settings.pre_registration_div:
            addrow(form, '',
                   DIV(_id="pre-reg", *self.settings.pre_registration_div),
                   '', formstyle, '')

        key = web2py_uuid()
        if self.settings.registration_requires_approval:
            key = 'pending-' + key

        table_user.registration_key.default = key
        if form.accepts(request, session if self.csrf_prevention else None,
                        formname='register',
                        onvalidation=onvalidation,
                        hideerror=self.settings.hideerror):
            description = self.messages.group_description % form.vars
            if self.settings.create_user_groups:
                group_id = self.add_group(self.settings.create_user_groups % form.vars, description)
                self.add_membership(group_id, form.vars.id)
            if self.settings.everybody_group_id:
                self.add_membership(self.settings.everybody_group_id, form.vars.id)
            if self.settings.registration_requires_verification:
                link = self.url(
                    self.settings.function, args=('verify_email', key), scheme=True)
                d = dict(form.vars)
                d.update(dict(key=key, link=link, username=form.vars[username],
                              firstname=form.vars['firstname'],
                              lastname=form.vars['lastname']))
                if not (self.settings.mailer and self.settings.mailer.send(
                        to=form.vars.email,
                        subject=self.messages.verify_email_subject,
                        message=self.messages.verify_email % d)):
                    self.db.rollback()
                    response.flash = self.messages.unable_send_email
                    return form
                session.flash = self.messages.email_sent
            if self.settings.registration_requires_approval and \
               not self.settings.registration_requires_verification:
                table_user[form.vars.id] = dict(registration_key='pending')
                session.flash = self.messages.registration_pending
            elif (not self.settings.registration_requires_verification or self.settings.login_after_registration):
                if not self.settings.registration_requires_verification:
                    table_user[form.vars.id] = dict(registration_key='')
                session.flash = self.messages.registration_successful
                user = table_user(**{username: form.vars[username]})
                self.login_user(user)
                session.flash = self.messages.logged_in
            self.log_event(log, form.vars)
            callback(onaccept, form)
            if not next:
                next = self.url(args=request.args)
            else:
                next = replace_id(next, form)
            redirect(next, client_side=self.settings.client_side)

        return form

    def verify_email(self,
                     next=DEFAULT,
                     onaccept=DEFAULT,
                     log=DEFAULT,
                     ):
        """
        Action used to verify the registration email
        """

        key = getarg(-1)
        table_user = self.table_user()
        user = table_user(registration_key=key)
        if not user:
            redirect(self.settings.login_url)
        if self.settings.registration_requires_approval:
            user.update_record(registration_key='pending')
            current.session.flash = self.messages.registration_pending
        else:
            user.update_record(registration_key='')
            current.session.flash = self.messages.email_verified
        # make sure session has same user.registrato_key as db record
        if current.session.auth and current.session.auth.user:
            current.session.auth.user.registration_key = user.registration_key
        if log is DEFAULT:
            log = self.messages['verify_email_log']
        if next is DEFAULT:
            next = self.settings.verify_email_next
        if onaccept is DEFAULT:
            onaccept = self.settings.verify_email_onaccept
        self.log_event(log, user)
        callback(onaccept, user)
        redirect(next)

    def retrieve_username(self,
                          next=DEFAULT,
                          onvalidation=DEFAULT,
                          onaccept=DEFAULT,
                          log=DEFAULT,
                          ):
        """
        Returns a form to retrieve the user username
        (only if there is a username field)
        """

        table_user = self.table_user()
        if 'username' not in table_user.fields:
            raise HTTP(404)
        request = current.request
        response = current.response
        session = current.session
        captcha = self.settings.retrieve_username_captcha or \
            (self.settings.retrieve_username_captcha is not False and self.settings.captcha)
        if not self.settings.mailer:
            response.flash = self.messages.function_disabled
            return ''
        if next is DEFAULT:
            next = self.get_vars_next() or self.settings.retrieve_username_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.retrieve_username_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.retrieve_username_onaccept
        if log is DEFAULT:
            log = self.messages['retrieve_username_log']
        old_requires = table_user.email.requires
        table_user.email.requires = [IS_IN_DB(self.db, table_user.email,
                                              error_message=self.messages.invalid_email)]
        form = SQLFORM(table_user,
                       fields=['email'],
                       hidden=dict(_next=next),
                       showid=self.settings.showid,
                       submit_button=self.messages.submit_button,
                       delete_label=self.messages.delete_label,
                       formstyle=self.settings.formstyle,
                       separator=self.settings.label_separator
                       )
        if captcha:
            addrow(form, captcha.label, captcha,
                   captcha.comment, self.settings.formstyle, 'captcha__row')

        if form.accepts(request, session if self.csrf_prevention else None,
                        formname='retrieve_username', dbio=False,
                        onvalidation=onvalidation, hideerror=self.settings.hideerror):
            users = table_user._db(table_user.email == form.vars.email).select()
            if not users:
                current.session.flash = \
                    self.messages.invalid_email
                redirect(self.url(args=request.args))
            username = ', '.join(u.username for u in users)
            self.settings.mailer.send(to=form.vars.email,
                                      subject=self.messages.retrieve_username_subject,
                                      message=self.messages.retrieve_username % dict(username=username))
            session.flash = self.messages.email_sent
            for user in users:
                self.log_event(log, user)
            callback(onaccept, form)
            if not next:
                next = self.url(args=request.args)
            else:
                next = replace_id(next, form)
            redirect(next)
        table_user.email.requires = old_requires
        return form

    def random_password(self):
        import string
        import random
        password = ''
        specials = r'!#$*'
        for i in range(0, 3):
            password += random.choice(string.ascii_lowercase)
            password += random.choice(string.ascii_uppercase)
            password += random.choice(string.digits)
            password += random.choice(specials)
        return ''.join(random.sample(password, len(password)))

    def reset_password_deprecated(self,
                                  next=DEFAULT,
                                  onvalidation=DEFAULT,
                                  onaccept=DEFAULT,
                                  log=DEFAULT,
                                  ):
        """
        Returns a form to reset the user password (deprecated)
        """

        table_user = self.table_user()
        request = current.request
        response = current.response
        session = current.session
        if not self.settings.mailer:
            response.flash = self.messages.function_disabled
            return ''
        if next is DEFAULT:
            next = self.get_vars_next() or self.settings.retrieve_password_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.retrieve_password_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.retrieve_password_onaccept
        if log is DEFAULT:
            log = self.messages['retrieve_password_log']
        old_requires = table_user.email.requires
        table_user.email.requires = [IS_IN_DB(self.db, table_user.email,
                                              error_message=self.messages.invalid_email)]
        form = SQLFORM(table_user,
                       fields=['email'],
                       hidden=dict(_next=next),
                       showid=self.settings.showid,
                       submit_button=self.messages.submit_button,
                       delete_label=self.messages.delete_label,
                       formstyle=self.settings.formstyle,
                       separator=self.settings.label_separator
                       )
        if form.accepts(request, session if self.csrf_prevention else None,
                        formname='retrieve_password', dbio=False,
                        onvalidation=onvalidation, hideerror=self.settings.hideerror):
            user = table_user(email=form.vars.email)
            key = user.registration_key
            if not user:
                current.session.flash = \
                    self.messages.invalid_email
                redirect(self.url(args=request.args))
            elif key in ('pending', 'disabled', 'blocked') or (key or '').startswith('pending'):
                current.session.flash = \
                    self.messages.registration_pending
                redirect(self.url(args=request.args))
            password = self.random_password()
            passfield = self.settings.password_field
            d = {
                passfield: str(table_user[passfield].validate(password)[0]),
                'registration_key': ''
            }
            user.update_record(**d)
            if self.settings.mailer and \
               self.settings.mailer.send(to=form.vars.email,
                                         subject=self.messages.retrieve_password_subject,
                                         message=self.messages.retrieve_password % dict(password=password)):
                session.flash = self.messages.email_sent
            else:
                session.flash = self.messages.unable_send_email
            self.log_event(log, user)
            callback(onaccept, form)
            if not next:
                next = self.url(args=request.args)
            else:
                next = replace_id(next, form)
            redirect(next)
        table_user.email.requires = old_requires
        return form

    def confirm_registration(self,
                             next=DEFAULT,
                             onvalidation=DEFAULT,
                             onaccept=DEFAULT,
                             log=DEFAULT,
                             ):
        """
        Returns a form to confirm user registration
        """

        table_user = self.table_user()
        request = current.request
        # response = current.response
        session = current.session

        if next is DEFAULT:
            next = self.get_vars_next() or self.settings.reset_password_next

        if self.settings.prevent_password_reset_attacks:
            key = request.vars.key
            if not key and len(request.args) > 1:
                key = request.args[-1]
            if key:
                session._reset_password_key = key
                if next:
                    redirect_vars = {'_next': next}
                else:
                    redirect_vars = {}
                redirect(self.url(args='confirm_registration',
                                  vars=redirect_vars))
            else:
                key = session._reset_password_key
        else:
            key = request.vars.key or getarg(-1)
        try:
            t0 = int(key.split('-')[0])
            if time.time() - t0 > 60 * 60 * 24:
                raise Exception
            user = table_user(reset_password_key=key)
            if not user:
                raise Exception
        except Exception as e:
            session.flash = self.messages.invalid_reset_password
            redirect(next, client_side=self.settings.client_side)
        passfield = self.settings.password_field
        form = SQLFORM.factory(
            Field('first_name',
                  label='First Name',
                  required=True),
            Field('last_name',
                  label='Last Name',
                  required=True),
            Field('new_password', 'password',
                  label=self.messages.new_password,
                  requires=self.table_user()[passfield].requires),
            Field('new_password2', 'password',
                  label=self.messages.verify_password,
                  requires=[IS_EXPR('value==%s' % repr(request.vars.new_password),
                                    self.messages.mismatched_password)]),
            submit_button='Confirm Registration',
            hidden=dict(_next=next),
            formstyle=self.settings.formstyle,
            separator=self.settings.label_separator
        )
        if form.process().accepted:
            user.update_record(
                **{passfield: str(form.vars.new_password),
                   'first_name': str(form.vars.first_name),
                   'last_name': str(form.vars.last_name),
                   'registration_key': '',
                   'reset_password_key': ''})
            session.flash = self.messages.password_changed
            if self.settings.login_after_password_change:
                self.login_user(user)
            redirect(next, client_side=self.settings.client_side)
        return form

    def email_registration(self, subject, body, user):
        """
        Sends and email invitation to a user informing they have been registered with the application
        """
        reset_password_key = str(int(time.time())) + '-' + web2py_uuid()
        link = self.url(self.settings.function,
                        args=('confirm_registration',), vars={'key': reset_password_key},
                        scheme=True)
        d = dict(user)
        d.update(dict(key=reset_password_key, link=link, site=current.request.env.http_host))
        if self.settings.mailer and self.settings.mailer.send(
            to=user.email,
            subject=subject % d,
                message=body % d):
            user.update_record(reset_password_key=reset_password_key)
            return True
        return False

    def bulk_register(self, max_emails=100):
        """
        Creates a form for ther user to send invites to other users to join
        """
        if not self.user:
            redirect(self.settings.login_url)
        if not self.settings.bulk_register_enabled:
            return HTTP(404)

        form = SQLFORM.factory(
            Field('subject', 'string', default=self.messages.bulk_invite_subject, requires=IS_NOT_EMPTY()),
            Field('emails', 'text', requires=IS_NOT_EMPTY()),
            Field('message', 'text', default=self.messages.bulk_invite_body, requires=IS_NOT_EMPTY()),
            formstyle=self.settings.formstyle)

        if form.process().accepted:
            emails = re.compile('[^\s\'"@<>,;:]+\@[^\s\'"@<>,;:]+').findall(form.vars.emails)
            # send the invitations
            emails_sent = []
            emails_fail = []
            emails_exist = []
            for email in emails[:max_emails]:
                if self.table_user()(email=email):
                    emails_exist.append(email)
                else:
                    user = self.register_bare(email=email)
                    if self.email_registration(form.vars.subject, form.vars.message, user):
                        emails_sent.append(email)
                    else:
                        emails_fail.append(email)
            emails_fail += emails[max_emails:]
            form = DIV(H4('Emails sent'), UL(*[A(x, _href='mailto:' + x) for x in emails_sent]),
                       H4('Emails failed'), UL(*[A(x, _href='mailto:' + x) for x in emails_fail]),
                       H4('Emails existing'), UL(*[A(x, _href='mailto:' + x) for x in emails_exist]))
        return form

    def manage_tokens(self):
        if not self.user:
            redirect(self.settings.login_url)
        table_token = self.table_token()
        table_token.user_id.writable = False
        table_token.user_id.default = self.user.id
        table_token.token.writable = False
        if current.request.args(1) == 'new':
            table_token.token.readable = False
        form = SQLFORM.grid(table_token, args=['manage_tokens'])
        return form

    def reset_password(self,
                       next=DEFAULT,
                       onvalidation=DEFAULT,
                       onaccept=DEFAULT,
                       log=DEFAULT,
                       ):
        """
        Returns a form to reset the user password
        """

        table_user = self.table_user()
        request = current.request
        # response = current.response
        session = current.session

        if next is DEFAULT:
            next = self.get_vars_next() or self.settings.reset_password_next

        if self.settings.prevent_password_reset_attacks:
            key = request.vars.key
            if key:
                session._reset_password_key = key
                redirect(self.url(args='reset_password'))
            else:
                key = session._reset_password_key
        else:
            key = request.vars.key
        try:
            t0 = int(key.split('-')[0])
            if time.time() - t0 > 60 * 60 * 24:
                raise Exception
            user = table_user(reset_password_key=key)
            if not user:
                raise Exception
        except Exception:
            session.flash = self.messages.invalid_reset_password
            redirect(next, client_side=self.settings.client_side)

        key = user.registration_key
        if key in ('pending', 'disabled', 'blocked') or (key or '').startswith('pending'):
            session.flash = self.messages.registration_pending
            redirect(next, client_side=self.settings.client_side)

        if onvalidation is DEFAULT:
            onvalidation = self.settings.reset_password_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.reset_password_onaccept

        passfield = self.settings.password_field
        form = SQLFORM.factory(
            Field('new_password', 'password',
                  label=self.messages.new_password,
                  requires=self.table_user()[passfield].requires),
            Field('new_password2', 'password',
                  label=self.messages.verify_password,
                  requires=[IS_EXPR('value==%s' % repr(request.vars.new_password),
                                    self.messages.mismatched_password)]),
            submit_button=self.messages.password_reset_button,
            hidden=dict(_next=next),
            formstyle=self.settings.formstyle,
            separator=self.settings.label_separator
        )
        if form.accepts(request, session, onvalidation=onvalidation,
                        hideerror=self.settings.hideerror):
            user.update_record(
                **{passfield: str(form.vars.new_password),
                   'registration_key': '',
                   'reset_password_key': ''})
            session.flash = self.messages.password_changed
            if self.settings.login_after_password_change:
                self.login_user(user)
            callback(onaccept, form)
            redirect(next, client_side=self.settings.client_side)
        return form

    def request_reset_password(self,
                               next=DEFAULT,
                               onvalidation=DEFAULT,
                               onaccept=DEFAULT,
                               log=DEFAULT,
                               ):
        """
        Returns a form to reset the user password
        """
        table_user = self.table_user()
        request = current.request
        response = current.response
        session = current.session
        captcha = self.settings.retrieve_password_captcha or \
            (self.settings.retrieve_password_captcha is not False and self.settings.captcha)

        if next is DEFAULT:
            next = self.get_vars_next() or self.settings.request_reset_password_next
        if not self.settings.mailer:
            response.flash = self.messages.function_disabled
            return ''
        if onvalidation is DEFAULT:
            onvalidation = self.settings.request_reset_password_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.request_reset_password_onaccept
        if log is DEFAULT:
            log = self.messages['reset_password_log']
        userfield = self.settings.login_userfield or 'username' \
            if 'username' in table_user.fields else 'email'
        if userfield == 'email':
            table_user.email.requires = [
                IS_EMAIL(error_message=self.messages.invalid_email),
                IS_IN_DB(self.db, table_user.email,
                         error_message=self.messages.invalid_email)]
            if not self.settings.email_case_sensitive:
                table_user.email.requires.insert(0, IS_LOWER())
        else:
            table_user.username.requires = [
                IS_IN_DB(self.db, table_user.username,
                         error_message=self.messages.invalid_username)]
            if not self.settings.username_case_sensitive:
                table_user.username.requires.insert(0, IS_LOWER())

        form = SQLFORM(table_user,
                       fields=[userfield],
                       hidden=dict(_next=next),
                       showid=self.settings.showid,
                       submit_button=self.messages.password_reset_button,
                       delete_label=self.messages.delete_label,
                       formstyle=self.settings.formstyle,
                       separator=self.settings.label_separator
                       )
        if captcha:
            addrow(form, captcha.label, captcha,
                   captcha.comment, self.settings.formstyle, 'captcha__row')
        if form.accepts(request, session if self.csrf_prevention else None,
                        formname='reset_password', dbio=False,
                        onvalidation=onvalidation,
                        hideerror=self.settings.hideerror):
            user = table_user(**{userfield: form.vars.get(userfield)})
            key = user.registration_key
            if not user:
                session.flash = self.messages['invalid_%s' % userfield]
                redirect(self.url(args=request.args),
                         client_side=self.settings.client_side)
            elif key in ('pending', 'disabled', 'blocked') or (key or '').startswith('pending'):
                session.flash = self.messages.registration_pending
                redirect(self.url(args=request.args),
                         client_side=self.settings.client_side)
            if self.email_reset_password(user):
                session.flash = self.messages.email_sent
            else:
                session.flash = self.messages.unable_send_email
            self.log_event(log, user)
            callback(onaccept, form)
            if not next:
                next = self.url(args=request.args)
            else:
                next = replace_id(next, form)
            redirect(next, client_side=self.settings.client_side)
        # old_requires = table_user.email.requires
        return form

    def email_reset_password(self, user):
        reset_password_key = str(int(time.time())) + '-' + web2py_uuid()
        link = self.url(self.settings.function,
                        args=('reset_password',), vars={'key': reset_password_key},
                        scheme=True)
        d = dict(user)
        d.update(dict(key=reset_password_key, link=link))
        if self.settings.mailer and self.settings.mailer.send(
            to=user.email,
            subject=self.messages.reset_password_subject,
                message=self.messages.reset_password % d):
            user.update_record(reset_password_key=reset_password_key)
            return True
        return False

    def retrieve_password(self,
                          next=DEFAULT,
                          onvalidation=DEFAULT,
                          onaccept=DEFAULT,
                          log=DEFAULT,
                          ):
        if self.settings.reset_password_requires_verification:
            return self.request_reset_password(next, onvalidation, onaccept, log)
        else:
            return self.reset_password_deprecated(next, onvalidation, onaccept, log)

    def change_password(self,
                        next=DEFAULT,
                        onvalidation=DEFAULT,
                        onaccept=DEFAULT,
                        log=DEFAULT,
                        ):
        """
        Returns a form that lets the user change password
        """

        if not self.is_logged_in():
            redirect(self.settings.login_url,
                     client_side=self.settings.client_side)

        # Go to external link to change the password
        if self.settings.login_form != self:
            cas = self.settings.login_form
            # To prevent error if change_password_url function is not defined in alternate login
            if hasattr(cas, 'change_password_url'):
                next = cas.change_password_url(next)
                if next is not None:
                    redirect(next)

        db = self.db
        table_user = self.table_user()
        s = db(table_user.id == self.user.id)

        request = current.request
        session = current.session
        if next is DEFAULT:
            next = self.get_vars_next() or self.settings.change_password_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.change_password_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.change_password_onaccept
        if log is DEFAULT:
            log = self.messages['change_password_log']
        passfield = self.settings.password_field
        requires = table_user[passfield].requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        requires = list(filter(lambda t: isinstance(t, CRYPT), requires))
        if requires:
            requires[0] = CRYPT(**requires[0].__dict__) # Copy the existing CRYPT attributes
            requires[0].min_length = 0 # But do not enforce minimum length for the old password
        form = SQLFORM.factory(
            Field('old_password', 'password', requires=requires,
                  label=self.messages.old_password),
            Field('new_password', 'password',
                  label=self.messages.new_password,
                  requires=table_user[passfield].requires),
            Field('new_password2', 'password',
                  label=self.messages.verify_password,
                  requires=[IS_EXPR('value==%s' % repr(request.vars.new_password),
                                    self.messages.mismatched_password)]),
            submit_button=self.messages.password_change_button,
            hidden=dict(_next=next),
            formstyle=self.settings.formstyle,
            separator=self.settings.label_separator
        )
        if form.accepts(request, session,
                        formname='change_password',
                        onvalidation=onvalidation,
                        hideerror=self.settings.hideerror):

            current_user = s.select(limitby=(0, 1), orderby_on_limitby=False).first()
            if not form.vars['old_password'] == current_user[passfield]:
                form.errors['old_password'] = self.messages.invalid_password
            else:
                d = {passfield: str(form.vars.new_password)}
                s.update(**d)
                session.flash = self.messages.password_changed
                self.log_event(log, self.user)
                callback(onaccept, form)
                if not next:
                    next = self.url(args=request.args)
                else:
                    next = replace_id(next, form)
                redirect(next, client_side=self.settings.client_side)
        return form

    def profile(self,
                next=DEFAULT,
                onvalidation=DEFAULT,
                onaccept=DEFAULT,
                log=DEFAULT,
                ):
        """
        Returns a form that lets the user change his/her profile
        """

        table_user = self.table_user()
        if not self.is_logged_in():
            redirect(self.settings.login_url,
                     client_side=self.settings.client_side)
        passfield = self.settings.password_field
        table_user[passfield].writable = False
        table_user['email'].writable = False
        request = current.request
        session = current.session
        if next is DEFAULT:
            next = self.get_vars_next() or self.settings.profile_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.profile_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.profile_onaccept
        if log is DEFAULT:
            log = self.messages['profile_log']

        form = SQLFORM(
            table_user,
            self.user.id,
            fields=self.settings.profile_fields,
            hidden=dict(_next=next),
            showid=self.settings.showid,
            submit_button=self.messages.profile_save_button,
            delete_label=self.messages.delete_label,
            upload=self.settings.download_url,
            formstyle=self.settings.formstyle,
            separator=self.settings.label_separator,
            deletable=self.settings.allow_delete_accounts,
        )
        if form.accepts(request, session,
                        formname='profile',
                        onvalidation=onvalidation,
                        hideerror=self.settings.hideerror):
            extra_fields = self.settings.extra_fields.get(self.settings.table_user_name, [])
            if any(f.compute for f in extra_fields):
                user = table_user[self.user.id]
                self._update_session_user(user)
                self.update_groups()
            else:
                self.user.update(table_user._filter_fields(form.vars))
            session.flash = self.messages.profile_updated
            self.log_event(log, self.user)
            callback(onaccept, form)
            if form.deleted:
                return self.logout()
            if not next:
                next = self.url(args=request.args)
            else:
                next = replace_id(next, form)
            redirect(next, client_side=self.settings.client_side)
        return form

    def run_login_onaccept(self):
        onaccept = self.settings.login_onaccept
        if onaccept:
            form = Storage(dict(vars=self.user))
            if not isinstance(onaccept, (list, tuple)):
                onaccept = [onaccept]
            for callback in onaccept:
                callback(form)

    def jwt(self):
        """
        To use JWT authentication:
        1) instantiate auth with::

            auth = Auth(db, jwt = {'secret_key':'secret'})

        where 'secret' is your own secret string.

        2) Decorate functions that require login but should accept the JWT token credentials::

            @auth.allows_jwt()
            @auth.requires_login()
            def myapi(): return 'hello %s' % auth.user.email

        Notice jwt is allowed but not required. if user is logged in, myapi is accessible.

        3) Use it!

        Now API users can obtain a token with

            http://.../app/default/user/jwt?username=...&password=....

        (returns json object with a token attribute)
        API users can refresh an existing token with

            http://.../app/default/user/jwt?token=...

        they can authenticate themselves when calling http:/.../myapi by injecting a header

            Authorization: Bearer <the jwt token>

        Any additional attributes in the jwt argument of Auth() below::

           auth = Auth(db, jwt = {...})

        are passed to the constructor of class AuthJWT. Look there for documentation.
        """
        if not self.jwt_handler:
            raise HTTP(400, "Not authorized")
        else:
            rtn = self.jwt_handler.jwt_token_manager()
            raise HTTP(200, rtn, cookies=None, **current.response.headers)

    def is_impersonating(self):
        return self.is_logged_in() and 'impersonator' in current.session.auth

    def impersonate(self, user_id=DEFAULT):
        """
        To use this make a POST to
        `http://..../impersonate request.post_vars.user_id=<id>`

        Set request.post_vars.user_id to 0 to restore original user.

        requires impersonator is logged in and::

            has_permission('impersonate', 'auth_user', user_id)

        """
        request = current.request
        session = current.session
        auth = session.auth
        table_user = self.table_user()
        if not self.is_logged_in():
            raise HTTP(401, "Not Authorized")
        current_id = auth.user.id
        requested_id = user_id
        user = None
        if user_id is DEFAULT:
            user_id = current.request.post_vars.user_id
        if user_id and user_id != self.user.id and user_id != '0':
            if not self.has_permission('impersonate',
                                       self.table_user(),
                                       user_id):
                raise HTTP(403, "Forbidden")
            user = table_user(user_id)
            if not user:
                raise HTTP(401, "Not Authorized")
            auth.impersonator = pickle.dumps(session, pickle.HIGHEST_PROTOCOL)
            auth.user.update(
                table_user._filter_fields(user, True))
            self.user = auth.user
            self.update_groups()
            log = self.messages['impersonate_log']
            self.log_event(log, dict(id=current_id, other_id=auth.user.id))
            self.run_login_onaccept()
        elif user_id in (0, '0'):
            if self.is_impersonating():
                session.clear()
                session.update(pickle.loads(auth.impersonator))
                self.user = session.auth.user
                self.update_groups()
                self.run_login_onaccept()
            return None
        if requested_id is DEFAULT and not request.post_vars:
            return SQLFORM.factory(Field('user_id', 'integer'))
        elif not user:
            return None
        else:
            return SQLFORM(table_user, user.id, readonly=True)

    def groups(self):
        """
        Displays the groups and their roles for the logged in user
        """

        if not self.is_logged_in():
            redirect(self.settings.login_url)
        table_membership = self.table_membership()
        memberships = self.db(
            table_membership.user_id == self.user.id).select()
        table = TABLE()
        for membership in memberships:
            table_group = self.table_group()
            groups = self.db(table_group.id == membership.group_id).select()
            if groups:
                group = groups[0]
                table.append(TR(H3(group.role, '(%s)' % group.id)))
                table.append(TR(P(group.description)))
        if not memberships:
            return None
        return table

    def not_authorized(self):
        """
        You can change the view for this page to make it look as you like
        """
        if current.request.ajax:
            raise HTTP(403, 'ACCESS DENIED')
        return self.messages.access_denied

    def allows_jwt(self, otherwise=None):
        if not self.jwt_handler:
            raise HTTP(400, "Not authorized")
        else:
            return self.jwt_handler.allows_jwt(otherwise=otherwise)

    def requires(self, condition, requires_login=True, otherwise=None):
        """
        Decorator that prevents access to action if not logged in
        """

        def decorator(action):

            def f(*a, **b):

                basic_allowed, basic_accepted, user = self.basic()
                user = user or self.user
                login_required = requires_login
                if callable(login_required):
                    login_required = login_required()

                if login_required:
                    if not user:
                        if current.request.ajax:
                            raise HTTP(401, self.messages.ajax_failed_authentication)
                        elif otherwise is not None:
                            if callable(otherwise):
                                return otherwise()
                            redirect(otherwise)
                        elif self.settings.allow_basic_login_only or \
                                basic_accepted or current.request.is_restful:
                            raise HTTP(403, "Not authorized")
                        else:
                            next = self.here()
                            current.session.flash = current.response.flash
                            return call_or_redirect(self.settings.on_failed_authentication,
                                                    self.settings.login_url + '?_next=' + urllib_quote(next))

                if callable(condition):
                    flag = condition()
                else:
                    flag = condition
                if not flag:
                    current.session.flash = self.messages.access_denied
                    return call_or_redirect(
                        self.settings.on_failed_authorization)
                return action(*a, **b)
            f.__doc__ = action.__doc__
            f.__name__ = action.__name__
            f.__dict__.update(action.__dict__)
            return f

        return decorator

    def requires_login(self, otherwise=None):
        """
        Decorator that prevents access to action if not logged in
        """
        return self.requires(True, otherwise=otherwise)

    def requires_login_or_token(self, otherwise=None):
        if self.settings.enable_tokens is True:
            user = None
            request = current.request
            token = request.env.http_web2py_user_token or request.vars._token
            table_token = self.table_token()
            table_user = self.table_user()
            from gluon.settings import global_settings
            if global_settings.web2py_runtime_gae:
                row = table_token(token=token)
                if row:
                    user = table_user(row.user_id)
            else:
                row = self.db(table_token.token == token)(table_user.id == table_token.user_id).select().first()
                if row:
                    user = row[table_user._tablename]
            if user:
                self.login_user(user)
        return self.requires(True, otherwise=otherwise)

    def requires_membership(self, role=None, group_id=None, otherwise=None):
        """
        Decorator that prevents access to action if not logged in or
        if user logged in is not a member of group_id.
        If role is provided instead of group_id then the
        group_id is calculated.
        """

        def has_membership(self=self, group_id=group_id, role=role):
            return self.has_membership(group_id=group_id, role=role)
        return self.requires(has_membership, otherwise=otherwise)

    def requires_permission(self, name, table_name='', record_id=0,
                            otherwise=None):
        """
        Decorator that prevents access to action if not logged in or
        if user logged in is not a member of any group (role) that
        has 'name' access to 'table_name', 'record_id'.
        """

        def has_permission(self=self, name=name, table_name=table_name, record_id=record_id):
            return self.has_permission(name, table_name, record_id)
        return self.requires(has_permission, otherwise=otherwise)

    def requires_signature(self, otherwise=None, hash_vars=True):
        """
        Decorator that prevents access to action if not logged in or
        if user logged in is not a member of group_id.
        If role is provided instead of group_id then the
        group_id is calculated.
        """
        def verify():
            return URL.verify(current.request, user_signature=True, hash_vars=hash_vars)
        return self.requires(verify, otherwise)

    def accessible_query(self, name, table, user_id=None):
        """
        Returns a query with all accessible records for user_id or
        the current logged in user
        this method does not work on GAE because uses JOIN and IN

        Example:
            Use as::

                db(auth.accessible_query('read', db.mytable)).select(db.mytable.ALL)

        """
        if not user_id:
            user_id = self.user_id
        db = self.db
        if isinstance(table, str) and table in self.db.tables():
            table = self.db[table]
        elif isinstance(table, (Set, Query)):
            # experimental: build a chained query for all tables
            if isinstance(table, Set):
                cquery = table.query
            else:
                cquery = table
            tablenames = db._adapter.tables(cquery)
            for tablename in tablenames:
                cquery &= self.accessible_query(name, tablename, user_id=user_id)
            return cquery
        if not isinstance(table, str) and \
                self.has_permission(name, table, 0, user_id):
            return table.id > 0
        membership = self.table_membership()
        permission = self.table_permission()
        query = table.id.belongs(
            db(membership.user_id == user_id)
            (membership.group_id == permission.group_id)
            (permission.name == name)
            (permission.table_name == table)
            ._select(permission.record_id))
        if self.settings.everybody_group_id:
            query |= table.id.belongs(
                db(permission.group_id == self.settings.everybody_group_id)
                (permission.name == name)
                (permission.table_name == table)
                ._select(permission.record_id))
        return query

    @staticmethod
    def archive(form,
                archive_table=None,
                current_record='current_record',
                archive_current=False,
                fields=None):
        """
        If you have a table (db.mytable) that needs full revision history you
        can just do::

            form = crud.update(db.mytable, myrecord, onaccept=auth.archive)

        or::

            form = SQLFORM(db.mytable, myrecord).process(onaccept=auth.archive)

        crud.archive will define a new table "mytable_archive" and store
        a copy of the current record (if archive_current=True)
        or a copy of the previous record (if archive_current=False)
        in the newly created table including a reference
        to the current record.

        fields allows to specify extra fields that need to be archived.

        If you want to access such table you need to define it yourself
        in a model::

            db.define_table('mytable_archive',
                            Field('current_record', db.mytable),
                            db.mytable)

        Notice such table includes all fields of db.mytable plus one: current_record.
        crud.archive does not timestamp the stored record unless your original table
        has a fields like::

            db.define_table(...,
                Field('saved_on', 'datetime',
                      default=request.now, update=request.now, writable=False),
                Field('saved_by', auth.user,
                      default=auth.user_id, update=auth.user_id, writable=False),

        there is nothing special about these fields since they are filled before
        the record is archived.

        If you want to change the archive table name and the name of the reference field
        you can do, for example::

            db.define_table('myhistory',
                Field('parent_record', db.mytable), db.mytable)

        and use it as::

            form = crud.update(db.mytable, myrecord,
                               onaccept=lambda form:crud.archive(form,
                                                                 archive_table=db.myhistory,
                                                                 current_record='parent_record'))

        """
        if not archive_current and not form.record:
            return None
        table = form.table
        if not archive_table:
            archive_table_name = '%s_archive' % table
            if archive_table_name not in table._db:
                table._db.define_table(
                    archive_table_name,
                    Field(current_record, table),
                    *[field.clone(unique=False) for field in table])
            archive_table = table._db[archive_table_name]
        new_record = {current_record: form.vars.id}
        for fieldname in archive_table.fields:
            if fieldname not in ['id', current_record]:
                if archive_current and fieldname in form.vars:
                    new_record[fieldname] = form.vars[fieldname]
                elif form.record and fieldname in form.record:
                    new_record[fieldname] = form.record[fieldname]
        if fields:
            new_record.update(fields)
        id = archive_table.insert(**new_record)
        return id

    def wiki(self,
             slug=None,
             env=None,
             render='markmin',
             manage_permissions=False,
             force_prefix='',
             restrict_search=False,
             resolve=True,
             extra=None,
             menu_groups=None,
             templates=None,
             migrate=True,
             controller=None,
             function=None,
             force_render=False,
             groups=None):

        if controller and function:
            resolve = False

        if not hasattr(self, '_wiki'):
            self._wiki = Wiki(self, render=render,
                              manage_permissions=manage_permissions,
                              force_prefix=force_prefix,
                              restrict_search=restrict_search,
                              env=env, extra=extra or {},
                              menu_groups=menu_groups,
                              templates=templates,
                              migrate=migrate,
                              controller=controller,
                              function=function,
                              groups=groups)
        else:
            self._wiki.settings.extra = extra or {}
            self._wiki.env.update(env or {})

        # if resolve is set to True, process request as wiki call
        # resolve=False allows initial setup without wiki redirection
        wiki = None
        if resolve:
            if slug:
                wiki = self._wiki.read(slug, force_render)
                if isinstance(wiki, dict) and 'content' in wiki:
                    # We don't want to return a dict object, just the wiki
                    wiki = wiki['content']
            else:
                wiki = self._wiki()
            if isinstance(wiki, basestring):
                wiki = XML(wiki)
            return wiki

    def wikimenu(self):
        """To be used in menu.py for app wide wiki menus"""
        if (hasattr(self, "_wiki") and
                self._wiki.settings.controller and
                self._wiki.settings.function):
            self._wiki.automenu()


class Crud(object):  # pragma: no cover

    default_messages = dict(
        submit_button='Submit',
        delete_label='Check to delete',
        record_created='Record Created',
        record_updated='Record Updated',
        record_deleted='Record Deleted',
        update_log='Record %(id)s updated',
        create_log='Record %(id)s created',
        read_log='Record %(id)s read',
        delete_log='Record %(id)s deleted',
    )

    def url(self, f=None, args=None, vars=None):
        """
        This should point to the controller that exposes
        download and crud
        """
        if args is None:
            args = []
        if vars is None:
            vars = {}
        return URL(c=self.settings.controller, f=f, args=args, vars=vars)

    def __init__(self, environment, db=None, controller='default'):
        self.db = db
        if not db and environment and isinstance(environment, DAL):
            self.db = environment
        elif not db:
            raise SyntaxError("must pass db as first or second argument")
        self.environment = current
        settings = self.settings = Settings()
        settings.auth = None
        settings.logger = None

        settings.create_next = None
        settings.update_next = None
        settings.controller = controller
        settings.delete_next = self.url()
        settings.download_url = self.url('download')
        settings.create_onvalidation = StorageList()
        settings.update_onvalidation = StorageList()
        settings.delete_onvalidation = StorageList()
        settings.create_onaccept = StorageList()
        settings.update_onaccept = StorageList()
        settings.update_ondelete = StorageList()
        settings.delete_onaccept = StorageList()
        settings.update_deletable = True
        settings.showid = False
        settings.keepvalues = False
        settings.create_captcha = None
        settings.update_captcha = None
        settings.captcha = None
        settings.formstyle = 'table3cols'
        settings.label_separator = ': '
        settings.hideerror = False
        settings.detect_record_change = True
        settings.hmac_key = None
        settings.lock_keys = True

        messages = self.messages = Messages(current.T)
        messages.update(Crud.default_messages)
        messages.lock_keys = True

    def __call__(self):
        args = current.request.args
        if len(args) < 1:
            raise HTTP(404)
        elif args[0] == 'tables':
            return self.tables()
        elif len(args) > 1 and not args(1) in self.db.tables:
            raise HTTP(404)
        table = self.db[args(1)]
        if args[0] == 'create':
            return self.create(table)
        elif args[0] == 'select':
            return self.select(table, linkto=self.url(args='read'))
        elif args[0] == 'search':
            form, rows = self.search(table, linkto=self.url(args='read'))
            return DIV(form, SQLTABLE(rows))
        elif args[0] == 'read':
            return self.read(table, args(2))
        elif args[0] == 'update':
            return self.update(table, args(2))
        elif args[0] == 'delete':
            return self.delete(table, args(2))
        else:
            raise HTTP(404)

    def log_event(self, message, vars):
        if self.settings.logger:
            self.settings.logger.log_event(message, vars, origin='crud')

    def has_permission(self, name, table, record=0):
        if not self.settings.auth:
            return True
        try:
            record_id = record.id
        except:
            record_id = record
        return self.settings.auth.has_permission(name, str(table), record_id)

    def tables(self):
        return TABLE(*[TR(A(name,
                            _href=self.url(args=('select', name))))
                       for name in self.db.tables])

    @staticmethod
    def archive(form, archive_table=None, current_record='current_record'):
        return Auth.archive(form, archive_table=archive_table,
                            current_record=current_record)

    def update(self,
               table,
               record,
               next=DEFAULT,
               onvalidation=DEFAULT,
               onaccept=DEFAULT,
               ondelete=DEFAULT,
               log=DEFAULT,
               message=DEFAULT,
               deletable=DEFAULT,
               formname=DEFAULT,
               **attributes
               ):
        if not (isinstance(table, Table) or table in self.db.tables) \
                or (isinstance(record, str) and not str(record).isdigit()):
            raise HTTP(404)
        if not isinstance(table, Table):
            table = self.db[table]
        try:
            record_id = record.id
        except:
            record_id = record or 0
        if record_id and not self.has_permission('update', table, record_id):
            redirect(self.settings.auth.settings.on_failed_authorization)
        if not record_id and not self.has_permission('create', table, record_id):
            redirect(self.settings.auth.settings.on_failed_authorization)

        request = current.request
        response = current.response
        session = current.session
        if request.extension == 'json' and request.vars.json:
            request.vars.update(json.loads(request.vars.json))
        if next is DEFAULT:
            next = request.get_vars._next \
                or request.post_vars._next \
                or self.settings.update_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.update_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.update_onaccept
        if ondelete is DEFAULT:
            ondelete = self.settings.update_ondelete
        if log is DEFAULT:
            log = self.messages['update_log']
        if deletable is DEFAULT:
            deletable = self.settings.update_deletable
        if message is DEFAULT:
            message = self.messages.record_updated
        if 'hidden' not in attributes:
            attributes['hidden'] = {}
        attributes['hidden']['_next'] = next
        form = SQLFORM(
            table,
            record,
            showid=self.settings.showid,
            submit_button=self.messages.submit_button,
            delete_label=self.messages.delete_label,
            deletable=deletable,
            upload=self.settings.download_url,
            formstyle=self.settings.formstyle,
            separator=self.settings.label_separator,
            **attributes  # contains hidden
        )
        self.accepted = False
        self.deleted = False
        captcha = self.settings.update_captcha or self.settings.captcha
        if record and captcha:
            addrow(form, captcha.label, captcha, captcha.comment, self.settings.formstyle, 'captcha__row')
        captcha = self.settings.create_captcha or self.settings.captcha
        if not record and captcha:
            addrow(form, captcha.label, captcha, captcha.comment, self.settings.formstyle, 'captcha__row')
        if request.extension not in ('html', 'load'):
            (_session, _formname) = (None, None)
        else:
            (_session, _formname) = (
                session, '%s/%s' % (table._tablename, form.record_id))
        if formname is not DEFAULT:
            _formname = formname
        keepvalues = self.settings.keepvalues
        if request.vars.delete_this_record:
            keepvalues = False
        if isinstance(onvalidation, StorageList):
            onvalidation = onvalidation.get(table._tablename, [])
        if form.accepts(request, _session, formname=_formname,
                        onvalidation=onvalidation, keepvalues=keepvalues,
                        hideerror=self.settings.hideerror,
                        detect_record_change=self.settings.detect_record_change):
            self.accepted = True
            response.flash = message
            if log:
                self.log_event(log, form.vars)
            if request.vars.delete_this_record:
                self.deleted = True
                message = self.messages.record_deleted
                callback(ondelete, form, table._tablename)
            response.flash = message
            callback(onaccept, form, table._tablename)
            if request.extension not in ('html', 'load'):
                raise HTTP(200, 'RECORD CREATED/UPDATED')
            if isinstance(next, (list, tuple)):  # fix issue with 2.6
                next = next[0]
            if next:  # Only redirect when explicit
                next = replace_id(next, form)
                session.flash = response.flash
                redirect(next)
        elif request.extension not in ('html', 'load'):
            raise HTTP(401, serializers.json(dict(errors=form.errors)))
        return form

    def create(self,
               table,
               next=DEFAULT,
               onvalidation=DEFAULT,
               onaccept=DEFAULT,
               log=DEFAULT,
               message=DEFAULT,
               formname=DEFAULT,
               **attributes
               ):

        if next is DEFAULT:
            next = self.settings.create_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.create_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.create_onaccept
        if log is DEFAULT:
            log = self.messages['create_log']
        if message is DEFAULT:
            message = self.messages.record_created
        return self.update(table,
                           None,
                           next=next,
                           onvalidation=onvalidation,
                           onaccept=onaccept,
                           log=log,
                           message=message,
                           deletable=False,
                           formname=formname,
                           **attributes
                           )

    def read(self, table, record):
        if not (isinstance(table, Table) or table in self.db.tables) \
                or (isinstance(record, str) and not str(record).isdigit()):
            raise HTTP(404)
        if not isinstance(table, Table):
            table = self.db[table]
        if not self.has_permission('read', table, record):
            redirect(self.settings.auth.settings.on_failed_authorization)
        form = SQLFORM(
            table,
            record,
            readonly=True,
            comments=False,
            upload=self.settings.download_url,
            showid=self.settings.showid,
            formstyle=self.settings.formstyle,
            separator=self.settings.label_separator
        )
        if current.request.extension not in ('html', 'load'):
            return table._filter_fields(form.record, id=True)
        return form

    def delete(self,
               table,
               record_id,
               next=DEFAULT,
               message=DEFAULT,
               ):
        if not (isinstance(table, Table) or table in self.db.tables):
            raise HTTP(404)
        if not isinstance(table, Table):
            table = self.db[table]
        if not self.has_permission('delete', table, record_id):
            redirect(self.settings.auth.settings.on_failed_authorization)
        request = current.request
        session = current.session
        if next is DEFAULT:
            next = request.get_vars._next \
                or request.post_vars._next \
                or self.settings.delete_next
        if message is DEFAULT:
            message = self.messages.record_deleted
        record = table[record_id]
        if record:
            callback(self.settings.delete_onvalidation, record)
            del table[record_id]
            callback(self.settings.delete_onaccept, record, table._tablename)
            session.flash = message
        redirect(next)

    def rows(self,
             table,
             query=None,
             fields=None,
             orderby=None,
             limitby=None,
             ):
        if not (isinstance(table, Table) or table in self.db.tables):
            raise HTTP(404)
        if not self.has_permission('select', table):
            redirect(self.settings.auth.settings.on_failed_authorization)
        # if record_id and not self.has_permission('select', table):
        #    redirect(self.settings.auth.settings.on_failed_authorization)
        if not isinstance(table, Table):
            table = self.db[table]
        if not query:
            query = table.id > 0
        if not fields:
            fields = [field for field in table if field.readable]
        else:
            fields = [table[f] if isinstance(f, str) else f for f in fields]
        rows = self.db(query).select(*fields, **dict(orderby=orderby,
                                                     limitby=limitby))
        return rows

    def select(self,
               table,
               query=None,
               fields=None,
               orderby=None,
               limitby=None,
               headers=None,
               **attr
               ):
        headers = headers or {}
        rows = self.rows(table, query, fields, orderby, limitby)
        if not rows:
            return None  # Nicer than an empty table.
        if 'upload' not in attr:
            attr['upload'] = self.url('download')
        if current.request.extension not in ('html', 'load'):
            return rows.as_list()
        if not headers:
            if isinstance(table, str):
                table = self.db[table]
            headers = dict((str(k), k.label) for k in table)
        return SQLTABLE(rows, headers=headers, **attr)

    def get_format(self, field):
        rtable = field._db[field.type[10:]]
        format = rtable.get('_format', None)
        if format and isinstance(format, str):
            return format[2:-2]
        return field.name

    def get_query(self, field, op, value, refsearch=False):
        try:
            if refsearch:
                format = self.get_format(field)
            if op == 'equals':
                if not refsearch:
                    return field == value
                else:
                    return lambda row: row[field.name][format] == value
            elif op == 'not equal':
                if not refsearch:
                    return field != value
                else:
                    return lambda row: row[field.name][format] != value
            elif op == 'greater than':
                if not refsearch:
                    return field > value
                else:
                    return lambda row: row[field.name][format] > value
            elif op == 'less than':
                if not refsearch:
                    return field < value
                else:
                    return lambda row: row[field.name][format] < value
            elif op == 'starts with':
                if not refsearch:
                    return field.like(value + '%')
                else:
                    return lambda row: str(row[field.name][format]).startswith(value)
            elif op == 'ends with':
                if not refsearch:
                    return field.like('%' + value)
                else:
                    return lambda row: str(row[field.name][format]).endswith(value)
            elif op == 'contains':
                if not refsearch:
                    return field.like('%' + value + '%')
                else:
                    return lambda row: value in row[field.name][format]
        except:
            return None

    def search(self, *tables, **args):
        """
        Creates a search form and its results for a table
        Examples:
            Use as::

                form, results = crud.search(db.test,
                   queries = ['equals', 'not equal', 'contains'],
                   query_labels={'equals':'Equals',
                                 'not equal':'Not equal'},
                   fields = ['id','children'],
                   field_labels = {
                       'id':'ID','children':'Children'},
                   zero='Please choose',
                   query = (db.test.id > 0)&(db.test.id != 3) )

        """
        table = tables[0]
        fields = args.get('fields', table.fields)
        validate = args.get('validate', True)
        request = current.request
        db = self.db
        if not (isinstance(table, Table) or table in db.tables):
            raise HTTP(404)
        attributes = {}
        for key in ('orderby', 'groupby', 'left', 'distinct', 'limitby', 'cache'):
            if key in args:
                attributes[key] = args[key]
        tbl = TABLE()
        selected = []
        refsearch = []
        results = []
        showall = args.get('showall', False)
        if showall:
            selected = fields
        chkall = args.get('chkall', False)
        if chkall:
            for f in fields:
                request.vars['chk%s' % f] = 'on'
        ops = args.get('queries', [])
        zero = args.get('zero', '')
        if not ops:
            ops = ['equals', 'not equal', 'greater than',
                   'less than', 'starts with',
                   'ends with', 'contains']
        ops.insert(0, zero)
        query_labels = args.get('query_labels', {})
        query = args.get('query', table.id > 0)
        field_labels = args.get('field_labels', {})
        for field in fields:
            field = table[field]
            if not field.readable:
                continue
            fieldname = field.name
            chkval = request.vars.get('chk' + fieldname, None)
            txtval = request.vars.get('txt' + fieldname, None)
            opval = request.vars.get('op' + fieldname, None)
            row = TR(TD(INPUT(_type="checkbox", _name="chk" + fieldname,
                              _disabled=(field.type == 'id'),
                              value=(field.type == 'id' or chkval == 'on'))),
                     TD(field_labels.get(fieldname, field.label)),
                     TD(SELECT([OPTION(query_labels.get(op, op),
                                       _value=op) for op in ops],
                               _name="op" + fieldname,
                               value=opval)),
                     TD(INPUT(_type="text", _name="txt" + fieldname,
                              _value=txtval, _id='txt' + fieldname,
                              _class=str(field.type))))
            tbl.append(row)
            if request.post_vars and (chkval or field.type == 'id'):
                if txtval and opval != '':
                    if field.type[0:10] == 'reference ':
                        refsearch.append(self.get_query(field, opval, txtval, refsearch=True))
                    elif validate:
                        value, error = field.validate(txtval)
                        if not error:
                            # TODO deal with 'starts with', 'ends with', 'contains' on GAE
                            query &= self.get_query(field, opval, value)
                        else:
                            row[3].append(DIV(error, _class='error'))
                    else:
                        query &= self.get_query(field, opval, txtval)
                selected.append(field)
        form = FORM(tbl, INPUT(_type="submit"))
        if selected:
            try:
                results = db(query).select(*selected, **attributes)
                for r in refsearch:
                    results = results.find(r)
            except:  # TODO: hmmm, we should do better here
                results = None
        return form, results


urllib2.install_opener(urllib2.build_opener(urllib2.HTTPCookieProcessor()))


def fetch(url, data=None, headers=None,
          cookie=Cookie.SimpleCookie(),
          user_agent='Mozilla/5.0'):
    headers = headers or {}
    if data is not None:
        data = urlencode(data)
    if user_agent:
        headers['User-agent'] = user_agent
    headers['Cookie'] = ' '.join(
        ['%s=%s;' % (c.key, c.value) for c in cookie.values()])
    try:
        from google.appengine.api import urlfetch
    except ImportError:
        req = urllib2.Request(url, data, headers)
        html = urllib2.urlopen(req).read()
    else:
        method = ((data is None) and urlfetch.GET) or urlfetch.POST
        while url is not None:
            response = urlfetch.fetch(url=url, payload=data,
                                      method=method, headers=headers,
                                      allow_truncated=False, follow_redirects=False,
                                      deadline=10)
            # next request will be a get, so no need to send the data again
            data = None
            method = urlfetch.GET
            # load cookies from the response
            cookie.load(response.headers.get('set-cookie', ''))
            url = response.headers.get('location')
        html = response.content
    return html

regex_geocode = \
    re.compile(r"""<geometry>[\W]*?<location>[\W]*?<lat>(?P<la>[^<]*)</lat>[\W]*?<lng>(?P<lo>[^<]*)</lng>[\W]*?</location>""")


def geocode(address):
    try:
        a = urllib_quote(address)
        txt = fetch('http://maps.googleapis.com/maps/api/geocode/xml?sensor=false&address=%s' % a)
        item = regex_geocode.search(txt)
        (la, lo) = (float(item.group('la')), float(item.group('lo')))
        return (la, lo)
    except:
        return (0.0, 0.0)


def reverse_geocode(lat, lng, lang=None):
    """ Try to get an approximate address for a given latitude, longitude. """
    if not lang:
        lang = current.T.accepted_language
    try:
        return json.loads(fetch('http://maps.googleapis.com/maps/api/geocode/json?latlng=%(lat)s,%(lng)s&language=%(lang)s' % locals()))['results'][0]['formatted_address']
    except:
        return ''


def universal_caller(f, *a, **b):
    c = f.__code__.co_argcount
    n = f.__code__.co_varnames[:c]

    defaults = f.__defaults__ or []
    pos_args = n[0:-len(defaults)]
    named_args = n[-len(defaults):]

    arg_dict = {}

    # Fill the arg_dict with name and value for the submitted, positional values
    for pos_index, pos_val in enumerate(a[:c]):
        arg_dict[n[pos_index]] = pos_val    # n[pos_index] is the name of the argument

    # There might be pos_args left, that are sent as named_values. Gather them as well.
    # If a argument already is populated with values we simply replaces them.
    for arg_name in pos_args[len(arg_dict):]:
        if arg_name in b:
            arg_dict[arg_name] = b[arg_name]

    if len(arg_dict) >= len(pos_args):
        # All the positional arguments is found. The function may now be called.
        # However, we need to update the arg_dict with the values from the named arguments as well.
        for arg_name in named_args:
            if arg_name in b:
                arg_dict[arg_name] = b[arg_name]

        return f(**arg_dict)

    # Raise an error, the function cannot be called.
    raise HTTP(404, "Object does not exist")


class Service(object):

    def __init__(self, environment=None, check_args=False):
        self.check_args = check_args

        self.run_procedures = {}
        self.csv_procedures = {}
        self.xml_procedures = {}
        self.rss_procedures = {}
        self.json_procedures = {}
        self.jsonrpc_procedures = {}
        self.jsonrpc2_procedures = {}
        self.xmlrpc_procedures = {}
        self.amfrpc_procedures = {}
        self.amfrpc3_procedures = {}
        self.soap_procedures = {}

    def run(self, f):
        """
        Example:
            Use as::

                service = Service()
                @service.run
                def myfunction(a, b):
                    return a + b
                def call():
                    return service()

            Then call it with::

                wget http://..../app/default/call/run/myfunction?a=3&b=4

        """
        self.run_procedures[f.__name__] = f
        return f

    def csv(self, f):
        """
        Example:
            Use as::

                service = Service()
                @service.csv
                def myfunction(a, b):
                    return a + b
                def call():
                    return service()

            Then call it with::

                wget http://..../app/default/call/csv/myfunction?a=3&b=4

        """
        self.csv_procedures[f.__name__] = f
        return f

    def xml(self, f):
        """
        Example:
            Use as::

                service = Service()
                @service.xml
                def myfunction(a, b):
                    return a + b
                def call():
                    return service()

            Then call it with::

                wget http://..../app/default/call/xml/myfunction?a=3&b=4

        """
        self.xml_procedures[f.__name__] = f
        return f

    def rss(self, f):
        """
        Example:
            Use as::

                service = Service()
                @service.rss
                def myfunction():
                    return dict(title=..., link=..., description=...,
                        created_on=..., entries=[dict(title=..., link=...,
                            description=..., created_on=...])
                def call():
                    return service()

            Then call it with:

                wget http://..../app/default/call/rss/myfunction

        """
        self.rss_procedures[f.__name__] = f
        return f

    def json(self, f):
        """
        Example:
            Use as::

                service = Service()
                @service.json
                def myfunction(a, b):
                    return [{a: b}]
                def call():
                    return service()

            Then call it with:;

                wget http://..../app/default/call/json/myfunction?a=hello&b=world

        """
        self.json_procedures[f.__name__] = f
        return f

    def jsonrpc(self, f):
        """
        Example:
            Use as::

                service = Service()
                @service.jsonrpc
                def myfunction(a, b):
                    return a + b
                def call():
                    return service()

            Then call it with:

                wget http://..../app/default/call/jsonrpc/myfunction?a=hello&b=world

        """
        self.jsonrpc_procedures[f.__name__] = f
        return f

    def jsonrpc2(self, f):
        """
        Example:
            Use as::

                service = Service()
                @service.jsonrpc2
                def myfunction(a, b):
                    return a + b
                def call():
                    return service()

            Then call it with:

                wget --post-data '{"jsonrpc": "2.0",
                                   "id": 1,
                                   "method": "myfunction",
                                   "params": {"a": 1, "b": 2}}' http://..../app/default/call/jsonrpc2

        """
        self.jsonrpc2_procedures[f.__name__] = f
        return f

    def xmlrpc(self, f):
        """
        Example:
            Use as::

                service = Service()
                @service.xmlrpc
                def myfunction(a, b):
                    return a + b
                def call():
                    return service()

            The call it with:

                wget http://..../app/default/call/xmlrpc/myfunction?a=hello&b=world

        """
        self.xmlrpc_procedures[f.__name__] = f
        return f

    def amfrpc(self, f):
        """
        Example:
            Use as::

                service = Service()
                @service.amfrpc
                def myfunction(a, b):
                    return a + b
                def call():
                    return service()


            Then call it with::

                wget http://..../app/default/call/amfrpc/myfunction?a=hello&b=world

        """
        self.amfrpc_procedures[f.__name__] = f
        return f

    def amfrpc3(self, domain='default'):
        """
        Example:
            Use as::

                service = Service()
                @service.amfrpc3('domain')
                def myfunction(a, b):
                    return a + b
                def call():
                    return service()

            Then call it with:

                wget http://..../app/default/call/amfrpc3/myfunction?a=hello&b=world

        """
        if not isinstance(domain, str):
            raise SyntaxError("AMF3 requires a domain for function")

        def _amfrpc3(f):
            if domain:
                self.amfrpc3_procedures[domain + '.' + f.__name__] = f
            else:
                self.amfrpc3_procedures[f.__name__] = f
            return f
        return _amfrpc3

    def soap(self, name=None, returns=None, args=None, doc=None, response_element_name=None):
        """
        Example:
            Use as::

                service = Service()
                @service.soap('MyFunction',returns={'result':int},args={'a':int,'b':int,})
                def myfunction(a, b):
                    return a + b
                def call():
                    return service()

        Then call it with::

            from gluon.contrib.pysimplesoap.client import SoapClient
            client = SoapClient(wsdl="http://..../app/default/call/soap?WSDL")
            response = client.MyFunction(a=1,b=2)
            return response['result']

        It also exposes online generated documentation and xml example messages
        at `http://..../app/default/call/soap`
        """

        def _soap(f):
            self.soap_procedures[name or f.__name__] = f, returns, args, doc, response_element_name
            return f
        return _soap

    def serve_run(self, args=None):
        request = current.request
        if not args:
            args = request.args
        if args and args[0] in self.run_procedures:
            return str(self.call_service_function(self.run_procedures[args[0]],
                                                  *args[1:], **dict(request.vars)))
        self.error()

    def serve_csv(self, args=None):
        request = current.request
        response = current.response
        response.headers['Content-Type'] = 'text/x-csv'
        if not args:
            args = request.args

        def none_exception(value):
            if isinstance(value, unicodeT):
                return value.encode('utf8')
            if hasattr(value, 'isoformat'):
                return value.isoformat()[:19].replace('T', ' ')
            if value is None:
                return '<NULL>'
            return value
        if args and args[0] in self.csv_procedures:
            import types
            r = self.call_service_function(self.csv_procedures[args[0]],
                                           *args[1:], **dict(request.vars))
            s = StringIO()
            if hasattr(r, 'export_to_csv_file'):
                r.export_to_csv_file(s)
            elif r and not isinstance(r, types.GeneratorType) and isinstance(r[0], (dict, Storage)):
                import csv
                writer = csv.writer(s)
                writer.writerow(r[0].keys())
                for line in r:
                    writer.writerow([none_exception(v)
                                     for v in line.values()])
            else:
                import csv
                writer = csv.writer(s)
                for line in r:
                    writer.writerow(line)
            return s.getvalue()
        self.error()

    def serve_xml(self, args=None):
        request = current.request
        response = current.response
        response.headers['Content-Type'] = 'text/xml'
        if not args:
            args = request.args
        if args and args[0] in self.xml_procedures:
            s = self.call_service_function(self.xml_procedures[args[0]],
                                           *args[1:], **dict(request.vars))
            if hasattr(s, 'as_list'):
                s = s.as_list()
            return serializers.xml(s, quote=False)
        self.error()

    def serve_rss(self, args=None):
        request = current.request
        response = current.response
        if not args:
            args = request.args
        if args and args[0] in self.rss_procedures:
            feed = self.call_service_function(self.rss_procedures[args[0]],
                                              *args[1:], **dict(request.vars))
        else:
            self.error()
        response.headers['Content-Type'] = 'application/rss+xml'
        return serializers.rss(feed)

    def serve_json(self, args=None):
        request = current.request
        response = current.response
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        if not args:
            args = request.args
        d = dict(request.vars)
        if args and args[0] in self.json_procedures:
            s = self.call_service_function(self.json_procedures[args[0]], *args[1:], **d)
            if hasattr(s, 'as_list'):
                s = s.as_list()
            return response.json(s)
        self.error()

    class JsonRpcException(Exception):

        def __init__(self, code, info):
            jrpc_error = Service.jsonrpc_errors.get(code)
            if jrpc_error:
                self.message, self.description = jrpc_error
            self.code, self.info = code, info

    # jsonrpc 2.0 error types.  records the following structure {code: (message,meaning)}
    jsonrpc_errors = {
        -32700: ("Parse error. Invalid JSON was received by the server.",
                 "An error occurred on the server while parsing the JSON text."),
        -32600: ("Invalid Request", "The JSON sent is not a valid Request object."),
        -32601: ("Method not found", "The method does not exist / is not available."),
        -32602: ("Invalid params", "Invalid method parameter(s)."),
        -32603: ("Internal error", "Internal JSON-RPC error."),
        -32099: ("Server error", "Reserved for implementation-defined server-errors.")}

    def serve_jsonrpc(self):
        def return_response(id, result):
            return serializers.json({'version': '1.1', 'id': id, 'result': result, 'error': None})

        def return_error(id, code, message, data=None):
            error = {'name': 'JSONRPCError',
                     'code': code, 'message': message}
            if data is not None:
                error['data'] = data
            return serializers.json({'id': id,
                                     'version': '1.1',
                                     'error': error,
                                     })

        request = current.request
        response = current.response
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        methods = self.jsonrpc_procedures
        data = json.loads(request.body.read())
        jsonrpc_2 = data.get('jsonrpc')
        if jsonrpc_2:  # hand over to version 2 of the protocol
            return self.serve_jsonrpc2(data)
        id, method, params = data.get('id'), data.get('method'), data.get('params', [])
        if id is None:
            return return_error(0, 100, 'missing id')
        if method not in methods:
            return return_error(id, 100, 'method "%s" does not exist' % method)
        try:
            if isinstance(params, dict):
                s = methods[method](**params)
            else:
                s = methods[method](*params)
            if hasattr(s, 'as_list'):
                s = s.as_list()
            return return_response(id, s)
        except Service.JsonRpcException as e:
            return return_error(id, e.code, e.info)
        except:
            etype, eval, etb = sys.exc_info()
            message = '%s: %s' % (etype.__name__, eval)
            data = request.is_local and traceback.format_tb(etb)
            logger.warning('jsonrpc exception %s\n%s' % (message, traceback.format_tb(etb)))
            return return_error(id, 100, message, data)

    def serve_jsonrpc2(self, data=None, batch_element=False):

        def return_response(id, result):
            if not must_respond:
                return None
            return serializers.json({'jsonrpc': '2.0', 'id': id, 'result': result})

        def return_error(id, code, message=None, data=None):
            error = {'code': code}
            if code in Service.jsonrpc_errors:
                error['message'] = Service.jsonrpc_errors[code][0]
                error['data'] = Service.jsonrpc_errors[code][1]
            if message is not None:
                error['message'] = message
            if data is not None:
                error['data'] = data
            return serializers.json({'jsonrpc': '2.0', 'id': id, 'error': error})

        def validate(data):
            """
            Validate request as defined in: http://www.jsonrpc.org/specification#request_object.

            Args:
                data(str): The json object.

            Returns:
                - True -- if successful
                - False -- if no error should be reported (i.e. data is missing 'id' member)

            Raises:
                JsonRPCException

            """

            iparms = set(data.keys())
            mandatory_args = set(['jsonrpc', 'method'])
            missing_args = mandatory_args - iparms

            if missing_args:
                raise Service.JsonRpcException(-32600, 'Missing arguments %s.' % list(missing_args))
            if data['jsonrpc'] != '2.0':
                raise Service.JsonRpcException(-32603, 'Unsupported jsonrpc version "%s"' % data['jsonrpc'])
            if 'id' not in iparms:
                return False

            return True

        request = current.request
        response = current.response
        if not data:
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            try:
                data = json.loads(request.body.read())
            except ValueError:  # decoding error in json lib
                return return_error(None, -32700)

        # Batch handling
        if isinstance(data, list) and not batch_element:
            retlist = []
            for c in data:
                retstr = self.serve_jsonrpc2(c, batch_element=True)
                if retstr:  # do not add empty responses
                    retlist.append(retstr)
            if len(retlist) == 0:  # return nothing
                return ''
            else:
                return "[" + ','.join(retlist) + "]"
        methods = self.jsonrpc2_procedures
        methods.update(self.jsonrpc_procedures)

        try:
            must_respond = validate(data)
        except Service.JsonRpcException as e:
            return return_error(None, e.code, e.info)

        id, method, params = data.get('id'), data['method'], data.get('params', '')
        if method not in methods:
            return return_error(id, -32601, data='Method "%s" does not exist' % method)
        try:
            if isinstance(params, dict):
                s = methods[method](**params)
            else:
                s = methods[method](*params)
            if hasattr(s, 'as_list'):
                s = s.as_list()
            if must_respond:
                return return_response(id, s)
            else:
                return ''
        except HTTP as e:
            raise e
        except Service.JsonRpcException as e:
            return return_error(id, e.code, e.info)
        except:
            etype, eval, etb = sys.exc_info()
            data = '%s: %s\n' % (etype.__name__, eval) + str(request.is_local and traceback.format_tb(etb))
            logger.warning('%s: %s\n%s' % (etype.__name__, eval, traceback.format_tb(etb)))
            return return_error(id, -32099, data=data)

    def serve_xmlrpc(self):
        request = current.request
        response = current.response
        services = self.xmlrpc_procedures.values()
        return response.xmlrpc(request, services)

    def serve_amfrpc(self, version=0):
        try:
            import pyamf
            import pyamf.remoting.gateway
        except:
            return "pyamf not installed or not in Python sys.path"
        request = current.request
        response = current.response
        if version == 3:
            services = self.amfrpc3_procedures
            base_gateway = pyamf.remoting.gateway.BaseGateway(services)
            pyamf_request = pyamf.remoting.decode(request.body)
        else:
            services = self.amfrpc_procedures
            base_gateway = pyamf.remoting.gateway.BaseGateway(services)
            context = pyamf.get_context(pyamf.AMF0)
            pyamf_request = pyamf.remoting.decode(request.body, context)
        pyamf_response = pyamf.remoting.Envelope(pyamf_request.amfVersion)
        for name, message in pyamf_request:
            pyamf_response[name] = base_gateway.getProcessor(message)(message)
        response.headers['Content-Type'] = pyamf.remoting.CONTENT_TYPE
        if version == 3:
            return pyamf.remoting.encode(pyamf_response).getvalue()
        else:
            return pyamf.remoting.encode(pyamf_response, context).getvalue()

    def serve_soap(self, version="1.1"):
        try:
            from gluon.contrib.pysimplesoap.server import SoapDispatcher
        except:
            return "pysimplesoap not installed in contrib"
        request = current.request
        response = current.response
        procedures = self.soap_procedures

        location = "%s://%s%s" % (request.env.wsgi_url_scheme,
                                  request.env.http_host,
                                  URL(r=request, f="call/soap", vars={}))
        namespace = 'namespace' in response and response.namespace or location
        documentation = response.description or ''
        dispatcher = SoapDispatcher(
            name=response.title,
            location=location,
            action=location,  # SOAPAction
            namespace=namespace,
            prefix='pys',
            documentation=documentation,
            ns=True)
        for method, (function, returns, args, doc, resp_elem_name) in iteritems(procedures):
            dispatcher.register_function(method, function, returns, args, doc, resp_elem_name)
        if request.env.request_method == 'POST':
            fault = {}
            # Process normal Soap Operation
            response.headers['Content-Type'] = 'text/xml'
            xml = dispatcher.dispatch(request.body.read(), fault=fault)
            if fault:
                # May want to consider populating a ticket here...
                response.status = 500
            # return the soap response
            return xml
        elif 'WSDL' in request.vars:
            # Return Web Service Description
            response.headers['Content-Type'] = 'text/xml'
            return dispatcher.wsdl()
        elif 'op' in request.vars:
            # Return method help webpage
            response.headers['Content-Type'] = 'text/html'
            method = request.vars['op']
            sample_req_xml, sample_res_xml, doc = dispatcher.help(method)
            body = [H1("Welcome to Web2Py SOAP webservice gateway"),
                    A("See all webservice operations",
                      _href=URL(r=request, f="call/soap", vars={})),
                    H2(method),
                    P(doc),
                    UL(LI("Location: %s" % dispatcher.location),
                       LI("Namespace: %s" % dispatcher.namespace),
                       LI("SoapAction: %s" % dispatcher.action),
                       ),
                    H3("Sample SOAP XML Request Message:"),
                    CODE(sample_req_xml, language="xml"),
                    H3("Sample SOAP XML Response Message:"),
                    CODE(sample_res_xml, language="xml"),
                    ]
            return {'body': body}
        else:
            # Return general help and method list webpage
            response.headers['Content-Type'] = 'text/html'
            body = [H1("Welcome to Web2Py SOAP webservice gateway"),
                    P(response.description),
                    P("The following operations are available"),
                    A("See WSDL for webservice description",
                      _href=URL(r=request, f="call/soap", vars={"WSDL": None})),
                    UL([LI(A("%s: %s" % (method, doc or ''),
                             _href=URL(r=request, f="call/soap", vars={'op': method})))
                        for method, doc in dispatcher.list_methods()]),
                    ]
            return {'body': body}

    def __call__(self):
        """
        Registers services with::

            service = Service()
            @service.run
            @service.rss
            @service.json
            @service.jsonrpc
            @service.xmlrpc
            @service.amfrpc
            @service.amfrpc3('domain')
            @service.soap('Method', returns={'Result':int}, args={'a':int,'b':int,})

        Exposes services with::

            def call():
                return service()

        You can call services with::

            http://..../app/default/call/run?[parameters]
            http://..../app/default/call/rss?[parameters]
            http://..../app/default/call/json?[parameters]
            http://..../app/default/call/jsonrpc
            http://..../app/default/call/xmlrpc
            http://..../app/default/call/amfrpc
            http://..../app/default/call/amfrpc3
            http://..../app/default/call/soap

        """

        request = current.request
        if len(request.args) < 1:
            raise HTTP(404, "Not Found")
        arg0 = request.args(0)
        if arg0 == 'run':
            return self.serve_run(request.args[1:])
        elif arg0 == 'rss':
            return self.serve_rss(request.args[1:])
        elif arg0 == 'csv':
            return self.serve_csv(request.args[1:])
        elif arg0 == 'xml':
            return self.serve_xml(request.args[1:])
        elif arg0 == 'json':
            return self.serve_json(request.args[1:])
        elif arg0 == 'jsonrpc':
            return self.serve_jsonrpc()
        elif arg0 == 'jsonrpc2':
            return self.serve_jsonrpc2()
        elif arg0 == 'xmlrpc':
            return self.serve_xmlrpc()
        elif arg0 == 'amfrpc':
            return self.serve_amfrpc()
        elif arg0 == 'amfrpc3':
            return self.serve_amfrpc(3)
        elif arg0 == 'soap':
            return self.serve_soap()
        else:
            self.error()

    def error(self):
        raise HTTP(404, "Object does not exist")

    # we make this a method so that subclasses can override it if they want to do more specific argument-checking
    # but the default implmentation is the simplest: just pass the arguments we got, with no checking
    def call_service_function(self, f, *a, **b):
        if self.check_args:
            return universal_caller(f, *a, **b)
        else:
            return f(*a, **b)


def completion(callback):
    """
    Executes a task on completion of the called action.

    Example:
        Use as::

            from gluon.tools import completion
            @completion(lambda d: logging.info(repr(d)))
            def index():
                return dict(message='hello')

    It logs the output of the function every time input is called.
    The argument of completion is executed in a new thread.
    """
    def _completion(f):
        def __completion(*a, **b):
            d = None
            try:
                d = f(*a, **b)
                return d
            finally:
                thread.start_new_thread(callback, (d,))
        return __completion
    return _completion


def prettydate(d, T=lambda x: x, utc=False):
    now = datetime.datetime.utcnow() if utc else datetime.datetime.now()
    if isinstance(d, datetime.datetime):
        dt = now - d
    elif isinstance(d, datetime.date):
        dt = now.date() - d
    elif not d:
        return ''
    else:
        return '[invalid date]'
    if dt.days < 0:
        suffix = ' from now'
        dt = -dt
    else:
        suffix = ' ago'
    if dt.days >= 2 * 365:
        return T('%d years' + suffix) % int(dt.days // 365)
    elif dt.days >= 365:
        return T('1 year' + suffix)
    elif dt.days >= 60:
        return T('%d months' + suffix) % int(dt.days // 30)
    elif dt.days >= 27:  # 4 weeks ugly
        return T('1 month' + suffix)
    elif dt.days >= 14:
        return T('%d weeks' + suffix) % int(dt.days // 7)
    elif dt.days >= 7:
        return T('1 week' + suffix)
    elif dt.days > 1:
        return T('%d days' + suffix) % dt.days
    elif dt.days == 1:
        return T('1 day' + suffix)
    elif dt.seconds >= 2 * 60 * 60:
        return T('%d hours' + suffix) % int(dt.seconds // 3600)
    elif dt.seconds >= 60 * 60:
        return T('1 hour' + suffix)
    elif dt.seconds >= 2 * 60:
        return T('%d minutes' + suffix) % int(dt.seconds // 60)
    elif dt.seconds >= 60:
        return T('1 minute' + suffix)
    elif dt.seconds > 1:
        return T('%d seconds' + suffix) % dt.seconds
    elif dt.seconds == 1:
        return T('1 second' + suffix)
    else:
        return T('now')


def test_thread_separation():
    def f():
        c = PluginManager()
        lock1.acquire()
        lock2.acquire()
        c.x = 7
        lock1.release()
        lock2.release()
    lock1 = thread.allocate_lock()
    lock2 = thread.allocate_lock()
    lock1.acquire()
    thread.start_new_thread(f, ())
    a = PluginManager()
    a.x = 5
    lock1.release()
    lock2.acquire()
    return a.x


class PluginManager(object):
    """

    Plugin Manager is similar to a storage object but it is a single level
    singleton. This means that multiple instances within the same thread share
    the same attributes.
    Its constructor is also special. The first argument is the name of the
    plugin you are defining.
    The named arguments are parameters needed by the plugin with default values.
    If the parameters were previous defined, the old values are used.

    Example:
        in some general configuration file::

            plugins = PluginManager()
            plugins.me.param1=3

        within the plugin model::

            _ = PluginManager('me',param1=5,param2=6,param3=7)

        where the plugin is used::

            >>> print(plugins.me.param1)
            3
            >>> print(plugins.me.param2)
            6
            >>> plugins.me.param3 = 8
            >>> print(plugins.me.param3)
            8

        Here are some tests::

            >>> a=PluginManager()
            >>> a.x=6
            >>> b=PluginManager('check')
            >>> print(b.x)
            6
            >>> b=PluginManager() # reset settings
            >>> print(b.x)
            <Storage {}>
            >>> b.x=7
            >>> print(a.x)
            7
            >>> a.y.z=8
            >>> print(b.y.z)
            8
            >>> test_thread_separation()
            5
            >>> plugins=PluginManager('me',db='mydb')
            >>> print(plugins.me.db)
            mydb
            >>> print('me' in plugins)
            True
            >>> print(plugins.me.installed)
            True

    """
    instances = {}

    def __new__(cls, *a, **b):
        id = thread.get_ident()
        lock = thread.allocate_lock()
        try:
            lock.acquire()
            try:
                return cls.instances[id]
            except KeyError:
                instance = object.__new__(cls, *a, **b)
                cls.instances[id] = instance
                return instance
        finally:
            lock.release()

    def __init__(self, plugin=None, **defaults):
        if not plugin:
            self.__dict__.clear()
        settings = self.__getattr__(plugin)
        settings.installed = True
        settings.update(
            (k, v) for k, v in defaults.items() if k not in settings)

    def __getattr__(self, key):
        if key not in self.__dict__:
            self.__dict__[key] = Storage()
        return self.__dict__[key]

    def keys(self):
        return self.__dict__.keys()

    def __contains__(self, key):
        return key in self.__dict__


class Expose(object):

    def __init__(self, base=None, basename=None, extensions=None,
                 allow_download=True, follow_symlink_out=False):
        """
        Examples:
            Use as::

                def static():
                    return dict(files=Expose())

            or::

                def static():
                    path = os.path.join(request.folder,'static','public')
                    return dict(files=Expose(path,basename='public'))

        Args:
            extensions: an optional list of file extensions for filtering
                displayed files: e.g. `['.py', '.jpg']`
            allow_download: whether to allow downloading selected files
            follow_symlink_out: whether to follow symbolic links that points
                points outside of `base`.
                Warning: setting this to `True` might pose a security risk
                         if you don't also have complete control over writing
                         and file creation under `base`.

        """
        # why would this not be callable? but otherwise tests do not pass
        if current.session and callable(current.session.forget):
            current.session.forget()
        self.follow_symlink_out = follow_symlink_out
        self.base = self.normalize_path(
            base or os.path.join(current.request.folder, 'static'))
        self.basename = basename or current.request.function
        self.base = base = os.path.realpath(base or os.path.join(current.request.folder, 'static'))
        basename = basename or current.request.function
        self.basename = basename

        if current.request.raw_args:
            self.args = [arg for arg in current.request.raw_args.split('/') if arg]
        else:
            self.args = [arg for arg in current.request.args if arg]

        filename = os.path.join(self.base, *self.args)
        if not os.path.exists(filename):
            raise HTTP(404, "FILE NOT FOUND")
        if not self.in_base(filename):
            raise HTTP(401, "NOT AUTHORIZED")
        if allow_download and not os.path.isdir(filename):
            current.response.headers['Content-Type'] = contenttype(filename)
            raise HTTP(200, open(filename, 'rb'), **current.response.headers)
        self.path = path = os.path.join(filename, '*')
        dirname_len = len(path) - 1
        allowed = [f for f in sorted(glob.glob(path))
                   if not any([self.isprivate(f), self.issymlink_out(f)])]
        self.folders = [f[dirname_len:]
                        for f in allowed if os.path.isdir(f)]
        self.filenames = [f[dirname_len:]
                          for f in allowed if not os.path.isdir(f)]
        if 'README' in self.filenames:
            with open(os.path.join(filename, 'README')) as f:
                readme = f.read()
            self.paragraph = MARKMIN(readme)
        else:
            self.paragraph = None
        if extensions:
            self.filenames = [f for f in self.filenames
                              if os.path.splitext(f)[-1] in extensions]

    def breadcrumbs(self, basename):
        path = []
        span = SPAN()
        span.append(A(basename, _href=URL()))
        for arg in self.args:
            span.append('/')
            path.append(arg)
            span.append(A(arg, _href=URL(args='/'.join(path))))
        return span

    def table_folders(self):
        if self.folders:
            return SPAN(H3('Folders'),
                        TABLE(*[TR(TD(A(folder, _href=URL(args=self.args + [folder]))))
                                for folder in self.folders], **dict(_class="table")))
        return ''

    @staticmethod
    def __in_base(subdir, basedir, sep=os.path.sep):
        """True if subdir/ is under basedir/"""
        s = lambda f: '%s%s' % (f.rstrip(sep), sep)  # f -> f/
        # The trailing '/' is for the case of '/foobar' in_base of '/foo':
        # - becase '/foobar'  starts with        '/foo'
        # - but    '/foobar/' doesn't start with '/foo/'
        return s(subdir).startswith(s(basedir))

    def in_base(self, f):
        """True if f/ is under self.base/
        Where f ans slef.base are normalized paths
        """
        return self.__in_base(self.normalize_path(f), self.base)

    def normalize_path(self, f):
        if self.follow_symlink_out:
            return os.path.normpath(f)
        else:
            return os.path.realpath(f)

    def issymlink_out(self, f):
        """True if f is a symlink and is pointing outside of self.base"""
        return os.path.islink(f) and not self.in_base(f)

    @staticmethod
    def isprivate(f):
        # remove '/private' prefix to deal with symbolic links on OSX
        if f.startswith('/private/'):
            f = f[8:]
        return 'private' in f or f.startswith('.') or f.endswith('~')

    @staticmethod
    def isimage(f):
        return os.path.splitext(f)[-1].lower() in (
            '.png', '.jpg', '.jpeg', '.gif', '.tiff')

    def table_files(self, width=160):
        if self.filenames:
            return SPAN(H3('Files'),
                        TABLE(*[TR(TD(A(f, _href=URL(args=self.args + [f]))),
                                   TD(IMG(_src=URL(args=self.args + [f]),
                                          _style='max-width:%spx' % width)
                                      if width and self.isimage(f) else ''))
                                for f in self.filenames], **dict(_class="table")))
        return ''

    def xml(self):
        return DIV(
            H2(self.breadcrumbs(self.basename)),
            self.paragraph or '',
            self.table_folders(),
            self.table_files()).xml()


class Wiki(object):
    everybody = 'everybody'
    rows_page = 25

    def markmin_base(self, body):
        return MARKMIN(body, extra=self.settings.extra,
                       url=True, environment=self.env,
                       autolinks=lambda link: expand_one(link, {})).xml()

    def render_tags(self, tags):
        return DIV(
            _class='w2p_wiki_tags',
            *[A(t.strip(), _href=URL(args='_search', vars=dict(q=t)))
              for t in tags or [] if t.strip()])

    def markmin_render(self, page):
        return self.markmin_base(page.body) + self.render_tags(page.tags).xml()

    def html_render(self, page):
        html = page.body
        # @///function -> http://..../function
        html = replace_at_urls(html, URL)
        # http://...jpg -> <img src="http://...jpg/> or embed
        html = replace_autolinks(html, lambda link: expand_one(link, {}))
        # @{component:name} -> <script>embed component name</script>
        html = replace_components(html, self.env)
        html = html + self.render_tags(page.tags).xml()
        return html

    @staticmethod
    def component(text):
        """
        In wiki docs allows `@{component:controller/function/args}`
        which renders as a `LOAD(..., ajax=True)`
        """
        items = text.split('/')
        controller, function, args = items[0], items[1], items[2:]
        return LOAD(controller, function, args=args, ajax=True).xml()

    def get_renderer(self):
        if isinstance(self.settings.render, basestring):
            r = getattr(self, "%s_render" % self.settings.render)
        elif callable(self.settings.render):
            r = self.settings.render
        elif isinstance(self.settings.render, dict):
            def custom_render(page):
                if page.render:
                    if page.render in self.settings.render.keys():
                        my_render = self.settings.render[page.render]
                    else:
                        my_render = getattr(self, "%s_render" % page.render)
                else:
                    my_render = self.markmin_render
                return my_render(page)
            r = custom_render
        else:
            raise ValueError(
                "Invalid render type %s" % type(self.settings.render))
        return r

    def __init__(self, auth, env=None, render='markmin',
                 manage_permissions=False, force_prefix='',
                 restrict_search=False, extra=None,
                 menu_groups=None, templates=None, migrate=True,
                 controller=None, function=None, groups=None):

        settings = self.settings = auth.settings.wiki

        """
        Args:
            render:

                - "markmin"
                - "html"
                - `<function>` : Sets a custom render function
                - `dict(html=<function>, markmin=...)`: dict(...) allows
                   multiple custom render functions
                - "multiple" : Is the same as `{}`. It enables per-record
                   formats using builtins

        """
        engines = set(['markmin', 'html'])
        show_engine = False
        if render == "multiple":
            render = {}
        if isinstance(render, dict):
            [engines.add(key) for key in render]
            show_engine = True
        settings.render = render
        perms = settings.manage_permissions = manage_permissions

        settings.force_prefix = force_prefix
        settings.restrict_search = restrict_search
        settings.extra = extra or {}
        settings.menu_groups = menu_groups
        settings.templates = templates
        settings.controller = controller
        settings.function = function
        settings.groups = auth.user_groups.values() \
            if groups is None else groups

        db = auth.db
        self.env = env or {}
        self.env['component'] = Wiki.component
        self.auth = auth
        self.wiki_menu_items = None

        if self.auth.user:
            self.settings.force_prefix = force_prefix % self.auth.user
        else:
            self.settings.force_prefix = force_prefix

        self.host = current.request.env.http_host

        table_definitions = [
            ('wiki_page', {
                'args': [
                    Field('slug',
                          requires=[IS_SLUG(),
                                    IS_NOT_IN_DB(db, 'wiki_page.slug')],
                          writable=False),
                    Field('title', length=255, unique=True),
                    Field('body', 'text', notnull=True),
                    Field('tags', 'list:string'),
                    Field('can_read', 'list:string',
                          writable=perms,
                          readable=perms,
                          default=[Wiki.everybody]),
                    Field('can_edit', 'list:string',
                          writable=perms, readable=perms,
                          default=[Wiki.everybody]),
                    Field('changelog'),
                    Field('html', 'text',
                          compute=self.get_renderer(),
                          readable=False, writable=False),
                    Field('render', default="markmin",
                          readable=show_engine,
                          writable=show_engine,
                          requires=IS_EMPTY_OR(
                              IS_IN_SET(engines))),
                    auth.signature],
                'vars': {'format': '%(title)s', 'migrate': migrate}}),
            ('wiki_tag', {
                'args': [
                    Field('name'),
                    Field('wiki_page', 'reference wiki_page'),
                    auth.signature],
                'vars':{'format': '%(title)s', 'migrate': migrate}}),
            ('wiki_media', {
                'args': [
                    Field('wiki_page', 'reference wiki_page'),
                    Field('title', required=True),
                    Field('filename', 'upload', required=True),
                    auth.signature],
                'vars': {'format': '%(title)s', 'migrate': migrate}}),
        ]

        # define only non-existent tables
        for key, value in table_definitions:
            args = []
            if key not in db.tables():
                # look for wiki_ extra fields in auth.settings
                extra_fields = auth.settings.extra_fields
                if extra_fields:
                    if key in extra_fields:
                        if extra_fields[key]:
                            for field in extra_fields[key]:
                                args.append(field)
                args += value['args']
                db.define_table(key, *args, **value['vars'])

        if self.settings.templates is None and not self.settings.manage_permissions:
            self.settings.templates = \
                db.wiki_page.tags.contains('template') & db.wiki_page.can_read.contains('everybody')

        def update_tags_insert(page, id, db=db):
            for tag in page.tags or []:
                tag = tag.strip().lower()
                if tag:
                    db.wiki_tag.insert(name=tag, wiki_page=id)

        def update_tags_update(dbset, page, db=db):
            page = dbset.select(limitby=(0, 1)).first()
            db(db.wiki_tag.wiki_page == page.id).delete()
            for tag in page.tags or []:
                tag = tag.strip().lower()
                if tag:
                    db.wiki_tag.insert(name=tag, wiki_page=page.id)
        db.wiki_page._after_insert.append(update_tags_insert)
        db.wiki_page._after_update.append(update_tags_update)

        if (auth.user and
            check_credentials(current.request, gae_login=False) and
            'wiki_editor' not in auth.user_groups.values() and
                self.settings.groups == auth.user_groups.values()):
            group = db.auth_group(role='wiki_editor')
            gid = group.id if group else db.auth_group.insert(
                role='wiki_editor')
            auth.add_membership(gid)

        settings.lock_keys = True

    # WIKI ACCESS POLICY

    def not_authorized(self, page=None):
        raise HTTP(401)

    def can_read(self, page):
        if 'everybody' in page.can_read or not self.settings.manage_permissions:
            return True
        elif self.auth.user:
            groups = self.settings.groups
            if ('wiki_editor' in groups or
                    set(groups).intersection(set(page.can_read + page.can_edit)) or
                    page.created_by == self.auth.user.id):
                return True
        return False

    def can_edit(self, page=None):
        if not self.auth.user:
            redirect(self.auth.settings.login_url)
        groups = self.settings.groups
        return ('wiki_editor' in groups or
                (page is None and 'wiki_author' in groups) or
                page is not None and (set(groups).intersection(set(page.can_edit)) or
                                      page.created_by == self.auth.user.id))

    def can_manage(self):
        if not self.auth.user:
            return False
        groups = self.settings.groups
        return 'wiki_editor' in groups

    def can_search(self):
        return True

    def can_see_menu(self):
        if self.auth.user:
            if self.settings.menu_groups is None:
                return True
            else:
                groups = self.settings.groups
                if any(t in self.settings.menu_groups for t in groups):
                    return True
        return False

    # END POLICY

    def automenu(self):
        """adds the menu if not present"""
        if (not self.wiki_menu_items and self.settings.controller and self.settings.function):
            self.wiki_menu_items = self.menu(self.settings.controller,
                                             self.settings.function)
            current.response.menu += self.wiki_menu_items

    def __call__(self):
        request = current.request
        settings = self.settings
        settings.controller = settings.controller or request.controller
        settings.function = settings.function or request.function
        self.automenu()

        zero = request.args(0) or 'index'
        if zero and zero.isdigit():
            return self.media(int(zero))
        elif not zero or not zero.startswith('_'):
            return self.read(zero)
        elif zero == '_edit':
            return self.edit(request.args(1) or 'index', request.args(2) or 0)
        elif zero == '_editmedia':
            return self.editmedia(request.args(1) or 'index')
        elif zero == '_create':
            return self.create()
        elif zero == '_pages':
            return self.pages()
        elif zero == '_search':
            return self.search()
        elif zero == '_recent':
            ipage = int(request.vars.page or 0)
            query = self.auth.db.wiki_page.created_by == request.args(
                1, cast=int)
            return self.search(query=query,
                               orderby=~self.auth.db.wiki_page.created_on,
                               limitby=(ipage * self.rows_page,
                                        (ipage + 1) * self.rows_page),
                               )
        elif zero == '_cloud':
            return self.cloud()
        elif zero == '_preview':
            return self.preview(self.get_renderer())

    def first_paragraph(self, page):
        if not self.can_read(page):
            mm = (page.body or '').replace('\r', '')
            ps = [p for p in mm.split('\n\n') if not p.startswith('#') and p.strip()]
            if ps:
                return ps[0]
        return ''

    def fix_hostname(self, body):
        return (body or '').replace('://HOSTNAME', '://%s' % self.host)

    def read(self, slug, force_render=False):
        if slug in '_cloud':
            return self.cloud()
        elif slug in '_search':
            return self.search()
        page = self.auth.db.wiki_page(slug=slug)
        if page and (not self.can_read(page)):
            return self.not_authorized(page)
        if current.request.extension == 'html':
            if not page:
                url = URL(args=('_create', slug))
                return dict(content=A('Create page "%s"' % slug, _href=url, _class="btn"))
            else:
                html = page.html if not force_render else self.get_renderer()(page)
                content = XML(self.fix_hostname(html))
                return dict(title=page.title,
                            slug=page.slug,
                            page=page,
                            content=content,
                            tags=page.tags,
                            created_on=page.created_on,
                            modified_on=page.modified_on)
        elif current.request.extension == 'load':
            return self.fix_hostname(page.html) if page else ''
        else:
            if not page:
                raise HTTP(404)
            else:
                return dict(title=page.title,
                            slug=page.slug,
                            page=page,
                            content=page.body,
                            tags=page.tags,
                            created_on=page.created_on,
                            modified_on=page.modified_on)

    def edit(self, slug, from_template=0):
        auth = self.auth
        db = auth.db
        page = db.wiki_page(slug=slug)
        if not self.can_edit(page):
            return self.not_authorized(page)
        title_guess = ' '.join(c.capitalize() for c in slug.split('-'))
        if not page:
            if not (self.can_manage() or
                    slug.startswith(self.settings.force_prefix)):
                current.session.flash = 'slug must have "%s" prefix' \
                    % self.settings.force_prefix
                redirect(URL(args=('_create')))
            db.wiki_page.can_read.default = [Wiki.everybody]
            db.wiki_page.can_edit.default = [auth.user_group_role()]
            db.wiki_page.title.default = title_guess
            db.wiki_page.slug.default = slug
            if slug == 'wiki-menu':
                db.wiki_page.body.default = \
                    '- Menu Item > @////index\n- - Submenu > http://web2py.com'
            else:
                db.wiki_page.body.default = db(db.wiki_page.id == from_template).select(db.wiki_page.body)[0].body \
                    if int(from_template) > 0 else '## %s\n\npage content' % title_guess
        vars = current.request.post_vars
        if vars.body:
            vars.body = vars.body.replace('://%s' % self.host, '://HOSTNAME')
        form = SQLFORM(db.wiki_page, page, deletable=True,
                       formstyle='table2cols', showid=False).process()
        if form.deleted:
            current.session.flash = 'page deleted'
            redirect(URL())
        elif form.accepted:
            current.session.flash = 'page created'
            redirect(URL(args=slug))
        script = """
        jQuery(function() {
            if (!jQuery('#wiki_page_body').length) return;
            var pagecontent = jQuery('#wiki_page_body');
            pagecontent.css('font-family',
                            'Monaco,Menlo,Consolas,"Courier New",monospace');
            var prevbutton = jQuery('<button class="btn nopreview">Preview</button>');
            var preview = jQuery('<div id="preview"></div>').hide();
            var previewmedia = jQuery('<div id="previewmedia"></div>');
            var form = pagecontent.closest('form');
            preview.insertBefore(form);
            prevbutton.insertBefore(form);
            if(%(link_media)s) {
              var mediabutton = jQuery('<button class="btn nopreview">Media</button>');
              mediabutton.insertBefore(form);
              previewmedia.insertBefore(form);
              mediabutton.click(function() {
                if (mediabutton.hasClass('nopreview')) {
                    web2py_component('%(urlmedia)s', 'previewmedia');
                } else {
                    previewmedia.empty();
                }
                mediabutton.toggleClass('nopreview');
              });
            }
            prevbutton.click(function(e) {
                e.preventDefault();
                if (prevbutton.hasClass('nopreview')) {
                    prevbutton.addClass('preview').removeClass(
                        'nopreview').html('Edit Source');
                    try{var wiki_render = jQuery('#wiki_page_render').val()}
                    catch(e){var wiki_render = null;}
                    web2py_ajax_page('post', \
                        '%(url)s', {body: jQuery('#wiki_page_body').val(), \
                                    render: wiki_render}, 'preview');
                    form.fadeOut('fast', function() {preview.fadeIn()});
                } else {
                    prevbutton.addClass(
                        'nopreview').removeClass('preview').html('Preview');
                    preview.fadeOut('fast', function() {form.fadeIn()});
                }
            })
        })
        """ % dict(url=URL(args=('_preview', slug)), link_media=('true' if page else 'false'),
                   urlmedia=URL(extension='load',
                                args=('_editmedia', slug),
                                vars=dict(embedded=1)))
        return dict(content=TAG[''](form, SCRIPT(script)))

    def editmedia(self, slug):
        auth = self.auth
        db = auth.db
        page = db.wiki_page(slug=slug)
        if not (page and self.can_edit(page)):
            return self.not_authorized(page)
        self.auth.db.wiki_media.id.represent = lambda id, row: \
            id if not row.filename else \
            SPAN('@////%i/%s.%s' % (id, IS_SLUG.urlify(row.title.split('.')[0]), row.filename.split('.')[-1]))
        self.auth.db.wiki_media.wiki_page.default = page.id
        self.auth.db.wiki_media.wiki_page.writable = False
        links = []
        csv = True
        create = True
        if current.request.vars.embedded:
            script = "var c = jQuery('#wiki_page_body'); c.val(c.val() + jQuery('%s').text()); return false;"
            fragment = self.auth.db.wiki_media.id.represent
            csv = False
            create = False
            links = [lambda row: A('copy into source', _href='#', _onclick=script % (fragment(row.id, row)))]
        content = SQLFORM.grid(
            self.auth.db.wiki_media.wiki_page == page.id,
            orderby=self.auth.db.wiki_media.title,
            links=links,
            csv=csv,
            create=create,
            args=['_editmedia', slug],
            user_signature=False)
        return dict(content=content)

    def create(self):
        if not self.can_edit():
            return self.not_authorized()
        db = self.auth.db
        slugs = db(db.wiki_page.id > 0).select(db.wiki_page.id, db.wiki_page.slug)
        options = [OPTION(row.slug, _value=row.id) for row in slugs]
        options.insert(0, OPTION('', _value=''))
        fields = [Field("slug", default=current.request.args(1) or
                        self.settings.force_prefix,
                        requires=(IS_SLUG(), IS_NOT_IN_DB(db, db.wiki_page.slug))), ]
        if self.settings.templates:
            fields.append(
                Field("from_template", "reference wiki_page",
                      requires=IS_EMPTY_OR(IS_IN_DB(db(self.settings.templates), db.wiki_page._id, '%(slug)s')),
                      comment=current.T("Choose Template or empty for new Page")))
        form = SQLFORM.factory(*fields, **dict(_class="well"))
        form.element("[type=submit]").attributes["_value"] = \
            current.T("Create Page from Slug")

        if form.process().accepted:
            form.vars.from_template = 0 if not form.vars.from_template else form.vars.from_template
            redirect(URL(args=('_edit', form.vars.slug, form.vars.from_template or 0)))  # added param
        return dict(content=form)

    def pages(self):
        if not self.can_manage():
            return self.not_authorized()
        self.auth.db.wiki_page.slug.represent = lambda slug, row: SPAN(
            '@////%s' % slug)
        self.auth.db.wiki_page.title.represent = lambda title, row: \
            A(title, _href=URL(args=row.slug))
        wiki_table = self.auth.db.wiki_page
        content = SQLFORM.grid(
            wiki_table,
            fields=[wiki_table.slug,
                    wiki_table.title, wiki_table.tags,
                    wiki_table.can_read, wiki_table.can_edit],
            links=[
                lambda row:
                    A('edit', _href=URL(args=('_edit', row.slug)), _class='btn'),
                lambda row:
                    A('media', _href=URL(args=('_editmedia', row.slug)), _class='btn')],
            details=False, editable=False, deletable=False, create=False,
            orderby=self.auth.db.wiki_page.title,
            args=['_pages'],
            user_signature=False)

        return dict(content=content)

    def media(self, id):
        request, response, db = current.request, current.response, self.auth.db
        media = db.wiki_media(id)
        if media:
            if self.settings.manage_permissions:
                page = db.wiki_page(media.wiki_page)
                if not self.can_read(page):
                    return self.not_authorized(page)
            request.args = [media.filename]
            m = response.download(request, db)
            current.session.forget()  # get rid of the cookie
            response.headers['Last-Modified'] = \
                request.utcnow.strftime("%a, %d %b %Y %H:%M:%S GMT")
            if 'Content-Disposition' in response.headers:
                del response.headers['Content-Disposition']
            response.headers['Pragma'] = 'cache'
            response.headers['Cache-Control'] = 'private'
            return m
        else:
            raise HTTP(404)

    def menu(self, controller='default', function='index'):
        db = self.auth.db
        request = current.request
        menu_page = db.wiki_page(slug='wiki-menu')
        menu = []
        if menu_page:
            tree = {'': menu}
            regex = re.compile('[\r\n\t]*(?P<base>(\s*\-\s*)+)(?P<title>\w.*?)\s+\>\s+(?P<link>\S+)')
            for match in regex.finditer(self.fix_hostname(menu_page.body)):
                base = match.group('base').replace(' ', '')
                title = match.group('title')
                link = match.group('link')
                title_page = None
                if link.startswith('@'):
                    items = link[2:].split('/')
                    if len(items) > 3:
                        title_page = items[3]
                        link = URL(a=items[0] or None, c=items[1] or controller,
                                   f=items[2] or function, args=items[3:])
                parent = tree.get(base[1:], tree[''])
                subtree = []
                tree[base] = subtree
                parent.append((current.T(title),
                               request.args(0) == title_page,
                               link, subtree))
        if self.can_see_menu():
            submenu = []
            menu.append((current.T('[Wiki]'), None, None, submenu))
            if URL() == URL(controller, function):
                if not str(request.args(0)).startswith('_'):
                    slug = request.args(0) or 'index'
                    mode = 1
                elif request.args(0) == '_edit':
                    slug = request.args(1) or 'index'
                    mode = 2
                elif request.args(0) == '_editmedia':
                    slug = request.args(1) or 'index'
                    mode = 3
                else:
                    mode = 0
                if mode in (2, 3):
                    submenu.append((current.T('View Page'), None,
                                    URL(controller, function, args=slug)))
                if mode in (1, 3):
                    submenu.append((current.T('Edit Page'), None,
                                    URL(controller, function, args=('_edit', slug))))
                if mode in (1, 2):
                    submenu.append((current.T('Edit Page Media'), None,
                                    URL(controller, function, args=('_editmedia', slug))))

            submenu.append((current.T('Create New Page'), None,
                            URL(controller, function, args=('_create'))))
            # Moved next if to inside self.auth.user check
            if self.can_manage():
                submenu.append((current.T('Manage Pages'), None,
                                URL(controller, function, args=('_pages'))))
                submenu.append((current.T('Edit Menu'), None,
                                URL(controller, function, args=('_edit', 'wiki-menu'))))
            # Also moved inside self.auth.user check
            submenu.append((current.T('Search Pages'), None,
                            URL(controller, function, args=('_search'))))
        return menu

    def search(self, tags=None, query=None, cloud=True, preview=True,
               limitby=(0, 100), orderby=None):
        if not self.can_search():
            return self.not_authorized()
        request = current.request
        content = CAT()
        if tags is None and query is None:
            form = FORM(INPUT(_name='q', requires=IS_NOT_EMPTY(),
                              value=request.vars.q),
                        INPUT(_type="submit", _value=current.T('Search')),
                        _method='GET')
            content.append(DIV(form, _class='w2p_wiki_form'))
            if request.vars.q:
                tags = [v.strip() for v in request.vars.q.split(',')]
                tags = [v.lower() for v in tags if v]
        if tags or query is not None:
            db = self.auth.db
            count = db.wiki_tag.wiki_page.count()
            fields = [db.wiki_page.id, db.wiki_page.slug,
                      db.wiki_page.title, db.wiki_page.tags,
                      db.wiki_page.can_read, db.wiki_page.can_edit]
            if preview:
                fields.append(db.wiki_page.body)
            if query is None:
                query = (db.wiki_page.id == db.wiki_tag.wiki_page) &\
                    (db.wiki_tag.name.belongs(tags))
                query = query | db.wiki_page.title.contains(request.vars.q)
            if self.settings.restrict_search and not self.can_manage():
                query = query & (db.wiki_page.created_by == self.auth.user_id)
            pages = db(query).select(count,
                                     *fields, **dict(orderby=orderby or ~count,
                                                     groupby=reduce(lambda a, b: a | b, fields),
                                                     distinct=True,
                                                     limitby=limitby))
            if request.extension in ('html', 'load'):
                if not pages:
                    content.append(DIV(current.T("No results"),
                                       _class='w2p_wiki_form'))

                def link(t):
                    return A(t, _href=URL(args='_search', vars=dict(q=t)))
                items = [DIV(H3(A(p.wiki_page.title, _href=URL(
                    args=p.wiki_page.slug))),
                    MARKMIN(self.first_paragraph(p.wiki_page))
                    if preview else '',
                    DIV(_class='w2p_wiki_tags',
                        *[link(t.strip()) for t in
                          p.wiki_page.tags or [] if t.strip()]),
                    _class='w2p_wiki_search_item')
                    for p in pages]
                content.append(DIV(_class='w2p_wiki_pages', *items))
            else:
                cloud = False
                content = [p.wiki_page.as_dict() for p in pages]
        elif cloud:
            content.append(self.cloud()['content'])
        if request.extension == 'load':
            return content
        return dict(content=content)

    def cloud(self):
        db = self.auth.db
        count = db.wiki_tag.wiki_page.count(distinct=True)
        ids = db(db.wiki_tag).select(
            db.wiki_tag.name, count,
            distinct=True,
            groupby=db.wiki_tag.name,
            orderby=~count, limitby=(0, 20))
        if ids:
            a, b = ids[0](count), ids[-1](count)

        def style(c):
            STYLE = 'padding:0 0.2em;line-height:%.2fem;font-size:%.2fem'
            size = (1.5 * (c - b) / max(a - b, 1) + 1.3)
            return STYLE % (1.3, size)
        items = []
        for item in ids:
            items.append(A(item.wiki_tag.name,
                           _style=style(item(count)),
                           _href=URL(args='_search',
                                     vars=dict(q=item.wiki_tag.name))))
            items.append(' ')
        return dict(content=DIV(_class='w2p_cloud', *items))

    def preview(self, render):
        request = current.request
        # FIXME: This is an ugly hack to ensure a default render
        # engine if not specified (with multiple render engines)
        if 'render' not in request.post_vars:
            request.post_vars.render = None
        return render(request.post_vars)


class Config(object):

    def __init__(
        self,
        filename,
        section,
        default_values={}
    ):
        self.config = configparser.ConfigParser(default_values)
        self.config.read(filename)
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.section = section
        self.filename = filename

    def read(self):
        if not(isinstance(current.session['settings_%s' % self.section], dict)):
            settings = dict(self.config.items(self.section))
        else:
            settings = current.session['settings_%s' % self.section]
        return settings

    def save(self, options):
        for option, value in options:
            self.config.set(self.section, option, value)
        try:
            self.config.write(open(self.filename, 'w'))
            result = True
        except:
            current.session['settings_%s' % self.section] = dict(self.config.items(self.section))
            result = False
        return result

if __name__ == '__main__':
    import doctest
    doctest.testmod()
