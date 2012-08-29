"""
Developed by Massimo Di Pierro
Released under the web2py license (LGPL)

It an interface on top of urllib2 that allows authentication and understand
web2py cookies and web2py forms. An example of usage is at the bottom.
"""

import re
import urllib
import urllib2

class WebClient(object):
    regex = re.compile('\<input name\="_formkey" type\="hidden" value\="(?P<formkey>.+?)" \/\>\<input name\="_formname" type\="hidden" value\="(?P<formname>.+?)" \/\>')

    def __init__(self,app=''):
        self.app = app
        self.cookies = {}
    
    def get(self,url,cookies=None,headers=None,auth=None):
        return self.post(url,data=None,cookies=cookies,headers=headers)
        
    def post(self,url,data=None,cookies=None,headers=None,auth=None):
        self.url = self.app+url
        if cookies is None: cookies = self.cookies
        if auth:
            auth_handler = urllib2.HTTPBasicAuthHandler()
            auth_handler.add_password(**auth)
            opener = urllib2.build_opener(auth_handler)
        else:
            opener = urllib2.build_opener()
        headers_list = []
        for key,value in (headers or {}).iteritems():
            if isinstance(value,(list,tuple)):
                for v in value: headers_list.append((key,v))
            else:
                headers_list.append((key,value))
        for key,value in (cookies or {}).iteritems():
            headers_list.append(('Cookie','%s=%s' % (key,value)))
        for key,value in headers_list:
            opener.addheaders.append((key,str(value)))
        if data is not None:
            # if there is only one form, set _formname automatically
            if not '_formname' in data and len(self.forms)==1:
                data['_formname'] = self.forms.keys()[0]
            # if there is no formkey but it is known, set it
            if '_formname' in data and not '_formkey' in data and \
                    data['_formname'] in self.forms:
                data['_formkey'] = self.forms[data['_formname']]
            data = urllib.urlencode(data)
            self.request = opener.open(self.url,data)
        else:
            self.request = opener.open(self.url)
        self.status = self.request.getcode()
        self.text = self.request.read()        
        self.headers = dict(self.request.headers)
        self.cookies = dict(item[:item.find(';')].split('=') for item in \
                                self.headers.get('set-cookie','').split(','))
        self.forms = {}
        for match in WebClient.regex.finditer(self.text):
            self.forms[match.group('formname')] = match.group('formkey')

def test_web2py_registration_and_login():
    session = WebClient('http://127.0.0.1:8000/welcome/default/')
    session.get('user/register')
    session_id_welcome = session.cookies['session_id_welcome']
    data = dict(first_name = 'Homer',
                last_name = 'Simpson',
                email = 'homer@web2py.com',
                password = 'test',
                password_two = 'test',
                _formname = 'register')
    session.post('user/register',data = data)

    session.get('user/login')
    data = dict(email='homer@web2py.com',
                password='test',
                _formname = 'login')
    session.post('user/login',data = data)
    
    session.get('index')

    # check registration and login were successful
    assert 'Welcome Homer' in session.text

    # check we are always in the same session
    assert session_id_welcome == session.cookies['session_id_welcome']


if __name__ == '__main__':
    test_web2py_registration_and_login()

