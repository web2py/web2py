#
# This files allows to delegate authentication for every URL within a domain
# to a web2py app within the same domain
# If you are logged in the app, you have access to the URL
# even if the URL is not a web2py URL
#
# in /etc/apache2/sites-available/default
#
# <VirtualHost *:80>
#   WSGIDaemonProcess web2py user=www-data group=www-data
#   WSGIProcessGroup web2py
#   WSGIScriptAlias / /home/www-data/web2py/wsgihandler.py
#
#   AliasMatch ^myapp/whatever/myfile /path/to/myfile
#   <Directory /path/to/>
#     WSGIAccessScript /path/to/web2py/scripts/access.wsgi
#   </Directory>
# </VirtualHost>
#
# in yourapp/controllers/default.py
#
# def check_access():
#     request_uri = request.vars.request_uri
#     return 'true' if auth.is_logged_in() else 'false'
#
# start web2py as deamon
#
# nohup python web2py.py -a '' -p 8002
#
# now try visit:
#
#    http://domain/myapp/whatever/myfile
#
# and you will have access ONLY if you are logged into myapp
#

URL_CHECK_ACCESS = 'http://127.0.0.1:8002/%(app)s/default/check_access'

def allow_access(environ,host):
    import os
    import urllib
    import urllib2
    import datetime
    header = '%s @ %s ' % (datetime.datetime.now(),host) + '='*20
    pprint = '\n'.join('%s:%s' % item for item in environ.items())
    filename = os.path.join(os.path.dirname(__file__),'access.wsgi.log')
    f = open(filename,'a')
    try:
        f.write('\n'+header+'\n'+pprint+'\n')
    finally:
        f.close()
    app = environ['REQUEST_URI'].split('/')[1]
    keys = [key for key in environ if key.startswith('HTTP_')]
    headers = {}
    for key in environ:
        if key.startswith('HTTP_'):
            headers[key[5:]] = environ[key] # this passes the cookies through!
    try:
        data = urllib.urlencode({'request_uri':environ['REQUEST_URI']})
        request = urllib2.Request(URL_CHECK_ACCESS % dict(app=app),data,headers)
        response = urllib2.urlopen(request).read().strip().lower()
        if response.startswith('true'): return True
    except: pass
    return False
