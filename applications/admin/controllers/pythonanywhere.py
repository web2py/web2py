# -*- coding: utf-8 -*-
import base64
import os
import re
import gzip
import tarfile
import io
from urllib.parse import urlencode
from urllib import request as urllib2
from xmlrpc.client import ProtocolError
from gluon.contrib.simplejsonrpc import ServerProxy
from gluon.admin import apath, check_app_path


APPNAME = re.compile(r'^\w+$')


def list_authorized_apps():
    local = sorted(f for f in os.listdir(apath(r=request)) if APPNAME.match(f))
    if not MULTI_USER_MODE or is_manager():
        return local
    owned = db(db.app.owner == auth.user.id).select(db.app.name)
    owned = set(row.name for row in owned)
    return [app for app in local if app in owned]


def authorized_app_path(app):
    if not APPNAME.match(app or ''):
        raise HTTP(403)
    if (MULTI_USER_MODE and not is_manager() and
            not db(db.app.name == app)(db.app.owner == auth.user.id).count()):
        raise HTTP(403)
    folder = check_app_path(request, app, apath(app, r=request))
    if not os.path.isdir(folder):
        raise HTTP(404)
    return folder


def deploy():
    response.title = T('Deploy to pythonanywhere')
    return {}


def create_account():
    """ Create a PythonAnywhere account """
    if not request.vars:
        raise HTTP(400)

    if request.vars.username and request.vars.web2py_admin_password:
        # Check if web2py is already there otherwise we get an error 500 too.
        client = ServerProxy('https://%(username)s:%(web2py_admin_password)s@%(username)s.pythonanywhere.com/admin/webservices/call/jsonrpc' % request.vars)
        try:
            if client.login() is True:
                return response.json({'status': 'ok'})
        except ProtocolError as error:
            pass

    url = 'https://www.pythonanywhere.com/api/web2py/create_account'
    data = urlencode(request.vars)
    req = urllib2.Request(url, data)

    try:
        reply = urllib2.urlopen(req)
    except urllib2.HTTPError as error:
        if error.code == 400:
            reply = error
        elif error.code == 500:
            return response.json({'status':'error', 'errors':{'username': ['An App other than web2py is installed in the domain %(username)s.pythonanywhere.com' % request.vars]}})
        else:
            raise
    response.headers['Content-Type'] = 'application/json'
    return reply.read()


def list_apps():
    """ Get a list of apps both remote and local """
    if not request.vars.username or not request.vars.password:
        raise HTTP(400)
    client = ServerProxy('https://%(username)s:%(password)s@%(username)s.pythonanywhere.com/admin/webservices/call/jsonrpc' % request.vars)
    local = list_authorized_apps()
    try:
        pythonanywhere = client.list_apps()
    except ProtocolError as error:
        raise HTTP(error.errcode)
    return response.json({'local': local, 'pythonanywhere': pythonanywhere})


def bulk_install():
    """ Install a list of apps """

    def b64pack(app):
        """
        Given an app's name, return the base64 representation of its packed version.
        """
        folder = authorized_app_path(app)
        tmpfile = io.StringIO()
        tar = tarfile.TarFile(fileobj=tmpfile, mode='w')
        try:
            filenames = listdir(folder, r'^[\w\.\-]+$', add_dirs=True,
                                exclude_content_from=['cache', 'sessions', 'errors'])
            for fname in filenames:
                tar.add(os.path.join(folder, fname), fname, False)
        finally:
            tar.close()
        tmpfile.seek(0)
        gzfile = io.StringIO()
        w2pfp = gzip.GzipFile(fileobj=gzfile, mode='wb')
        w2pfp.write(tmpfile.read())
        w2pfp.close()
        gzfile.seek(0)
        return base64.b64encode(gzfile.read())

    request.vars.apps = request.vars['apps[]']
    if not request.vars.apps or not request.vars.username or not request.vars.password:
        raise HTTP(400)
    if not isinstance(request.vars.apps, list):
        request.vars.apps = [request.vars.apps]  # Only one app selected

    client = ServerProxy('https://%(username)s:%(password)s@%(username)s.pythonanywhere.com/admin/webservices/call/jsonrpc' % request.vars)

    for app in request.vars.apps:
        try:
            client.install(app, app+'.w2p', b64pack(app))
        except ProtocolError as error:
            raise HTTP(error.errcode)

    return response.json({'status': 'ok'})
