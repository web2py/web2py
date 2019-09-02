# -*- coding: utf-8 -*-

"""Unit tests for rewrite.py regex routing option"""

import os
import tempfile
import unittest
import shutil

from gluon.rewrite import load, filter_url, filter_err, regex_filter_out
from gluon.html import URL
from gluon.settings import global_settings
from gluon.http import HTTP
from gluon.storage import Storage
from gluon._compat import to_bytes


old_root = root = None

def setUpModule():
    def make_apptree(root):
        "build a temporary applications tree"
        # applications/
        os.mkdir(os.path.join(root, 'applications'))
        # applications/app/
        for app in ('admin', 'examples', 'welcome'):
            os.mkdir(os.path.join(root, 'applications', app))
            #  applications/app/(controllers, static)
            for subdir in ('controllers', 'static'):
                os.mkdir(os.path.join(root, 'applications', app, subdir))
        # applications/admin/controllers/*.py
        base = os.path.join(root, 'applications', 'admin', 'controllers')
        for ctr in ('appadmin', 'default', 'gae', 'mercurial', 'shell', 'wizard'):
            open(os.path.join(base, '%s.py' % ctr), 'w').close()
        # applications/examples/controllers/*.py
        base = os.path.join(root, 'applications', 'examples', 'controllers')
        for ctr in ('ajax_examples', 'appadmin', 'default', 'global', 'spreadsheet'):
            open(os.path.join(base, '%s.py' % ctr), 'w').close()
        # applications/welcome/controllers/*.py
        base = os.path.join(root, 'applications', 'welcome', 'controllers')
        for ctr in ('appadmin', 'default'):
            open(os.path.join(base, '%s.py' % ctr), 'w').close()
        # create an app-specific routes.py for examples app
        routes = os.path.join(root, 'applications', 'examples', 'routes.py')
        with open(routes, 'w') as r:
            r.write("default_function='exdef'\n")

    global old_root, root
    if old_root is None:  # do this only once
        old_root = global_settings.applications_parent
        root = global_settings.applications_parent = tempfile.mkdtemp()
        make_apptree(root)


def tearDownModule():
    if old_root is not None:
        global_settings.applications_parent = old_root
        shutil.rmtree(root)


def norm_root(root):
    return root.replace('/', os.sep)


