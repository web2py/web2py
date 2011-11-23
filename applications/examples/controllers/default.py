# -*- coding: utf-8 -*-

from gluon.fileutils import read_file

response.title = T('web2py Web Framework')
response.keywords = T('web2py, Python, Web Framework')
response.description = T('web2py Web Framework')

session.forget()

@cache('index')
def index():
    return response.render()

@cache('what')
def what():
    import urllib;
    try:
        images = XML(urllib.urlopen('http://web2py.com/poweredby/default/images').read())
    except:
        images = []
    return response.render(images=images)

@cache('download')
def download():
    return response.render()

@cache('who')
def who():
    return response.render()

@cache('support')
def support():
    return response.render()

@cache('documentation')
def documentation():
    return response.render()

@cache('usergroups')
def usergroups():
    return response.render()

def contact():
    redirect(URL('default','usergroups'))

@cache('videos')
def videos():
    return response.render()

def security():
    redirect('http://www.web2py.com/book/default/chapter/01#security')

def api():
    redirect('http://web2py.com/book/default/chapter/04#API')

@cache('license')
def license():
    import os
    filename = os.path.join(request.env.gluon_parent, 'LICENSE')
    return response.render(dict(license=MARKMIN(read_file(filename))))

def version():
    return 'Version %s.%s.%s (%s) %s' % request.env.web2py_version

@cache('examples')
def examples():
    return response.render()

@cache('changelog')
def changelog():
    import os
    filename = os.path.join(request.env.gluon_parent, 'CHANGELOG')
    return response.render(dict(changelog=MARKMIN(read_file(filename))))
