#!/usr/bin/env python
# coding: utf8

"""
   Dropbox Authentication for web2py
   Developed by Massimo Di Pierro (2012)
   Same License as Web2py License
"""

# mind here session is dropbox session, not current.session

import os
import re
import urllib
from dropbox import client, rest, session
from gluon import *
from gluon.tools import fetch
from gluon.storage import Storage
import gluon.contrib.simplejson as json

class DropboxAccount(object):

    """
    from gluon.contrib.login_methods.dropbox_account import DropboxAccount
    auth.settings.actions_disabled=['register','change_password','request_reset_password']
    auth.settings.login_form = DropboxAccount(request,
              key="...",
              secret="...",
              access_type="...",
              url = "http://localhost:8000/%s/default/user/login" % request.application)
    when logged in
    client = auth.settings.login_form.client
    """

    def __init__(self,
                 request,
                 key = "",
                 secret = "",
                 access_type="app_folder",
                 login_url = "",
                 on_login_failure=None,
                 ):

        self.request=request
        self.key=key
        self.secret=secret
        self.access_type=access_type
        self.login_url = login_url
        self.on_login_failure = on_login_failure
        self.sess = session.DropboxSession(
            self.key,self.secret,self.access_type)


    def get_user(self):
        request = self.request
        token = current.session.dropbox_token
        try:
            access_token = self.sess.obtain_access_token(token)
        except:
            access_token = None
        if access_token:
            user = Storage()
            self.client = client.DropboxClient(self.sess)
            data = self.client.account_info()
            display_name = data.get('display_name','').split(' ',1)
            user = dict(email = data.get('email',None),
                        first_name = display_name[0],
                        last_name = display_name[-1],
                        registration_id = data.get('uid',None))
            if not user['registration_id'] and self.on_login_failure:
                redirect(self.on_login_failure)
            return user
        return None

    def login_form(self):
        token = self.sess.obtain_request_token()
        current.session.dropbox_token = token
        dropbox_url = self.sess.build_authorize_url(token,self.login_url)
        redirect(dropbox_url)
        form = IFRAME(_src=dropbox_url,
                      _scrolling="no",
                      _frameborder="no",
                      _style="width:400px;height:240px;")
        return form
    def logout_url(self, next = "/"):
        current.session.dropbox_token=None
        current.session.auth=None
        redirect('https://www.dropbox.com/logout')
        return next
    def put(self,filename,file):
        return json.loads(self.client.put_file(filename,file))['bytes']
    def get(self,filename,file):
        return self.client.get_file(filename)
    def dir(self,path):
        return json.loads(self.client.metadata(path))

def use_dropbox(auth,filename='private/dropbox.key',**kwargs):
    path = os.path.join(current.request.folder,filename)
    if os.path.exists(path):
        request = current.request
        key,secret,access_type = open(path,'r').read().strip().split(':')
        host = current.request.env.http_host
        login_url = "http://%s/%s/default/user/login" % \
            (host,request.application)
        auth.settings.actions_disabled = \
            ['register','change_password','request_reset_password']
        auth.settings.login_form = DropboxAccount(
            request,key=key,secret=secret,access_type=access_type,
            login_url = login_url,**kwargs)

