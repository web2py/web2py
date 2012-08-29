"""
Developed by Massimo Di Pierro
Released under the web2py license (LGPL)

It an interface on top of urllib2 that allows authentication and understand
web2py cookies and web2py forms. An example of usage is at the bottom.
"""

import re
import time
import urllib
import urllib2


class WebClient(object):
    regex = re.compile('\<input name\="_formkey" type\="hidden" value\="(?P<formkey>.+?)" \/\>\<input name\="_formname" type\="hidden" value\="(?P<formname>.+?)" \/\>')

    def __init__(self,app='', postbacks=True):
        self.postbacks = postbacks
        self.history = []
        self.app = app
        self.cookies = {}
    
    def get(self,url,cookies=None,headers=None,auth=None):
        return self.post(url,data=None,cookies=cookies,headers=headers)
        
    def post(self,url,data=None,cookies=None,headers=None,auth=None):
        self.url = self.app+url
        if data and '_formname' in data and self.postbacks and \
                self.history and self.history[-1][1]!=self.url:        
            # to bypass the web2py CSRF need to get formkey
            # before submitting the form
            self.get(url,cookies=None,headers=None,auth=None)
        if cookies is None: cookies = self.cookies
        if auth:
            auth_handler = urllib2.HTTPBasicAuthHandler()
            auth_handler.add_password(**auth)
            opener = urllib2.build_opener(auth_handler)
        else:
            opener = urllib2.build_opener()
        # copy headers from dict to list of key,value
        headers_list = []
        for key,value in (headers or {}).iteritems():
            if isinstance(value,(list,tuple)):
                for v in value: headers_list.append((key,v))
            else:
                headers_list.append((key,value))
        # move cookies to headers
        for key,value in (cookies or {}).iteritems():
            headers_list.append(('Cookie','%s=%s' % (key,value)))
        # add headers to request
        for key,value in headers_list:
            opener.addheaders.append((key,str(value)))
        if data is not None:
            self.method = 'POST'
            # if there is only one form, set _formname automatically
            if not '_formname' in data and len(self.forms)==1:
                data['_formname'] = self.forms.keys()[0]
            # if there is no formkey but it is known, set it
            if '_formname' in data and not '_formkey' in data and \
                    data['_formname'] in self.forms:
                data['_formkey'] = self.forms[data['_formname']]
            data = urllib.urlencode(data)
            t0 = time.time()
            self.request = opener.open(self.url,data)
            self.time = time.time()-t0
        else:
            self.method = 'GET'
            t0 = time.time()
            self.request = opener.open(self.url)
            self.time = time.time()-t0
        self.status = self.request.getcode()
        self.text = self.request.read()        
        self.headers = dict(self.request.headers)
        # parse headers into cookies
        self.cookies = dict(item[:item.find(';')].split('=') for item in \
                                self.headers.get('set-cookie','').split(','))
        self.forms = {}
        # find all forms and formkeys
        for match in WebClient.regex.finditer(self.text):
            self.forms[match.group('formname')] = match.group('formkey')
        # log this request
        self.history.append((self.method,self.url,self.status,self.time))

def test_web2py_registration_and_login():
    client = WebClient('http://127.0.0.1:8000/welcome/default/')
    client.get('index')
    session_id_welcome = client.cookies['session_id_welcome']

    data = dict(first_name = 'Homer',
                last_name = 'Simpson',
                email = 'homer@web2py.com',
                password = 'test',
                password_two = 'test',
                _formname = 'register')
    client.post('user/register',data = data)

    data = dict(email='homer@web2py.com',
                password='test',
                _formname = 'login')
    client.post('user/login',data = data)
    
    client.get('index')

    # check registration and login were successful
    assert 'Welcome Homer' in client.text

    # check we are always in the same session
    assert session_id_welcome == client.cookies['session_id_welcome']

    for method, url, status, t in client.history:
        print method, url, status, t

if __name__ == '__main__':
    test_web2py_registration_and_login()

