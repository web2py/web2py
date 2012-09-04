#!/bin/python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""

import base64
import cPickle
import datetime
import thread
import logging
import sys
import glob
import os
import re
import time
import traceback
import smtplib
import urllib
import urllib2
import Cookie
import cStringIO
from email import MIMEBase, MIMEMultipart, MIMEText, Encoders, Header, message_from_string

from contenttype import contenttype
from storage import Storage, StorageList, Settings, Messages
from utils import web2py_uuid
from fileutils import read_file, check_credentials
from gluon import *
from gluon.contrib.autolinks import expand_one
from gluon.dal import Row

import serializers

try:
    import json as json_parser                      # try stdlib (Python 2.6)
except ImportError:
    try:
        import simplejson as json_parser            # try external module
    except:
        import contrib.simplejson as json_parser    # fallback to pure-Python module

__all__ = ['Mail', 'Auth', 'Recaptcha', 'Crud', 'Service', 'Wiki',
           'PluginManager', 'fetch', 'geocode', 'prettydate']

### mind there are two loggers here (logger and crud.settings.logger)!
logger = logging.getLogger("web2py")

DEFAULT = lambda: None

def getarg(position,default=None):
    args = current.request.args
    if position<0 and len(args)>=-position:
        return args[position]
    elif position>=0 and len(args)>position:
        return args[position]
    else:
        return default

def callback(actions,form,tablename=None):
    if actions:
        if tablename and isinstance(actions,dict):
            actions = actions.get(tablename, [])
        if not isinstance(actions,(list, tuple)):
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

def call_or_redirect(f,*args):
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
    """

    class Attachment(MIMEBase.MIMEBase):
        """
        Email attachment

        Arguments:

            payload: path to file or file-like object with read() method
            filename: name of the attachment stored in message; if set to
                      None, it will be fetched from payload path; file-like
                      object payload must have explicit filename specified
            content_id: id of the attachment; automatically contained within
                        < and >
            content_type: content type of the attachment; if set to None,
                          it will be fetched from filename using gluon.contenttype
                          module
            encoding: encoding of all strings passed to this function (except
                      attachment body)

        Content ID is used to identify attachments within the html body;
        in example, attached image with content ID 'photo' may be used in
        html message as a source of img tag <img src="cid:photo" />.

        Examples:

            #Create attachment from text file:
            attachment = Mail.Attachment('/path/to/file.txt')

            Content-Type: text/plain
            MIME-Version: 1.0
            Content-Disposition: attachment; filename="file.txt"
            Content-Transfer-Encoding: base64

            SOMEBASE64CONTENT=

            #Create attachment from image file with custom filename and cid:
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
            filename = filename.encode(encoding)
            if content_type is None:
                content_type = contenttype(filename)
            self.my_filename = filename
            self.my_payload = payload
            MIMEBase.MIMEBase.__init__(self, *content_type.split('/', 1))
            self.set_payload(payload)
            self['Content-Disposition'] = 'attachment; filename="%s"' % filename
            if not content_id is None:
                self['Content-Id'] = '<%s>' % content_id.encode(encoding)
            Encoders.encode_base64(self)

    def __init__(self, server=None, sender=None, login=None, tls=True):
        """
        Main Mail object

        Arguments:

            server: SMTP server address in address:port notation
            sender: sender email address
            login: sender login name and password in login:password notation
                   or None if no authentication is required
            tls: enables/disables encryption (True by default)

        In Google App Engine use:

            server='gae'

        For sake of backward compatibility all fields are optional and default
        to None, however, to be able to send emails at least server and sender
        must be specified. They are available under following fields:

            mail.settings.server
            mail.settings.sender
            mail.settings.login

        When server is 'logging', email is logged but not sent (debug mode)

        Optionally you can use PGP encryption or X509:

            mail.settings.cipher_type = None
            mail.settings.gpg_home = None
            mail.settings.sign = True
            mail.settings.sign_passphrase = None
            mail.settings.encrypt = True
            mail.settings.x509_sign_keyfile = None
            mail.settings.x509_sign_certfile = None
            mail.settings.x509_nocerts = False
            mail.settings.x509_crypt_certfiles = None

            cipher_type       : None
                                gpg - need a python-pyme package and gpgme lib
                                x509 - smime
            gpg_home          : you can set a GNUPGHOME environment variable
                                to specify home of gnupg
            sign              : sign the message (True or False)
            sign_passphrase   : passphrase for key signing
            encrypt           : encrypt the message
                             ... x509 only ...
            x509_sign_keyfile : the signers private key filename (PEM format)
            x509_sign_certfile: the signers certificate filename (PEM format)
            x509_nocerts      : if True then no attached certificate in mail
            x509_crypt_certfiles: the certificates file to encrypt the messages
                                  with can be a file name or a list of
                                  file names (PEM format)

        Examples:

            #Create Mail object with authentication data for remote server:
            mail = Mail('example.com:25', 'me@example.com', 'me:password')
        """

        settings = self.settings = Settings()
        settings.server = server
        settings.sender = sender
        settings.login = login
        settings.tls = tls
        settings.ssl = False
        settings.cipher_type = None
        settings.gpg_home = None
        settings.sign = True
        settings.sign_passphrase = None
        settings.encrypt = True
        settings.x509_sign_keyfile = None
        settings.x509_sign_certfile = None
        settings.x509_nocerts = False
        settings.x509_crypt_certfiles = None
        settings.debug = False
        settings.lock_keys = True
        self.result = {}
        self.error = None

    def send(
        self,
        to,
        subject='None',
        message='None',
        attachments=None,
        cc=None,
        bcc=None,
        reply_to=None,
        encoding='utf-8',
        raw=False,
        headers={}
        ):
        """
        Sends an email using data specified in constructor

        Arguments:

            to: list or tuple of receiver addresses; will also accept single
                object
            subject: subject of the email
            message: email body text; depends on type of passed object:
                     if 2-list or 2-tuple is passed: first element will be
                     source of plain text while second of html text;
                     otherwise: object will be the only source of plain text
                     and html source will be set to None;
                     If text or html source is:
                     None: content part will be ignored,
                     string: content part will be set to it,
                     file-like object: content part will be fetched from
                                       it using it's read() method
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
                     sending mail, e.g. {'Return-Path' : 'bounces@example.org'}

        Examples:

            #Send plain text message to single address:
            mail.send('you@example.com',
                      'Message subject',
                      'Plain text body of the message')

            #Send html message to single address:
            mail.send('you@example.com',
                      'Message subject',
                      '<html>Plain text body of the message</html>')

            #Send text and html message to three addresses (two in cc):
            mail.send('you@example.com',
                      'Message subject',
                      ('Plain text body', '<html>html body</html>'),
                      cc=['other1@example.com', 'other2@example.com'])

            #Send html only message with image attachment available from
            the message by 'photo' content id:
            mail.send('you@example.com',
                      'Message subject',
                      (None, '<html><img src="cid:photo" /></html>'),
                      Mail.Attachment('/path/to/photo.jpg'
                                      content_id='photo'))

            #Send email with two attachments and no body text
            mail.send('you@example.com,
                      'Message subject',
                      None,
                      [Mail.Attachment('/path/to/fist.file'),
                       Mail.Attachment('/path/to/second.file')])

        Returns True on success, False on failure.

        Before return, method updates two object's fields:
        self.result: return value of smtplib.SMTP.sendmail() or GAE's
                     mail.send_mail() method
        self.error: Exception message or None if above was successful
        """

        def encode_header(key):
            if [c for c in key if 32>ord(c) or ord(c)>127]:
                return Header.Header(key.encode('utf-8'),'utf-8')
            else:
                return key

        # encoded or raw text
        def encoded_or_raw(text):
            if raw:
                text = encode_header(text)
            return text

        if not isinstance(self.settings.server, str):
            raise Exception('Server address not specified')
        if not isinstance(self.settings.sender, str):
            raise Exception('Sender address not specified')

        if not raw:
            payload_in = MIMEMultipart.MIMEMultipart('mixed')
        else:
            # no encoding configuration for raw messages
            if isinstance(message, basestring):
                text = message.decode(encoding).encode('utf-8')
            else:
                text = message.read().decode(encoding).encode('utf-8')
            # No charset passed to avoid transport encoding
            # NOTE: some unicode encoded strings will produce
            # unreadable mail contents.
            payload_in = MIMEText.MIMEText(text)
        if to:
            if not isinstance(to, (list,tuple)):
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
        elif message.strip().startswith('<html') and message.strip().endswith('</html>'):
            text = self.settings.server=='gae' and message or None
            html = message
        else:
            text = message
            html = None

        if (not text is None or not html is None) and (not raw):
            attachment = MIMEMultipart.MIMEMultipart('alternative')
            if not text is None:
                if isinstance(text, basestring):
                    text = text.decode(encoding).encode('utf-8')
                else:
                    text = text.read().decode(encoding).encode('utf-8')
                attachment.attach(MIMEText.MIMEText(text,_charset='utf-8'))
            if not html is None:
                if isinstance(html, basestring):
                    html = html.decode(encoding).encode('utf-8')
                else:
                    html = html.read().decode(encoding).encode('utf-8')
                attachment.attach(MIMEText.MIMEText(html, 'html',_charset='utf-8'))
            payload_in.attach(attachment)
        if (attachments is None) or raw:
            pass
        elif isinstance(attachments, (list, tuple)):
            for attachment in attachments:
                payload_in.attach(attachment)
        else:
            payload_in.attach(attachments)


        #######################################################
        #                      CIPHER                         #
        #######################################################
        cipher_type = self.settings.cipher_type
        sign = self.settings.sign
        sign_passphrase = self.settings.sign_passphrase
        encrypt = self.settings.encrypt
        #######################################################
        #                       GPGME                         #
        #######################################################
        if cipher_type == 'gpg':
            if self.settings.gpg_home:
                # Set GNUPGHOME environment variable to set home of gnupg
                import os
                os.environ['GNUPGHOME'] = self.settings.gpg_home
            if not sign and not encrypt:
                self.error="No sign and no encrypt is set but cipher type to gpg"
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
                pin=string.replace(payload_in.as_string(),'\n','\r\n')
                plain = core.Data(pin)
                sig = core.Data()
                c = core.Context()
                c.set_armor(1)
                c.signers_clear()
                # search for signing key for From:
                for sigkey in c.op_keylist_all(self.settings.sender, 1):
                    if sigkey.can_sign:
                        c.signers_add(sigkey)
                if not c.signers_enum(0):
                    self.error='No key for signing [%s]' % self.settings.sender
                    return False
                c.set_passphrase_cb(lambda x,y,z: sign_passphrase)
                try:
                    # make a signature
                    c.op_sign(plain,sig,mode.DETACH)
                    sig.seek(0,0)
                    # make it part of the email
                    payload=MIMEMultipart.MIMEMultipart('signed',
                                                        boundary=None,
                                                        _subparts=None,
                                                        **dict(micalg="pgp-sha1",
                                                               protocol="application/pgp-signature"))
                    # insert the origin payload
                    payload.attach(payload_in)
                    # insert the detached signature
                    p=MIMEBase.MIMEBase("application",'pgp-signature')
                    p.set_payload(sig.read())
                    payload.attach(p)
                    # it's just a trick to handle the no encryption case
                    payload_in=payload
                except errors.GPGMEError, ex:
                    self.error="GPG error: %s" % ex.getstring()
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
                recipients=[]
                rec=to[:]
                if cc:
                    rec.extend(cc)
                if bcc:
                    rec.extend(bcc)
                for addr in rec:
                    c.op_keylist_start(addr,0)
                    r = c.op_keylist_next()
                    if r is None:
                        self.error='No key for [%s]' % addr
                        return False
                    recipients.append(r)
                try:
                    # make the encryption
                    c.op_encrypt(recipients, 1, plain, cipher)
                    cipher.seek(0,0)
                    # make it a part of the email
                    payload=MIMEMultipart.MIMEMultipart('encrypted',
                                                        boundary=None,
                                                        _subparts=None,
                                                        **dict(protocol="application/pgp-encrypted"))
                    p=MIMEBase.MIMEBase("application",'pgp-encrypted')
                    p.set_payload("Version: 1\r\n")
                    payload.attach(p)
                    p=MIMEBase.MIMEBase("application",'octet-stream')
                    p.set_payload(cipher.read())
                    payload.attach(p)
                except errors.GPGMEError, ex:
                    self.error="GPG error: %s" % ex.getstring()
                    return False
        #######################################################
        #                       X.509                         #
        #######################################################
        elif cipher_type == 'x509':
            if not sign and not encrypt:
                self.error = "No sign and no encrypt is set but cipher type to x509"
                return False
            x509_sign_keyfile = self.settings.x509_sign_keyfile
            if self.settings.x509_sign_certfile:
                x509_sign_certfile = self.settings.x509_sign_certfile
            else:
                # if there is no sign certfile we'll assume the
                # cert is in keyfile
                x509_sign_certfile = self.settings.x509_sign_keyfile
            # crypt certfiles could be a string or a list
            x509_crypt_certfiles = self.settings.x509_crypt_certfiles
            x509_nocerts = self.settings.x509_nocerts

            # need m2crypto
            try:
                from M2Crypto import BIO, SMIME, X509
            except Exception, e:
                self.error = "Can't load M2Crypto module"
                return False
            msg_bio = BIO.MemoryBuffer( payload_in.as_string() )
            s = SMIME.SMIME()

            #                   SIGN
            if sign:
                #key for signing
                try:
                    s.load_key( x509_sign_keyfile, x509_sign_certfile, callback = lambda x: sign_passphrase )
                except Exception, e:
                    self.error = "Something went wrong on certificate / private key loading: <%s>" % str( e )
                    return False
                try:
                    if x509_nocerts:
                        flags = SMIME.PKCS7_NOCERTS
                    else:
                        flags = 0
                    if not encrypt:
                        flags += SMIME.PKCS7_DETACHED
                    p7 = s.sign( msg_bio, flags = flags )
                    msg_bio = BIO.MemoryBuffer( payload_in.as_string() ) # Recreate coz sign() has consumed it.
                except Exception, e:
                    self.error = "Something went wrong on signing: <%s> %s" % ( str( e ), str( flags ) )
                    return False

            #                   ENCRYPT
            if encrypt:
                try:
                    sk = X509.X509_Stack()
                    if not isinstance(x509_crypt_certfiles, (list, tuple)):
                        x509_crypt_certfiles = [x509_crypt_certfiles]

                    # make an encryption cert's stack
                    for x in x509_crypt_certfiles:
                        sk.push(X509.load_cert(x))
                    s.set_x509_stack(sk)

                    s.set_cipher(SMIME.Cipher('des_ede3_cbc'))
                    tmp_bio = BIO.MemoryBuffer()
                    if sign:
                        s.write(tmp_bio, p7)
                    else:
                        tmp_bio.write(payload_in.as_string())
                    p7 = s.encrypt(tmp_bio)
                except Exception,e:
                    self.error="Something went wrong on encrypting: <%s>" %str(e)
                    return False

            #                 Final stage in sign and encryption
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
            st=str(out.read())
            payload=message_from_string(st)
        else:
            # no cryptography process as usual
            payload=payload_in

        payload['From'] = encoded_or_raw(self.settings.sender.decode(encoding))
        origTo = to[:]
        if to:
            payload['To'] = encoded_or_raw(', '.join(to).decode(encoding))
        if reply_to:
            payload['Reply-To'] = encoded_or_raw(reply_to.decode(encoding))
        if cc:
            payload['Cc'] = encoded_or_raw(', '.join(cc).decode(encoding))
            to.extend(cc)
        if bcc:
            to.extend(bcc)
        payload['Subject'] = encoded_or_raw(subject.decode(encoding))
        payload['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S +0000",
                                        time.gmtime())
        for k,v in headers.iteritems():
            payload[k] = encoded_or_raw(v.decode(encoding))
        result = {}
        try:
            if self.settings.server == 'logging':
                logger.warn('email not sent\n%s\nFrom: %s\nTo: %s\nSubject: %s\n\n%s\n%s\n' % \
                                ('-'*40,self.settings.sender,
                                 ', '.join(to),subject,
                                 text or html,'-'*40))
            elif self.settings.server == 'gae':
                xcc = dict()
                if cc:
                    xcc['cc'] = cc
                if bcc:
                    xcc['bcc'] = bcc
                if reply_to:
                    xcc['reply_to'] = reply_to
                from google.appengine.api import mail
                attachments = attachments and [(a.my_filename,a.my_payload) for a in attachments if not raw]
                if attachments:
                    result = mail.send_mail(sender=self.settings.sender, to=origTo,
                                            subject=subject, body=text, html=html,
                                            attachments=attachments, **xcc)
                elif html and (not raw):
                    result = mail.send_mail(sender=self.settings.sender, to=origTo,
                                            subject=subject, body=text, html=html, **xcc)
                else:
                    result = mail.send_mail(sender=self.settings.sender, to=origTo,
                                            subject=subject, body=text, **xcc)
            else:
                smtp_args = self.settings.server.split(':')
                if self.settings.ssl:
                    server = smtplib.SMTP_SSL(*smtp_args)
                else:
                    server = smtplib.SMTP(*smtp_args)
                if self.settings.tls and not self.settings.ssl:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                if self.settings.login:
                    server.login(*self.settings.login.split(':',1))
                result = server.sendmail(self.settings.sender, to, payload.as_string())
                server.quit()
        except Exception, e:
            logger.warn('Mail.send failure:%s' % e)
            self.result = result
            self.error = e
            return False
        self.result = result
        self.error = None
        return True