class TestRoutes(unittest.TestCase):
    """ Tests the regex routing logic from gluon.rewrite """

    def test_routes_null(self):
        """ Tests a null routes table """
        load(data='')
        # incoming
        self.assertEqual(
            filter_url('http://domain.com'), '/init/default/index')
        self.assertEqual(
            filter_url('http://domain.com/'), '/init/default/index')
        self.assertEqual(
            filter_url('http://domain.com/abc'), '/abc/default/index')
        self.assertEqual(
            filter_url('http://domain.com/abc/'), '/abc/default/index')
        self.assertEqual(
            filter_url('http://domain.com/abc/def'), "/abc/def/index")
        self.assertEqual(
            filter_url('http://domain.com/abc/def/'), "/abc/def/index")
        self.assertEqual(
            filter_url('http://domain.com/abc/def/ghi'), "/abc/def/ghi")
        self.assertEqual(
            filter_url('http://domain.com/abc/def/ghi/'), "/abc/def/ghi")
        self.assertEqual(filter_url(
            'http://domain.com/abc/def/ghi/jkl'), "/abc/def/ghi ['jkl']")
        self.assertEqual(filter_url(
            'http://domain.com/abc/def/ghi/j%20kl'), "/abc/def/ghi ['j_kl']")
        self.assertEqual(filter_url('http://domain.com/welcome/static/path/to/static'),
            norm_root("%s/applications/welcome/static/path/to/static" % root))
        # no more necessary since explcit check for directory traversal attacks
        """
        self.assertRaises(HTTP, filter_url, 'http://domain.com/welcome/static/bad/path/to/st~tic')
        try:
            # 2.7+ only
            self.assertRaisesRegexp(HTTP, "400.*BAD REQUEST \[invalid path\]", filter_url, 'http://domain.com/welcome/static/bad/path/to/st~tic')
        except AttributeError:
            pass
        """
        # outgoing
        self.assertEqual(filter_url('http://domain.com/init/default/index',
                         out=True), '/init/default/index')
        self.assertEqual(filter_url('http://domain.com/init/default/index/arg1', out=True), '/init/default/index/arg1')
        self.assertEqual(filter_url('http://domain.com/init/default/abc',
                         out=True), '/init/default/abc')

    def test_routes_query(self):
        """ Test query appending """
        data = r'''
routes_in = (
 ('/service/$model/create', '/app/default/call/json/create?model=$model'),
)
'''
        load(data=data)
        self.assertEqual(filter_url('http://localhost:8000/service/person/create'), "/app/default/call ['json', 'create'] ?model=person")
        self.assertEqual(filter_url('http://localhost:8000/service/person/create?var1=val1'), "/app/default/call ['json', 'create'] ?model=person&var1=val1")

    def test_routes_specific(self):
        """
        Test app-specific routes.py

        Note that make_apptree above created applications/examples/routes.py with a default_function.
        """
        data = r'''
routes_app = [
    (r'/(?P<app>welcome|admin|examples)\b.*', r'\g<app>'),
    (r'$anything', r'welcome'),
    (r'/?$anything', r'welcome'),
]
'''
        load(data=data)
        self.assertEqual(
            filter_url('http://domain.com/welcome'), '/welcome/default/index')
        self.assertEqual(filter_url(
            'http://domain.com/examples'), '/examples/default/exdef')

    def test_routes_defapp(self):
        """ Test the default-application function """
        data = r'''
default_application = 'defapp'
'''
        load(data=data)
        # incoming
        self.assertEqual(
            filter_url('http://domain.com'), '/defapp/default/index')
        self.assertEqual(
            filter_url('http://domain.com/'), '/defapp/default/index')
        self.assertEqual(
            filter_url('http://domain.com/welcome'), '/welcome/default/index')
        self.assertEqual(
            filter_url('http://domain.com/app'), '/app/default/index')
        self.assertEqual(filter_url('http://domain.com/welcome/default/index/abc'), "/welcome/default/index ['abc']")
        self.assertEqual(filter_url('http://domain.com/welcome/static/abc'),
                         norm_root('%s/applications/welcome/static/abc' % root))
        self.assertEqual(filter_url('http://domain.com/defapp/static/path/to/static'),
            norm_root("%s/applications/defapp/static/path/to/static" % root))

    def test_routes_raise(self):
        '''
        Test URLs that raise exceptions
        '''
        # test non-exception variants
        load(data='')
        self.assertEqual(
            filter_url('http://domain.com/init'), "/init/default/index")
        self.assertEqual(filter_url(
            'http://domain.com/init/default'), "/init/default/index")
        self.assertEqual(filter_url('http://domain.com/init/default/fcn.ext'),
                         "/init/default/fcn.ext")
        self.assertEqual(filter_url('http://domain.com/init/default/fcn/arg'),
                         "/init/default/fcn ['arg']")
        # now raise-HTTP variants
        self.assertRaises(HTTP, filter_url, 'http://domain.com/bad!ctl')
        self.assertRaises(HTTP, filter_url, 'http://domain.com/ctl/bad!fcn')
        self.assertRaises(
            HTTP, filter_url, 'http://domain.com/ctl/fcn.bad!ext')
        #self.assertRaises(
        #    HTTP, filter_url, 'http://domain.com/ctl/fcn/bad!arg')
        #try:
        #    # 2.7+ only
        #    self.assertRaisesRegexp(HTTP, '400 BAD REQUEST \[invalid path\]', filter_url, 'http://domain.com/init/bad!ctl')
        #    self.assertRaisesRegexp(HTTP, '400 BAD REQUEST \[invalid path\]', filter_url, 'http://domain.com/init/ctlr/bad!fcn')
        #    self.assertRaisesRegexp(HTTP, '400 BAD REQUEST \[invalid path\]', filter_url, 'http://domain.com/init/ctlr/fcn.bad!ext')
        #    self.assertRaisesRegexp(HTTP, '400 BAD REQUEST \[invalid path\]', filter_url, 'http://domain.com/appc/init/fcn/bad!arg')
        #except AttributeError:
        #    pass

        self.assertEqual(filter_url('http://domain.com/welcome/default/fcn_1'),
                         "/welcome/default/fcn_1")
        #self.assertRaises(HTTP, filter_url, 'http://domain.com/welcome/default/fcn-1')
        #try:
        #    # 2.7+ only
        #    self.assertRaisesRegexp(HTTP, '400 BAD REQUEST \[invalid path\]', filter_url, 'http://domain.com/welcome/default/fcn-1')
        #except AttributeError:
        #    pass

    def test_routes_error(self):
        '''
        Test rewrite of HTTP errors
        '''
        router_err = dict()
        load(rdict=router_err)
        self.assertEqual(filter_err(200), 200)
        self.assertEqual(filter_err(399), 399)
        self.assertEqual(filter_err(400), 400)

    def test_routes_args(self):
        '''
        Test URL args parsing/generation
        '''
        data = r'''routes_in = [
    ('/robots.txt', '/welcome/static/robots.txt'),
    ('/favicon.ico', '/welcome/static/favicon.ico'),
    ('/admin$anything', '/admin$anything'),
    ('.*:https?://(.*\\.)?domain1.com:$method /', '/app1/default'),
    ('.*:https?://(.*\\.)?domain1.com:$method /static/$anything',
     '/app1/static/$anything'),
    ('.*:https?://(.*\\.)?domain1.com:$method /appadmin/$anything',
     '/app1/appadmin/$anything'),
    ('.*:https?://(.*\\.)?domain1.com:$method /$anything',
     '/app1/default/$anything'),
    ('.*:https?://(.*\\.)?domain2.com:$method /', '/app2/default'),
    ('.*:https?://(.*\\.)?domain2.com:$method /static/$anything',
     '/app2/static/$anything'),
    ('.*:https?://(.*\\.)?domain2.com:$method /appadmin/$anything',
     '/app2/appadmin/$anything'),
    ('.*:https?://(.*\\.)?domain2.com:$method /$anything',
     '/app2/default/$anything'),
    ('.*:https?://(.*\\.)?domain3.com:$method /', '/app3/defcon3'),
    ('.*:https?://(.*\\.)?domain3.com:$method /static/$anything',
     '/app3/static/$anything'),
    ('.*:https?://(.*\\.)?domain3.com:$method /appadmin/$anything',
     '/app3/appadmin/$anything'),
    ('.*:https?://(.*\\.)?domain3.com:$method /$anything',
     '/app3/defcon3/$anything'),
    ('/', '/welcome/default'),
    ('/welcome/default/$anything', '/welcome/default/$anything'),
    ('/welcome/$anything', '/welcome/default/$anything'),
    ('/static/$anything', '/welcome/static/$anything'),
    ('/appadmin/$anything', '/welcome/appadmin/$anything'),
    ('/$anything', '/welcome/default/$anything'),
    ]
routes_out = [
    ('/welcome/static/$anything', '/static/$anything'),
    ('/welcome/appadmin/$anything', '/appadmin/$anything'),
    ('/welcome/default/$anything', '/$anything'),
    ('/app1/static/$anything', '/static/$anything'),
    ('/app1/appadmin/$anything', '/appadmin/$anything'),
    ('/app1/default/$anything', '/$anything'),
    ('/app2/static/$anything', '/static/$anything'),
    ('/app2/appadmin/$anything', '/appadmin/$anything'),
    ('/app2/default/$anything', '/$anything'),
    ('/app3/static/$anything', '/static/$anything'),
    ('/app3/appadmin/$anything', '/appadmin/$anything'),
    ('/app3/defcon3/$anything', '/$anything')
    ]
'''
        load(data=data)
        self.assertEqual(
            filter_url('http://domain.com/welcome/default/f/arg1'),
            "/welcome/default/f ['arg1']")
        self.assertEqual(
            filter_url('http://domain.com/welcome/default/f/arg1/'),
            "/welcome/default/f ['arg1']")
        self.assertEqual(
            filter_url('http://domain.com/welcome/default/f/arg1//'),
            "/welcome/default/f ['arg1', '']")
        self.assertEqual(
            filter_url('http://domain.com/welcome/default/f//arg1'),
            "/welcome/default/f ['', 'arg1']")
        self.assertEqual(
            filter_url('http://domain.com/welcome/default/f/arg1/arg2'),
            "/welcome/default/f ['arg1', 'arg2']")
        self.assertEqual(
            filter_url('http://domain.com/welcome/default/f/arg1//arg2'),
            "/welcome/default/f ['arg1', '', 'arg2']")
        self.assertEqual(
            filter_url('http://domain.com/welcome/default/f/arg1//arg3/'),
            "/welcome/default/f ['arg1', '', 'arg3']")
        self.assertEqual(
            filter_url('http://domain.com/welcome/default/f/arg1//arg3//'),
            "/welcome/default/f ['arg1', '', 'arg3', '']")

        self.assertEqual(
            filter_url('http://domain.com/welcome/default/f', out=True), "/f")
        self.assertEqual(regex_filter_out('/welcome/default/f'), "/f")
        self.assertEqual(
            str(URL(a='welcome', c='default', f='f', args=None)), "/f")
        self.assertEqual(str(
            URL(a='welcome', c='default', f='f', args=['arg1'])), "/f/arg1")
        self.assertEqual(str(URL(
            a='welcome', c='default', f='f', args=['arg1', ''])), "/f/arg1//")
        self.assertEqual(str(URL(a='welcome', c='default', f='f',
                         args=['arg1', '', 'arg3'])), "/f/arg1//arg3")
        self.assertEqual(str(
            URL(a='welcome', c='default', f='f', args=['ar g'])), "/f/ar%20g")
        self.assertEqual(str(URL(
            a='welcome', c='default', f='f', args=['årg'])), "/f/%C3%A5rg")
        self.assertEqual(
            URL(a='welcome', c='default', f='fünc'), "/fünc")
        self.assertEqual(
            to_bytes(URL(a='welcome', c='default', f='fünc')), b"/f\xc3\xbcnc")

    def test_routes_anchor(self):
        '''
        Test URL with anchor
        '''
        self.assertEqual(
            str(URL(a='a', c='c', f='f', anchor='anchor')), "/a/c/f#anchor")
        load(data='')
        self.assertEqual(
            str(URL(a='a', c='c', f='f', anchor='anchor')), "/a/c/f#anchor")
        args = ['a1', 'a2']
        self.assertEqual(
            str(URL(a='a', c='c', f='f', args=args, anchor='anchor')),
            "/a/c/f/a1/a2#anchor")
        vars = dict(v1=1, v2=2)
        self.assertEqual(
            str(URL(a='a', c='c', f='f', vars=vars, anchor='anchor')),
            "/a/c/f?v1=1&v2=2#anchor")
        self.assertEqual(
            str(URL(
                a='a', c='c', f='f', args=args, vars=vars, anchor='anchor')),
            "/a/c/f/a1/a2?v1=1&v2=2#anchor")

        data = r'''routes_out = [
            ('/init/default/index', '/'),
        ]'''
        load(data=data)
        self.assertEqual(str(URL(a='init', c='default', f='index')),
                         "/")
        self.assertEqual(
            str(URL(a='init', c='default', f='index', anchor='anchor')),
            "/init/default/index#anchor")

        data = r'''routes_out = [
            (r'/init/default/index(?P<anchor>(#.*)?)', r'/\g<anchor>'),
        ]'''
        load(data=data)
        self.assertEqual(str(URL(a='init', c='default', f='index')),
                         "/")
        self.assertEqual(
            str(URL(a='init', c='default', f='index', anchor='anchor')),
            "/#anchor")

        data = r'''routes_out = [
            (r'/init/default/index(?P<qa>([?#].*)?)', r'/\g<qa>'),
        ]'''
        load(data=data)
        self.assertEqual(str(URL(a='init', c='default', f='index')),
                         "/")
        self.assertEqual(
            str(URL(a='init', c='default', f='index', anchor='anchor')),
            "/#anchor")
        query = dict(var='abc')
        self.assertEqual(
            str(URL(a='init', c='default', f='index', vars=query)),
            "/?var=abc")
        self.assertEqual(
            str(URL(a='init', c='default', f='index',
                vars=query, anchor='anchor')),
            "/?var=abc#anchor")

    def test_routes_absolute(self):
        '''
        Test absolute URL
        '''
        load(data='')
        r = Storage()
        r.env = Storage()
        r.env.http_host = 'domain.com'
        r.env.wsgi_url_scheme = 'httpx'  # distinguish incoming scheme
        self.assertEqual(str(URL(r=r, a='a', c='c', f='f')), "/a/c/f")
        self.assertEqual(str(URL(r=r, a='a', c='c', f='f', host=True)),
                         "httpx://domain.com/a/c/f")
        self.assertEqual(str(URL(r=r, a='a', c='c', f='f', host='host.com')),
                         "httpx://host.com/a/c/f")
        self.assertEqual(str(URL(r=r, a='a', c='c', f='f', scheme=True)),
                         "httpx://domain.com/a/c/f")
        self.assertEqual(str(URL(r=r, a='a', c='c', f='f', scheme=False)),
                         "/a/c/f")
        self.assertEqual(str(URL(r=r, a='a', c='c', f='f', scheme='https')),
                         "https://domain.com/a/c/f")
        self.assertEqual(str(URL(r=r, a='a', c='c', f='f', scheme='wss')),
                         "wss://domain.com/a/c/f")
        self.assertEqual(
            str(URL(r=r, a='a', c='c', f='f', scheme=True, host=True)),
            "httpx://domain.com/a/c/f")
        self.assertEqual(
            str(URL(r=r, a='a', c='c', f='f', scheme='https', host=True)),
            "https://domain.com/a/c/f")
        self.assertEqual(
            str(URL(r=r, a='a', c='c', f='f', scheme=False, host=True)),
            "httpx://domain.com/a/c/f")
        self.assertEqual(
            str(URL(r=r, a='a', c='c', f='f', scheme=True, host='host.com')),
            "httpx://host.com/a/c/f")
        self.assertEqual(
            str(URL(r=r, a='a', c='c', f='f', scheme=False, host='host.com')),
            "httpx://host.com/a/c/f")
        self.assertEqual(str(URL(r=r, a='a', c='c', f='f', port=1234)),
                         "httpx://domain.com:1234/a/c/f")
        self.assertEqual(
            str(URL(r=r, a='a', c='c', f='f', scheme=True, port=1234)),
            "httpx://domain.com:1234/a/c/f")
        self.assertEqual(
            str(URL(r=r, a='a', c='c', f='f', host='host.com', port=1234)),
            "httpx://host.com:1234/a/c/f")
        self.assertEqual(
            str(URL(r=r, a='a', c='c', f='f', scheme='wss',
                host='host.com', port=1234)),
            "wss://host.com:1234/a/c/f")

    def test_request_uri(self):
        '''
        Test REQUEST_URI in env
        '''
        data = r'''routes_in = [
    ('/abc', '/init/default/abc'),
    ('/index/$anything', '/init/default/index/$anything'),
    ]
'''
        load(data=data)
        self.assertEqual(
            filter_url('http://domain.com/abc', env=True).request_uri,
            '/init/default/abc')
        self.assertEqual(
            filter_url('http://domain.com/abc?def', env=True).request_uri,
            '/init/default/abc?def')
        self.assertEqual(
            filter_url('http://domain.com/index/abc', env=True).request_uri,
            "/init/default/index/abc")
        self.assertEqual(
            filter_url('http://domain.com/index/a%20bc', env=True).request_uri,
            "/init/default/index/a bc")
