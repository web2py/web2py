#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""

__all__ = ['HTTP', 'redirect']

defined_status = {
    200: 'OK',
    201: 'CREATED',
    202: 'ACCEPTED',
    203: 'NON-AUTHORITATIVE INFORMATION',
    204: 'NO CONTENT',
    205: 'RESET CONTENT',
    206: 'PARTIAL CONTENT',
    301: 'MOVED PERMANENTLY',
    302: 'FOUND',
    303: 'SEE OTHER',
    304: 'NOT MODIFIED',
    305: 'USE PROXY',
    307: 'TEMPORARY REDIRECT',
    400: 'BAD REQUEST',
    401: 'UNAUTHORIZED',
    403: 'FORBIDDEN',
    404: 'NOT FOUND',
    405: 'METHOD NOT ALLOWED',
    406: 'NOT ACCEPTABLE',
    407: 'PROXY AUTHENTICATION REQUIRED',
    408: 'REQUEST TIMEOUT',
    409: 'CONFLICT',
    410: 'GONE',
    411: 'LENGTH REQUIRED',
    412: 'PRECONDITION FAILED',
    413: 'REQUEST ENTITY TOO LARGE',
    414: 'REQUEST-URI TOO LONG',
    415: 'UNSUPPORTED MEDIA TYPE',
    416: 'REQUESTED RANGE NOT SATISFIABLE',
    417: 'EXPECTATION FAILED',
    500: 'INTERNAL SERVER ERROR',
    501: 'NOT IMPLEMENTED',
    502: 'BAD GATEWAY',
    503: 'SERVICE UNAVAILABLE',
    504: 'GATEWAY TIMEOUT',
    505: 'HTTP VERSION NOT SUPPORTED',
    }

# If web2py is executed with python2.4 we need
# to use Exception instead of BaseException

try:
    BaseException
except NameError:
    BaseException = Exception


class HTTP(BaseException):

    def __init__(
        self,
        status,
        body='',
        cookies=None,
        **headers
        ):
        self.status = status
        self.body = body
        self.headers = headers
        self.cookies2headers(cookies)

    def cookies2headers(self,cookies):
        if cookies and len(cookies)>0:
            self.headers['Set-Cookie'] = [
                str(cookie)[11:] for cookie in cookies.values()]

    def to(self, responder, env=None):
        env = env or {}
        status = self.status
        headers = self.headers
        if status in defined_status:
            status = '%d %s' % (status, defined_status[status])
        else:
            status = str(status) + ' '
        if not 'Content-Type' in headers:
            headers['Content-Type'] = 'text/html; charset=UTF-8'
        body = self.body
        if status[:1] == '4':
            if not body:
                body = status
            if isinstance(body, str):
                if len(body)<512 and headers['Content-Type'].startswith('text/html'):
                    body += '<!-- %s //-->' % ('x'*512) ### trick IE
                headers['Content-Length'] = len(body)
        rheaders = []
        for k, v in headers.iteritems():
            if isinstance(v, list):
                rheaders += [(k, str(item)) for item in v]
            else:
                rheaders.append((k, str(v)))
        responder(status, rheaders)
        if env.get('request_method','')=='HEAD':
            return ['']
        elif isinstance(body,str):
            return [body]
        elif hasattr(body, '__iter__'):
            return body
        else:
            return [str(body)]

    @property
    def message(self):
        """
        compose a message describing this exception

            "status defined_status [web2py_error]"

        message elements that are not defined are omitted
        """
        msg = '%(status)d'
        if self.status in defined_status:
            msg = '%(status)d %(defined_status)s'
        if 'web2py_error' in self.headers:
            msg += ' [%(web2py_error)s]'
        return msg % dict(status=self.status,
                          defined_status=defined_status.get(self.status),
                          web2py_error=self.headers.get('web2py_error'))

    def __str__(self):
        "stringify me"
        return self.message


def redirect(location, how=303, client_side=False):
    if location:
        from gluon import current
        loc = location.replace('\r', '%0D').replace('\n', '%0A')
        if client_side and current.request.ajax:
            raise HTTP(200, **{'web2py-redirect-location': loc})
        else:
            raise HTTP(how,
                       'You are being redirected <a href="%s">here</a>' % loc,
                       Location=loc)







