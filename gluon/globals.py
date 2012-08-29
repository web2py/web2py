#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Contains the classes for the global used variables:

- Request
- Response
- Session

"""

from storage import Storage, List
from streamer import streamer, stream_file_or_304_or_206, DEFAULT_CHUNK_SIZE
from xmlrpc import handler
from contenttype import contenttype
from html import xmlescape, TABLE, TR, PRE, URL
from http import HTTP, redirect
from fileutils import up
from serializers import json, custom_json
import settings
from utils import web2py_uuid
from settings import global_settings
import hashlib
import portalocker
import cPickle
import cStringIO
import datetime
import re
import Cookie
import os
import sys
import traceback
import threading
import hmac
import base64

try:
    from Crypto.Cipher import AES
except ImportError:
    from contrib import aes as AES

try:
    from gluon.contrib.minify import minify
    have_minify = True
except ImportError:
    have_minify = False

regex_session_id = re.compile('^([\w\-]+/)?[\w\-\.]+$')

__all__ = ['Request', 'Response', 'Session']

current = threading.local()  # thread-local storage for request-scope globals

css_template = '<link href="%s" rel="stylesheet" type="text/css" />'
js_template = '<script src="%s" type="text/javascript"></script>'
coffee_template = '<script src="%s" type="text/coffee"></script>'
less_template = '<link href="%s" rel="stylesheet/less" type="text/css" />'
css_inline = '<style type="text/css">\n%s\n</style>'
js_inline = '<script type="text/javascript">\n%s\n</script>'

class Request(Storage):

    """
    defines the request object and the default values of its members

    - env: environment variables, by gluon.main.wsgibase()
    - cookies
    - get_vars
    - post_vars
    - vars
    - folder
    - application
    - function
    - args
    - extension
    - now: datetime.datetime.today()
    - restful()
    """

    def __init__(self):
        Storage.__init__(self)
        self.wsgi = Storage() # hooks to environ and start_response
        self.env = Storage()
        self.cookies = Cookie.SimpleCookie()
        self.get_vars = Storage()
        self.post_vars = Storage()
        self.vars = Storage()
        self.folder = None
        self.application = None
        self.function = None
        self.args = List()
        self.extension = 'html'
        self.now = datetime.datetime.now()
        self.utcnow = datetime.datetime.utcnow()
        self.is_restful = False
        self.is_https = False
        self.is_local = False
        self.global_settings = settings.global_settings

    def compute_uuid(self):
        self.uuid = '%s/%s.%s.%s' % (
            self.application,
            self.client.replace(':', '_'),
            self.now.strftime('%Y-%m-%d.%H-%M-%S'),
            web2py_uuid())
        return self.uuid

    def user_agent(self):
        from gluon.contrib import user_agent_parser
        session = current.session
        user_agent = session._user_agent = session._user_agent or \
            user_agent_parser.detect(self.env.http_user_agent)
        user_agent = Storage(user_agent)
        for key,value in user_agent.items():
            if isinstance(value,dict):
                user_agent[key] = Storage(value)
        return user_agent

    def requires_https(self):
        """
        If request comes in over HTTP, redirect it to HTTPS
        and secure the session.
        """
        if not global_settings.cronjob and not self.is_https:
            redirect(URL(scheme='https', args=self.args, vars=self.vars))

        current.session.secure()

    def restful(self):
        def wrapper(action,self=self):
            def f(_action=action,_self=self,*a,**b):
                self.is_restful = True
                method = _self.env.request_method
                if len(_self.args) and '.' in _self.args[-1]:
                    _self.args[-1],_self.extension = _self.args[-1].rsplit('.',1)
                    current.response.headers['Content-Type'] = \
                        contenttype(_self.extension.lower())
                if not method in ['GET','POST','DELETE','PUT']:
                    raise HTTP(400,"invalid method")
                rest_action = _action().get(method,None)
                if not rest_action:
                    raise HTTP(400,"method not supported")
                try:
                    return rest_action(*_self.args,**_self.vars)
                except TypeError, e:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    if len(traceback.extract_tb(exc_traceback))==1:
                        raise HTTP(400,"invalid arguments")
                    else:
                        raise e
            f.__doc__ = action.__doc__
            f.__name__ = action.__name__
            return f
        return wrapper


class Response(Storage):

    """
    defines the response object and the default values of its members
    response.write(   ) can be used to write in the output html
    """

    def __init__(self):
        Storage.__init__(self)
        self.status = 200
        self.headers = dict()
        self.headers['X-Powered-By'] = 'web2py'
        self.body = cStringIO.StringIO()
        self.session_id = None
        self.cookies = Cookie.SimpleCookie()
        self.postprocessing = []
        self.flash = ''            # used by the default view layout
        self.meta = Storage()      # used by web2py_ajax.html
        self.menu = []             # used by the default view layout
        self.files = []            # used by web2py_ajax.html
        self.generic_patterns = [] # patterns to allow generic views
        self.delimiters = ('{{','}}')
        self._vars = None
        self._caller = lambda f: f()
        self._view_environment = None
        self._custom_commit = None
        self._custom_rollback = None

    def write(self, data, escape=True):
        if not escape:
            self.body.write(str(data))
        else:
            self.body.write(xmlescape(data))

    def render(self, *a, **b):
        from compileapp import run_view_in
        if len(a) > 2:
            raise SyntaxError, 'Response.render can be called with two arguments, at most'
        elif len(a) == 2:
            (view, self._vars) = (a[0], a[1])
        elif len(a) == 1 and isinstance(a[0], str):
            (view, self._vars) = (a[0], {})
        elif len(a) == 1 and hasattr(a[0], 'read') and callable(a[0].read):
            (view, self._vars) = (a[0], {})
        elif len(a) == 1 and isinstance(a[0], dict):
            (view, self._vars) = (None, a[0])
        else:
            (view, self._vars) = (None, {})
        self._vars.update(b)
        self._view_environment.update(self._vars)
        if view:
            import cStringIO
            (obody, oview) = (self.body, self.view)
            (self.body, self.view) = (cStringIO.StringIO(), view)
            run_view_in(self._view_environment)
            page = self.body.getvalue()
            self.body.close()
            (self.body, self.view) = (obody, oview)
        else:
            run_view_in(self._view_environment)
            page = self.body.getvalue()
        return page

    def include_meta(self):
        s = '\n'.join(
            '<meta name="%s" content="%s" />\n' % (k,xmlescape(v))
            for k,v in (self.meta or {}).iteritems())
        self.write(s,escape=False)

    def include_files(self):


        """
        Caching method for writing out files.
        By default, caches in ram for 5 minutes. To change,
        response.cache_includes = (cache_method, time_expire).
        Example: (cache.disk, 60) # caches to disk for 1 minute.
        """
        from gluon import URL

        files = []
        for item in self.files:
            if not item in files: files.append(item)
        if have_minify and (self.optimize_css or self.optimize_js):
            # cache for 5 minutes by default
            cache = self.cache_includes or (current.cache.ram, 60*5)
            def call_minify():
                return minify.minify(files,
                                     URL('static','temp'),
                                     current.request.folder,
                                     self.optimize_css,
                                     self.optimize_js)
            if cache:
                cache_model, time_expire = cache
                files = cache_model('response.files.minified',
                                    call_minify,
                                    time_expire)
            else:
                files = call_minify()
        s = ''
        for item in files:
            if isinstance(item,str):
                f = item.lower().split('?')[0]
                if f.endswith('.css'):  s += css_template % item
                elif f.endswith('.js'): s += js_template % item
                elif f.endswith('.coffee'): s += coffee_template % item
                elif f.endswith('.less'): s += less_template % item
            elif isinstance(item,(list,tuple)):
                f = item[0]
                if f=='css:inline':     s += css_inline % item[1]
                elif f=='js:inline':    s += js_inline % item[1]
        self.write(s, escape=False)

    def stream(
        self,
        stream,
        chunk_size = DEFAULT_CHUNK_SIZE,
        request=None,
        attachment=False,
        filename=None
        ):
        """
        if a controller function::

            return response.stream(file, 100)

        the file content will be streamed at 100 bytes at the time

        Optional kwargs:
            (for custom stream calls)
            attachment=True # Send as attachment. Usually creates a
                            # pop-up download window on browsers
            filename=None # The name for the attachment

        Note: for using the stream name (filename) with attachments
        the option must be explicitly set as function parameter(will
        default to the last request argument otherwise)
        """

        headers = self.headers
        # for attachment settings and backward compatibility
        keys = [item.lower() for item in headers]
        if attachment:
            if filename is None:
                attname = ""
            else:
                attname = filename
            headers["Content-Disposition"] = \
                "attachment;filename=%s" % attname

        if not request:
            request = current.request
        if isinstance(stream, (str, unicode)):
            stream_file_or_304_or_206(stream,
                                      chunk_size=chunk_size,
                                      request=request,
                                      headers=headers)

        # ## the following is for backward compatibility
        if hasattr(stream, 'name'):
            filename = stream.name

        if filename and not 'content-type' in keys:
            headers['Content-Type'] = contenttype(filename)
        if filename and not 'content-length' in keys:
            try:
                headers['Content-Length'] = \
                    os.path.getsize(filename)
            except OSError:
                pass
        
        env = request.env
        # Internet Explorer < 9.0 will not allow downloads over SSL unless caching is enabled
        if request.is_https and isinstance(env.http_user_agent,str) and \
                not re.search(r'Opera', env.http_user_agent) and \
                re.search(r'MSIE [5-8][^0-9]', env.http_user_agent):
            headers['Pragma'] = 'cache'
            headers['Cache-Control'] = 'private'

        if request and env.web2py_use_wsgi_file_wrapper:
            wrapped = env.wsgi_file_wrapper(stream, chunk_size)
        else:
            wrapped = streamer(stream, chunk_size=chunk_size)
        return wrapped

    def download(self, request, db, chunk_size = DEFAULT_CHUNK_SIZE, attachment=True):
        """
        example of usage in controller::

            def download():
                return response.download(request, db)

        downloads from http://..../download/filename
        """

        if not request.args:
            raise HTTP(404)
        name = request.args[-1]
        items = re.compile('(?P<table>.*?)\.(?P<field>.*?)\..*')\
                           .match(name)
        if not items:
            raise HTTP(404)
        (t, f) = (items.group('table'), items.group('field'))
        field = db[t][f]
        try:
            (filename, stream) = field.retrieve(name)
        except IOError:
            raise HTTP(404)
        headers = self.headers
        headers['Content-Type'] = contenttype(name)
        if attachment:
            headers['Content-Disposition'] = \
                'attachment; filename=%s' % filename
        return self.stream(stream, chunk_size=chunk_size, request=request)
                           

    def json(self, data, default=None):
        return json(data, default = default or custom_json)

    def xmlrpc(self, request, methods):
        """
        assuming::

            def add(a, b):
                return a+b

        if a controller function \"func\"::

            return response.xmlrpc(request, [add])

        the controller will be able to handle xmlrpc requests for
        the add function. Example::

            import xmlrpclib
            connection = xmlrpclib.ServerProxy('http://hostname/app/contr/func')
            print connection.add(3, 4)

        """

        return handler(request, self, methods)

    def toolbar(self):
        from html import DIV, SCRIPT, BEAUTIFY, TAG, URL
        BUTTON = TAG.button
        admin = URL("admin","default","design",
                    args=current.request.application)
        from gluon.dal import thread
        if hasattr(thread,'instances'):
            dbstats = [TABLE(*[TR(PRE(row[0]),'%.2fms' % (row[1]*1000)) \
                                   for row in i.db._timings]) \
                           for i in thread.instances]
            dbtables = dict([(i.uri, {'defined': sorted(list(set(i.db.tables) - 
                                                 set(i.db._LAZY_TABLES.keys()))) or
                                                 '[no defined tables]',
                                      'lazy': sorted(i.db._LAZY_TABLES.keys()) or
                                              '[no lazy tables]'})
                             for i in thread.instances])
        else:
            dbstats = [] # if no db or on GAE
            dbtables = {}
        u = web2py_uuid()
        return DIV(
            BUTTON('design',_onclick="document.location='%s'" % admin),
            BUTTON('request',_onclick="jQuery('#request-%s').slideToggle()"%u),
            DIV(BEAUTIFY(current.request),_class="hidden",_id="request-%s"%u),
            BUTTON('session',_onclick="jQuery('#session-%s').slideToggle()"%u),
            DIV(BEAUTIFY(current.session),_class="hidden",_id="session-%s"%u),
            BUTTON('response',_onclick="jQuery('#response-%s').slideToggle()"%u),
            DIV(BEAUTIFY(current.response),_class="hidden",_id="response-%s"%u),
            BUTTON('db tables',_onclick="jQuery('#db-tables-%s').slideToggle()"%u),
            DIV(BEAUTIFY(dbtables),_class="hidden",_id="db-tables-%s"%u),
            BUTTON('db stats',_onclick="jQuery('#db-stats-%s').slideToggle()"%u),
            DIV(BEAUTIFY(dbstats),_class="hidden",_id="db-stats-%s"%u),
            SCRIPT("jQuery('.hidden').hide()")
            )

class Session(Storage):

    """
    defines the session object and the default values of its members (None)
    """

    def connect(
        self,
        request,
        response,
        db=None,
        tablename='web2py_session',
        masterapp=None,
        migrate=True,
        separate = None,
        check_client=False,
        cookie_key=None,
        ):
        """
        separate can be separate=lambda(session_name): session_name[-2:]
        and it is used to determine a session prefix.
        separate can be True and it is set to session_name[-2:]
        """
        if separate == True:
            separate = lambda session_name: session_name[-2:]
        self._unlock(response)
        if not masterapp:
            masterapp = request.application
        response.session_id_name = 'session_id_%s' % masterapp.lower()

        # Load session data from cookie
        cookies = request.cookies
            
        if cookie_key:
            response.session_cookie_key = cookie_key
            response.session_cookie_key2 = hashlib.md5(cookie_key).digest()
            cookie_name = masterapp.lower()+'_session_data'
            response.session_cookie_name = cookie_name
            if cookie_name in cookies:
                cookie_value = cookies[cookie_name].value
                cookie_parts = cookie_value.split(":")
                enc = cookie_parts[2]
                cipher = AES.new(cookie_key)
                decrypted = cipher.decrypt(base64.b64decode(enc)).rstrip('{')
                check = hmac.new(response.session_cookie_key2,enc).hexdigest()
                if cookie_parts[0] == check:
                    session_data = cPickle.loads(decrypted)
                    self.update(session_data)
            else:
                return

        if not db:
            if global_settings.db_sessions is True \
                    or masterapp in global_settings.db_sessions:
                return
            response.session_new = False
            client = request.client and request.client.replace(':', '.')
            if response.session_id_name in cookies:
                response.session_id = \
                    cookies[response.session_id_name].value
                if regex_session_id.match(response.session_id):
                    response.session_filename = \
                        os.path.join(up(request.folder), masterapp,
                            'sessions', response.session_id)
                else:
                    response.session_id = None
            if response.session_id:
                try:
                    response.session_file = \
                        open(response.session_filename, 'rb+')
                    try:
                        portalocker.lock(response.session_file,
                                         portalocker.LOCK_EX)
                        response.session_locked = True
                        self.update(cPickle.load(response.session_file))
                        response.session_file.seek(0)
                        oc = response.session_filename.split('/')[-1]\
                            .split('-')[0]
                        if check_client and client!=oc:
                            raise Exception, "cookie attack"
                    finally:
                        pass
                        #This causes admin login to break. Must find out why.
                        #self._close(response)
                except:
                    response.session_id = None
            if not response.session_id:
                uuid = web2py_uuid()
                response.session_id = '%s-%s' % (client, uuid)
                if separate:
                    prefix = separate(response.session_id)
                    response.session_id = '%s/%s' % \
                        (prefix,response.session_id)
                response.session_filename = \
                    os.path.join(up(request.folder), masterapp,
                                 'sessions', response.session_id)
                response.session_new = True
        else:
            if global_settings.db_sessions is not True:
                global_settings.db_sessions.add(masterapp)
            response.session_db = True
            if response.session_file:
                self._close(response)
            if settings.global_settings.web2py_runtime_gae:
                # in principle this could work without GAE
                request.tickets_db = db
            if masterapp == request.application:
                table_migrate = migrate
            else:
                table_migrate = False
            tname = tablename + '_' + masterapp
            table = db.get(tname, None)
            Field = db.Field
            if table is None:
                db.define_table(
                    tname,
                    Field('locked', 'boolean', default=False),
                    Field('client_ip', length=64),
                    Field('created_datetime', 'datetime',
                             default=request.now),
                    Field('modified_datetime', 'datetime'),
                    Field('unique_key', length=64),
                    Field('session_data', 'blob'),
                    migrate=table_migrate,
                    )
                table = db[tname] # to allow for lazy table
            try:

                # Get session data out of the database
                # Key comes from the cookie
                key = cookies[response.session_id_name].value
                (record_id, unique_key) = key.split(':')
                if record_id == '0':
                    raise Exception, 'record_id == 0'
                        # Select from database
                rows = db(table.id == record_id).select()
                # Make sure the session data exists in the database
                if len(rows) == 0 or rows[0].unique_key != unique_key:
                    raise Exception, 'No record'
                # rows[0].update_record(locked=True)
                # Unpickle the data
                session_data = cPickle.loads(rows[0].session_data)
                self.update(session_data)
            except Exception:
                record_id = None
                unique_key = web2py_uuid()
                session_data = {}
            response._dbtable_and_field = \
                (response.session_id_name, table, record_id, unique_key)
            response.session_id = '%s:%s' % (record_id, unique_key)
        rcookies = response.cookies
        rcookies[response.session_id_name] = response.session_id
        rcookies[response.session_id_name]['path'] = '/'
        self.__hash = hashlib.md5(str(self)).digest()
        if self.flash:
            (response.flash, self.flash) = (self.flash, None)

    def is_new(self):
        if self._start_timestamp:
            return False
        else:
            self._start_timestamp = datetime.datetime.today()
            return True

    def is_expired(self, seconds = 3600):
        now = datetime.datetime.today()
        if not self._last_timestamp or \
                self._last_timestamp + datetime.timedelta(seconds = seconds) > now:
            self._last_timestamp = now
            return False
        else:
            return True

    def secure(self):
        self._secure = True

    def forget(self, response=None):
        self._close(response)
        self._forget = True

    def _try_store_in_cookie(self, request, response):
        pad = lambda s: s + (32 - len(s) % 32) * '{'
        data = cPickle.dumps(dict(self))
        cipher = AES.new(response.session_cookie_key)
        encrypted_data = base64.b64encode(cipher.encrypt(pad(data)))
        signature = hmac.new(response.session_cookie_key2,encrypted_data)\
            .hexdigest()
        value = signature+':'+encrypted_data
        response.cookies[response.session_cookie_name] = value
        response.cookies[response.session_cookie_name]['path'] = '/'

    def _try_store_in_db(self, request, response):
        # don't save if file-based sessions, no session id, or session being forgotten
        if not response.session_db or not response.session_id or self._forget:
            return

        # don't save if no change to session
        __hash = self.__hash
        if __hash is not None:
            del self.__hash
            if __hash == hashlib.md5(str(self)).digest():
                return

        (record_id_name, table, record_id, unique_key) = \
            response._dbtable_and_field
        dd = dict(locked=False, client_ip=request.client.replace(':','.'),
                  modified_datetime=request.now,
                  session_data=cPickle.dumps(dict(self)),
                  unique_key=unique_key)
        if record_id:
            table._db(table.id == record_id).update(**dd)
        else:
            record_id = table.insert(**dd)
        response.cookies[response.session_id_name] = '%s:%s'\
             % (record_id, unique_key)
        response.cookies[response.session_id_name]['path'] = '/'

    def _try_store_on_disk(self, request, response):

        # don't save if sessions not not file-based
        if response.session_db:
            return

        # don't save if no change to session
        __hash = self.__hash
        if __hash is not None:
            del self.__hash
            if __hash == hashlib.md5(str(self)).digest():
                self._close(response)
                return

        if not response.session_id or self._forget:
            self._close(response)
            return

        if response.session_new:
            # Tests if the session sub-folder exists, if not, create it
            session_folder = os.path.dirname(response.session_filename)
            if not os.path.exists(session_folder):
                os.mkdir(session_folder)
            response.session_file = open(response.session_filename, 'wb')
            portalocker.lock(response.session_file, portalocker.LOCK_EX)
            response.session_locked = True

        if response.session_file:
            cPickle.dump(dict(self), response.session_file)
            response.session_file.truncate()
            self._close(response)

    def _unlock(self, response):
        if response and response.session_file and response.session_locked:
            try:
                portalocker.unlock(response.session_file)
                response.session_locked = False
            except: ### this should never happen but happens in Windows
                pass

    def _close(self, response):
        if response and response.session_file:
            self._unlock(response)
            try:
                response.session_file.close()
                del response.session_file
            except:
                pass





