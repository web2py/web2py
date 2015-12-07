# -*- coding: utf-8 -*-
import datetime
import uuid
import time
from gluon.serializers import json_parser
import base64
import hmac
import hashlib
from gluon.storage import Storage
from gluon.utils import web2py_uuid
from gluon import current
from gluon.http import HTTP


class Web2pyJwt(object):

    """
    If left externally, this needs the usual "singleton" approach.
    Given I (we) don't know if to include in auth yet, let's stick to basics.

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
                             authorization takes place. You can raise with HTTP a proper error message
                             Example:
                             def mybefore_authorization(tokend):
                                 if not tokend['my_name_is'] == 'bond,james bond':
                                     raise HTTP(400, u'Invalid JWT my_name_is claim')
     - max_header_length: check max length to avoid load()ing unusually large tokens (could mean crafted, e.g. in a DDoS.)

    Basic Usage:
    in models (or the controller needing it)

        myjwt = Web2pyJwt('secret', auth)

    in the controller issuing tokens

        def login_and_take_token():
            return myjwt.jwt_token_manager()

    A call then to /app/controller/login_and_take_token/auth with username and password returns the token
    A call to /app/controller/login_and_take_token/refresh with the original token returns the refreshed token

    To protect a function with JWT

        @myjwt.requires_jwt()
        @auth.requires_login()
        def protected():
            return '%s$%s' % (request.now, auth.user_id)

    """

    def __init__(self, secret_key,
                 auth,
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
                 max_header_length=4*1024,
                 ):
        self.secret_key = secret_key
        self.auth = auth
        self.algorithm = algorithm
        if self.algorithm not in ('HS256', 'HS384', 'HS512'):
            raise NotImplementedError('Algoritm %s not allowed' % algorithm)
        self.verify_expiration = verify_expiration
        self.leeway = leeway
        self.expiration = expiration
        self.allow_refresh = allow_refresh
        self.refresh_expiration_delta = refresh_expiration_delta
        self.header_prefix = header_prefix
        self.jwt_add_header = jwt_add_header or {}
        base_header = {'alg': self.algorithm, 'typ': 'JWT'}
        for k, v in self.jwt_add_header.iteritems():
            base_header[k] = v
        self.cached_b64h = self.jwt_b64e(json_parser.dumps(base_header))
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
        print 'initialized'

    @staticmethod
    def jwt_b64e(string):
        if isinstance(string, unicode):
            string = string.encode('uft-8', 'strict')
        return base64.urlsafe_b64encode(string).strip(b'=')

    @staticmethod
    def jwt_b64d(string):
        """base64 decodes a single bytestring (and is tolerant to getting
        called with a unicode string).
        The result is also a bytestring.
        """
        if isinstance(string, unicode):
            string = string.encode('ascii', 'ignore')
        return base64.urlsafe_b64decode(string + '=' * (-len(string) % 4))

    def generate_token(self, payload):
        secret = self.secret_key
        if self.salt:
            if callable(self.salt):
                secret = "%s$%s" % (secret, self.salt(payload))
            else:
                secret = "%s$%s" % (secret, self.salt)
            if isinstance(secret, unicode):
                secret = secret.encode('ascii', 'ignore')
        b64h = self.cached_b64h
        b64p = self.jwt_b64e(json_parser.dumps(payload))
        jbody = b64h + '.' + b64p
        mauth = hmac.new(key=secret, msg=jbody, digestmod=self.digestmod)
        jsign = self.jwt_b64e(mauth.digest())
        return jbody + '.' + jsign

    def verify_signature(self, body, signature, secret):
        mauth = hmac.new(key=secret, msg=body, digestmod=self.digestmod)
        return hmac.compare_digest(self.jwt_b64e(mauth.digest()), signature)

    def load_token(self, token):
        if isinstance(token, unicode):
            token = token.encode('utf-8', 'strict')
        body, sig = token.rsplit('.', 1)
        b64h, b64b = body.split('.', 1)
        if b64h != self.cached_b64h:
            # header not the same
            raise HTTP(400, u'Invalid JWT Header')
        secret = self.secret_key
        tokend = json_parser.loads(self.jwt_b64d(b64b))
        if self.salt:
            if callable(self.salt):
                secret = "%s$%s" % (secret, self.salt(tokend))
            else:
                secret = "%s$%s" % (secret, self.salt)
            if isinstance(secret, unicode):
                secret = secret.encode('ascii', 'ignore')
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
        expires = now + self.refresh_expiration_delta
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

    def jwt_token_manager(self):
        """
        The part that issues (and refreshes) tokens.
        Used in a controller, given myjwt is the istantiated class, as

            def api_auth():
                return myjwt.jwt_token_manager()

        Then, a call to /app/c/api_auth/auth with username and password
        returns a token, while /app/c/api_auth/refresh with the current token
        issues another token
        """
        request = current.request
        # forget and unlock response
        if request.args(0) == 'auth':
            current.session.forget(current.response)
            username = request.vars[self.user_param]
            password = request.vars[self.pass_param]
            valid_user = self.auth.login_bare(username, password)
            if valid_user:
                payload = self.serialize_auth_session(current.session.auth)
                self.alter_payload(payload)
                return self.generate_token(payload)
            else:
                raise HTTP(
                    401, u'Not Authorized',
                    **{'WWW-Authenticate': u'JWT realm="%s"' % self.realm})
        elif request.args(0) == 'refresh':
            if not self.allow_refresh:
                raise HTTP(403, u'Refreshing token is not allowed')
            token = request.vars.token
            tokend = self.load_token(token)
            # verification can fail here
            refreshed = self.refresh_token(tokend)
            return self.generate_token(refreshed)

    def inject_token(self, tokend):
        """
        The real deal, not touching the db but still logging-in the user
        """
        self.auth.user = Storage(tokend['user'])
        self.auth.user_groups = tokend['user_groups']
        self.auth.hmac_key = tokend['hmac_key']

    def requires_jwt(self, otherwise=None):
        """
        The validator that checks for the header or the
        _token var
        """
        request = current.request
        token_in_header = request.env.http_authorization
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
            token = request.vars._token
        if token and len(token) < self.max_header_length:
            tokend = self.load_token(token)
            self.inject_token(tokend)
        return self.auth.requires(True, otherwise=otherwise)