class Recaptcha(DIV):

    """
    Usage:

        form = FORM(Recaptcha(public_key='...',private_key='...'))

    or

        form = SQLFORM(...)
        form.append(Recaptcha(public_key='...',private_key='...'))
    """

    API_SSL_SERVER = 'https://www.google.com/recaptcha/api'
    API_SERVER = 'http://www.google.com/recaptcha/api'
    VERIFY_SERVER = 'http://www.google.com/recaptcha/api/verify'

    def __init__(
        self,
        request=None,
        public_key='',
        private_key='',
        use_ssl=False,
        error=None,
        error_message='invalid',
        label = 'Verify:',
        options = ''
        ):
        self.request_vars = request and request.vars or current.request.vars
        self.remote_addr = request.env.remote_addr
        self.public_key = public_key
        self.private_key = private_key
        self.use_ssl = use_ssl
        self.error = error
        self.errors = Storage()
        self.error_message = error_message
        self.components = []
        self.attributes = {}
        self.label = label
        self.options = options
        self.comment = ''

    def _validate(self):

        # for local testing:

        recaptcha_challenge_field = \
            self.request_vars.recaptcha_challenge_field
        recaptcha_response_field = \
            self.request_vars.recaptcha_response_field
        private_key = self.private_key
        remoteip = self.remote_addr
        if not (recaptcha_response_field and recaptcha_challenge_field
                 and len(recaptcha_response_field)
                 and len(recaptcha_challenge_field)):
            self.errors['captcha'] = self.error_message
            return False
        params = urllib.urlencode({
            'privatekey': private_key,
            'remoteip': remoteip,
            'challenge': recaptcha_challenge_field,
            'response': recaptcha_response_field,
            })
        request = urllib2.Request(
            url=self.VERIFY_SERVER,
            data=params,
            headers={'Content-type': 'application/x-www-form-urlencoded',
                        'User-agent': 'reCAPTCHA Python'})
        httpresp = urllib2.urlopen(request)
        return_values = httpresp.read().splitlines()
        httpresp.close()
        return_code = return_values[0]
        if return_code == 'true':
            del self.request_vars.recaptcha_challenge_field
            del self.request_vars.recaptcha_response_field
            self.request_vars.captcha = ''
            return True
        self.errors['captcha'] = self.error_message
        return False

    def xml(self):
        public_key = self.public_key
        use_ssl = self.use_ssl
        error_param = ''
        if self.error:
            error_param = '&error=%s' % self.error
        if use_ssl:
            server = self.API_SSL_SERVER
        else:
            server = self.API_SERVER
        captcha = DIV(
            SCRIPT("var RecaptchaOptions = {%s};" % self.options),
            SCRIPT(_type="text/javascript",
                   _src="%s/challenge?k=%s%s" % (server,public_key,error_param)),
            TAG.noscript(IFRAME(_src="%s/noscript?k=%s%s" % (server,public_key,error_param),
                                _height="300",_width="500",_frameborder="0"), BR(),
                         INPUT(_type='hidden', _name='recaptcha_response_field',
                               _value='manual_challenge')), _id='recaptcha')
        if not self.errors.captcha:
            return XML(captcha).xml()
        else:
            captcha.append(DIV(self.errors['captcha'], _class='error'))
            return XML(captcha).xml()


def addrow(form, a, b, c, style, _id, position=-1):
    if style == "divs":
        form[0].insert(position, DIV(DIV(LABEL(a),_class='w2p_fl'),
                                     DIV(b, _class='w2p_fw'),
                                     DIV(c, _class='w2p_fc'),
                                     _id = _id))
    elif style == "table2cols":
        form[0].insert(position, TR(TD(LABEL(a),_class='w2p_fl'),
                                    TD(c,_class='w2p_fc')))
        form[0].insert(position+1, TR(TD(b,_class='w2p_fw'),
                                      _colspan=2, _id = _id))
    elif style == "ul":
        form[0].insert(position, LI(DIV(LABEL(a),_class='w2p_fl'),
                                    DIV(b, _class='w2p_fw'),
                                    DIV(c, _class='w2p_fc'),
                                    _id = _id))
    else:
        form[0].insert(position, TR(TD(LABEL(a),_class='w2p_fl'),
                                    TD(b,_class='w2p_fw'),
                                    TD(c,_class='w2p_fc'),_id = _id))


