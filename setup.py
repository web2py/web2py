#!/usr/bin/env python

from setuptools import setup
from gluon.fileutils import tar, untar, read_file, write_file
import tarfile
import sys


def tar(file, filelist, expression='^.+$'):
    """
    tars dir/files into file, only tars file that match expression
    """

    tar = tarfile.TarFile(file, 'w')
    try:
        for element in filelist:
            try:
                for file in listdir(element, expression, add_dirs=True):
                    tar.add(os.path.join(element, file), file, False)
            except:
                tar.add(element)
    finally:
        tar.close()


def start():
    if 'sdist' in sys.argv:
        tar('gluon/env.tar', ['applications', 'VERSION',
                              'extras/icons/splashlogo.gif'])

    setup(name='web2py',
          version=read_file("VERSION").split()[1],
          description="""full-stack framework for rapid development and prototyping
        of secure database-driven web-based applications, written and
        programmable in Python.""",
          long_description="""
        Everything in one package with no dependencies. Development, deployment,
        debugging, testing, database administration and maintenance of applications can
        be done via the provided web interface. web2py has no configuration files,
        requires no installation, can run off a USB drive. web2py uses Python for the
        Model, the Views and the Controllers, has a built-in ticketing system to manage
        errors, an internationalization engine, works with SQLite, PostgreSQL, MySQL,
        MSSQL, FireBird, Oracle, IBM DB2, Informix, Ingres, sybase and Google App Engine via a
        Database Abstraction Layer. web2py includes libraries to handle
        HTML/XML, RSS, ATOM, CSV, RTF, JSON, AJAX, XMLRPC, WIKI markup. Production
        ready, capable of upload/download streaming of very large files, and always
        backward compatible.
        """,
          author='Massimo Di Pierro',
          author_email='mdipierro@cs.depaul.edu',
          license='http://web2py.com/examples/default/license',
          classifiers=["Development Status :: 5 - Production/Stable"],
          url='http://web2py.com',
          platforms='Windows, Linux, Mac, Unix,Windows Mobile',
          packages=['gluon',
                    'gluon/contrib',
                    'gluon/contrib/gateways',
                    'gluon/contrib/login_methods',
                    'gluon/contrib/markdown',
                    'gluon/contrib/markmin',
                    'gluon/contrib/memcache',
                    'gluon/contrib/fpdf',
                    'gluon/contrib/pymysql',
                    'gluon/contrib/pyrtf',
                    'gluon/contrib/pysimplesoap',
                    'gluon/contrib/plural_rules',
                    'gluon/contrib/minify',
                    'gluon/contrib/pyaes',
                    'gluon/contrib/pyuca',
                    'gluon/tests',
                    ],
          package_data={'gluon': ['env.tar']},
#          scripts=['w2p_apps', 'w2p_run', 'w2p_clone'],
          )

if __name__ == '__main__':
    #print "web2py does not require installation and"
    #print "you should just start it with:"
    #print
    #print "$ python web2py.py"
    #print
    #print "are you sure you want to install it anyway (y/n)?"
    #s = raw_input('>')
    #if s.lower()[:1]=='y':
    start()