class Auth(object):

    default_settings = dict(
        hideerror = False,
        password_min_length = 4,
        cas_maps = None,
        reset_password_requires_verification = False,
        registration_requires_verification = False,
        registration_requires_approval = False,
        login_after_registration = False,
        login_after_password_change = True,
        alternate_requires_registration = False,
        create_user_groups = "user_%(id)s",
        everybody_group_id = None,
        login_captcha = None,
        register_captcha = None,
        retrieve_username_captcha = None,
        retrieve_password_captcha = None,
        captcha = None,
        expiration = 3600,            # one hour
        long_expiration = 3600*30*24, # one month
        remember_me_form = True,
        allow_basic_login = False,
        allow_basic_login_only = False,
        on_failed_authentication = lambda x: redirect(x),
        formstyle = "table3cols",
        label_separator =  ": ",
        password_field = 'password',
        table_user_name = 'auth_user',
        table_group_name = 'auth_group',
        table_membership_name = 'auth_membership',
        table_permission_name = 'auth_permission',
        table_event_name = 'auth_event',
        table_cas_name = 'auth_cas',
        table_user = None,
        table_group = None,
        table_membership = None,
        table_permission = None,
        table_event = None,
        table_cas = None,
        showid = False,
        use_username = False,
        login_email_validate = True,
        login_userfield = None,
        logout_onlogout = None,
        register_fields = None,
        register_verify_password = True,
        profile_fields = None,
        email_case_sensitive = True,
        username_case_sensitive = True,
        )
        # ## these are messages that can be customized
    default_messages = dict(
        login_button = 'Login',
        register_button = 'Register',
        password_reset_button = 'Request reset password',
        password_change_button = 'Change password',
        profile_save_button = 'Save profile',
        submit_button = 'Submit',
        verify_password = 'Verify Password',
        delete_label = 'Check to delete',
        function_disabled = 'Function disabled',
        access_denied = 'Insufficient privileges',
        registration_verifying = 'Registration needs verification',
        registration_pending = 'Registration is pending approval',
        login_disabled = 'Login disabled by administrator',
        logged_in = 'Logged in',
        email_sent = 'Email sent',
        unable_to_send_email = 'Unable to send email',
        email_verified = 'Email verified',
        logged_out = 'Logged out',
        registration_successful = 'Registration successful',
        invalid_email = 'Invalid email',
        unable_send_email = 'Unable to send email',
        invalid_login = 'Invalid login',
        invalid_user = 'Invalid user',
        invalid_password = 'Invalid password',
        is_empty = "Cannot be empty",
        mismatched_password = "Password fields don't match",
        verify_email = 'Click on the link %(link)s to verify your email',
        verify_email_subject = 'Email verification',
        username_sent = 'Your username was emailed to you',
        new_password_sent = 'A new password was emailed to you',
        password_changed = 'Password changed',
        retrieve_username = 'Your username is: %(username)s',
        retrieve_username_subject = 'Username retrieve',
        retrieve_password = 'Your password is: %(password)s',
        retrieve_password_subject = 'Password retrieve',
        reset_password = \
            'Click on the link %(link)s to reset your password',
        reset_password_subject = 'Password reset',
        invalid_reset_password = 'Invalid reset password',
        profile_updated = 'Profile updated',
        new_password = 'New password',
        old_password = 'Old password',
        group_description = 'Group uniquely assigned to user %(id)s',
        register_log = 'User %(id)s Registered',
        login_log = 'User %(id)s Logged-in',
        login_failed_log = None,
        logout_log = 'User %(id)s Logged-out',
        profile_log = 'User %(id)s Profile updated',
        verify_email_log = 'User %(id)s Verification email sent',
        retrieve_username_log = 'User %(id)s Username retrieved',
        retrieve_password_log = 'User %(id)s Password retrieved',
        reset_password_log = 'User %(id)s Password reset',
        change_password_log = 'User %(id)s Password changed',
        add_group_log = 'Group %(group_id)s created',
        del_group_log = 'Group %(group_id)s deleted',
        add_membership_log = None,
        del_membership_log = None,
        has_membership_log = None,
        add_permission_log = None,
        del_permission_log = None,
        has_permission_log = None,
        impersonate_log = 'User %(id)s is impersonating %(other_id)s',
        label_first_name = 'First name',
        label_last_name = 'Last name',
        label_username = 'Username',
        label_email = 'E-mail',
        label_password = 'Password',
        label_registration_key = 'Registration key',
        label_reset_password_key = 'Reset Password key',
        label_registration_id = 'Registration identifier',
        label_role = 'Role',
        label_description = 'Description',
        label_user_id = 'User ID',
        label_group_id = 'Group ID',
        label_name = 'Name',
        label_table_name = 'Object or table name',
        label_record_id = 'Record ID',
        label_time_stamp = 'Timestamp',
        label_client_ip = 'Client IP',
        label_origin = 'Origin',
        label_remember_me = "Remember me (for 30 days)",
        verify_password_comment = 'please input your password again',
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

    Authentication Example:

        from contrib.utils import *
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

    exposes:

    - http://.../{application}/{controller}/authentication/login
    - http://.../{application}/{controller}/authentication/logout
    - http://.../{application}/{controller}/authentication/register
    - http://.../{application}/{controller}/authentication/verify_email
    - http://.../{application}/{controller}/authentication/retrieve_username
    - http://.../{application}/{controller}/authentication/retrieve_password
    - http://.../{application}/{controller}/authentication/reset_password
    - http://.../{application}/{controller}/authentication/profile
    - http://.../{application}/{controller}/authentication/change_password

    On registration a group with role=new_user.id is created
    and user is given membership of this group.

    You can create a group with:

        group_id=auth.add_group('Manager', 'can access the manage action')
        auth.add_permission(group_id, 'access to manage')

    Here \"access to manage\" is just a user defined string.
    You can give access to a user:

        auth.add_membership(group_id, user_id)

    If user id is omitted, the logged in user is assumed

    Then you can decorate any action:

        @auth.requires_permission('access to manage')
        def manage():
            return dict()

    You can restrict a permission to a specific table:

        auth.add_permission(group_id, 'edit', db.sometable)
        @auth.requires_permission('edit', db.sometable)

    Or to a specific record:

        auth.add_permission(group_id, 'edit', db.sometable, 45)
        @auth.requires_permission('edit', db.sometable, 45)

    If authorization is not granted calls:

        auth.settings.on_failed_authorization

    Other options:

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
            filename = os.path.join(request.folder,'private','auth.key')
        if os.path.exists(filename):
            key = open(filename,'r').read().strip()
        else:
            key = alg+':'+web2py_uuid()
            open(filename,'w').write(key)
        return key

    def url(self, f=None, args=None, vars=None, scheme=False):
        if args is None: args=[]
        if vars is None: vars={}
        return URL(c=self.settings.controller, 
                   f=f, args=args, vars=vars,scheme=scheme)

    def here(self):
        return URL(args=current.request.args,vars=current.request.vars)

    def __init__(self, environment=None, db=None, mailer=True,
                 hmac_key=None, controller='default', function='user',
                 cas_provider=None, signature=True):
        """
        auth=Auth(db)

        - environment is there for legacy but unused (awful)
        - db has to be the database where to create tables for authentication
        - mailer=Mail(...) or None (no mailed) or True (make a mailer)
        - hmac_key can be a hmac_key or hmac_key=Auth.get_or_create_key()
        - controller (where is the user action?)
        - cas_provider (delegate authentication to the URL, CAS2)
        """
        ## next two lines for backward compatibility
        if not db and environment and isinstance(environment,DAL):
            db = environment
        self.db = db
        self.environment = current
        request = current.request
        session = current.session
        auth = session.auth
        self.user_groups = auth and auth.user_groups or {}
        if auth and auth.last_visit and auth.last_visit + \
                datetime.timedelta(days=0, seconds=auth.expiration) > request.now:
            self.user = auth.user
            # this is a trick to speed up sessions
            if (request.now - auth.last_visit).seconds > (auth.expiration/10):
                auth.last_visit = request.now
        else:
            self.user = None
            session.auth = None
        # ## what happens after login?

        self.next = current.request.vars._next
        if isinstance(self.next,(list,tuple)):
            self.next = self.next[0]
        url_index = URL(controller,'index')
        url_login = URL(controller,function,args='login')
        # ## what happens after registration?
            
        settings = self.settings = Settings()
        settings.update(Auth.default_settings)
        settings.update(
            cas_domains = [request.env.http_host],
            cas_provider = cas_provider,
            cas_actions = dict(login ='login',
                               validate ='validate',
                               servicevalidate ='serviceValidate',
                               proxyvalidate ='proxyValidate',
                               logout ='logout'),
            extra_fields = {},
            actions_disabled = [],
            controller = controller,
            function = function,
            login_url = url_login,
            logged_url = URL(controller, function, args='profile'),
            download_url = URL(controller,'download'),
            mailer = (mailer==True) and Mail() or mailer,
            on_failed_authorization = \
                URL(controller,function, args='not_authorized'),
            login_next = url_index,
            login_onvalidation = [],
            login_onaccept = [],
            login_methods = [self],
            login_form = self,
            logout_next = url_index,
            logout_onlogout = None,
            register_next = url_index,
            register_onvalidation = [],
            register_onaccept = [],
            verify_email_next = url_login,
            verify_email_onaccept = [],
            profile_next = url_index,
            profile_onvalidation = [],
            profile_onaccept = [],
            retrieve_username_next = url_index,
            retrieve_password_next = url_index,
            request_reset_password_next = url_login,
            reset_password_next = url_index,
            change_password_next = url_index,
            change_password_onvalidation = [],
            change_password_onaccept = [],
            retrieve_password_onvalidation = [],
            reset_password_onvalidation = [],
            reset_password_onaccept = [],
            hmac_key = hmac_key,
            )
        settings.lock_keys = True

        # ## these are messages that can be customized
        messages = self.messages = Messages(current.T)
        messages.update(Auth.default_messages)
        messages.lock_keys = True

        # for "remember me" option
        response = current.response
        if auth  and  auth.remember:
            # when user wants to be logged in for longer
            response.cookies[response.session_id_name]["expires"] = \
                auth.expiration
        if signature:
            self.define_signature()
        else:
            self.signature = None

    def _get_user_id(self):
       "accessor for auth.user_id"
       return self.user and self.user.id or None

    user_id = property(_get_user_id, doc="user.id or None")

    def table_user(self):
        return self.db[self.settings.table_user_name]
    def table_group(self):
        return self.db[self.settings.table_group_name]
    def table_membership(self):
        return self.db[self.settings.table_membership_name]
    def table_permission(self):
        return self.db[self.settings.table_permission_name]
    def table_event(self):
        return self.db[self.settings.table_event_name]
    def table_cas(self):
        return self.db[self.settings.table_cas_name]

    def _HTTP(self, *a, **b):
        """
        only used in lambda: self._HTTP(404)
        """

        raise HTTP(*a, **b)

    def __call__(self):
        """
        usage:

        def authentication(): return dict(form=auth())
        """

        request = current.request
        args = request.args
        if not args:
            redirect(self.url(args='login',vars=request.vars))
        elif args[0] in self.settings.actions_disabled:
            raise HTTP(404)
        if args[0] in ('login','logout','register','verify_email',
                       'retrieve_username','retrieve_password',
                       'reset_password','request_reset_password',
                       'change_password','profile','groups',
                       'impersonate','not_authorized'):
            return getattr(self,args[0])()
        elif args[0]=='cas' and not self.settings.cas_provider:
            if args(1) == self.settings.cas_actions['login']:
                return self.cas_login(version=2)
            elif args(1) == self.settings.cas_actions['validate']:
                return self.cas_validate(version=1)
            elif args(1) == self.settings.cas_actions['servicevalidate']:
                return self.cas_validate(version=2, proxy=False)
            elif args(1) == self.settings.cas_actions['proxyvalidate']:
                return self.cas_validate(version=2, proxy=True)
            elif args(1) == self.settings.cas_actions['logout']:
                return self.logout(next=request.vars.service or DEFAULT)
        else:
            raise HTTP(404)

    def navbar(self, prefix='Welcome', action=None,
               separators=(' [ ',' | ',' ] '), user_identifier=DEFAULT,
               referrer_actions=DEFAULT):
        referrer_actions = [] if not referrer_actions else referrer_actions
        request = current.request
        T = current.T
        if isinstance(prefix, str):
            prefix = T(prefix)
        if prefix:
            prefix = prefix.strip() + ' '
        if not action:
            action=self.url(self.settings.function)
        s1,s2,s3 = separators
        if URL() == action:
            next = ''
        else:
            next = '?_next=' + urllib.quote(URL(args=request.args,
                                                vars=request.get_vars))

        href = lambda function: '%s/%s%s' % (action, function,
            next if referrer_actions is DEFAULT or function in referrer_actions else '')

        if self.user_id:
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
            logout = A(T('Logout'), _href='%s/logout?_next=%s' %
                      (action, urllib.quote(self.settings.logout_next)))
            profile = A(T('Profile'), _href=href('profile'))
            password = A(T('Password'), _href=href('change_password'))
            bar = SPAN(prefix, user_identifier, s1, logout, s3, _class='auth_navbar')
            if not 'profile' in self.settings.actions_disabled:
                bar.insert(-1, s2)
                bar.insert(-1, profile)
            if not 'change_password' in self.settings.actions_disabled:
                bar.insert(-1, s2)
                bar.insert(-1, password)
        else:
            login = A(T('Login'), _href=href('login'))
            register = A(T('Register'), _href=href('register'))
            retrieve_username = A(
                T('Forgot username?'), _href=href('retrieve_username'))
            lost_password = A(
                T('Lost password?'), _href=href('request_reset_password'))
            bar = SPAN(s1, login, s3, _class='auth_navbar')

            if not 'register' in self.settings.actions_disabled:
                bar.insert(-1, s2)
                bar.insert(-1, register)
            if self.settings.use_username and not 'retrieve_username' \
                    in self.settings.actions_disabled:
                bar.insert(-1, s2)
                bar.insert(-1, retrieve_username)
            if not 'request_reset_password' \
                    in self.settings.actions_disabled:
                bar.insert(-1, s2)
                bar.insert(-1, lost_password)
        return bar

    def __get_migrate(self, tablename, migrate=True):

        if type(migrate).__name__ == 'str':
            return (migrate + tablename + '.table')
        elif migrate == False:
            return False
        else:
            return True

    def enable_record_versioning(self,
                                 tables,
                                 archive_db = None,
                                 archive_names='%(tablename)s_archive',
                                 current_record='current_record'):
        """
        to enable full record vernionioning (including auth tables):

        auth = Auth(db)
        auth.define_tables(signature=True)
        # define our own tables
        db.define_table('mything',Field('name'),auth.signature)
        auth.enable_record_vernining(tables=db)

        tables can be the db (all table) or a list of tables.
        only tables with modified_by and modified_on fiels (as created
        by auth.signature) will have versioning. Old record versions will be
        in table 'mything_archive' automatically defined.

        when you enable enable_record_versioning, records are never
        deleted but marked with is_active=False.

        enable_record_versioning enables a common_filter for
        every table that filters out records with is_active = False

        Important: If you use auth.enable_record_versioning,
        do not use auth.archive or you will end up with duplicates.
        auth.archive does explicitely what enable_record_versioning
        does automatically.

        """
        tables = [table for table in tables]
        for table in tables:
            if 'modified_on' in table.fields():
                table._enable_record_versioning(
                    archive_db = archive_db,
                    archive_name = archive_names,
                    current_record = current_record)

    def define_signature(self):
        db = self.db
        settings = self.settings
        request = current.request
        T = current.T
        reference_user = 'reference %s' % settings.table_user_name
        def lazy_user (auth = self):
            return auth.user_id        
        def represent(id,record=None,s=settings):
            try:
                user = s.table_user(id)
                return '%(first_name)s %(last_name)s' % user
            except:
                return id
        self.signature = db.Table(
            self.db,'auth_signature',
            Field('is_active','boolean',
                  default=True,
                  readable=False, writable=False,
                  label=T('Is Active')),
            Field('created_on','datetime',
                  default=request.now,
                  writable=False, readable=False,
                  label=T('Created On')),
            Field('created_by',
                  reference_user,
                  default=lazy_user, represent=represent,
                  writable=False, readable=False,
                  label=T('Created By')),
            Field('modified_on','datetime',
                  update=request.now,default=request.now,
                  writable=False,readable=False,
                  label=T('Modified On')),
            Field('modified_by',
                  reference_user,represent=represent,
                  default=lazy_user,update=lazy_user,
                  writable=False,readable=False,
                  label=T('Modified By')))

    def define_tables(self, username=None, signature=None,
                      migrate=True, fake_migrate=False):
        """
        to be called unless tables are defined manually

        usages:

            # defines all needed tables and table files
            # 'myprefix_auth_user.table', ...
            auth.define_tables(migrate='myprefix_')

            # defines all needed tables without migration/table files
            auth.define_tables(migrate=False)

        """

        db = self.db
        settings = self.settings
        if username is None:
            username = settings.use_username
        else:
            settings.use_username = username
        if not self.signature:
            self.define_signature()
        if signature==True:
            signature_list = [self.signature]
        elif not signature:
            signature_list = []
        elif isinstance(signature,self.db.Table):
            signature_list = [signature]
        else:
            signature_list = signature        
        is_not_empty = IS_NOT_EMPTY(error_message=self.messages.is_empty)
        is_crypted = CRYPT(key=settings.hmac_key,
                           min_length=settings.password_min_length)
        is_unique_email = [
            IS_EMAIL(error_message=self.messages.invalid_email),
            IS_NOT_IN_DB(db, '%s.email' % settings.table_user_name)]
        if not settings.email_case_sensitive:
            is_unique_email.insert(1,IS_LOWER())
        if not settings.table_user_name in db.tables:
            passfield = settings.password_field
            extra_fields = settings.extra_fields.get(
                settings.table_user_name,[])+signature_list
            if username or settings.cas_provider:
                is_unique_username = \
                    [IS_MATCH('[\w\.\-]+'),
                     IS_NOT_IN_DB(db,'%s.username' % settings.table_user_name)]
                if not settings.username_case_sensitive:
                    is_unique_username.insert(1,IS_LOWER())
                table = db.define_table(
                    settings.table_user_name,
                    Field('first_name', length=128, default='',
                          label=self.messages.label_first_name,
                          requires = is_not_empty),
                    Field('last_name', length=128, default='',
                          label=self.messages.label_last_name,
                          requires = is_not_empty),
                    Field('email', length=512, default='',
                          label=self.messages.label_email,
                          requires = is_unique_email),
                    Field('username', length=128, default='',
                          label=self.messages.label_username,
                          requires=is_unique_username),
                    Field(passfield, 'password', length=512,
                          readable=False, label=self.messages.label_password,
                          requires = [is_crypted]),
                    Field('registration_key', length=512,
                          writable=False, readable=False, default='',
                          label=self.messages.label_registration_key),
                    Field('reset_password_key', length=512,
                          writable=False, readable=False, default='',
                          label=self.messages.label_reset_password_key),
                    Field('registration_id', length=512,
                          writable=False, readable=False, default='',
                          label=self.messages.label_registration_id),
                    *extra_fields,
                    **dict(
                        migrate=self.__get_migrate(settings.table_user_name,
                                                   migrate),
                        fake_migrate=fake_migrate,
                        format='%(username)s'))
            else:
                table = db.define_table(
                    settings.table_user_name,
                    Field('first_name', length=128, default='',
                          label=self.messages.label_first_name,
                          requires = is_not_empty),
                    Field('last_name', length=128, default='',
                          label=self.messages.label_last_name,
                          requires = is_not_empty),
                    Field('email', length=512, default='',
                          label=self.messages.label_email,
                          requires = is_unique_email),
                    Field(passfield, 'password', length=512,
                          readable=False, label=self.messages.label_password,
                          requires = [is_crypted]),
                    Field('registration_key', length=512,
                          writable=False, readable=False, default='',
                          label=self.messages.label_registration_key),
                    Field('reset_password_key', length=512,
                          writable=False, readable=False, default='',
                          label=self.messages.label_reset_password_key),
                    Field('registration_id', length=512,
                          writable=False, readable=False, default='',
                          label=self.messages.label_registration_id),
                    *extra_fields,
                    **dict(
                        migrate=self.__get_migrate(settings.table_user_name,
                                                   migrate),
                        fake_migrate=fake_migrate,
                        format='%(first_name)s %(last_name)s (%(id)s)'))
        reference_table_user = 'reference %s' % settings.table_user_name
        if not settings.table_group_name in db.tables:
            extra_fields = settings.extra_fields.get(
                settings.table_group_name,[])+signature_list
            table = db.define_table(
                settings.table_group_name,
                Field('role', length=512, default='',
                        label=self.messages.label_role,
                      requires = IS_NOT_IN_DB(
                        db, '%s.role'% settings.table_group_name)),
                Field('description', 'text',
                        label=self.messages.label_description),
                *extra_fields,
                **dict(
                    migrate=self.__get_migrate(
                        settings.table_group_name, migrate),
                    fake_migrate=fake_migrate,
                    format = '%(role)s (%(id)s)'))
        reference_table_group = 'reference %s' % settings.table_group_name
        if not settings.table_membership_name in db.tables:
            extra_fields = settings.extra_fields.get(
                settings.table_membership_name,[])+signature_list
            table = db.define_table(
                settings.table_membership_name,
                Field('user_id', reference_table_user,
                        label=self.messages.label_user_id),
                Field('group_id', reference_table_group,
                        label=self.messages.label_group_id),
                *extra_fields,
                **dict(
                    migrate=self.__get_migrate(
                        settings.table_membership_name, migrate),
                    fake_migrate=fake_migrate))
        if not settings.table_permission_name in db.tables:
            extra_fields = settings.extra_fields.get(
                settings.table_permission_name,[])+signature_list
            table = db.define_table(
                settings.table_permission_name,
                Field('group_id', reference_table_group,
                      label=self.messages.label_group_id),
                Field('name', default='default', length=512,
                      label=self.messages.label_name,
                      requires=is_not_empty),
                Field('table_name', length=512,
                      label=self.messages.label_table_name),
                Field('record_id', 'integer',default=0,
                      label=self.messages.label_record_id,
                      requires = IS_INT_IN_RANGE(0, 10 ** 9)),
                *extra_fields,
                **dict(
                    migrate=self.__get_migrate(
                        settings.table_permission_name, migrate),
                    fake_migrate=fake_migrate))
        if not settings.table_event_name in db.tables:
            table  = db.define_table(
                settings.table_event_name,
                Field('time_stamp', 'datetime',
                        default=current.request.now,
                        label=self.messages.label_time_stamp),
                Field('client_ip',
                        default=current.request.client,
                        label=self.messages.label_client_ip),
                Field('user_id', reference_table_user, default=None,
                      label=self.messages.label_user_id),
                Field('origin', default='auth', length=512,
                      label=self.messages.label_origin,
                      requires=is_not_empty),
                Field('description', 'text', default='',
                      label=self.messages.label_description,
                      requires=is_not_empty),
                *settings.extra_fields.get(settings.table_event_name,[]),
                **dict(
                    migrate=self.__get_migrate(
                        settings.table_event_name, migrate),
                    fake_migrate=fake_migrate))
        now = current.request.now
        if settings.cas_domains:
            if not settings.table_cas_name in db.tables:
                table  = db.define_table(
                    settings.table_cas_name,
                    Field('user_id', reference_table_user, default=None,
                          label=self.messages.label_user_id),
                    Field('created_on','datetime',default=now),
                    Field('service',requires=IS_URL()),
                    Field('ticket'),
                    Field('renew', 'boolean', default=False),
                    *settings.extra_fields.get(settings.table_cas_name,[]),
                    **dict(
                        migrate=self.__get_migrate(
                            settings.table_cas_name, migrate),
                        fake_migrate=fake_migrate))
        if not db._lazy_tables:
            settings.table_user = db[settings.table_user_name]
            settings.table_group = db[settings.table_group_name]
            settings.table_membership = db[settings.table_membership_name]
            settings.table_permission = db[settings.table_permission_name]
            settings.table_event = db[settings.table_event_name]
            if settings.cas_domains:
                settings.table_cas = db[settings.table_cas_name]

        if settings.cas_provider: ### THIS IS NOT LAZY
            settings.actions_disabled = \
                ['profile','register','change_password',
                 'request_reset_password']
            from gluon.contrib.login_methods.cas_auth import CasAuth
            maps = settings.cas_maps
            if not maps:
                table_user = self.table_user()
                maps = dict((name,lambda v,n=name:v.get(n,None)) for name in \
                                table_user.fields if name!='id' \
                                and table_user[name].readable)
                maps['registration_id'] = \
                    lambda v,p=settings.cas_provider:'%s/%s' % (p,v['user'])
            actions = [settings.cas_actions['login'],
                       settings.cas_actions['servicevalidate'],
                       settings.cas_actions['logout']]
            settings.login_form = CasAuth(
                casversion = 2,
                urlbase = settings.cas_provider,
                actions=actions,
                maps=maps)

    def log_event(self, description, vars=None, origin='auth'):
        """
        usage:

            auth.log_event(description='this happened', origin='auth')
        """
        if not description:
            return
        elif self.is_logged_in():
            user_id = self.user.id
        else:
            user_id = None  # user unknown
        vars = vars or {}
        self.table_event().insert(
            description=description % vars,
            origin=origin, user_id=user_id)

    def get_or_create_user(self, keys, update_fields=['email']):
        """
        Used for alternate login methods:
            If the user exists already then password is updated.
            If the user doesn't yet exist, then they are created.
        """
        table_user = self.table_user()
        user = None
        checks = []
        # make a guess about who this user is
        for fieldname in ['registration_id','username','email']:
            if fieldname in table_user.fields() and \
                    keys.get(fieldname,None):
                checks.append(fieldname)
                value = keys[fieldname]
                user = table_user(**{fieldname:value})
                if user: break
        if not checks:
            return None
        if not 'registration_id' in keys:
            keys['registration_id'] = keys[checks[0]]
        # if we think we found the user but registration_id does not match,
        # make new user
        if 'registration_id' in checks \
                and user \
                and user.registration_id \
                and user.registration_id!=keys.get('registration_id',None):
            user = None # THINK MORE ABOUT THIS? DO WE TRUST OPENID PROVIDER?
        if user:
            update_keys = dict(registration_id=keys['registration_id'])
            for key in update_fields:
                if key in keys:
                    update_keys[key] = keys[key]
            user.update_record(**update_keys)
        elif checks:
            if not 'first_name' in keys and 'first_name' in table_user.fields:
                guess = keys.get('email','anonymous').split('@')[0]
                keys['first_name'] = keys.get('username',guess)
            user_id = table_user.insert(**table_user._filter_fields(keys))
            user =  self.user = table_user[user_id]
            if self.settings.create_user_groups:
                group_id = self.add_group(
                    self.settings.create_user_groups % user)
                self.add_membership(group_id, user_id)
            if self.settings.everybody_group_id:
                self.add_membership(self.settings.everybody_group_id, user_id)
        return user

    def basic(self):
        """
        perform basic login.
        reads current.request.env.http_authorization
        and returns basic_allowed,basic_accepted,user 
        """
        if not self.settings.allow_basic_login:
            return (False,False,False)
        basic = current.request.env.http_authorization
        if not basic or not basic[:6].lower() == 'basic ':
            return (True, False, False)
        (username, password) = base64.b64decode(basic[6:]).split(':')
        return (True, True, self.login_bare(username, password))

    def login_user(self,user):
        """
        login the user = db.auth_user(id)
        """
        # user=Storage(self.table_user()._filter_fields(user,id=True))
        current.session.auth = Storage(
            user = user, 
            last_visit = current.request.now,
            expiration = self.settings.expiration,
            hmac_key = web2py_uuid())
        self.user = user
        self.update_groups()

    def login_bare(self, username, password):
        """
        logins user as specified by usernname (or email) and password
        """
        request = current.request
        session = current.session
        table_user = self.table_user()
        if self.settings.login_userfield:
            userfield = self.settings.login_userfield
        elif 'username' in table_user.fields:
            userfield = 'username'
        else:
            userfield = 'email'
        passfield = self.settings.password_field
        user = self.db(table_user[userfield] == username).select().first()
        if user and user.get(passfield,False):
            password = table_user[passfield].validate(password)[0]
            if not user.registration_key and password == user[passfield]:
                self.login_user(user)
                return user
        else:
            # user not in database try other login methods
            for login_method in self.settings.login_methods:
                if login_method != self and login_method(username, password):
                    self.user = username
                    return username
        return False

    def cas_login(
        self,
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
        if not request.env.http_host in self.settings.cas_domains or \
                not session._cas_service:
            raise HTTP(403,'not authorized')
        def allow_access(interactivelogin=False):
            row = table(service=session._cas_service,user_id=self.user.id)
            if row:
                ticket = row.ticket
            else:
                ticket = 'ST-'+web2py_uuid()
                table.insert(service=session._cas_service,
                             user_id=self.user.id,
                             ticket=ticket,
                             created_on=request.now,
                             renew=interactivelogin)
            service = session._cas_service
            del session._cas_service
            if 'warn' in request.vars and not interactivelogin:
                response.headers['refresh'] = "5;URL=%s"%service+"?ticket="+ticket
                return A("Continue to %s"%service,
                    _href=service+"?ticket="+ticket)
            else:
                redirect(service+"?ticket="+ticket)
        if self.is_logged_in() and not 'renew' in request.vars:
            return allow_access()
        elif not self.is_logged_in() and 'gateway' in request.vars:
            redirect(service)
        def cas_onaccept(form, onaccept=onaccept):
            if not onaccept is DEFAULT: onaccept(form)
            return allow_access(interactivelogin=True)
        return self.login(next,onvalidation,cas_onaccept,log)


    def cas_validate(self, version=2, proxy=False):
        request = current.request
        db, table = self.db, self.table_cas()
        current.response.headers['Content-Type']='text'
        ticket = request.vars.ticket
        renew = 'renew' in request.vars
        row = table(ticket=ticket)
        success = False
        if row:
            if self.settings.login_userfield:
                userfield = self.settings.login_userfield
            elif 'username' in table.fields:
                userfield = 'username'
            else:
                userfield = 'email'
            # If ticket is a service Ticket and RENEW flag respected
            if ticket[0:3] == 'ST-' and \
                    not ((row.renew and renew) ^ renew):
                user = self.table_user()(row.user_id)
                row.delete_record()
                success = True
        def build_response(body):
            return '<?xml version="1.0" encoding="UTF-8"?>\n'+\
                TAG['cas:serviceResponse'](
                body,**{'_xmlns:cas':'http://www.yale.edu/tp/cas'}).xml()
        if success:
            if version == 1:
                message = 'yes\n%s' % user[userfield]
            else: # assume version 2
                username = user.get('username',user[userfield])
                message = build_response(
                    TAG['cas:authenticationSuccess'](
                        TAG['cas:user'](username),
                        *[TAG['cas:'+field.name](user[field.name]) \
                              for field in self.table_user() \
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
        raise HTTP(200,message)

    def login(
        self,
        next=DEFAULT,
        onvalidation=DEFAULT,
        onaccept=DEFAULT,
        log=DEFAULT,
        ):
        """
        returns a login form

        method: Auth.login([next=DEFAULT [, onvalidation=DEFAULT
            [, onaccept=DEFAULT [, log=DEFAULT]]]])

        """

        table_user = self.table_user()
        if self.settings.login_userfield:
            username = self.settings.login_userfield
        elif 'username' in table_user.fields:
            username = 'username'
        else:
            username = 'email'
        if 'username' in table_user.fields or \
                not self.settings.login_email_validate:
            tmpvalidator = IS_NOT_EMPTY(error_message=self.messages.is_empty)
        else:
            tmpvalidator = IS_EMAIL(error_message=self.messages.invalid_email)
        old_requires = table_user[username].requires
        table_user[username].requires = tmpvalidator

        request = current.request
        response = current.response
        session = current.session

        passfield = self.settings.password_field
        try: table_user[passfield].requires[-1].min_length = 0
        except: pass

        ### use session for federated login
        if self.next:
            session._auth_next = self.next
        elif session._auth_next:
            self.next = session._auth_next
        ### pass

        if next is DEFAULT:
            next = self.next or self.settings.login_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.login_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.login_onaccept
        if log is DEFAULT:
            log = self.messages.login_log

        user = None # default

        # do we use our own login form, or from a central source?
        if self.settings.login_form == self:
            form = SQLFORM(
                table_user,
                fields=[username, passfield],
                hidden = dict(_next=next),
                showid=self.settings.showid,
                submit_button=self.messages.login_button,
                delete_label=self.messages.delete_label,
                formstyle=self.settings.formstyle,
                separator=self.settings.label_separator
                )

            if self.settings.remember_me_form:
                ## adds a new input checkbox "remember me for longer"
                addrow(form,XML("&nbsp;"),
                       DIV(XML("&nbsp;"),
                           INPUT(_type='checkbox',
                                 _class='checkbox',
                                 _id="auth_user_remember",
                                 _name="remember",
                                 ),
                           XML("&nbsp;&nbsp;"),
                           LABEL(
                            self.messages.label_remember_me,
                            _for="auth_user_remember",
                            )),"",
                       self.settings.formstyle,
                       'auth_user_remember__row')

            captcha = self.settings.login_captcha or \
                (self.settings.login_captcha!=False and self.settings.captcha)
            if captcha:
                addrow(form, captcha.label, captcha, captcha.comment,
                       self.settings.formstyle,'captcha__row')
            accepted_form = False

            if form.accepts(request, session,
                            formname='login', dbio=False,
                            onvalidation=onvalidation,
                            hideerror=self.settings.hideerror):

                accepted_form = True
                # check for username in db
                user = self.db(table_user[username] == form.vars[username]).select().first()
                if user:
                    # user in db, check if registration pending or disabled
                    temp_user = user
                    if temp_user.registration_key == 'pending':
                        response.flash = self.messages.registration_pending
                        return form
                    elif temp_user.registration_key in ('disabled','blocked'):
                        response.flash = self.messages.login_disabled
                        return form
                    elif not temp_user.registration_key is None and \
                            temp_user.registration_key.strip():
                        response.flash = \
                            self.messages.registration_verifying
                        return form
                    # try alternate logins 1st as these have the
                    # current version of the password
                    user = None
                    for login_method in self.settings.login_methods:
                        if login_method != self and \
                                login_method(request.vars[username],
                                             request.vars[passfield]):
                            if not self in self.settings.login_methods:
                                # do not store password in db
                                form.vars[passfield] = None
                            user = self.get_or_create_user(form.vars)
                            break
                    if not user:
                        # alternates have failed, maybe because service inaccessible
                        if self.settings.login_methods[0] == self:
                            # try logging in locally using cached credentials
                            if form.vars.get(passfield, '') == temp_user[passfield]:
                                # success
                                user = temp_user
                else:
                    # user not in db
                    if not self.settings.alternate_requires_registration:
                        # we're allowed to auto-register users from external systems
                        for login_method in self.settings.login_methods:
                            if login_method != self and \
                                    login_method(request.vars[username],
                                                 request.vars[passfield]):
                                if not self in self.settings.login_methods:
                                    # do not store password in db
                                    form.vars[passfield] = None
                                user = self.get_or_create_user(form.vars)
                                break
                if not user:
                    self.log_event(self.messages.login_failed_log,
                                   request.post_vars)
                    # invalid login
                    session.flash = self.messages.invalid_login
                    redirect(self.url(args=request.args,vars=request.get_vars))

        else:
            # use a central authentication server
            cas = self.settings.login_form
            cas_user = cas.get_user()

            if cas_user:
                cas_user[passfield] = None
                user = self.get_or_create_user(table_user._filter_fields(cas_user))
            elif hasattr(cas,'login_form'):
                return cas.login_form()
            else:
                # we need to pass through login again before going on
                next = self.url(self.settings.function, args='login')
                redirect(cas.login_url(next))

        # process authenticated users
        if user:
            user = Row(table_user._filter_fields(user, id=True))
            # process authenticated users
            # user wants to be logged in for longer
            self.login_user(user)
            session.auth.expiration = \
                request.vars.get('remember',False) and \
                self.settings.long_expiration or \
                self.settings.expiration
            session.auth.remember = 'remember' in request.vars
            self.log_event(log, user)
            session.flash = self.messages.logged_in

        # how to continue
        if self.settings.login_form == self:
            if accepted_form:
                callback(onaccept,form)
                if next == session._auth_next:
                     session._auth_next = None
                next = replace_id(next, form)
                redirect(next)
            table_user[username].requires = old_requires
            return form
        elif user:
            callback(onaccept,None)
        if next == session._auth_next:
            del session._auth_next
        redirect(next)

    def logout(self, next=DEFAULT, onlogout=DEFAULT, log=DEFAULT):
        """
        logout and redirects to login

        method: Auth.logout ([next=DEFAULT[, onlogout=DEFAULT[,
            log=DEFAULT]]])

        """

        if next is DEFAULT:
            next = self.settings.logout_next
        if onlogout is DEFAULT:
            onlogout = self.settings.logout_onlogout
        if onlogout:
            onlogout(self.user)
        if log is DEFAULT:
            log = self.messages.logout_log
        if self.user:
            self.log_event(log, self.user)
        if self.settings.login_form != self:
            cas = self.settings.login_form
            cas_user = cas.get_user()
            if cas_user:
                next = cas.logout_url(next)

        current.session.auth = None
        current.session.flash = self.messages.logged_out
        redirect(next)

    def register(
        self,
        next=DEFAULT,
        onvalidation=DEFAULT,
        onaccept=DEFAULT,
        log=DEFAULT,
        ):
        """
        returns a registration form

        method: Auth.register([next=DEFAULT [, onvalidation=DEFAULT
            [, onaccept=DEFAULT [, log=DEFAULT]]]])

        """

        table_user = self.table_user()
        request = current.request
        response = current.response
        session = current.session
        if self.is_logged_in():
            redirect(self.settings.logged_url)
        if next is DEFAULT:
            next = self.next or self.settings.register_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.register_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.register_onaccept
        if log is DEFAULT:
            log = self.messages.register_log

        table_user = self.table_user()
        if 'username' in table_user.fields:
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
        form = SQLFORM(table_user,
                       fields = self.settings.register_fields,
                       hidden = dict(_next=next),
                       showid=self.settings.showid,
                       submit_button=self.messages.register_button,
                       delete_label=self.messages.delete_label,
                       formstyle=formstyle,
                       separator=self.settings.label_separator
                       )
        if self.settings.register_verify_password:
            for i, row in enumerate(form[0].components):
                item = row.element('input',_name=passfield)
                if item:
                    form.custom.widget.password_two = \
                        INPUT(_name="password_two",  _type="password",
                              requires=IS_EXPR(
                            'value==%s' % \
                                repr(request.vars.get(passfield, None)),
                            error_message=self.messages.mismatched_password))

                    addrow(form, self.messages.verify_password + self.settings.label_separator,
                           form.custom.widget.password_two,
                           self.messages.verify_password_comment,
                           formstyle,
                           '%s_%s__row' % (table_user, 'password_two'),
                           position=i+1)
                    break
        captcha = self.settings.register_captcha or self.settings.captcha
        if captcha:
            addrow(form, captcha.label, captcha, captcha.comment,self.settings.formstyle, 'captcha__row')

        table_user.registration_key.default = key = web2py_uuid()
        if form.accepts(request, session, formname='register',
                        onvalidation=onvalidation,hideerror=self.settings.hideerror):
            description = self.messages.group_description % form.vars
            if self.settings.create_user_groups:
                group_id = self.add_group(self.settings.create_user_groups % form.vars, description)
                self.add_membership(group_id, form.vars.id)
            if self.settings.everybody_group_id:
                self.add_membership(self.settings.everybody_group_id, form.vars.id)
            if self.settings.registration_requires_verification:
                link = self.url('user',args=('verify_email',key),scheme=True)
                                
                if not self.settings.mailer or \
                   not self.settings.mailer.send(
                    to=form.vars.email,
                    subject=self.messages.verify_email_subject,
                    message=self.messages.verify_email \
                        % dict(key=key,link=link)):
                    self.db.rollback()
                    response.flash = self.messages.unable_send_email
                    return form
                session.flash = self.messages.email_sent
            if self.settings.registration_requires_approval and \
               not self.settings.registration_requires_verification:
                table_user[form.vars.id] = dict(registration_key='pending')
                session.flash = self.messages.registration_pending
            elif (not self.settings.registration_requires_verification or \
                      self.settings.login_after_registration):
                if not self.settings.registration_requires_verification:
                    table_user[form.vars.id] = dict(registration_key='')
                session.flash = self.messages.registration_successful
                user = self.db(
                    table_user[username] == form.vars[username]
                    ).select().first()                
                self.login_user(user)
                session.flash = self.messages.logged_in
            self.log_event(log, form.vars)
            callback(onaccept,form)
            if not next:
                next = self.url(args = request.args)
            else:
                next = replace_id(next, form)
            redirect(next)
        return form

    def is_logged_in(self):
        """
        checks if the user is logged in and returns True/False.
        if so user is in auth.user as well as in session.auth.user
        """

        if self.user:
            return True
        return False

    def verify_email(
        self,
        next=DEFAULT,
        onaccept=DEFAULT,
        log=DEFAULT,
        ):
        """
        action user to verify the registration email, XXXXXXXXXXXXXXXX

        method: Auth.verify_email([next=DEFAULT [, onvalidation=DEFAULT
            [, onaccept=DEFAULT [, log=DEFAULT]]]])

        """

        key = getarg(-1)
        table_user = self.table_user()
        user = table_user(registration_key=key)
        if not user:
            redirect(self.settings.login_url)
        if self.settings.registration_requires_approval:
            user.update_record(registration_key = 'pending')
            current.session.flash = self.messages.registration_pending
        else:
            user.update_record(registration_key = '')
            current.session.flash = self.messages.email_verified
        # make sure session has same user.registrato_key as db record
        if current.session.auth and current.session.auth.user:
            current.session.auth.user.registration_key = user.registration_key
        if log is DEFAULT:
            log = self.messages.verify_email_log
        if next is DEFAULT:
            next = self.settings.verify_email_next
        if onaccept is DEFAULT:
            onaccept = self.settings.verify_email_onaccept
        self.log_event(log, user)
        callback(onaccept,user)
        redirect(next)

    def retrieve_username(
        self,
        next=DEFAULT,
        onvalidation=DEFAULT,
        onaccept=DEFAULT,
        log=DEFAULT,
        ):
        """
        returns a form to retrieve the user username
        (only if there is a username field)

        method: Auth.retrieve_username([next=DEFAULT
            [, onvalidation=DEFAULT [, onaccept=DEFAULT [, log=DEFAULT]]]])

        """

        table_user = self.table_user()
        if not 'username' in table_user.fields:
            raise HTTP(404)
        request = current.request
        response = current.response
        session = current.session
        captcha = self.settings.retrieve_username_captcha or \
                (self.settings.retrieve_username_captcha!=False and self.settings.captcha)
        if not self.settings.mailer:
            response.flash = self.messages.function_disabled
            return ''
        if next is DEFAULT:
            next = self.next or self.settings.retrieve_username_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.retrieve_username_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.retrieve_username_onaccept
        if log is DEFAULT:
            log = self.messages.retrieve_username_log
        old_requires = table_user.email.requires
        table_user.email.requires = [IS_IN_DB(self.db, table_user.email,
            error_message=self.messages.invalid_email)]
        form = SQLFORM(table_user,
                       fields=['email'],
                       hidden = dict(_next=next),
                       showid=self.settings.showid,
                       submit_button=self.messages.submit_button,
                       delete_label=self.messages.delete_label,
                       formstyle=self.settings.formstyle,
                       separator=self.settings.label_separator
                       )
        if captcha:
            addrow(form, captcha.label, captcha, captcha.comment,self.settings.formstyle, 'captcha__row')

        if form.accepts(request, session,
                        formname='retrieve_username', dbio=False,
                        onvalidation=onvalidation,hideerror=self.settings.hideerror):
            user = table_user(email=form.vars.email)
            if not user:
                current.session.flash = \
                    self.messages.invalid_email
                redirect(self.url(args=request.args))
            username = user.username
            self.settings.mailer.send(to=form.vars.email,
                    subject=self.messages.retrieve_username_subject,
                    message=self.messages.retrieve_username
                     % dict(username=username))
            session.flash = self.messages.email_sent
            self.log_event(log, user)
            callback(onaccept,form)
            if not next:
                next = self.url(args = request.args)
            else:
                next = replace_id(next, form)
            redirect(next)
        table_user.email.requires = old_requires
        return form

    def random_password(self):
        import string
        import random
        password = ''
        specials=r'!#$*'
        for i in range(0,3):
            password += random.choice(string.lowercase)
            password += random.choice(string.uppercase)
            password += random.choice(string.digits)
            password += random.choice(specials)
        return ''.join(random.sample(password,len(password)))

    def reset_password_deprecated(
        self,
        next=DEFAULT,
        onvalidation=DEFAULT,
        onaccept=DEFAULT,
        log=DEFAULT,
        ):
        """
        returns a form to reset the user password (deprecated)

        method: Auth.reset_password_deprecated([next=DEFAULT
            [, onvalidation=DEFAULT [, onaccept=DEFAULT [, log=DEFAULT]]]])

        """

        table_user = self.table_user()
        request = current.request
        response = current.response
        session = current.session
        if not self.settings.mailer:
            response.flash = self.messages.function_disabled
            return ''
        if next is DEFAULT:
            next = self.next or self.settings.retrieve_password_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.retrieve_password_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.retrieve_password_onaccept
        if log is DEFAULT:
            log = self.messages.retrieve_password_log
        old_requires = table_user.email.requires
        table_user.email.requires = [IS_IN_DB(self.db, table_user.email,
            error_message=self.messages.invalid_email)]
        form = SQLFORM(table_user,
                       fields=['email'],
                       hidden = dict(_next=next),
                       showid=self.settings.showid,
                       submit_button=self.messages.submit_button,
                       delete_label=self.messages.delete_label,
                       formstyle=self.settings.formstyle,
                       separator=self.settings.label_separator
                       )
        if form.accepts(request, session,
                        formname='retrieve_password', dbio=False,
                        onvalidation=onvalidation,hideerror=self.settings.hideerror):
            user = table_user(email=form.vars.email)
            if not user:
                current.session.flash = \
                    self.messages.invalid_email
                redirect(self.url(args=request.args))
            elif user.registration_key in ('pending','disabled','blocked'):
                current.session.flash = \
                    self.messages.registration_pending
                redirect(self.url(args=request.args))
            password = self.random_password()
            passfield = self.settings.password_field
            d = dict(
                passfield = str(table_user[passfield].validate(password)[0]),
                registration_key = '')
            user.update_record(**d)
            if self.settings.mailer and \
               self.settings.mailer.send(to=form.vars.email,
                        subject=self.messages.retrieve_password_subject,
                        message=self.messages.retrieve_password \
                        % dict(password=password)):
                session.flash = self.messages.email_sent
            else:
                session.flash = self.messages.unable_to_send_email
            self.log_event(log, user)
            callback(onaccept,form)
            if not next:
                next = self.url(args = request.args)
            else:
                next = replace_id(next, form)
            redirect(next)
        table_user.email.requires = old_requires
        return form

    def reset_password(
        self,
        next=DEFAULT,
        onvalidation=DEFAULT,
        onaccept=DEFAULT,
        log=DEFAULT,
        ):
        """
        returns a form to reset the user password

        method: Auth.reset_password([next=DEFAULT
            [, onvalidation=DEFAULT [, onaccept=DEFAULT [, log=DEFAULT]]]])

        """

        table_user = self.table_user()
        request = current.request
        # response = current.response
        session = current.session

        if next is DEFAULT:
            next = self.settings.reset_password_next
        try:
            key = request.vars.key or getarg(-1)
            t0 = int(key.split('-')[0])
            if time.time()-t0 > 60*60*24: raise Exception
            user = table_user(reset_password_key=key)
            if not user: raise Exception
        except Exception:
            session.flash = self.messages.invalid_reset_password
            redirect(next)
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
            hidden = dict(_next=next),
            formstyle=self.settings.formstyle,
            separator=self.settings.label_separator
        )
        if form.accepts(request,session,
                        hideerror=self.settings.hideerror):
            user.update_record(
                **{passfield:str(form.vars.new_password),
                   'registration_key':'',
                   'reset_password_key':''})
            session.flash = self.messages.password_changed
            if self.settings.login_after_password_change:
                self.login_user(user)
            redirect(next)
        return form

    def request_reset_password(
        self,
        next=DEFAULT,
        onvalidation=DEFAULT,
        onaccept=DEFAULT,
        log=DEFAULT,
        ):
        """
        returns a form to reset the user password

        method: Auth.reset_password([next=DEFAULT
            [, onvalidation=DEFAULT [, onaccept=DEFAULT [, log=DEFAULT]]]])

        """
        table_user = self.table_user()
        request = current.request
        response = current.response
        session = current.session
        captcha = self.settings.retrieve_password_captcha or \
                (self.settings.retrieve_password_captcha!=False and self.settings.captcha)

        if next is DEFAULT:
            next = self.next or self.settings.request_reset_password_next
        if not self.settings.mailer:
            response.flash = self.messages.function_disabled
            return ''
        if onvalidation is DEFAULT:
            onvalidation = self.settings.reset_password_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.reset_password_onaccept
        if log is DEFAULT:
            log = self.messages.reset_password_log
        table_user.email.requires = [
            IS_EMAIL(error_message=self.messages.invalid_email),
            IS_IN_DB(self.db, table_user.email,
                     error_message=self.messages.invalid_email)]
        form = SQLFORM(table_user,
                       fields=['email'],
                       hidden = dict(_next=next),
                       showid=self.settings.showid,
                       submit_button=self.messages.password_reset_button,
                       delete_label=self.messages.delete_label,
                       formstyle=self.settings.formstyle,
                       separator=self.settings.label_separator
                       )
        if captcha:
            addrow(form, captcha.label, captcha, captcha.comment, self.settings.formstyle,'captcha__row')
        if form.accepts(request, session,
                        formname='reset_password', dbio=False,
                        onvalidation=onvalidation,
                        hideerror=self.settings.hideerror):
            user = table_user(email=form.vars.email)
            if not user:
                session.flash = self.messages.invalid_email
                redirect(self.url(args=request.args))
            elif user.registration_key in ('pending','disabled','blocked'):
                session.flash = self.messages.registration_pending
                redirect(self.url(args=request.args))
            if self.email_reset_password(user):
                session.flash = self.messages.email_sent
            else:
                session.flash = self.messages.unable_to_send_email
            self.log_event(log, user)
            callback(onaccept,form)
            if not next:
                next = self.url(args = request.args)
            else:
                next = replace_id(next, form)
            redirect(next)
        # old_requires = table_user.email.requires
        return form

    def email_reset_password(self,user):
        reset_password_key = str(int(time.time()))+'-' + web2py_uuid()
        link = self.url('user',
                        args=('reset_password',reset_password_key),
                        scheme=True) 
        if self.settings.mailer.send(
            to=user.email,
            subject=self.messages.reset_password_subject,
            message=self.messages.reset_password % \
                dict(key=reset_password_key,link=link)):
            user.update_record(reset_password_key=reset_password_key)
            return True
        return False

    def retrieve_password(
        self,
        next=DEFAULT,
        onvalidation=DEFAULT,
        onaccept=DEFAULT,
        log=DEFAULT,
        ):
        if self.settings.reset_password_requires_verification:
            return self.request_reset_password(next,onvalidation,onaccept,log)
        else:
            return self.reset_password_deprecated(next,onvalidation,onaccept,log)

    def change_password(
        self,
        next=DEFAULT,
        onvalidation=DEFAULT,
        onaccept=DEFAULT,
        log=DEFAULT,
        ):
        """
        returns a form that lets the user change password

        method: Auth.change_password([next=DEFAULT[, onvalidation=DEFAULT[,
            onaccept=DEFAULT[, log=DEFAULT]]]])
        """

        if not self.is_logged_in():
            redirect(self.settings.login_url)
        db = self.db
        table_user = self.table_user()
        usern = self.settings.table_user_name
        s = db(table_user.id == self.user.id)

        request = current.request
        session = current.session
        if next is DEFAULT:
            next = self.next or self.settings.change_password_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.change_password_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.change_password_onaccept
        if log is DEFAULT:
            log = self.messages.change_password_log
        passfield = self.settings.password_field
        form = SQLFORM.factory(
            Field('old_password', 'password',
                label=self.messages.old_password,
                requires=table_user[passfield].requires),
            Field('new_password', 'password',
                label=self.messages.new_password,
                requires=table_user[passfield].requires),
            Field('new_password2', 'password',
                label=self.messages.verify_password,
                requires=[IS_EXPR('value==%s' % repr(request.vars.new_password),
                              self.messages.mismatched_password)]),
            submit_button=self.messages.password_change_button,
            hidden = dict(_next=next),
            formstyle = self.settings.formstyle,
            separator=self.settings.label_separator
        )
        if form.accepts(request, session,
                        formname='change_password',
                        onvalidation=onvalidation,
                        hideerror=self.settings.hideerror):

            if not form.vars['old_password'] == s.select().first()[passfield]:
                form.errors['old_password'] = self.messages.invalid_password
            else:
                d = {passfield: str(form.vars.new_password)}
                s.update(**d)
                session.flash = self.messages.password_changed
                self.log_event(log, self.user)
                callback(onaccept,form)
                if not next:
                    next = self.url(args=request.args)
                else:
                    next = replace_id(next, form)
            redirect(next)
        return form

    def profile(
        self,
        next=DEFAULT,
        onvalidation=DEFAULT,
        onaccept=DEFAULT,
        log=DEFAULT,
        ):
        """
        returns a form that lets the user change his/her profile

        method: Auth.profile([next=DEFAULT [, onvalidation=DEFAULT
            [, onaccept=DEFAULT [, log=DEFAULT]]]])

        """

        table_user = self.table_user()
        if not self.is_logged_in():
            redirect(self.settings.login_url)
        passfield = self.settings.password_field
        table_user[passfield].writable = False
        request = current.request
        session = current.session
        if next is DEFAULT:
            next = self.next or self.settings.profile_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.profile_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.profile_onaccept
        if log is DEFAULT:
            log = self.messages.profile_log
        form = SQLFORM(
            table_user,
            self.user.id,
            fields = self.settings.profile_fields,
            hidden = dict(_next=next),
            showid = self.settings.showid,
            submit_button = self.messages.profile_save_button,
            delete_label = self.messages.delete_label,
            upload = self.settings.download_url,
            formstyle = self.settings.formstyle,
            separator=self.settings.label_separator
            )
        if form.accepts(request, session,
                        formname='profile',
                        onvalidation=onvalidation, hideerror=self.settings.hideerror):
            self.user.update(table_user._filter_fields(form.vars))
            session.flash = self.messages.profile_updated
            self.log_event(log,self.user)
            callback(onaccept,form)
            if not next:
                next = self.url(args=request.args)
            else:
                next = replace_id(next, form)
            redirect(next)
        return form

    def is_impersonating(self):
        return self.is_logged_in() and 'impersonator' in current.session.auth

    def impersonate(self, user_id=DEFAULT):
        """
        usage: POST TO http://..../impersonate request.post_vars.user_id=<id>
        set request.post_vars.user_id to 0 to restore original user.

        requires impersonator is logged in and
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
        if user_id is DEFAULT:
            user_id = current.request.post_vars.user_id
        if user_id and user_id != self.user.id and user_id != '0':
            if not self.has_permission('impersonate',
                                       self.settings.table_user_name,
                                       user_id):
                raise HTTP(403, "Forbidden")
            user = table_user(user_id)
            if not user:
                raise HTTP(401, "Not Authorized")
            auth.impersonator = cPickle.dumps(session)
            auth.user.update(
                table_user._filter_fields(user, True))
            self.user = auth.user
            if self.settings.login_onaccept:
                form = Storage(dict(vars=self.user))
                for callback in self.settings.login_onaccept:
                    callback(form)
            log = self.messages.impersonate_log
            self.log_event(log,dict(id=current_id, other_id=auth.user.id))
        elif user_id in (0, '0') and self.is_impersonating():
            session.clear()
            session.update(cPickle.loads(auth.impersonator))
            self.user = session.auth.user
        if requested_id is DEFAULT and not request.post_vars:
            return SQLFORM.factory(Field('user_id', 'integer'))
        return self.user

    def update_groups(self):
        if not self.user:
            return
        user_groups = self.user_groups = {}
        if current.session.auth:
            current.session.auth.user_groups = self.user_groups
        table_group = self.table_group()
        table_membership = self.table_membership()
        memberships = self.db(table_membership.user_id==self.user.id).select()
        for membership in memberships:
            group = table_group(membership.group_id)
            if group:
                user_groups[membership.group_id] = group.role

    def groups(self):
        """
        displays the groups and their roles for the logged in user
        """

        if not self.is_logged_in():
            redirect(self.settings.login_url)
        table_membership = self.table_membership()
        memberships = self.db(table_membership.user_id==self.user.id).select()
        table = TABLE()
        for membership in memberships:
            table_group = self.db[self.settings.table_group_name]
            groups = self.db(table_group.id==membership.group_id).select()
            if groups:
                group = groups[0]
                table.append(TR(H3(group.role, '(%s)' % group.id)))
                table.append(TR(P(group.description)))
        if not memberships:
            return None
        return table

    def not_authorized(self):
        """
        you can change the view for this page to make it look as you like
        """
        if current.request.ajax:
            raise HTTP(403,'ACCESS DENIED')
        return 'ACCESS DENIED'

    def requires(self, condition, requires_login=True, otherwise=None):
        """
        decorator that prevents access to action if not logged in
        """

        def decorator(action):

            def f(*a, **b):

                basic_allowed,basic_accepted,user = self.basic()
                user = user or self.user
                if requires_login:
                    if not user:
                        if not otherwise is None:
                            if callable(otherwise):
                                return otherwise()
                            redirect(otherwise)
                        elif self.settings.allow_basic_login_only or \
                                basic_accepted or current.request.is_restful:
                            raise HTTP(403,"Not authorized")
                        elif current.request.ajax:
                            return A('login',_href=self.settings.login_url)
                        else:
                            next = self.here()
                            current.session.flash = current.response.flash
                            return call_or_redirect(
                                self.settings.on_failed_authentication,
                                self.settings.login_url+\
                                    '?_next='+urllib.quote(next))

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

    def requires_login(self,otherwise=None):
        """
        decorator that prevents access to action if not logged in
        """
        return self.requires(True,otherwise=otherwise)

    def requires_membership(self, role=None, group_id=None,otherwise=None):
        """
        decorator that prevents access to action if not logged in or
        if user logged in is not a member of group_id.
        If role is provided instead of group_id then the
        group_id is calculated.
        """
        return self.requires(lambda: self.has_membership(
                group_id=group_id, role=role),otherwise=otherwise)

    def requires_permission(self, name, table_name='', record_id=0,
                            otherwise=None):
        """
        decorator that prevents access to action if not logged in or
        if user logged in is not a member of any group (role) that
        has 'name' access to 'table_name', 'record_id'.
        """
        return self.requires(lambda: self.has_permission(
                name, table_name, record_id),otherwise=otherwise)

    def requires_signature(self,otherwise=None):
        """
        decorator that prevents access to action if not logged in or
        if user logged in is not a member of group_id.
        If role is provided instead of group_id then the
        group_id is calculated.
        """
        return self.requires(lambda: URL.verify(
                current.request,user_signature=True),otherwise=otherwise)

    def add_group(self, role, description=''):
        """
        creates a group associated to a role
        """

        group_id = self.table_group().insert(
            role=role, description=description)
        self.log_event(self.messages.add_group_log,
                       dict(group_id=group_id, role=role))
        return group_id

    def del_group(self, group_id):
        """
        deletes a group
        """
        self.db(self.table_group().id == group_id).delete()
        self.db(self.table_membership().group_id == group_id).delete()
        self.db(self.table_permission().group_id == group_id).delete()
        self.update_groups()
        self.log_event(self.messages.del_group_log,dict(group_id=group_id))

    def id_group(self, role):
        """
        returns the group_id of the group specified by the role
        """
        rows = self.db(self.table_group().role == role).select()
        if not rows:
            return None
        return rows[0].id

    def user_group(self, user_id = None):
        """
        returns the group_id of the group uniquely associated to this user
        i.e. role=user:[user_id]
        """
        return self.id_group(self.user_group_role(user_id))

    def user_group_role(self, user_id=None):
        if user_id:
            user = self.table_user()[user_id]
        else:
            user = self.user
        return self.settings.create_user_groups % user


    def has_membership(self, group_id=None, user_id=None, role=None):
        """
        checks if user is member of group_id or role
        """

        group_id = group_id or self.id_group(role)
        try:
            group_id = int(group_id)
        except:
            group_id = self.id_group(group_id) # interpret group_id as a role
        if not user_id and self.user:
            user_id = self.user.id
        membership = self.table_membership()
        if self.db((membership.user_id == user_id)
                    & (membership.group_id == group_id)).select():
            r = True
        else:
            r = False
        self.log_event(self.messages.has_membership_log,
                       dict(user_id=user_id,group_id=group_id, check=r))
        return r

    def add_membership(self, group_id=None, user_id=None, role=None):
        """
        gives user_id membership of group_id or role
        if user is None than user_id is that of current logged in user
        """

        group_id = group_id or self.id_group(role)
        try:
            group_id = int(group_id)
        except:
            group_id = self.id_group(group_id) # interpret group_id as a role
        if not user_id and self.user:
            user_id = self.user.id
        membership = self.table_membership()
        record = membership(user_id = user_id,group_id = group_id)
        if record:
            return record.id
        else:
            id = membership.insert(group_id=group_id, user_id=user_id)
        self.update_groups()
        self.log_event(self.messages.add_membership_log,
                       dict(user_id=user_id, group_id=group_id))
        return id

    def del_membership(self, group_id=None, user_id=None, role=None):
        """
        revokes membership from group_id to user_id
        if user_id is None than user_id is that of current logged in user
        """

        group_id = group_id or self.id_group(role)
        if not user_id and self.user:
            user_id = self.user.id
        membership = self.table_membership()
        self.log_event(self.messages.del_membership_log,
                       dict(user_id=user_id,group_id=group_id))
        ret = self.db(membership.user_id
                      == user_id)(membership.group_id
                                  == group_id).delete()
        self.update_groups()
        return ret

    def has_permission(
        self,
        name='any',
        table_name='',
        record_id=0,
        user_id=None,
        group_id=None,
        ):
        """
        checks if user_id or current logged in user is member of a group
        that has 'name' permission on 'table_name' and 'record_id'
        if group_id is passed, it checks whether the group has the permission
        """

        if not group_id and self.settings.everybody_group_id and \
                self.has_permission(
            name,table_name,record_id,user_id=None,
            group_id=self.settings.everybody_group_id): return True

        if not user_id and not group_id and self.user:
            user_id = self.user.id
        if user_id:
            membership = self.table_membership()
            rows = self.db(membership.user_id
                           == user_id).select(membership.group_id)
            groups = set([row.group_id for row in rows])
            if group_id and not group_id in groups:
                return False
        else:
            groups = set([group_id])
        permission = self.table_permission()
        rows = self.db(permission.name == name)(permission.table_name
                 == str(table_name))(permission.record_id
                 == record_id).select(permission.group_id)
        groups_required = set([row.group_id for row in rows])
        if record_id:
            rows = self.db(permission.name
                            == name)(permission.table_name
                     == str(table_name))(permission.record_id
                     == 0).select(permission.group_id)
            groups_required = groups_required.union(set([row.group_id
                    for row in rows]))
        if groups.intersection(groups_required):
            r = True
        else:
            r = False
        if user_id:
            self.log_event(self.messages.has_permission_log,
                           dict(user_id=user_id, name=name,
                                table_name=table_name, record_id=record_id))
        return r

    def add_permission(
        self,
        group_id,
        name='any',
        table_name='',
        record_id=0,
        ):
        """
        gives group_id 'name' access to 'table_name' and 'record_id'
        """

        permission = self.table_permission()
        if group_id == 0:
            group_id = self.user_group()
        record = self.db(permission.group_id==group_id)(permission.name==name)\
            (permission.table_name==str(table_name))\
            (permission.record_id==long(record_id)).select().first()
        if record:
            id = record.id
        else:
            id = permission.insert(group_id=group_id, name=name,
                                   table_name=str(table_name),
                                   record_id=long(record_id))
        self.log_event(self.messages.add_permission_log,
                       dict(permission_id=id, group_id=group_id,
                            name=name, table_name=table_name,
                            record_id=record_id))
        return id

    def del_permission(
        self,
        group_id,
        name='any',
        table_name='',
        record_id=0,
        ):
        """
        revokes group_id 'name' access to 'table_name' and 'record_id'
        """

        permission = self.table_permission()
        self.log_event(self.messages.del_permission_log,
                       dict(group_id=group_id, name=name,
                            table_name=table_name, record_id=record_id))
        return self.db(permission.group_id == group_id)(permission.name
                 == name)(permission.table_name
                           == str(table_name))(permission.record_id
                 == long(record_id)).delete()

    def accessible_query(self, name, table, user_id=None):
        """
        returns a query with all accessible records for user_id or
        the current logged in user
        this method does not work on GAE because uses JOIN and IN

        example:

           db(auth.accessible_query('read', db.mytable)).select(db.mytable.ALL)

        """
        if not user_id:
            user_id = self.user_id
        if isinstance(table,str) and table in self.db.tables():
            table = self.db[table]
        if not isinstance(table,str) and\
                self.has_permission(name, table, 0, user_id):
            return table.id > 0
        db = self.db
        membership = self.table_membership()
        permission = self.table_permission()
        query = table.id.belongs(
            db(membership.user_id == user_id)\
                (membership.group_id == permission.group_id)\
                (permission.name == name)\
                (permission.table_name == table)\
                ._select(permission.record_id))
        if self.settings.everybody_group_id:
            query|=table.id.belongs(
                db(permission.group_id==self.settings.everybody_group_id)\
                    (permission.name == name)\
                    (permission.table_name == table)\
                    ._select(permission.record_id))
        return query

    @staticmethod
    def archive(form,
                archive_table=None,
                current_record='current_record',
                archive_current=False,
                fields=None):
        """
        If you have a table (db.mytable) that needs full revision history you can just do:

            form=crud.update(db.mytable,myrecord,onaccept=auth.archive)

        or

            form=SQLFORM(db.mytable,myrecord).process(onaccept=auth.archive)

        crud.archive will define a new table "mytable_archive" and store
        a copy of the current record (if archive_current=True)
        or a copy of the previous record (if archive_current=False)
        in the newly created table including a reference
        to the current record.

        fields allows to specify extra fields that need to be archived.

        If you want to access such table you need to define it yourself
        in a model:

            db.define_table('mytable_archive',
                Field('current_record',db.mytable),
                db.mytable)

        Notice such table includes all fields of db.mytable plus one: current_record.
        crud.archive does not timestamp the stored record unless your original table
        has a fields like:

            db.define_table(...,
                Field('saved_on','datetime',
                     default=request.now,update=request.now,writable=False),
                Field('saved_by',auth.user,
                     default=auth.user_id,update=auth.user_id,writable=False),

        there is nothing special about these fields since they are filled before
        the record is archived.

        If you want to change the archive table name and the name of the reference field
        you can do, for example:

            db.define_table('myhistory',
                Field('parent_record',db.mytable),
                db.mytable)

        and use it as:

            form=crud.update(db.mytable,myrecord,
                             onaccept=lambda form:crud.archive(form,
                             archive_table=db.myhistory,
                             current_record='parent_record'))

        """
        if not archive_current and not form.record:
            return None
        table = form.table
        if not archive_table:
            archive_table_name = '%s_archive' % table
            if not archive_table_name in table._db:
                table._db.define_table(
                    archive_table_name,
                    Field(current_record,table),
                    *[field.clone(unique=False) for field in table])
            archive_table = table._db[archive_table_name]
        new_record = {current_record:form.vars.id}
        for fieldname in archive_table.fields:
            if not fieldname in ['id',current_record]:
                if archive_current and fieldname in form.vars:
                    new_record[fieldname]=form.vars[fieldname]
                elif form.record and fieldname in form.record:
                    new_record[fieldname]=form.record[fieldname]
        if fields:
            new_record.update(fields)
        id = archive_table.insert(**new_record)
        return id

    def wiki(self,slug=None,env=None,manage_permissions=False,force_prefix='', resolve=True):
        if not hasattr(self,'_wiki'):
            self._wiki = Wiki(self,
                              manage_permissions=manage_permissions,
                              force_prefix=force_prefix,env=env)
        else:
            self._wiki.env.update(env or {})
        # if resolve is set to True, process request as wiki call
        # resolve=False allows initial setup without wiki redirection
        if resolve:
            return self._wiki.read(slug)['content'] if slug else self._wiki()

class Crud(object):

    def url(self, f=None, args=None, vars=None):
        """
        this should point to the controller that exposes
        download and crud
        """
        if args is None: args=[]
        if vars is None: vars={}
        return URL(c=self.settings.controller, f=f, args=args, vars=vars)

    def __init__(self, environment, db=None, controller='default'):
        self.db = db
        if not db and environment and isinstance(environment,DAL):
            self.db = environment
        elif not db:
            raise SyntaxError, "must pass db as first or second argument"
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
        messages.submit_button = 'Submit'
        messages.delete_label = 'Check to delete:'
        messages.record_created = 'Record Created'
        messages.record_updated = 'Record Updated'
        messages.record_deleted = 'Record Deleted'

        messages.update_log = 'Record %(id)s updated'
        messages.create_log = 'Record %(id)s created'
        messages.read_log = 'Record %(id)s read'
        messages.delete_log = 'Record %(id)s deleted'

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
            return self.select(table,linkto=self.url(args='read'))
        elif args[0] == 'search':
            form, rows = self.search(table,linkto=self.url(args='read'))
            return DIV(form,SQLTABLE(rows))
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
            self.settings.logger.log_event(message, vars, origin = 'crud')

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
                            _href=self.url(args=('select',name)))) \
                           for name in self.db.tables])

    @staticmethod
    def archive(form,archive_table=None,current_record='current_record'):
        return Auth.archive(form,archive_table=archive_table,
                            current_record=current_record)

    def update(
        self,
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
        ):
        """
        method: Crud.update(table, record, [next=DEFAULT
            [, onvalidation=DEFAULT [, onaccept=DEFAULT [, log=DEFAULT
            [, message=DEFAULT[, deletable=DEFAULT]]]]]])

        """
        if not (isinstance(table, self.db.Table) or table in self.db.tables) \
                or (isinstance(record, str) and not str(record).isdigit()):
            raise HTTP(404)
        if not isinstance(table, self.db.Table):
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
            request.vars.update(json_parser.loads(request.vars.json))
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
            log = self.messages.update_log
        if deletable is DEFAULT:
            deletable = self.settings.update_deletable
        if message is DEFAULT:
            message = self.messages.record_updated
        form = SQLFORM(
            table,
            record,
            hidden=dict(_next=next),
            showid=self.settings.showid,
            submit_button=self.messages.submit_button,
            delete_label=self.messages.delete_label,
            deletable=deletable,
            upload=self.settings.download_url,
            formstyle=self.settings.formstyle,
            separator=self.settings.label_separator
            )
        self.accepted = False
        self.deleted = False
        captcha = self.settings.update_captcha or self.settings.captcha
        if record and captcha:
            addrow(form, captcha.label, captcha, captcha.comment,
                         self.settings.formstyle,'captcha__row')
        captcha = self.settings.create_captcha or self.settings.captcha
        if not record and captcha:
            addrow(form, captcha.label, captcha, captcha.comment,
                         self.settings.formstyle,'captcha__row')
        if not request.extension in ('html','load'):
            (_session, _formname) = (None, None)
        else:
            (_session, _formname) = (session, '%s/%s' % (table._tablename, form.record_id))
        if not formname is DEFAULT:
            _formname = formname
        keepvalues = self.settings.keepvalues
        if request.vars.delete_this_record:
            keepvalues = False
        if isinstance(onvalidation,StorageList):
            onvalidation=onvalidation.get(table._tablename, [])
        if form.accepts(request, _session, formname=_formname,
                        onvalidation=onvalidation, keepvalues=keepvalues,
                        hideerror=self.settings.hideerror,
                        detect_record_change = self.settings.detect_record_change):
            self.accepted = True
            response.flash = message
            if log:
                self.log_event(log, form.vars)
            if request.vars.delete_this_record:
                self.deleted = True
                message = self.messages.record_deleted
                callback(ondelete,form,table._tablename)
            response.flash = message
            callback(onaccept,form,table._tablename)
            if not request.extension in ('html','load'):
                raise HTTP(200, 'RECORD CREATED/UPDATED')
            if isinstance(next, (list, tuple)): ### fix issue with 2.6
               next = next[0]
            if next: # Only redirect when explicit
                next = replace_id(next, form)
                session.flash = response.flash
                redirect(next)
        elif not request.extension in ('html','load'):
            raise HTTP(401,serializers.json(dict(errors=form.errors)))
        return form

    def create(
        self,
        table,
        next=DEFAULT,
        onvalidation=DEFAULT,
        onaccept=DEFAULT,
        log=DEFAULT,
        message=DEFAULT,
        formname=DEFAULT,
        ):
        """
        method: Crud.create(table, [next=DEFAULT [, onvalidation=DEFAULT
            [, onaccept=DEFAULT [, log=DEFAULT[, message=DEFAULT]]]]])
        """

        if next is DEFAULT:
            next = self.settings.create_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.create_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.create_onaccept
        if log is DEFAULT:
            log = self.messages.create_log
        if message is DEFAULT:
            message = self.messages.record_created
        return self.update(
            table,
            None,
            next=next,
            onvalidation=onvalidation,
            onaccept=onaccept,
            log=log,
            message=message,
            deletable=False,
            formname=formname,
            )

    def read(self, table, record):
        if not (isinstance(table, self.db.Table) or table in self.db.tables) \
                or (isinstance(record, str) and not str(record).isdigit()):
            raise HTTP(404)
        if not isinstance(table, self.db.Table):
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
        if not current.request.extension in ('html','load'):
            return table._filter_fields(form.record, id=True)
        return form

    def delete(
        self,
        table,
        record_id,
        next=DEFAULT,
        message=DEFAULT,
        ):
        """
        method: Crud.delete(table, record_id, [next=DEFAULT
            [, message=DEFAULT]])
        """
        if not (isinstance(table, self.db.Table) or table in self.db.tables):
            raise HTTP(404)
        if not isinstance(table, self.db.Table):
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
            callback(self.settings.delete_onvalidation,record)
            del table[record_id]
            callback(self.settings.delete_onaccept,record,table._tablename)
            session.flash = message
        redirect(next)

    def rows(
        self,
        table,
        query=None,
        fields=None,
        orderby=None,
        limitby=None,
        ):
        if not (isinstance(table, self.db.Table) or table in self.db.tables):
            raise HTTP(404)
        if not self.has_permission('select', table):
            redirect(self.settings.auth.settings.on_failed_authorization)
        #if record_id and not self.has_permission('select', table):
        #    redirect(self.settings.auth.settings.on_failed_authorization)
        if not isinstance(table, self.db.Table):
            table = self.db[table]
        if not query:
            query = table.id > 0
        if not fields:
            fields = [field for field in table if field.readable]
        else:
            fields = [table[f] if isinstance(f,str) else f for f in fields]
        rows = self.db(query).select(*fields,**dict(orderby=orderby,
                                                    limitby=limitby))
        return rows

    def select(
        self,
        table,
        query=None,
        fields=None,
        orderby=None,
        limitby=None,
        headers=None,
        **attr
        ):
        headers = headers or {}
        rows = self.rows(table,query,fields,orderby,limitby)
        if not rows:
            return None # Nicer than an empty table.
        if not 'upload' in attr:
            attr['upload'] = self.url('download')
        if not current.request.extension in ('html','load'):
            return rows.as_list()
        if not headers:
            if isinstance(table,str):
                table = self.db[table]
            headers = dict((str(k),k.label) for k in table)
        return SQLTABLE(rows,headers=headers,**attr)

    def get_format(self, field):
        rtable = field._db[field.type[10:]]
        format = rtable.get('_format', None)
        if format and isinstance(format, str):
            return format[2:-2]
        return field.name

    def get_query(self, field, op, value, refsearch=False):
        try:
            if refsearch: format = self.get_format(field)
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
                    return field.like(value+'%')
                else:
                    return lambda row: str(row[field.name][format]).startswith(value)
            elif op == 'ends with':
                if not refsearch:
                    return field.like('%'+value)
                else:
                    return lambda row: str(row[field.name][format]).endswith(value)
            elif op == 'contains':
                if not refsearch:
                    return field.like('%'+value+'%')
                else:
                    return lambda row: value in row[field.name][format]
        except:
            return None

    def search(self, *tables, **args):
        """
        Creates a search form and its results for a table
        Example usage:
        form, results = crud.search(db.test,
                               queries = ['equals', 'not equal', 'contains'],
                               query_labels={'equals':'Equals',
                                             'not equal':'Not equal'},
                               fields = ['id','children'],
                               field_labels = {'id':'ID','children':'Children'},
                               zero='Please choose',
                               query = (db.test.id > 0)&(db.test.id != 3) )
        """
        table = tables[0]
        fields = args.get('fields', table.fields)
        request = current.request
        db = self.db
        if not (isinstance(table, db.Table) or table in db.tables):
            raise HTTP(404)
        attributes = {}
        for key in ('orderby','groupby','left','distinct','limitby','cache'):
            if key in args: attributes[key]=args[key]
        tbl = TABLE()
        selected = []; refsearch = []; results = []
        showall = args.get('showall', False)
        if showall:
            selected = fields
        chkall = args.get('chkall', False)
        if chkall:
            for f in fields:
                request.vars['chk%s'%f] = 'on'
        ops = args.get('queries', [])
        zero = args.get('zero', '')
        if not ops:
            ops = ['equals', 'not equal', 'greater than',
                   'less than', 'starts with',
                   'ends with', 'contains']
        ops.insert(0,zero)
        query_labels = args.get('query_labels', {})
        query = args.get('query',table.id > 0)
        field_labels = args.get('field_labels',{})
        for field in fields:
            field = table[field]
            if not field.readable: continue
            fieldname = field.name
            chkval = request.vars.get('chk' + fieldname, None)
            txtval = request.vars.get('txt' + fieldname, None)
            opval = request.vars.get('op' + fieldname, None)
            row = TR(TD(INPUT(_type = "checkbox", _name = "chk" + fieldname,
                              _disabled = (field.type == 'id'),
                              value = (field.type == 'id' or chkval == 'on'))),
                     TD(field_labels.get(fieldname,field.label)),
                     TD(SELECT([OPTION(query_labels.get(op,op),
                                       _value=op) for op in ops],
                               _name = "op" + fieldname,
                               value = opval)),
                     TD(INPUT(_type = "text", _name = "txt" + fieldname,
                              _value = txtval, _id='txt' + fieldname,
                              _class = str(field.type))))
            tbl.append(row)
            if request.post_vars and (chkval or field.type=='id'):
                if txtval and opval != '':
                    if field.type[0:10] == 'reference ':
                        refsearch.append(self.get_query(field,
                                    opval, txtval, refsearch=True))
                    else:
                        value, error = field.validate(txtval)
                        if not error:
                            ### TODO deal with 'starts with', 'ends with', 'contains' on GAE
                            query &= self.get_query(field, opval, value)
                        else:
                            row[3].append(DIV(error,_class='error'))
                selected.append(field)
        form = FORM(tbl,INPUT(_type="submit"))
        if selected:
            try:
                results = db(query).select(*selected,**attributes)
                for r in refsearch:
                    results = results.find(r)
            except: # hmmm, we should do better here
                results = None
        return form, results


urllib2.install_opener(urllib2.build_opener(urllib2.HTTPCookieProcessor()))

def fetch(url, data=None, headers=None,
          cookie=Cookie.SimpleCookie(),
          user_agent='Mozilla/5.0'):
    headers = headers or {}
    if not data is None:
        data = urllib.urlencode(data)
    if user_agent: headers['User-agent'] = user_agent
    headers['Cookie'] = ' '.join(['%s=%s;'%(c.key,c.value) for c in cookie.values()])
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
                                      allow_truncated=False,follow_redirects=False,
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
        a = urllib.quote(address)
        txt = fetch('http://maps.googleapis.com/maps/api/geocode/xml?sensor=false&address=%s'
                     % a)
        item = regex_geocode.search(txt)
        (la, lo) = (float(item.group('la')), float(item.group('lo')))
        return (la, lo)
    except:
        return (0.0, 0.0)


def universal_caller(f, *a, **b):
    c = f.func_code.co_argcount
    n = f.func_code.co_varnames[:c]

    defaults = f.func_defaults or []
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

    def __init__(self, environment=None):
        self.run_procedures = {}
        self.csv_procedures = {}
        self.xml_procedures = {}
        self.rss_procedures = {}
        self.json_procedures = {}
        self.jsonrpc_procedures = {}
        self.xmlrpc_procedures = {}
        self.amfrpc_procedures = {}
        self.amfrpc3_procedures = {}
        self.soap_procedures = {}

    def run(self, f):
        """
        example:

            service = Service()
            @service.run
            def myfunction(a, b):
                return a + b
            def call():
                return service()

        Then call it with:

            wget http://..../app/default/call/run/myfunction?a=3&b=4

        """
        self.run_procedures[f.__name__] = f
        return f

    def csv(self, f):
        """
        example:

            service = Service()
            @service.csv
            def myfunction(a, b):
                return a + b
            def call():
                return service()

        Then call it with:

            wget http://..../app/default/call/csv/myfunction?a=3&b=4

        """
        self.run_procedures[f.__name__] = f
        return f

    def xml(self, f):
        """
        example:

            service = Service()
            @service.xml
            def myfunction(a, b):
                return a + b
            def call():
                return service()

        Then call it with:

            wget http://..../app/default/call/xml/myfunction?a=3&b=4

        """
        self.run_procedures[f.__name__] = f
        return f

    def rss(self, f):
        """
        example:

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
        example:

            service = Service()
            @service.json
            def myfunction(a, b):
                return [{a: b}]
            def call():
                return service()

        Then call it with:

            wget http://..../app/default/call/json/myfunction?a=hello&b=world

        """
        self.json_procedures[f.__name__] = f
        return f

    def jsonrpc(self, f):
        """
        example:

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

    def xmlrpc(self, f):
        """
        example:

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
        example:

            service = Service()
            @service.amfrpc
            def myfunction(a, b):
                return a + b
            def call():
                return service()

        The call it with:

            wget http://..../app/default/call/amfrpc/myfunction?a=hello&b=world

        """
        self.amfrpc_procedures[f.__name__] = f
        return f

    def amfrpc3(self, domain='default'):
        """
        example:

            service = Service()
            @service.amfrpc3('domain')
            def myfunction(a, b):
                return a + b
            def call():
                return service()

        The call it with:

            wget http://..../app/default/call/amfrpc3/myfunction?a=hello&b=world

        """
        if not isinstance(domain, str):
            raise SyntaxError, "AMF3 requires a domain for function"

        def _amfrpc3(f):
            if domain:
                self.amfrpc3_procedures[domain+'.'+f.__name__] = f
            else:
                self.amfrpc3_procedures[f.__name__] = f
            return f
        return _amfrpc3

    def soap(self, name=None, returns=None, args=None,doc=None):
        """
        example:

            service = Service()
            @service.soap('MyFunction',returns={'result':int},args={'a':int,'b':int,})
            def myfunction(a, b):
                return a + b
            def call():
                return service()

        The call it with:

            from gluon.contrib.pysimplesoap.client import SoapClient
            client = SoapClient(wsdl="http://..../app/default/call/soap?WSDL")
            response = client.MyFunction(a=1,b=2)
            return response['result']

        Exposes online generated documentation and xml example messages at:
        - http://..../app/default/call/soap
        """

        def _soap(f):
            self.soap_procedures[name or f.__name__] = f, returns, args, doc
            return f
        return _soap

    def serve_run(self, args=None):
        request = current.request
        if not args:
            args = request.args
        if args and args[0] in self.run_procedures:
            return str(universal_caller(self.run_procedures[args[0]],
                                        *args[1:], **dict(request.vars)))
        self.error()

    def serve_csv(self, args=None):
        request = current.request
        response = current.response
        response.headers['Content-Type'] = 'text/x-csv'
        if not args:
            args = request.args

        def none_exception(value):
            if isinstance(value, unicode):
                return value.encode('utf8')
            if hasattr(value, 'isoformat'):
                return value.isoformat()[:19].replace('T', ' ')
            if value is None:
                return '<NULL>'
            return value
        if args and args[0] in self.run_procedures:
            r = universal_caller(self.run_procedures[args[0]],
                                 *args[1:], **dict(request.vars))
            s = cStringIO.StringIO()
            if hasattr(r, 'export_to_csv_file'):
                r.export_to_csv_file(s)
            elif r and isinstance(r[0], (dict, Storage)):
                import csv
                writer = csv.writer(s)
                writer.writerow(r[0].keys())
                for line in r:
                    writer.writerow([none_exception(v) \
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
        if args and args[0] in self.run_procedures:
            s = universal_caller(self.run_procedures[args[0]],
                                 *args[1:], **dict(request.vars))
            if hasattr(s, 'as_list'):
                s = s.as_list()
            return serializers.xml(s,quote=False)
        self.error()

    def serve_rss(self, args=None):
        request = current.request
        response = current.response
        if not args:
            args = request.args
        if args and args[0] in self.rss_procedures:
            feed = universal_caller(self.rss_procedures[args[0]],
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
            s = universal_caller(self.json_procedures[args[0]],*args[1:],**d)
            if hasattr(s, 'as_list'):
                s = s.as_list()
            return response.json(s)
        self.error()

    class JsonRpcException(Exception):
        def __init__(self,code,info):
            self.code,self.info = code,info

    def serve_jsonrpc(self):
        def return_response(id, result):
            return serializers.json({'version': '1.1',
                'id': id, 'result': result, 'error': None})
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
        data = json_parser.loads(request.body.read())
        id, method, params = data['id'], data['method'], data.get('params','')
        if not method in methods:
            return return_error(id, 100, 'method "%s" does not exist' % method)
        try:
            s = methods[method](*params)
            if hasattr(s, 'as_list'):
                s = s.as_list()
            return return_response(id, s)
        except Service.JsonRpcException, e:
            return return_error(id, e.code, e.info)
        except BaseException:
            etype, eval, etb = sys.exc_info()
            code = 100
            message = '%s: %s' % (etype.__name__, eval)
            data = request.is_local and traceback.format_tb(etb)
            return return_error(id, code, message, data)
        except:
            etype, eval, etb = sys.exc_info()
            return return_error(id, 100, 'Exception %s: %s' % (etype, eval))

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
        if version==3:
            return pyamf.remoting.encode(pyamf_response).getvalue()
        else:
            return pyamf.remoting.encode(pyamf_response, context).getvalue()

    def serve_soap(self, version="1.1"):
        try:
            from contrib.pysimplesoap.server import SoapDispatcher
        except:
            return "pysimplesoap not installed in contrib"
        request = current.request
        response = current.response
        procedures = self.soap_procedures

        location = "%s://%s%s" % (
                        request.env.wsgi_url_scheme,
                        request.env.http_host,
                        URL(r=request,f="call/soap",vars={}))
        namespace = 'namespace' in response and response.namespace or location
        documentation = response.description or ''
        dispatcher = SoapDispatcher(
            name = response.title,
            location = location,
            action = location, # SOAPAction
            namespace = namespace,
            prefix='pys',
            documentation = documentation,
            ns = True)
        for method, (function, returns, args, doc) in procedures.iteritems():
            dispatcher.register_function(method, function, returns, args, doc)
        if request.env.request_method == 'POST':
            # Process normal Soap Operation
            response.headers['Content-Type'] = 'text/xml'
            return dispatcher.dispatch(request.body.read())
        elif 'WSDL' in request.vars:
            # Return Web Service Description
            response.headers['Content-Type'] = 'text/xml'
            return dispatcher.wsdl()
        elif 'op' in request.vars:
            # Return method help webpage
            response.headers['Content-Type'] = 'text/html'
            method  = request.vars['op']
            sample_req_xml, sample_res_xml, doc = dispatcher.help(method)
            body = [H1("Welcome to Web2Py SOAP webservice gateway"),
                    A("See all webservice operations",
                      _href=URL(r=request,f="call/soap",vars={})),
                    H2(method),
                    P(doc),
                    UL(LI("Location: %s" % dispatcher.location),
                       LI("Namespace: %s" % dispatcher.namespace),
                       LI("SoapAction: %s" % dispatcher.action),
                    ),
                    H3("Sample SOAP XML Request Message:"),
                    CODE(sample_req_xml,language="xml"),
                    H3("Sample SOAP XML Response Message:"),
                    CODE(sample_res_xml,language="xml"),
                    ]
            return {'body': body}
        else:
            # Return general help and method list webpage
            response.headers['Content-Type'] = 'text/html'
            body = [H1("Welcome to Web2Py SOAP webservice gateway"),
                    P(response.description),
                    P("The following operations are available"),
                    A("See WSDL for webservice description",
                      _href=URL(r=request,f="call/soap",vars={"WSDL":None})),
                    UL([LI(A("%s: %s" % (method, doc or ''),
                             _href=URL(r=request,f="call/soap",vars={'op': method})))
                        for method, doc in dispatcher.list_methods()]),
                    ]
            return {'body': body}

    def __call__(self):
        """
        register services with:
        service = Service()
        @service.run
        @service.rss
        @service.json
        @service.jsonrpc
        @service.xmlrpc
        @service.amfrpc
        @service.amfrpc3('domain')
        @service.soap('Method', returns={'Result':int}, args={'a':int,'b':int,})

        expose services with

        def call(): return service()

        call services with
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


def completion(callback):
    """
    Executes a task on completion of the called action. For example:

        from gluon.tools import completion
        @completion(lambda d: logging.info(repr(d)))
        def index():
            return dict(message='hello')

    It logs the output of the function every time input is called.
    The argument of completion is executed in a new thread.
    """
    def _completion(f):
        def __completion(*a,**b):
            d = None
            try:
                d = f(*a,**b)
                return d
            finally:
                thread.start_new_thread(callback,(d,))
        return __completion
    return _completion

def prettydate(d,T=lambda x:x):
    if isinstance(d,datetime.datetime):
        dt = datetime.datetime.now() - d
    elif isinstance(d,datetime.date):
        dt = datetime.date.today() - d
    elif not d:
        return ''
    else:
        return '[invalid date]'
    if dt.days >= 2*365:
        return T('%d years ago') % int(dt.days / 365)
    elif dt.days >= 365:
        return T('1 year ago')
    elif dt.days >= 60:
        return T('%d months ago') % int(dt.days / 30)
    elif dt.days > 21:
        return T('1 month ago')
    elif dt.days >= 14:
        return T('%d weeks ago') % int(dt.days / 7)
    elif dt.days >= 7:
        return T('1 week ago')
    elif dt.days > 1:
        return T('%d days ago') % dt.days
    elif dt.days == 1:
        return T('1 day ago')
    elif dt.seconds >= 2*60*60:
        return T('%d hours ago') % int(dt.seconds / 3600)
    elif dt.seconds >= 60*60:
        return T('1 hour ago')
    elif dt.seconds >= 2*60:
        return T('%d minutes ago') % int(dt.seconds / 60)
    elif dt.seconds >= 60:
        return T('1 minute ago')
    elif dt.seconds > 1:
        return T('%d seconds ago') % dt.seconds
    elif dt.seconds == 1:
        return T('1 second ago')
    else:
        return T('now')

def test_thread_separation():
    def f():
        c=PluginManager()
        lock1.acquire()
        lock2.acquire()
        c.x=7
        lock1.release()
        lock2.release()
    lock1=thread.allocate_lock()
    lock2=thread.allocate_lock()
    lock1.acquire()
    thread.start_new_thread(f,())
    a=PluginManager()
    a.x=5
    lock1.release()
    lock2.acquire()
    return a.x

class PluginManager(object):
    """

    Plugin Manager is similar to a storage object but it is a single level singleton
    this means that multiple instances within the same thread share the same attributes
    Its constructor is also special. The first argument is the name of the plugin you are defining.
    The named arguments are parameters needed by the plugin with default values.
    If the parameters were previous defined, the old values are used.

    For example:

    ### in some general configuration file:
    >>> plugins = PluginManager()
    >>> plugins.me.param1=3

    ### within the plugin model
    >>> _ = PluginManager('me',param1=5,param2=6,param3=7)

    ### where the plugin is used
    >>> print plugins.me.param1
    3
    >>> print plugins.me.param2
    6
    >>> plugins.me.param3 = 8
    >>> print plugins.me.param3
    8

    Here are some tests:

    >>> a=PluginManager()
    >>> a.x=6
    >>> b=PluginManager('check')
    >>> print b.x
    6
    >>> b=PluginManager() # reset settings
    >>> print b.x
    <Storage {}>
    >>> b.x=7
    >>> print a.x
    7
    >>> a.y.z=8
    >>> print b.y.z
    8
    >>> test_thread_separation()
    5
    >>> plugins=PluginManager('me',db='mydb')
    >>> print plugins.me.db
    mydb
    >>> print 'me' in plugins
    True
    >>> print plugins.me.installed
    True
    """
    instances = {}
    def __new__(cls,*a,**b):
        id = thread.get_ident()
        lock = thread.allocate_lock()
        try:
            lock.acquire()
            try:
                return cls.instances[id]
            except KeyError:
                instance = object.__new__(cls,*a,**b)
                cls.instances[id] = instance
                return instance
        finally:
            lock.release()
    def __init__(self,plugin=None,**defaults):
        if not plugin:
            self.__dict__.clear()
        settings = self.__getattr__(plugin)
        settings.installed = True
        settings.update(
            (k,v) for k,v in defaults.items() if not k in settings)
                            
    def __getattr__(self, key):
        if not key in self.__dict__:
            self.__dict__[key] = Storage()
        return self.__dict__[key]
    def keys(self):
        return self.__dict__.keys()
    def __contains__(self,key):
        return key in self.__dict__

class Expose(object):
    def __init__(self,base=None,basename='base'):
        current.session.forget()
        base = base or os.path.join(current.request.folder,'static')
        self.basename = basename
        args = self.args = current.request.raw_args and \
            current.request.raw_args.split('/') or []
        filename = os.path.join(base,*args)
        if not os.path.normpath(filename).startswith(base):
            raise HTTP(401,"NOT AUTHORIZED")
        if not os.path.isdir(filename):
            current.response.headers['Content-Type'] = contenttype(filename)
            raise HTTP(200,open(filename,'rb'),**current.response.headers)
        self.path = path = os.path.join(filename,'*')
        self.folders = [f[len(path)-1:] for f in sorted(glob.glob(path)) \
                            if os.path.isdir(f) and not self.isprivate(f)]
        self.filenames = [f[len(path)-1:] for f in sorted(glob.glob(path)) \
                            if not os.path.isdir(f) and not self.isprivate(f)]

    def breadcrumbs(self, basename):
        path = []
        span = SPAN()
        span.append(A(basename,_href=URL()))
        span.append('/')
        args = current.request.raw_args and \
            current.request.raw_args.split('/') or []
        for arg in args:
            path.append(arg)
            span.append(A(arg,_href=URL(args='/'.join(path))))
            span.append('/')
        return span

    def table_folders(self):
        return TABLE(*[TR(TD(A(folder,_href=URL(args=self.args+[folder])))) \
                           for folder in self.folders])
    @staticmethod
    def isprivate(f):
        return 'private' in f or f.startswith('.') or f.endswith('~')

    @staticmethod
    def isimage(f):
        return f.rsplit('.')[-1].lower() in ('png','jpg','jpeg','gif','tiff')

    def table_files(self,width=160):
        return TABLE(*[TR(TD(A(f,_href=URL(args=self.args+[f]))),
                          TD(IMG(_src=URL(args=self.args+[f]),
                                 _style='max-width:%spx' % width) \
                                 if width and self.isimage(f) else '')) \
                           for f in self.filenames])
    def xml(self):
        return DIV(
            H2(self.breadcrumbs(self.basename)),
            H3('Folders'),
            self.table_folders(),
            H3('Files'),
            self.table_files()).xml()


class Wiki(object):
    everybody = 'everybody'
    rows_page = 25
    regex_redirect = re.compile('redirect\s+(\w+\://\S+)\s*')
    def markmin_render(self,page):
        html = MARKMIN(page.body,url=True,environment=self.env,
                       autolinks=lambda link: expand_one(link,{})).xml()
        html += DIV(_class='w2p_wiki_tags',
                    *[A(t.strip(),_href=URL(args='_search',vars=dict(q=t)))
                      for t in page.tags or [] if t.strip()]).xml()
        return html
    @staticmethod
    def component(text):
        """
        In wiki docs allows @{component:controller/function/args}
        which renders as a LOAD(..., ajax=True)
        """
        items = text.split('/')
        controller, function, args = items[0], items[1], items[2:]
        return LOAD(controller, function, args=args, ajax=True).xml()
    def __init__(self,auth,env=None,render='markmin',
                 manage_permissions=False,force_prefix=''):
        self.env = env or {}
        self.env['component'] = Wiki.component
        if render == 'markmin': render=self.markmin_render
        self.auth = auth
        if self.auth.user:
            self.force_prefix = force_prefix % self.auth.user
        else:
            self.force_prefix = force_prefix
        self.host = current.request.env.http_host
        perms = self.manage_permissions = manage_permissions
        db = auth.db
        table_definitions = {
            'wiki_page':{
                'args':[
                    Field('slug',
                          requires=[IS_SLUG(),
                                    IS_NOT_IN_DB(db,'wiki_page.slug')],
                          readable=False,writable=False),
                    Field('title',unique=True),
                    Field('body','text',notnull=True),
                    Field('tags','list:string'),
                    Field('can_read','list:string',
                          writable=perms,
                          readable=perms,
                          default=[Wiki.everybody]),
                    Field('can_edit', 'list:string',
                          writable=perms,readable=perms,
                          default=[Wiki.everybody]),
                    Field('changelog'),
                    Field('html','text',compute=render,
                          readable=False, writable=False),
                    auth.signature],
                'vars':{'format':'%(title)s'}},
             'wiki_tag':{
                'args':[
                    Field('name'),
                    Field('wiki_page','reference wiki_page'),
                    auth.signature],
                'vars':{'format':'%(name)s'}},
           'wiki_media':{
                'args':[
                    Field('wiki_page','reference wiki_page'),
                    Field('title',required=True),
                    Field('file','upload',required=True),
                    auth.signature],
                'vars':{'format':'%(title)s'}}
            }

        # define only non-existent tables
        for key, value in table_definitions.iteritems():
            if not key in db.tables():
                db.define_table(key, *value['args'], **value['vars'])

        def update_tags_insert(page,id,db=db):
            for tag in page.tags or []:
                tag = tag.strip().lower()
                if tag: db.wiki_tag.insert(name=tag,wiki_page=id)
        def update_tags_update(dbset,page,db=db):
            page = dbset.select().first()
            db(db.wiki_tag.wiki_page==page.id).delete()
            for tag in page.tags or []:
                tag = tag.strip().lower()
                if tag: db.wiki_tag.insert(name=tag,wiki_page=page.id)
        db.wiki_page._after_insert.append(update_tags_insert)
        db.wiki_page._after_update.append(update_tags_update)
        if auth.user and check_credentials(current.request) and \
                not 'wiki_editor' in auth.user_groups.values():
            group = db.auth_group(role='wiki_editor')
            gid = group.id if group else db.auth_group.insert(role='wiki_editor')
            auth.add_membership(gid)
    # WIKI ACCESS POLICY
    def not_authorized(self,page=None):
        raise HTTP(401)
    def can_read(self,page):
        if 'everybody' in page.can_read or not self.manage_permissions:
            return True
        elif self.auth.user:
            groups = self.auth.user_groups.values()
            if ('wiki_editor' in groups or
                set(groups).intersection(set(page.can_read+page.can_edit)) or
                page.created_by==self.auth.user.id): return True
        return False
    def can_edit(self,page=None):
        if not self.auth.user: redirect(self.auth.settings.login_url)
        groups = self.auth.user_groups.values()
        return ('wiki_editor' in groups or
                (page is None and 'wiki_author' in groups) or
                not page is None and (
                set(groups).intersection(set(page.can_edit)) or
                page.created_by==self.auth.user.id))
    def can_manage(self):
        if not self.auth.user: redirect(self.auth.settings.login_url)
        groups = self.auth.user_groups.values()
        return 'wiki_editor' in groups
    def can_search(self):
        return True
    ### END POLICY
    def __call__(self):
        request =  current.request
        automenu = self.menu(request.controller,request.function)
        current.response.menu += automenu
        zero = request.args(0)
        if zero and zero.isdigit():
            return self.media(int(zero))
        elif not zero or not zero.startswith('_'):
            return self.read(zero or 'index')
        elif zero=='_edit':
            return self.edit(request.args(1) or 'index')
        elif zero=='_editmedia':
            return self.editmedia(request.args(1) or 'index')
        elif zero=='_create':
            return self.create()
        elif zero=='_pages':
            return self.pages()
        elif zero=='_search':
            return self.search()
        elif zero=='_recent':
            ipage = int(request.vars.page or 0)
            query = self.auth.db.wiki_page.created_by==request.args(1,cast=int)
            return self.search(query=query,
                               orderby=~self.auth.db.wiki_page.created_on,
                               limitby=(ipage*self.rows_page,
                                        (ipage+1)*self.rows_page),
                               )
        elif zero=='_cloud':
            return self.cloud()

    def first_paragraph(self,page):
        if not self.can_read(page):
            mm = page.body.replace('\r','')
            ps = [p for p in mm.split('\n\n') \
                      if not p.startswith('#') and p.strip()]
            if ps: return ps[0]
        return ''

    def fix_hostname(self,body):
        return body.replace('://HOSTNAME','://%s' % self.host)

    def read(self,slug):
        if slug in '_cloud': return self.cloud()
        elif slug in '_search': return self.search()
        page = self.auth.db.wiki_page(slug=slug)
        if not page:
            redirect(URL(args=('_create',slug)))
        if not self.can_read(page): return self.not_authorized(page)
        if current.request.extension == 'html':
            if not page:
                url = URL(args=('_edit',slug))
                return dict(content=A('Create page "%s"' % slug,_href=url,_class="btn"))
            else:
                match = self.regex_redirect.match(page.body)
                if match: redirect(match.group(1))
                return dict(content=XML(self.fix_hostname(page.html)))
        elif current.request.extension == 'load':
            return self.fix_hostname(page.html) if page else ''
        else:
            if not page:
                raise HTTP(404)
            else:
                return dict(title=page.title,
                            slug=page.slug,
                            content=page.body,
                            tags=page.tags,
                            created_on=page.created_on,
                            modified_on=page.modified_on)
    def check_editor(self,role='wiki_editor',act=False):
        if not self.auth.user:
            if not act: return False
            redirect(self.auth.settings.login_url)
        elif not self.auth.has_membership(role):
            if not act: return False
            raise HTTP(401, "Not Authorized")
        return True
    def edit(self,slug):
        auth = self.auth
        db = auth.db
        page = db.wiki_page(slug=slug)
        if not self.can_edit(page): return self.not_authorized(page)
        title_guess = ' '.join(c.capitalize() for c in slug.split('-'))
        if not page:
            if not (self.can_manage() or slug.startswith(self.force_prefix)):
                current.session.flash='slug must have "%s" prefix' \
                    % self.force_prefix
                redirect(URL(args=('_edit',self.force_prefix+slug)))
            db.wiki_page.can_read.default = [Wiki.everybody]
            db.wiki_page.can_edit.default = [auth.user_group_role()]
            db.wiki_page.title.default = title_guess
            db.wiki_page.slug.default = slug
            if slug == 'wiki-menu':
                db.wiki_page.body.default = '- Menu Item > @////index\n- - Submenu > http://web2py.com'
            else:
                db.wiki_page.body.default = '## %s\n\npage content' % title_guess
        vars = current.request.post_vars
        if vars.body:
            vars.body=vars.body.replace('://%s' % self.host,'://HOSTNAME')
        form = SQLFORM(db.wiki_page,page,deletable=True,
                       formstyle='table2cols',showid=False).process()
        if form.deleted:
            current.session.flash = 'page deleted'
            redirect(URL())
        elif form.accepted:
            current.session.flash = 'page created'
            redirect(URL(args=slug))
        return dict(content=form)

    def editmedia(self,slug):
        auth = self.auth
        db = auth.db
        page = db.wiki_page(slug=slug)
        if not (page and self.can_edit(page)): return self.not_authorized(page)
        self.auth.db.wiki_media.id.represent = lambda id,row:\
            SPAN('@////%i/%s.%s' % \
                     (id,IS_SLUG.urlify(row.title.split('.')[0]),
                      row.file.split('.')[-1]))
        self.auth.db.wiki_media.wiki_page.default = page.id
        self.auth.db.wiki_media.wiki_page.writable = False
        content = SQLFORM.grid(
            self.auth.db.wiki_media.wiki_page==page.id,
            orderby = self.auth.db.wiki_media.title,
            args=['_editmedia',slug],
            user_signature=False)
        return dict(content=content)
    def create(self):
        if not self.can_edit(): return self.not_authorized()
        db = self.auth.db
        form = FORM(INPUT(_name='slug',value=current.request.args(1),
                          requires=(IS_SLUG(),
                                    IS_NOT_IN_DB(db,db.wiki_page.slug))),
                    INPUT(_type='submit',
                          _value=current.T('Create Page from Slug')))
        if form.process().accepted:
            redirect(URL(args=('_edit',form.vars.slug)))
        return dict(content=form)
    def pages(self):
        if not self.can_manage(): return self.not_authorized()
        self.auth.db.wiki_page.id.represent = lambda id,row:SPAN('@////%s' % row.slug)
        self.auth.db.wiki_page.title.represent = lambda title,row: \
            A(title,_href=URL(args=row.slug))
        content=SQLFORM.grid(
            self.auth.db.wiki_page,
            links = [
                lambda row: \
                    A('edit',_href=URL(args=('_edit',row.slug))),
                lambda row: \
                    A('media',_href=URL(args=('_editmedia',row.slug)))],
            details=False,editable=False,deletable=False,create=False,
            orderby=self.auth.db.wiki_page.title,
            args=['_pages'],
            user_signature=False)
        return dict(content=content)
    def media(self, id):
        request, db = current.request, self.auth.db
        media = db.wiki_media(id)
        if media:
            if self.manage_permissions:
                page = db.wiki_page(media.wiki_page)
                if not self.can_read(page): return self.not_authorized(page)
            request.args = [media.file]
            return current.response.download(request,db)
        else:
            raise HTTP(404)
    def menu(self,controller='default',function='index'):
        db = self.auth.db
        request = current.request
        menu_page = db.wiki_page(slug='wiki-menu')
        menu = []
        if menu_page:
            tree = {'':menu}
            regex = re.compile('[\r\n\t]*(?P<base>(\s*\-\s*)+)(?P<title>\w.*?)\s+\>\s+(?P<link>\S+)')
            for match in regex.finditer(self.fix_hostname(menu_page.body)):
                base = match.group('base').replace(' ','')
                title = match.group('title')
                link = match.group('link')
                if link.startswith('@'):
                    items = link[2:].split('/')
                    if len(items)>3:
                        link = URL(a=items[0] or None,c=items[1] or None,f=items[2] or None, args=items[3:])
                parent = tree.get(base[1:],tree[''])
                subtree = []
                tree[base] = subtree
                parent.append((current.T(title),False,link,subtree))
        if True:
            submenu = []
            menu.append((current.T('[Wiki]'),None,None,submenu))
            if URL() == URL(controller,function):
                if not str(request.args(0)).startswith('_'):
                    slug = request.args(0) or 'index'
                    mode=1
                elif request.args(0)=='_edit':
                    slug = request.args(1) or 'index'
                    mode=2
                elif request.args(0)=='_editmedia':
                    slug = request.args(1) or 'index'
                    mode=3
                else:
                    mode=0
                if mode in (2,3):
                    submenu.append((current.T('View Page'),None,
                    URL(controller,function,args=slug)))
                if mode in (1,3):
                    submenu.append((current.T('Edit Page'),None,
                    URL(controller,function,args=('_edit',slug))))
                if mode in (1,2):
                    submenu.append((current.T('Edit Page Media'),None,
                    URL(controller,function,args=('_editmedia',slug))))

            submenu.append((current.T('Create New Page'),None,
                            URL(controller,function,args=('_create'))))
        if self.can_manage():
            submenu.append((current.T('Manage Pages'),None,
                            URL(controller,function,args=('_pages'))))
            submenu.append((current.T('Edit Menu'),None,
                            URL(controller,function,args=('_edit','wiki-menu'))))
        # if self.can_search():
            submenu.append((current.T('Search Pages'),None,
                            URL(controller,function,args=('_search'))))
        return menu
    def search(self,tags=None,query=None,cloud=True,preview=True,
               limitby=(0,100),orderby=None):
        if not self.can_search(): return self.not_authorized()
        request = current.request
        content = CAT()
        if tags is None and query is None:
            form = FORM(INPUT(_name='q',requires=IS_NOT_EMPTY(),
                              value=request.vars.q),
                        INPUT(_type="submit",_value=current.T('Search')),
                        _method='GET')
            content.append(DIV(form,_class='w2p_wiki_form'))
            if request.vars.q:
                tags = [v.strip() for v in request.vars.q.split(',')]
                tags = [v for v in tags if v]
        if tags or not query is None:
            db = self.auth.db
            count = db.wiki_tag.wiki_page.count()
            fields = [db.wiki_page.id,db.wiki_page.slug,
                      db.wiki_page.title,db.wiki_page.tags,
                      db.wiki_page.can_read]
            if preview:
                fields.append(db.wiki_page.body)
            if query is None:
                query = (db.wiki_page.id==db.wiki_tag.wiki_page)&\
                    (db.wiki_tag.name.belongs(tags))
                query = query|db.wiki_page.title.startswith(request.vars.q)
            pages = db(query).select(
                *fields,**dict(orderby=orderby or ~count,
                               groupby=db.wiki_page.id,
                               limitby=limitby))
            if request.extension in ('html','load'):
                if not pages:
                    content.append(DIV(current.T("No results"),
                                       _class='w2p_wiki_form'))
                def link(t):
                    return A(t,_href=URL(args='_search',vars=dict(q=t)))
                items = [DIV(H3(A(p.title,_href=URL(args=p.slug))),
                             MARKMIN(self.first_paragraph(p)) \
                                 if preview else '',
                             DIV(_class='w2p_wiki_tags',
                                 *[link(t.strip()) for t in \
                                       p.tags or [] if t.strip()]),
                             _class='w2p_wiki_search_item')
                         for p in pages]
                content.append(DIV(_class='w2p_wiki_pages',*items))
            else:
                cloud=False
                content = [p.as_dict() for p in pages]
        elif cloud:
            content.append(self.cloud()['content'])
        if request.extension=='load':
            return content
        return dict(content=content)
    def cloud(self):
        db = self.auth.db
        count = db.wiki_tag.wiki_page.count(distinct=True)
        ids = db(db.wiki_tag).select(
            db.wiki_tag.name,count,
            groupby=db.wiki_tag.name,
            orderby=~count,limitby=(0,20))
        if ids:
            a,b = ids[0](count), ids[-1](count)
        def scale(c):
            return '%.2f' % (3.0*(c-b)/max(a-b,1)+1)
        items = [A(item.wiki_tag.name,
                   _style='padding:0.2em;font-size:%sem' \
                       % scale(item(count)),
                   _href=URL(args='_search',
                             vars=dict(q=item.wiki_tag.name)))
                 for item in ids]
        return dict(content=DIV(_class='w2p_cloud',*items))

if __name__ == '__main__':
    import doctest
    doctest.testmod()





