#!/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Thanks to
    * Niall Sweeny <niall.sweeny@fonjax.com> for MS SQL support
    * Marcel Leuthi <mluethi@mlsystems.ch> for Oracle support
    * Denes
    * Chris Clark
    * clach05
    * Denes Lengyel
    * and many others who have contributed to current and previous versions

This file contains the DAL support for many relational databases,
including:
- SQLite & SpatiaLite
- MySQL
- Postgres
- Firebird
- Oracle
- MS SQL
- DB2
- Interbase
- Ingres
- Informix (9+ and SE)
- SapDB (experimental)
- Cubrid (experimental)
- CouchDB (experimental)
- MongoDB (in progress)
- Google:nosql
- Google:sql
- Teradata
- IMAP (experimental)

Example of usage:

>>> # from dal import DAL, Field

### create DAL connection (and create DB if it doesn't exist)
>>> db = DAL(('sqlite://storage.sqlite','mysql://a:b@localhost/x'),
... folder=None)

### define a table 'person' (create/alter as necessary)
>>> person = db.define_table('person',Field('name','string'))

### insert a record
>>> id = person.insert(name='James')

### retrieve it by id
>>> james = person(id)

### retrieve it by name
>>> james = person(name='James')

### retrieve it by arbitrary query
>>> query = (person.name=='James') & (person.name.startswith('J'))
>>> james = db(query).select(person.ALL)[0]

### update one record
>>> james.update_record(name='Jim')
<Row {'id': 1, 'name': 'Jim'}>

### update multiple records by query
>>> db(person.name.like('J%')).update(name='James')
1

### delete records by query
>>> db(person.name.lower() == 'jim').delete()
0

### retrieve multiple records (rows)
>>> people = db(person).select(orderby=person.name,
... groupby=person.name, limitby=(0,100))

### further filter them
>>> james = people.find(lambda row: row.name == 'James').first()
>>> print james.id, james.name
1 James

### check aggregates
>>> counter = person.id.count()
>>> print db(person).select(counter).first()(counter)
1

### delete one record
>>> james.delete_record()
1

### delete (drop) entire database table
>>> person.drop()

Supported field types:
id string text boolean integer double decimal password upload
blob time date datetime

Supported DAL URI strings:
'sqlite://test.db'
'spatialite://test.db'
'sqlite:memory'
'spatialite:memory'
'jdbc:sqlite://test.db'
'mysql://root:none@localhost/test'
'postgres://mdipierro:password@localhost/test'
'postgres:psycopg2://mdipierro:password@localhost/test'
'postgres:pg8000://mdipierro:password@localhost/test'
'jdbc:postgres://mdipierro:none@localhost/test'
'mssql://web2py:none@A64X2/web2py_test'
'mssql2://web2py:none@A64X2/web2py_test' # alternate mappings
'oracle://username:password@database'
'firebird://user:password@server:3050/database'
'db2://DSN=dsn;UID=user;PWD=pass'
'firebird://username:password@hostname/database'
'firebird_embedded://username:password@c://path'
'informix://user:password@server:3050/database'
'informixu://user:password@server:3050/database' # unicode informix
'ingres://database'  # or use an ODBC connection string, e.g. 'ingres://dsn=dsn_name'
'google:datastore' # for google app engine datastore
'google:sql' # for google app engine with sql (mysql compatible)
'teradata://DSN=dsn;UID=user;PWD=pass; DATABASE=database' # experimental
'imap://user:password@server:port' # experimental
'mongodb://user:password@server:port/database' # experimental

For more info:
help(DAL)
help(Field)
"""

###################################################################################
# this file only exposes DAL and Field
###################################################################################

__all__ = ['DAL', 'Field']

DEFAULTLENGTH = {'string':512,
                 'password':512,
                 'upload':512,
                 'text':2**15,
                 'blob':2**31}
TIMINGSSIZE = 100
SPATIALLIBS = {
    'Windows':'libspatialite',
    'Linux':'libspatialite.so',
    'Darwin':'libspatialite.dylib'
    }
DEFAULT_URI = 'sqlite://dummy.db'

import re
import sys
import locale
import os
import types
import datetime
import threading
import time
import csv
import cgi
import copy
import socket
import logging
import base64
import shutil
import marshal
import decimal
import struct
import urllib
import hashlib
import uuid
import glob
import traceback
import platform

PYTHON_VERSION = sys.version_info[:3]
if PYTHON_VERSION[0] == 2:
    import cPickle as pickle
    import cStringIO as StringIO
    import copy_reg as copyreg
    hashlib_md5 = hashlib.md5
    bytes, unicode = str, unicode
else:
    import pickle
    from io import StringIO as StringIO
    import copyreg
    long = int
    hashlib_md5 = lambda s: hashlib.md5(bytes(s,'utf8'))
    bytes, unicode = bytes, str

if PYTHON_VERSION[:2] < (2, 7):
    from gluon.contrib.ordereddict import OrderedDict
else:
    from collections import OrderedDict


CALLABLETYPES = (types.LambdaType, types.FunctionType,
                 types.BuiltinFunctionType,
                 types.MethodType, types.BuiltinMethodType)

TABLE_ARGS = set(
    ('migrate','primarykey','fake_migrate','format','redefine',
     'singular','plural','trigger_name','sequence_name','fields',
     'common_filter','polymodel','table_class','on_define','rname'))

SELECT_ARGS = set(
    ('orderby', 'groupby', 'limitby','required', 'cache', 'left',
     'distinct', 'having', 'join','for_update', 'processor','cacheable', 'orderby_on_limitby'))

ogetattr = object.__getattribute__
osetattr = object.__setattr__
exists = os.path.exists
pjoin = os.path.join

###################################################################################
# following checks allow the use of dal without web2py, as a standalone module
###################################################################################
try:
    from gluon.utils import web2py_uuid
except (ImportError, SystemError):
    import uuid
    def web2py_uuid(): return str(uuid.uuid4())

try:
    import portalocker
    have_portalocker = True
except ImportError:
    have_portalocker = False

try:
    from gluon import serializers
    have_serializers = True
except ImportError:
    have_serializers = False
    try:
        import json as simplejson
    except ImportError:
        try:
            import gluon.contrib.simplejson as simplejson
        except ImportError:
            simplejson = None

LOGGER = logging.getLogger("web2py.dal")
DEFAULT = lambda:0

GLOBAL_LOCKER = threading.RLock()
THREAD_LOCAL = threading.local()

# internal representation of tables with field
#  <table>.<field>, tables and fields may only be [a-zA-Z0-9_]

REGEX_TYPE = re.compile('^([\w\_\:]+)')
REGEX_DBNAME = re.compile('^(\w+)(\:\w+)*')
REGEX_W = re.compile('^\w+$')
REGEX_TABLE_DOT_FIELD = re.compile('^(\w+)\.(\w+)$')
REGEX_UPLOAD_PATTERN = re.compile('(?P<table>[\w\-]+)\.(?P<field>[\w\-]+)\.(?P<uuidkey>[\w\-]+)(\.(?P<name>\w+))?\.\w+$')
REGEX_CLEANUP_FN = re.compile('[\'"\s;]+')
REGEX_UNPACK = re.compile('(?<!\|)\|(?!\|)')
REGEX_PYTHON_KEYWORDS = re.compile('^(and|del|from|not|while|as|elif|global|or|with|assert|else|if|pass|yield|break|except|import|print|class|exec|in|raise|continue|finally|is|return|def|for|lambda|try)$')
REGEX_SELECT_AS_PARSER = re.compile("\s+AS\s+(\S+)")
REGEX_CONST_STRING = re.compile('(\"[^\"]*?\")|(\'[^\']*?\')')
REGEX_SEARCH_PATTERN = re.compile('^{[^\.]+\.[^\.]+(\.(lt|gt|le|ge|eq|ne|contains|startswith|year|month|day|hour|minute|second))?(\.not)?}$')
REGEX_SQUARE_BRACKETS = re.compile('^.+\[.+\]$')
REGEX_STORE_PATTERN = re.compile('\.(?P<e>\w{1,5})$')
REGEX_QUOTES = re.compile("'[^']*'")
REGEX_ALPHANUMERIC = re.compile('^[0-9a-zA-Z]\w*$')
REGEX_PASSWORD = re.compile('\://([^:@]*)\:')
REGEX_NOPASSWD = re.compile('\/\/[\w\.\-]+[\:\/](.+)(?=@)') # was '(?<=[\:\/])([^:@/]+)(?=@.+)'

# list of drivers will be built on the fly
# and lists only what is available
DRIVERS = []

try:
    from new import classobj
    from google.appengine.ext import db as gae
    from google.appengine.ext import ndb
    from google.appengine.api import namespace_manager, rdbms
    from google.appengine.api.datastore_types import Key  ### for belongs on ID
    from google.appengine.ext.db.polymodel import PolyModel
    from google.appengine.ext.ndb.polymodel import PolyModel as NDBPolyModel
    DRIVERS.append('google')
except ImportError:
    pass

if not 'google' in DRIVERS:

    try:
        from pysqlite2 import dbapi2 as sqlite2
        DRIVERS.append('SQLite(sqlite2)')
    except ImportError:
        LOGGER.debug('no SQLite drivers pysqlite2.dbapi2')

    try:
        from sqlite3 import dbapi2 as sqlite3
        DRIVERS.append('SQLite(sqlite3)')
    except ImportError:
        LOGGER.debug('no SQLite drivers sqlite3')

    try:
        # first try contrib driver, then from site-packages (if installed)
        try:
            import gluon.contrib.pymysql as pymysql
            # monkeypatch pymysql because they havent fixed the bug:
            # https://github.com/petehunt/PyMySQL/issues/86
            pymysql.ESCAPE_REGEX = re.compile("'")
            pymysql.ESCAPE_MAP = {"'": "''"}
            # end monkeypatch
        except ImportError:
            import pymysql
        DRIVERS.append('MySQL(pymysql)')
    except ImportError:
        LOGGER.debug('no MySQL driver pymysql')

    try:
        import MySQLdb
        DRIVERS.append('MySQL(MySQLdb)')
    except ImportError:
        LOGGER.debug('no MySQL driver MySQLDB')

    try:
        import mysql.connector as mysqlconnector
        DRIVERS.append("MySQL(mysqlconnector)")
    except ImportError:
        LOGGER.debug("no driver mysql.connector")

    try:
        import psycopg2
        from psycopg2.extensions import adapt as psycopg2_adapt
        DRIVERS.append('PostgreSQL(psycopg2)')
    except ImportError:
        LOGGER.debug('no PostgreSQL driver psycopg2')

    try:
        # first try contrib driver, then from site-packages (if installed)
        try:
            import gluon.contrib.pg8000.dbapi as pg8000
        except ImportError:
            import pg8000.dbapi as pg8000
        DRIVERS.append('PostgreSQL(pg8000)')
    except ImportError:
        LOGGER.debug('no PostgreSQL driver pg8000')

    try:
        import cx_Oracle
        DRIVERS.append('Oracle(cx_Oracle)')
    except ImportError:
        LOGGER.debug('no Oracle driver cx_Oracle')

    try:
        try:
            import pyodbc
        except ImportError:
            try:
                import gluon.contrib.pypyodbc as pyodbc
            except Exception, e:
                raise ImportError(str(e))
        DRIVERS.append('MSSQL(pyodbc)')
        DRIVERS.append('DB2(pyodbc)')
        DRIVERS.append('Teradata(pyodbc)')
        DRIVERS.append('Ingres(pyodbc)')
    except ImportError:
        LOGGER.debug('no MSSQL/DB2/Teradata/Ingres driver pyodbc')

    try:
        import Sybase
        DRIVERS.append('Sybase(Sybase)')
    except ImportError:
        LOGGER.debug('no Sybase driver')

    try:
        import kinterbasdb
        DRIVERS.append('Interbase(kinterbasdb)')
        DRIVERS.append('Firebird(kinterbasdb)')
    except ImportError:
        LOGGER.debug('no Firebird/Interbase driver kinterbasdb')

    try:
        import fdb
        DRIVERS.append('Firebird(fdb)')
    except ImportError:
        LOGGER.debug('no Firebird driver fdb')
#####
    try:
        import firebirdsql
        DRIVERS.append('Firebird(firebirdsql)')
    except ImportError:
        LOGGER.debug('no Firebird driver firebirdsql')

    try:
        import informixdb
        DRIVERS.append('Informix(informixdb)')
        LOGGER.warning('Informix support is experimental')
    except ImportError:
        LOGGER.debug('no Informix driver informixdb')

    try:
        import sapdb
        DRIVERS.append('SQL(sapdb)')
        LOGGER.warning('SAPDB support is experimental')
    except ImportError:
        LOGGER.debug('no SAP driver sapdb')

    try:
        import cubriddb
        DRIVERS.append('Cubrid(cubriddb)')
        LOGGER.warning('Cubrid support is experimental')
    except ImportError:
        LOGGER.debug('no Cubrid driver cubriddb')

    try:
        from com.ziclix.python.sql import zxJDBC
        import java.sql
        # Try sqlite jdbc driver from http://www.zentus.com/sqlitejdbc/
        from org.sqlite import JDBC # required by java.sql; ensure we have it
        zxJDBC_sqlite = java.sql.DriverManager
        DRIVERS.append('PostgreSQL(zxJDBC)')
        DRIVERS.append('SQLite(zxJDBC)')
        LOGGER.warning('zxJDBC support is experimental')
        is_jdbc = True
    except ImportError:
        LOGGER.debug('no SQLite/PostgreSQL driver zxJDBC')
        is_jdbc = False

    try:
        import couchdb
        DRIVERS.append('CouchDB(couchdb)')
    except ImportError:
        LOGGER.debug('no Couchdb driver couchdb')

    try:
        import pymongo
        DRIVERS.append('MongoDB(pymongo)')
    except:
        LOGGER.debug('no MongoDB driver pymongo')

    try:
        import imaplib
        DRIVERS.append('IMAP(imaplib)')
    except:
        LOGGER.debug('no IMAP driver imaplib')

PLURALIZE_RULES = [
    (re.compile('child$'), re.compile('child$'), 'children'),
    (re.compile('oot$'), re.compile('oot$'), 'eet'),
    (re.compile('ooth$'), re.compile('ooth$'), 'eeth'),
    (re.compile('l[eo]af$'), re.compile('l([eo])af$'), 'l\\1aves'),
    (re.compile('sis$'), re.compile('sis$'), 'ses'),
    (re.compile('man$'), re.compile('man$'), 'men'),
    (re.compile('ife$'), re.compile('ife$'), 'ives'),
    (re.compile('eau$'), re.compile('eau$'), 'eaux'),
    (re.compile('lf$'), re.compile('lf$'), 'lves'),
    (re.compile('[sxz]$'), re.compile('$'), 'es'),
    (re.compile('[^aeioudgkprt]h$'), re.compile('$'), 'es'),
    (re.compile('(qu|[^aeiou])y$'), re.compile('y$'), 'ies'),
    (re.compile('$'), re.compile('$'), 's'),
    ]

def pluralize(singular, rules=PLURALIZE_RULES):
    for line in rules:
        re_search, re_sub, replace = line
        plural = re_search.search(singular) and re_sub.sub(replace, singular)
        if plural: return plural

def hide_password(uri):
    if isinstance(uri,(list,tuple)):
        return [hide_password(item) for item in uri]
    return REGEX_NOPASSWD.sub('******',uri)

def OR(a,b):
    return a|b

def AND(a,b):
    return a&b

def IDENTITY(x): return x

def varquote_aux(name,quotestr='%s'):
    return name if REGEX_W.match(name) else quotestr % name

def quote_keyword(a,keyword='timestamp'):
    regex = re.compile('\.keyword(?=\w)')
    a = regex.sub('."%s"' % keyword,a)
    return a

if 'google' in DRIVERS:

    is_jdbc = False

    class GAEDecimalProperty(gae.Property):
        """
        GAE decimal implementation
        """
        data_type = decimal.Decimal

        def __init__(self, precision, scale, **kwargs):
            super(GAEDecimalProperty, self).__init__(self, **kwargs)
            d = '1.'
            for x in range(scale):
                d += '0'
            self.round = decimal.Decimal(d)

        def get_value_for_datastore(self, model_instance):
            value = super(GAEDecimalProperty, self)\
                .get_value_for_datastore(model_instance)
            if value is None or value == '':
                return None
            else:
                return str(value)

        def make_value_from_datastore(self, value):
            if value is None or value == '':
                return None
            else:
                return decimal.Decimal(value).quantize(self.round)

        def validate(self, value):
            value = super(GAEDecimalProperty, self).validate(value)
            if value is None or isinstance(value, decimal.Decimal):
                return value
            elif isinstance(value, basestring):
                return decimal.Decimal(value)
            raise gae.BadValueError("Property %s must be a Decimal or string."\
                                        % self.name)

    #TODO Needs more testing
    class NDBDecimalProperty(ndb.StringProperty):
        """
        NDB decimal implementation
        """
        data_type = decimal.Decimal

        def __init__(self, precision, scale, **kwargs):
            d = '1.'
            for x in range(scale):
                d += '0'
            self.round = decimal.Decimal(d)

        def _to_base_type(self, value):
            if value is None or value == '':
                return None
            else:
                return str(value)

        def _from_base_type(self, value):
            if value is None or value == '':
                return None
            else:
                return decimal.Decimal(value).quantize(self.round)

        def _validate(self, value):
            if value is None or isinstance(value, decimal.Decimal):
                return value
            elif isinstance(value, basestring):
                return decimal.Decimal(value)
            raise TypeError("Property %s must be a Decimal or string."\
                                        % self._name)

###################################################################################
# class that handles connection pooling (all adapters are derived from this one)
###################################################################################

class ConnectionPool(object):

    POOLS = {}
    check_active_connection = True

    @staticmethod
    def set_folder(folder):
        THREAD_LOCAL.folder = folder

    # ## this allows gluon to commit/rollback all dbs in this thread

    def close(self,action='commit',really=True):
        if action:
            if callable(action):
                action(self)
            else:
                getattr(self, action)()
        # ## if you want pools, recycle this connection
        if self.pool_size:
            GLOBAL_LOCKER.acquire()
            pool = ConnectionPool.POOLS[self.uri]
            if len(pool) < self.pool_size:
                pool.append(self.connection)
                really = False
            GLOBAL_LOCKER.release()
        if really:
            self.close_connection()
        self.connection = None

    @staticmethod
    def close_all_instances(action):
        """ to close cleanly databases in a multithreaded environment """
        dbs = getattr(THREAD_LOCAL,'db_instances',{}).items()
        for db_uid, db_group in dbs:
            for db in db_group:
                if hasattr(db,'_adapter'):
                    db._adapter.close(action)
        getattr(THREAD_LOCAL,'db_instances',{}).clear()
        getattr(THREAD_LOCAL,'db_instances_zombie',{}).clear()
        if callable(action):
            action(None)
        return

    def find_or_make_work_folder(self):
        """ this actually does not make the folder. it has to be there """
        self.folder = getattr(THREAD_LOCAL,'folder','')

        if (os.path.isabs(self.folder) and
            isinstance(self, UseDatabaseStoredFile) and
            self.folder.startswith(os.getcwd())):
            self.folder = os.path.relpath(self.folder, os.getcwd())

        # Creating the folder if it does not exist
        if False and self.folder and not exists(self.folder):
            os.mkdir(self.folder)

    def after_connection_hook(self):
        """hook for the after_connection parameter"""
        if callable(self._after_connection):
            self._after_connection(self)
        self.after_connection()

    def after_connection(self):
        """ this it is supposed to be overloaded by adapters"""
        pass

    def reconnect(self, f=None, cursor=True):
        """
        this function defines: self.connection and self.cursor
        (iff cursor is True)
        if self.pool_size>0 it will try pull the connection from the pool
        if the connection is not active (closed by db server) it will loop
        if not self.pool_size or no active connections in pool makes a new one
        """
        if getattr(self,'connection', None) != None:
            return
        if f is None:
            f = self.connector

        # if not hasattr(self, "driver") or self.driver is None:
        #     LOGGER.debug("Skipping connection since there's no driver")
        #     return

        if not self.pool_size:
            self.connection = f()
            self.cursor = cursor and self.connection.cursor()
        else:
            uri = self.uri
            POOLS = ConnectionPool.POOLS
            while True:
                GLOBAL_LOCKER.acquire()
                if not uri in POOLS:
                    POOLS[uri] = []
                if POOLS[uri]:
                    self.connection = POOLS[uri].pop()
                    GLOBAL_LOCKER.release()
                    self.cursor = cursor and self.connection.cursor()
                    try:
                        if self.cursor and self.check_active_connection:
                            self.execute('SELECT 1;')
                        break
                    except:
                        pass
                else:
                    GLOBAL_LOCKER.release()
                    self.connection = f()
                    self.cursor = cursor and self.connection.cursor()
                    break
        self.after_connection_hook()


###################################################################################
# this is a generic adapter that does nothing; all others are derived from this one
###################################################################################

class BaseAdapter(ConnectionPool):
    native_json = False
    driver = None
    driver_name = None
    drivers = () # list of drivers from which to pick
    connection = None
    commit_on_alter_table = False
    support_distributed_transaction = False
    uploads_in_blob = False
    can_select_for_update = True
    dbpath = None
    folder = None

    TRUE = 'T'
    FALSE = 'F'
    T_SEP = ' '
    QUOTE_TEMPLATE = '"%s"'

    types = {
        'boolean': 'CHAR(1)',
        'string': 'CHAR(%(length)s)',
        'text': 'TEXT',
        'json': 'TEXT',
        'password': 'CHAR(%(length)s)',
        'blob': 'BLOB',
        'upload': 'CHAR(%(length)s)',
        'integer': 'INTEGER',
        'bigint': 'INTEGER',
        'float':'DOUBLE',
        'double': 'DOUBLE',
        'decimal': 'DOUBLE',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'TEXT',
        'list:string': 'TEXT',
        'list:reference': 'TEXT',
        # the two below are only used when DAL(...bigint_id=True) and replace 'id','reference'
        'big-id': 'BIGINT PRIMARY KEY AUTOINCREMENT',
        'big-reference': 'BIGINT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        }

    def isOperationalError(self,exception):
        if not hasattr(self.driver, "OperationalError"):
            return None
        return isinstance(exception, self.driver.OperationalError)

    def isProgrammingError(self,exception):
        if not hasattr(self.driver, "ProgrammingError"):
            return None
        return isinstance(exception, self.driver.ProgrammingError)

    def id_query(self, table):
        pkeys = getattr(table,'_primarykey',None)
        if pkeys:
            return table[pkeys[0]] != None
        else:
            return table._id != None

    def adapt(self, obj):
        return "'%s'" % obj.replace("'", "''")

    def smart_adapt(self, obj):
        if isinstance(obj,(int,float)):
            return str(obj)
        return self.adapt(str(obj))

    def file_exists(self, filename):
        """
        to be used ONLY for files that on GAE may not be on filesystem
        """
        return exists(filename)

    def file_open(self, filename, mode='rb', lock=True):
        """
        to be used ONLY for files that on GAE may not be on filesystem
        """
        if have_portalocker and lock:
            fileobj = portalocker.LockedFile(filename,mode)
        else:
            fileobj = open(filename,mode)
        return fileobj

    def file_close(self, fileobj):
        """
        to be used ONLY for files that on GAE may not be on filesystem
        """
        if fileobj:
            fileobj.close()

    def file_delete(self, filename):
        os.unlink(filename)

    def find_driver(self,adapter_args,uri=None):
        self.adapter_args = adapter_args
        if getattr(self,'driver',None) != None:
            return
        drivers_available = [driver for driver in self.drivers
                             if driver in globals()]
        if uri:
            items = uri.split('://',1)[0].split(':')
            request_driver = items[1] if len(items)>1 else None
        else:
            request_driver = None
        request_driver = request_driver or adapter_args.get('driver')
        if request_driver:
            if request_driver in drivers_available:
                self.driver_name = request_driver
                self.driver = globals().get(request_driver)
            else:
                raise RuntimeError("driver %s not available" % request_driver)
        elif drivers_available:
            self.driver_name = drivers_available[0]
            self.driver = globals().get(self.driver_name)
        else:
            raise RuntimeError("no driver available %s" % str(self.drivers))

    def log(self, message, table=None):
        """ Logs migrations

        It will not log changes if logfile is not specified. Defaults
        to sql.log
        """

        isabs = None
        logfilename = self.adapter_args.get('logfile','sql.log')
        writelog = bool(logfilename)
        if writelog:
            isabs = os.path.isabs(logfilename)

        if table and table._dbt and writelog and self.folder:
            if isabs:
                table._loggername = logfilename
            else:
                table._loggername = pjoin(self.folder, logfilename)
            logfile = self.file_open(table._loggername, 'a')
            logfile.write(message)
            self.file_close(logfile)


    def __init__(self, db,uri,pool_size=0, folder=None, db_codec='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={},do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "None"
        self.uri = uri
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        class Dummy(object):
            lastrowid = 1
            def __getattr__(self, value):
                return lambda *a, **b: []
        self.connection = Dummy()
        self.cursor = Dummy()

    def sequence_name(self,tablename):
        return '%s_sequence' % tablename

    def trigger_name(self,tablename):
        return '%s_sequence' % tablename

    def varquote(self,name):
        return name

    def create_table(self, table,
                     migrate=True,
                     fake_migrate=False,
                     polymodel=None):
        db = table._db
        fields = []
        # PostGIS geo fields are added after the table has been created
        postcreation_fields = []
        sql_fields = {}
        sql_fields_aux = {}
        TFK = {}
        tablename = table._tablename
        sortable = 0
        types = self.types
        for field in table:
            sortable += 1
            field_name = field.name
            field_type = field.type
            if isinstance(field_type,SQLCustomType):
                ftype = field_type.native or field_type.type
            elif field_type.startswith('reference'):
                referenced = field_type[10:].strip()
                if referenced == '.':
                    referenced = tablename
                constraint_name = self.constraint_name(tablename, field_name)
                if not '.' in referenced \
                        and referenced != tablename \
                        and hasattr(table,'_primarykey'):
                    ftype = types['integer']
                else:
                    if hasattr(table,'_primarykey'):
                        rtablename,rfieldname = referenced.split('.')
                        rtable = db[rtablename]
                        rfield = rtable[rfieldname]
                        # must be PK reference or unique
                        if rfieldname in rtable._primarykey or \
                                rfield.unique:
                            ftype = types[rfield.type[:9]] % \
                                dict(length=rfield.length)
                            # multicolumn primary key reference?
                            if not rfield.unique and len(rtable._primarykey)>1:
                                # then it has to be a table level FK
                                if rtablename not in TFK:
                                    TFK[rtablename] = {}
                                TFK[rtablename][rfieldname] = field_name
                            else:
                                ftype = ftype + \
                                    types['reference FK'] % dict(
                                    constraint_name = constraint_name, # should be quoted
                                    foreign_key = '%s (%s)' % (rtablename,
                                                               rfieldname),
                                    table_name = tablename,
                                    field_name = field._rname or field.name,
                                    on_delete_action=field.ondelete)
                    else:
                        # make a guess here for circular references
                        if referenced in db:
                            id_fieldname = db[referenced]._id.name
                        elif referenced == tablename:
                            id_fieldname = table._id.name
                        else: #make a guess
                            id_fieldname = 'id'
                        #gotcha: the referenced table must be defined before
                        #the referencing one to be able to create the table
                        #Also if it's not recommended, we can still support
                        #references to tablenames without rname to make
                        #migrations and model relationship work also if tables
                        #are not defined in order
                        real_referenced = (
                            (db[referenced]._rname or db[referenced])
                            if referenced == tablename or referenced in db
                            else referenced)
                            
                        ftype = types[field_type[:9]] % dict(
                            index_name = field_name+'__idx',
                            field_name = field._rname or field.name,
                            constraint_name = constraint_name,
                            foreign_key = '%s (%s)' % (real_referenced,
                                                       id_fieldname),
                            on_delete_action=field.ondelete)
            elif field_type.startswith('list:reference'):
                ftype = types[field_type[:14]]
            elif field_type.startswith('decimal'):
                precision, scale = map(int,field_type[8:-1].split(','))
                ftype = types[field_type[:7]] % \
                    dict(precision=precision,scale=scale)
            elif field_type.startswith('geo'):
                if not hasattr(self,'srid'):
                    raise RuntimeError('Adapter does not support geometry')
                srid = self.srid
                geotype, parms = field_type[:-1].split('(')
                if not geotype in types:
                    raise SyntaxError(
                        'Field: unknown field type: %s for %s' \
                        % (field_type, field_name))
                ftype = types[geotype]
                if self.dbengine == 'postgres' and geotype == 'geometry':
                    # parameters: schema, srid, dimension
                    dimension = 2 # GIS.dimension ???
                    parms = parms.split(',')
                    if len(parms) == 3:
                        schema, srid, dimension = parms
                    elif len(parms) == 2:
                        schema, srid = parms
                    else:
                        schema = parms[0]
                    ftype = "SELECT AddGeometryColumn ('%%(schema)s', '%%(tablename)s', '%%(fieldname)s', %%(srid)s, '%s', %%(dimension)s);" % types[geotype]
                    ftype = ftype % dict(schema=schema,
                                         tablename=tablename,
                                         fieldname=field_name, srid=srid,
                                         dimension=dimension)
                    postcreation_fields.append(ftype)
            elif not field_type in types:
                raise SyntaxError('Field: unknown field type: %s for %s' % \
                    (field_type, field_name))
            else:
                ftype = types[field_type]\
                     % dict(length=field.length)
            if not field_type.startswith('id') and \
                    not field_type.startswith('reference'):
                if field.notnull:
                    ftype += ' NOT NULL'
                else:
                    ftype += self.ALLOW_NULL()
                if field.unique:
                    ftype += ' UNIQUE'
                if field.custom_qualifier:
                    ftype += ' %s' % field.custom_qualifier

            # add to list of fields
            sql_fields[field_name] = dict(
                length=field.length,
                unique=field.unique,
                notnull=field.notnull,
                sortable=sortable,
                type=str(field_type),
                sql=ftype)

            if field.notnull and not field.default is None:
                # Caveat: sql_fields and sql_fields_aux
                # differ for default values.
                # sql_fields is used to trigger migrations and sql_fields_aux
                # is used for create tables.
                # The reason is that we do not want to trigger
                # a migration simply because a default value changes.
                not_null = self.NOT_NULL(field.default, field_type)
                ftype = ftype.replace('NOT NULL', not_null)
            sql_fields_aux[field_name] = dict(sql=ftype)
            # Postgres - PostGIS:
            # geometry fields are added after the table has been created, not now
            if not (self.dbengine == 'postgres' and \
                        field_type.startswith('geom')):
                #fetch the rname if it's there
                field_rname = "%s" % (field._rname or field_name)
                fields.append('%s %s' % (field_rname, ftype))
        other = ';'

        # backend-specific extensions to fields
        if self.dbengine == 'mysql':
            if not hasattr(table, "_primarykey"):
                fields.append('PRIMARY KEY(%s)' % (table._id.name or table._id._rname))
            other = ' ENGINE=InnoDB CHARACTER SET utf8;'

        fields = ',\n    '.join(fields)
        for rtablename in TFK:
            rfields = TFK[rtablename]
            pkeys = db[rtablename]._primarykey
            fkeys = [ rfields[k] for k in pkeys ]
            fields = fields + ',\n    ' + \
                types['reference TFK'] % dict(
                table_name = tablename,
                field_name=', '.join(fkeys),
                foreign_table = rtablename,
                foreign_key = ', '.join(pkeys),
                on_delete_action = field.ondelete)
        #if there's a _rname, let's use that instead
        table_rname = table._rname or tablename

        if getattr(table,'_primarykey',None):
            query = "CREATE TABLE %s(\n    %s,\n    %s) %s" % \
                (table_rname, fields,
                 self.PRIMARY_KEY(', '.join(table._primarykey)),other)
        else:
            query = "CREATE TABLE %s(\n    %s\n)%s" % \
                (table_rname, fields, other)

        if self.uri.startswith('sqlite:///') \
                or self.uri.startswith('spatialite:///'):
            path_encoding = sys.getfilesystemencoding() \
                or locale.getdefaultlocale()[1] or 'utf8'
            dbpath = self.uri[9:self.uri.rfind('/')]\
                .decode('utf8').encode(path_encoding)
        else:
            dbpath = self.folder

        if not migrate:
            return query
        elif self.uri.startswith('sqlite:memory')\
                or self.uri.startswith('spatialite:memory'):
            table._dbt = None
        elif isinstance(migrate, str):
            table._dbt = pjoin(dbpath, migrate)
        else:
            table._dbt = pjoin(
                dbpath, '%s_%s.table' % (table._db._uri_hash, tablename))

        if not table._dbt or not self.file_exists(table._dbt):
            if table._dbt:
                self.log('timestamp: %s\n%s\n'
                         % (datetime.datetime.today().isoformat(),
                            query), table)
            if not fake_migrate:
                self.create_sequence_and_triggers(query,table)
                table._db.commit()
                # Postgres geom fields are added now,
                # after the table has been created
                for query in postcreation_fields:
                    self.execute(query)
                    table._db.commit()
            if table._dbt:
                tfile = self.file_open(table._dbt, 'w')
                pickle.dump(sql_fields, tfile)
                self.file_close(tfile)
                if fake_migrate:
                    self.log('faked!\n', table)
                else:
                    self.log('success!\n', table)
        else:
            tfile = self.file_open(table._dbt, 'r')
            try:
                sql_fields_old = pickle.load(tfile)
            except EOFError:
                self.file_close(tfile)
                raise RuntimeError('File %s appears corrupted' % table._dbt)
            self.file_close(tfile)
            if sql_fields != sql_fields_old:
                self.migrate_table(
                    table,
                    sql_fields, sql_fields_old,
                    sql_fields_aux, None,
                    fake_migrate=fake_migrate
                    )
        return query

    def migrate_table(
        self,
        table,
        sql_fields,
        sql_fields_old,
        sql_fields_aux,
        logfile,
        fake_migrate=False,
        ):

        # logfile is deprecated (moved to adapter.log method)
        db = table._db
        db._migrated.append(table._tablename)
        tablename = table._tablename
        def fix(item):
            k,v=item
            if not isinstance(v,dict):
                v=dict(type='unknown',sql=v)
            return k.lower(),v
        # make sure all field names are lower case to avoid
        # migrations because of case cahnge
        sql_fields = dict(map(fix,sql_fields.iteritems()))
        sql_fields_old = dict(map(fix,sql_fields_old.iteritems()))
        sql_fields_aux = dict(map(fix,sql_fields_aux.iteritems()))
        if db._debug:
            logging.debug('migrating %s to %s' % (sql_fields_old,sql_fields))

        keys = sql_fields.keys()
        for key in sql_fields_old:
            if not key in keys:
                keys.append(key)
        new_add = self.concat_add(tablename)

        metadata_change = False
        sql_fields_current = copy.copy(sql_fields_old)
        for key in keys:
            query = None
            if not key in sql_fields_old:
                sql_fields_current[key] = sql_fields[key]
                if self.dbengine in ('postgres',) and \
                   sql_fields[key]['type'].startswith('geometry'):
                    # 'sql' == ftype in sql
                    query = [ sql_fields[key]['sql'] ]
                else:
                    query = ['ALTER TABLE %s ADD %s %s;' % \
                         (tablename, key,
                          sql_fields_aux[key]['sql'].replace(', ', new_add))]
                metadata_change = True
            elif self.dbengine in ('sqlite', 'spatialite'):
                if key in sql_fields:
                    sql_fields_current[key] = sql_fields[key]
                metadata_change = True
            elif not key in sql_fields:
                del sql_fields_current[key]
                ftype = sql_fields_old[key]['type']
                if (self.dbengine in ('postgres',) and
                    ftype.startswith('geometry')):
                    geotype, parms = ftype[:-1].split('(')
                    schema = parms.split(',')[0]
                    query = [ "SELECT DropGeometryColumn ('%(schema)s', "+
                              "'%(table)s', '%(field)s');" %
                              dict(schema=schema, table=tablename, field=key,) ]
                elif self.dbengine in ('firebird',):
                    query = ['ALTER TABLE %s DROP %s;' % (tablename, key)]
                else:
                    query = ['ALTER TABLE %s DROP COLUMN %s;' %
                             (tablename, key)]
                metadata_change = True
            elif sql_fields[key]['sql'] != sql_fields_old[key]['sql'] \
                  and not (key in table.fields and
                           isinstance(table[key].type, SQLCustomType)) \
                  and not sql_fields[key]['type'].startswith('reference')\
                  and not sql_fields[key]['type'].startswith('double')\
                  and not sql_fields[key]['type'].startswith('id'):
                sql_fields_current[key] = sql_fields[key]
                t = tablename
                tt = sql_fields_aux[key]['sql'].replace(', ', new_add)
                if self.dbengine in ('firebird',):
                    drop_expr = 'ALTER TABLE %s DROP %s;'
                else:
                    drop_expr = 'ALTER TABLE %s DROP COLUMN %s;'
                key_tmp = key + '__tmp'
                query = ['ALTER TABLE %s ADD %s %s;' % (t, key_tmp, tt),
                         'UPDATE %s SET %s=%s;' % (t, key_tmp, key),
                         drop_expr % (t, key),
                         'ALTER TABLE %s ADD %s %s;' % (t, key, tt),
                         'UPDATE %s SET %s=%s;' % (t, key, key_tmp),
                         drop_expr % (t, key_tmp)]
                metadata_change = True
            elif sql_fields[key]['type'] != sql_fields_old[key]['type']:
                sql_fields_current[key] = sql_fields[key]
                metadata_change = True

            if query:
                self.log('timestamp: %s\n'
                    % datetime.datetime.today().isoformat(), table)
                db['_lastsql'] = '\n'.join(query)
                for sub_query in query:
                    self.log(sub_query + '\n', table)
                    if fake_migrate:
                        if db._adapter.commit_on_alter_table:
                            self.save_dbt(table,sql_fields_current)
                        self.log('faked!\n', table)
                    else:
                        self.execute(sub_query)
                        # Caveat: mysql, oracle and firebird
                        # do not allow multiple alter table
                        # in one transaction so we must commit
                        # partial transactions and
                        # update table._dbt after alter table.
                        if db._adapter.commit_on_alter_table:
                            db.commit()
                            self.save_dbt(table,sql_fields_current)
                            self.log('success!\n', table)

            elif metadata_change:
                self.save_dbt(table,sql_fields_current)

        if metadata_change and not (query and db._adapter.commit_on_alter_table):
            db.commit()
            self.save_dbt(table,sql_fields_current)
            self.log('success!\n', table)

    def save_dbt(self,table, sql_fields_current):
        tfile = self.file_open(table._dbt, 'w')
        pickle.dump(sql_fields_current, tfile)
        self.file_close(tfile)

    def LOWER(self, first):
        return 'LOWER(%s)' % self.expand(first)

    def UPPER(self, first):
        return 'UPPER(%s)' % self.expand(first)

    def COUNT(self, first, distinct=None):
        return ('COUNT(%s)' if not distinct else 'COUNT(DISTINCT %s)') \
            % self.expand(first)

    def EXTRACT(self, first, what):
        return "EXTRACT(%s FROM %s)" % (what, self.expand(first))

    def EPOCH(self, first):
        return self.EXTRACT(first, 'epoch')

    def LENGTH(self, first):
        return "LENGTH(%s)" % self.expand(first)

    def AGGREGATE(self, first, what):
        return "%s(%s)" % (what, self.expand(first))

    def JOIN(self):
        return 'JOIN'

    def LEFT_JOIN(self):
        return 'LEFT JOIN'

    def RANDOM(self):
        return 'Random()'

    def NOT_NULL(self, default, field_type):
        return 'NOT NULL DEFAULT %s' % self.represent(default,field_type)

    def COALESCE(self, first, second):
        expressions = [self.expand(first)]+[self.expand(e) for e in second]
        return 'COALESCE(%s)' % ','.join(expressions)

    def COALESCE_ZERO(self, first):
        return 'COALESCE(%s,0)' % self.expand(first)

    def RAW(self, first):
        return first

    def ALLOW_NULL(self):
        return ''

    def SUBSTRING(self, field, parameters):
        return 'SUBSTR(%s,%s,%s)' % (self.expand(field), parameters[0], parameters[1])

    def PRIMARY_KEY(self, key):
        return 'PRIMARY KEY(%s)' % key

    def _drop(self, table, mode):
        table_rname = table._rname or table
        return ['DROP TABLE %s;' % table_rname]

    def drop(self, table, mode=''):
        db = table._db
        queries = self._drop(table, mode)
        for query in queries:
            if table._dbt:
                self.log(query + '\n', table)
            self.execute(query)
        db.commit()
        del db[table._tablename]
        del db.tables[db.tables.index(table._tablename)]
        db._remove_references_to(table)
        if table._dbt:
            self.file_delete(table._dbt)
            self.log('success!\n', table)

    def _insert(self, table, fields):
        table_rname = table._rname or table
        if fields:
            keys = ','.join(f._rname or f.name for f, v in fields)
            values = ','.join(self.expand(v, f.type) for f, v in fields)
            return 'INSERT INTO %s(%s) VALUES (%s);' % (table_rname, keys, values)
        else:
            return self._insert_empty(table)

    def _insert_empty(self, table):
        table_rname = table._rname or table
        return 'INSERT INTO %s DEFAULT VALUES;' % table_rname

    def insert(self, table, fields):
        query = self._insert(table,fields)
        try:
            self.execute(query)
        except Exception:
            e = sys.exc_info()[1]
            if hasattr(table,'_on_insert_error'):
                return table._on_insert_error(table,fields,e)
            raise e
        if hasattr(table,'_primarykey'):
            return dict([(k[0].name, k[1]) for k in fields \
                             if k[0].name in table._primarykey])
        id = self.lastrowid(table)
        if not isinstance(id, (int, long)):
            return id
        rid = Reference(id)
        (rid._table, rid._record) = (table, None)
        return rid

    def bulk_insert(self, table, items):
        return [self.insert(table,item) for item in items]

    def NOT(self, first):
        return '(NOT %s)' % self.expand(first)

    def AND(self, first, second):
        return '(%s AND %s)' % (self.expand(first), self.expand(second))

    def OR(self, first, second):
        return '(%s OR %s)' % (self.expand(first), self.expand(second))

    def BELONGS(self, first, second):
        if isinstance(second, str):
            return '(%s IN (%s))' % (self.expand(first), second[:-1])
        if not second:
            return '(1=0)'
        items = ','.join(self.expand(item, first.type) for item in second)
        return '(%s IN (%s))' % (self.expand(first), items)

    def REGEXP(self, first, second):
        "regular expression operator"
        raise NotImplementedError

    def LIKE(self, first, second):
        "case sensitive like operator"
        raise NotImplementedError

    def ILIKE(self, first, second):
        "case in-sensitive like operator"
        return '(%s LIKE %s)' % (self.expand(first),
                                 self.expand(second, 'string'))

    def STARTSWITH(self, first, second):
        return '(%s LIKE %s)' % (self.expand(first),
                                 self.expand(second+'%', 'string'))

    def ENDSWITH(self, first, second):
        return '(%s LIKE %s)' % (self.expand(first),
                                 self.expand('%'+second, 'string'))

    def CONTAINS(self,first,second,case_sensitive=False):
        if first.type in ('string','text', 'json'):
            if isinstance(second,Expression):
                second = Expression(None,self.CONCAT('%',Expression(
                            None,self.REPLACE(second,('%','%%'))),'%'))
            else:
                second = '%'+str(second).replace('%','%%')+'%'
        elif first.type.startswith('list:'):
            if isinstance(second,Expression):
                second = Expression(None,self.CONCAT(
                        '%|',Expression(None,self.REPLACE(
                                Expression(None,self.REPLACE(
                                        second,('%','%%'))),('|','||'))),'|%'))
            else:
                second = '%|'+str(second).replace('%','%%')\
                    .replace('|','||')+'|%'
        op = case_sensitive and self.LIKE or self.ILIKE
        return op(first,second)

    def EQ(self, first, second=None):
        if second is None:
            return '(%s IS NULL)' % self.expand(first)
        return '(%s = %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def NE(self, first, second=None):
        if second is None:
            return '(%s IS NOT NULL)' % self.expand(first)
        return '(%s <> %s)' % (self.expand(first),
                               self.expand(second, first.type))

    def LT(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s < None" % first)
        return '(%s < %s)' % (self.expand(first),
                              self.expand(second,first.type))

    def LE(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s <= None" % first)
        return '(%s <= %s)' % (self.expand(first),
                               self.expand(second,first.type))

    def GT(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s > None" % first)
        return '(%s > %s)' % (self.expand(first),
                              self.expand(second,first.type))

    def GE(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s >= None" % first)
        return '(%s >= %s)' % (self.expand(first),
                               self.expand(second,first.type))

    def is_numerical_type(self, ftype):
        return ftype in ('integer','boolean','double','bigint') or \
            ftype.startswith('decimal')

    def REPLACE(self, first, (second, third)):
        return 'REPLACE(%s,%s,%s)' % (self.expand(first,'string'),
                                      self.expand(second,'string'),
                                      self.expand(third,'string'))

    def CONCAT(self, *items):
        return '(%s)' % ' || '.join(self.expand(x,'string') for x in items)

    def ADD(self, first, second):
        if self.is_numerical_type(first.type):
            return '(%s + %s)' % (self.expand(first),
                                  self.expand(second, first.type))
        else:
            return self.CONCAT(first, second)

    def SUB(self, first, second):
        return '(%s - %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def MUL(self, first, second):
        return '(%s * %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def DIV(self, first, second):
        return '(%s / %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def MOD(self, first, second):
        return '(%s %% %s)' % (self.expand(first),
                               self.expand(second, first.type))

    def AS(self, first, second):
        return '%s AS %s' % (self.expand(first), second)

    def ON(self, first, second):
        table_rname = first._ot and first or first._rname or first._tablename
        if use_common_filters(second):
            second = self.common_filter(second,[first._tablename])
        return '%s ON %s' % (self.expand(table_rname), self.expand(second))

    def INVERT(self, first):
        return '%s DESC' % self.expand(first)

    def COMMA(self, first, second):
        return '%s, %s' % (self.expand(first), self.expand(second))

    def CAST(self, first, second):
        return 'CAST(%s AS %s)' % (first, second)

    def expand(self, expression, field_type=None, colnames=False):
        if isinstance(expression, Field):
            et = expression.table
            if not colnames:
                table_rname = et._ot and et._tablename or et._rname or et._tablename
            else:
                table_rname = et._tablename
            if not colnames:
                out = '%s.%s' % (table_rname, expression._rname or expression.name)
            else:
                out = '%s.%s' % (table_rname, expression.name)
            if field_type == 'string' and not expression.type in (
                'string','text','json','password'):
                out = self.CAST(out, self.types['text'])
            return out
        elif isinstance(expression, (Expression, Query)):
            first = expression.first
            second = expression.second
            op = expression.op
            optional_args = expression.optional_args or {}
            if not second is None:
                out = op(first, second, **optional_args)
            elif not first is None:
                out = op(first,**optional_args)
            elif isinstance(op, str):
                if op.endswith(';'):
                    op=op[:-1]
                out = '(%s)' % op
            else:
                out = op()
            return out
        elif field_type:
            return str(self.represent(expression,field_type))
        elif isinstance(expression,(list,tuple)):
            return ','.join(self.represent(item,field_type) \
                                for item in expression)
        elif isinstance(expression, bool):
            return '1' if expression else '0'
        else:
            return str(expression)

    def table_alias(self,name):
        if not isinstance(name, Table):
            name = self.db[name]._rname or self.db[name]
        return str(name)

    def alias(self, table, alias):
        """
        Given a table object, makes a new table object
        with alias name.
        """
        other = copy.copy(table)
        other['_ot'] = other._ot or other._rname or other._tablename
        other['ALL'] = SQLALL(other)
        other['_tablename'] = alias
        for fieldname in other.fields:
            other[fieldname] = copy.copy(other[fieldname])
            other[fieldname]._tablename = alias
            other[fieldname].tablename = alias
            other[fieldname].table = other
        table._db[alias] = other
        return other

    def _truncate(self, table, mode=''):
        tablename = table._rname or table._tablename
        return ['TRUNCATE TABLE %s %s;' % (tablename, mode or '')]

    def truncate(self, table, mode= ' '):
        # Prepare functions "write_to_logfile" and "close_logfile"
        try:
            queries = table._db._adapter._truncate(table, mode)
            for query in queries:
                self.log(query + '\n', table)
                self.execute(query)
            self.log('success!\n', table)
        finally:
            pass

    def _update(self, tablename, query, fields):
        if query:
            if use_common_filters(query):
                query = self.common_filter(query, [tablename])
            sql_w = ' WHERE ' + self.expand(query)
        else:
            sql_w = ''
        sql_v = ','.join(['%s=%s' % (field._rname or field.name,
                                     self.expand(value, field.type)) \
                              for (field, value) in fields])
        tablename = "%s" % (self.db[tablename]._rname or tablename)
        return 'UPDATE %s SET %s%s;' % (tablename, sql_v, sql_w)

    def update(self, tablename, query, fields):
        sql = self._update(tablename, query, fields)
        try:
            self.execute(sql)
        except Exception:
            e = sys.exc_info()[1]
            table = self.db[tablename]
            if hasattr(table,'_on_update_error'):
                return table._on_update_error(table,query,fields,e)
            raise e
        try:
            return self.cursor.rowcount
        except:
            return None

    def _delete(self, tablename, query):
        if query:
            if use_common_filters(query):
                query = self.common_filter(query, [tablename])
            sql_w = ' WHERE ' + self.expand(query)
        else:
            sql_w = ''
        tablename = '%s' % (self.db[tablename]._rname or tablename)
        return 'DELETE FROM %s%s;' % (tablename, sql_w)

    def delete(self, tablename, query):
        sql = self._delete(tablename, query)
        ### special code to handle CASCADE in SQLite & SpatiaLite
        db = self.db
        table = db[tablename]
        if self.dbengine in ('sqlite', 'spatialite') and table._referenced_by:
            deleted = [x[table._id.name] for x in db(query).select(table._id)]
        ### end special code to handle CASCADE in SQLite & SpatiaLite
        self.execute(sql)
        try:
            counter = self.cursor.rowcount
        except:
            counter =  None
        ### special code to handle CASCADE in SQLite & SpatiaLite
        if self.dbengine in ('sqlite', 'spatialite') and counter:
            for field in table._referenced_by:
                if field.type=='reference '+table._tablename \
                        and field.ondelete=='CASCADE':
                    db(field.belongs(deleted)).delete()
        ### end special code to handle CASCADE in SQLite & SpatiaLite
        return counter

    def get_table(self, query):
        tablenames = self.tables(query)
        if len(tablenames)==1:
            return tablenames[0]
        elif len(tablenames)<1:
            raise RuntimeError("No table selected")
        else:
            raise RuntimeError("Too many tables selected")

    def expand_all(self, fields, tablenames):
        db = self.db
        new_fields = []
        append = new_fields.append
        for item in fields:
            if isinstance(item,SQLALL):
                new_fields += item._table
            elif isinstance(item,str):
                if REGEX_TABLE_DOT_FIELD.match(item):
                    tablename,fieldname = item.split('.')
                    append(db[tablename][fieldname])
                else:
                    append(Expression(db,lambda item=item:item))
            else:
                append(item)
        # ## if no fields specified take them all from the requested tables
        if not new_fields:
            for table in tablenames:
                for field in db[table]:
                    append(field)
        return new_fields

    def _select(self, query, fields, attributes):
        tables = self.tables
        for key in set(attributes.keys())-SELECT_ARGS:
            raise SyntaxError('invalid select attribute: %s' % key)
        args_get = attributes.get
        tablenames = tables(query)
        tablenames_for_common_filters = tablenames
        for field in fields:
            if isinstance(field, basestring) \
                    and REGEX_TABLE_DOT_FIELD.match(field):
                tn,fn = field.split('.')
                field = self.db[tn][fn]
            for tablename in tables(field):
                if not tablename in tablenames:
                    tablenames.append(tablename)

        if len(tablenames) < 1:
            raise SyntaxError('Set: no tables selected')
        def colexpand(field):
            return self.expand(field, colnames=True)
        self._colnames = map(colexpand, fields)
        def geoexpand(field):
            if isinstance(field.type,str) and field.type.startswith('geometry') and isinstance(field, Field):
                field = field.st_astext()
            return self.expand(field)
        sql_f = ', '.join(map(geoexpand, fields))
        sql_o = ''
        sql_s = ''
        left = args_get('left', False)
        inner_join = args_get('join', False)
        distinct = args_get('distinct', False)
        groupby = args_get('groupby', False)
        orderby = args_get('orderby', False)
        having = args_get('having', False)
        limitby = args_get('limitby', False)
        orderby_on_limitby = args_get('orderby_on_limitby', True)
        for_update = args_get('for_update', False)
        if self.can_select_for_update is False and for_update is True:
            raise SyntaxError('invalid select attribute: for_update')
        if distinct is True:
            sql_s += 'DISTINCT'
        elif distinct:
            sql_s += 'DISTINCT ON (%s)' % distinct
        if inner_join:
            icommand = self.JOIN()
            if not isinstance(inner_join, (tuple, list)):
                inner_join = [inner_join]
            ijoint = [t._tablename for t in inner_join
                      if not isinstance(t,Expression)]
            ijoinon = [t for t in inner_join if isinstance(t, Expression)]
            itables_to_merge={} #issue 490
            [itables_to_merge.update(
                    dict.fromkeys(tables(t))) for t in ijoinon]
            ijoinont = [t.first._tablename for t in ijoinon]
            [itables_to_merge.pop(t) for t in ijoinont
             if t in itables_to_merge] #issue 490
            iimportant_tablenames = ijoint + ijoinont + itables_to_merge.keys()
            iexcluded = [t for t in tablenames
                         if not t in iimportant_tablenames]
        if left:
            join = attributes['left']
            command = self.LEFT_JOIN()
            if not isinstance(join, (tuple, list)):
                join = [join]
            joint = [t._tablename for t in join
                     if not isinstance(t, Expression)]
            joinon = [t for t in join if isinstance(t, Expression)]
            #patch join+left patch (solves problem with ordering in left joins)
            tables_to_merge={}
            [tables_to_merge.update(
                    dict.fromkeys(tables(t))) for t in joinon]
            joinont = [t.first._tablename for t in joinon]
            [tables_to_merge.pop(t) for t in joinont if t in tables_to_merge]
            tablenames_for_common_filters = [t for t in tablenames
                        if not t in joinont ]
            important_tablenames = joint + joinont + tables_to_merge.keys()
            excluded = [t for t in tablenames
                        if not t in important_tablenames ]
        else:
            excluded = tablenames

        if use_common_filters(query):
            query = self.common_filter(query,tablenames_for_common_filters)
        sql_w = ' WHERE ' + self.expand(query) if query else ''

        if inner_join and not left:
            sql_t = ', '.join([self.table_alias(t) for t in iexcluded + \
                                   itables_to_merge.keys()])
            for t in ijoinon:
                sql_t += ' %s %s' % (icommand, t)
        elif not inner_join and left:
            sql_t = ', '.join([self.table_alias(t) for t in excluded + \
                                   tables_to_merge.keys()])
            if joint:
                sql_t += ' %s %s' % (command,
                                     ','.join([self.table_alias(t) for t in joint]))
            for t in joinon:
                sql_t += ' %s %s' % (command, t)
        elif inner_join and left:
            all_tables_in_query = set(important_tablenames + \
                                      iimportant_tablenames + \
                                      tablenames)
            tables_in_joinon = set(joinont + ijoinont)
            tables_not_in_joinon = \
                all_tables_in_query.difference(tables_in_joinon)
            sql_t = ','.join([self.table_alias(t) for t in tables_not_in_joinon])
            for t in ijoinon:
                sql_t += ' %s %s' % (icommand, t)
            if joint:
                sql_t += ' %s %s' % (command,
                                     ','.join([self.table_alias(t) for t in joint]))
            for t in joinon:
                sql_t += ' %s %s' % (command, t)
        else:
            sql_t = ', '.join(self.table_alias(t) for t in tablenames)
        if groupby:
            if isinstance(groupby, (list, tuple)):
                groupby = xorify(groupby)
            sql_o += ' GROUP BY %s' % self.expand(groupby)
            if having:
                sql_o += ' HAVING %s' % attributes['having']
        if orderby:
            if isinstance(orderby, (list, tuple)):
                orderby = xorify(orderby)
            if str(orderby) == '<random>':
                sql_o += ' ORDER BY %s' % self.RANDOM()
            else:
                sql_o += ' ORDER BY %s' % self.expand(orderby)
        if (limitby and not groupby and tablenames and orderby_on_limitby and not orderby):
            sql_o += ' ORDER BY %s' % ', '.join(
                ['%s.%s'%(t,x) for t in tablenames for x in (
                    hasattr(self.db[t],'_primarykey') and self.db[t]._primarykey
                    or [self.db[t]._id._rname or self.db[t]._id.name]
                    )
                 ]
                )
        # oracle does not support limitby
        sql = self.select_limitby(sql_s, sql_f, sql_t, sql_w, sql_o, limitby)
        if for_update and self.can_select_for_update is True:
            sql = sql.rstrip(';') + ' FOR UPDATE;'
        return sql

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_o += ' LIMIT %i OFFSET %i' % (lmax - lmin, lmin)
        return 'SELECT %s %s FROM %s%s%s;' % \
            (sql_s, sql_f, sql_t, sql_w, sql_o)

    def _fetchall(self):
        return self.cursor.fetchall()

    def _select_aux(self,sql,fields,attributes):
        args_get = attributes.get
        cache = args_get('cache',None)
        if not cache:
            self.execute(sql)
            rows = self._fetchall()
        else:
            (cache_model, time_expire) = cache
            key = self.uri + '/' + sql + '/rows'
            if len(key)>200: key = hashlib_md5(key).hexdigest()
            def _select_aux2():
                self.execute(sql)
                return self._fetchall()
            rows = cache_model(key,_select_aux2,time_expire)
        if isinstance(rows,tuple):
            rows = list(rows)
        limitby = args_get('limitby', None) or (0,)
        rows = self.rowslice(rows,limitby[0],None)
        processor = args_get('processor',self.parse)
        cacheable = args_get('cacheable',False)
        return processor(rows,fields,self._colnames,cacheable=cacheable)

    def select(self, query, fields, attributes):
        """
        Always returns a Rows object, possibly empty.
        """
        sql = self._select(query, fields, attributes)
        cache = attributes.get('cache', None)
        if cache and attributes.get('cacheable',False):
            del attributes['cache']
            (cache_model, time_expire) = cache
            key = self.uri + '/' + sql
            if len(key)>200: key = hashlib_md5(key).hexdigest()
            args = (sql,fields,attributes)
            return cache_model(
                key,
                lambda self=self,args=args:self._select_aux(*args),
                time_expire)
        else:
            return self._select_aux(sql,fields,attributes)

    def _count(self, query, distinct=None):
        tablenames = self.tables(query)
        if query:
            if use_common_filters(query):
                query = self.common_filter(query, tablenames)
            sql_w = ' WHERE ' + self.expand(query)
        else:
            sql_w = ''
        sql_t = ','.join(self.table_alias(t) for t in tablenames)
        if distinct:
            if isinstance(distinct,(list, tuple)):
                distinct = xorify(distinct)
            sql_d = self.expand(distinct)
            return 'SELECT count(DISTINCT %s) FROM %s%s;' % \
                (sql_d, sql_t, sql_w)
        return 'SELECT count(*) FROM %s%s;' % (sql_t, sql_w)

    def count(self, query, distinct=None):
        self.execute(self._count(query, distinct))
        return self.cursor.fetchone()[0]

    def tables(self, *queries):
        tables = set()
        for query in queries:
            if isinstance(query, Field):
                tables.add(query.tablename)
            elif isinstance(query, (Expression, Query)):
                if not query.first is None:
                    tables = tables.union(self.tables(query.first))
                if not query.second is None:
                    tables = tables.union(self.tables(query.second))
        return list(tables)

    def commit(self):
        if self.connection:
            return self.connection.commit()

    def rollback(self):
        if self.connection:
            return self.connection.rollback()

    def close_connection(self):
        if self.connection:
            r = self.connection.close()
            self.connection = None
            return r

    def distributed_transaction_begin(self, key):
        return

    def prepare(self, key):
        if self.connection: self.connection.prepare()

    def commit_prepared(self, key):
        if self.connection: self.connection.commit()

    def rollback_prepared(self, key):
        if self.connection: self.connection.rollback()

    def concat_add(self, tablename):
        return ', ADD '

    def constraint_name(self, table, fieldname):
        return '%s_%s__constraint' % (table,fieldname)

    def create_sequence_and_triggers(self, query, table, **args):
        self.execute(query)

    def log_execute(self, *a, **b):
        if not self.connection: return None
        command = a[0]
        if hasattr(self,'filter_sql_command'):
            command = self.filter_sql_command(command)
        if self.db._debug:
            LOGGER.debug('SQL: %s' % command)
        self.db._lastsql = command
        t0 = time.time()
        ret = self.cursor.execute(command, *a[1:], **b)
        self.db._timings.append((command,time.time()-t0))
        del self.db._timings[:-TIMINGSSIZE]
        return ret

    def execute(self, *a, **b):
        return self.log_execute(*a, **b)

    def represent(self, obj, fieldtype):
        field_is_type = fieldtype.startswith
        if isinstance(obj, CALLABLETYPES):
            obj = obj()
        if isinstance(fieldtype, SQLCustomType):
            value = fieldtype.encoder(obj)
            if fieldtype.type in ('string','text', 'json'):
                return self.adapt(value)
            return value
        if isinstance(obj, (Expression, Field)):
            return str(obj)
        if field_is_type('list:'):
            if not obj:
                obj = []
            elif not isinstance(obj, (list, tuple)):
                obj = [obj]
            if field_is_type('list:string'):
                obj = map(str,obj)
            else:
                obj = map(int,[o for o in obj if o != ''])
        # we don't want to bar_encode json objects
        if isinstance(obj, (list, tuple)) and (not fieldtype == "json"):
            obj = bar_encode(obj)
        if obj is None:
            return 'NULL'
        if obj == '' and not fieldtype[:2] in ['st', 'te', 'js', 'pa', 'up']:
            return 'NULL'
        r = self.represent_exceptions(obj, fieldtype)
        if not r is None:
            return r
        if fieldtype == 'boolean':
            if obj and not str(obj)[:1].upper() in '0F':
                return self.smart_adapt(self.TRUE)
            else:
                return self.smart_adapt(self.FALSE)
        if fieldtype == 'id' or fieldtype == 'integer':
            return str(long(obj))
        if field_is_type('decimal'):
            return str(obj)
        elif field_is_type('reference'): # reference
            if fieldtype.find('.')>0:
                return repr(obj)
            elif isinstance(obj, (Row, Reference)):
                return str(obj['id'])
            return str(long(obj))
        elif fieldtype == 'double':
            return repr(float(obj))
        if isinstance(obj, unicode):
            obj = obj.encode(self.db_codec)
        if fieldtype == 'blob':
            obj = base64.b64encode(str(obj))
        elif fieldtype == 'date':
            if isinstance(obj, (datetime.date, datetime.datetime)):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
        elif fieldtype == 'datetime':
            if isinstance(obj, datetime.datetime):
                obj = obj.isoformat(self.T_SEP)[:19]
            elif isinstance(obj, datetime.date):
                obj = obj.isoformat()[:10]+self.T_SEP+'00:00:00'
            else:
                obj = str(obj)
        elif fieldtype == 'time':
            if isinstance(obj, datetime.time):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
        elif fieldtype == 'json':
            if not self.native_json:
                if have_serializers:
                    obj = serializers.json(obj)
                elif simplejson:
                    obj = simplejson.dumps(obj)
                else:
                    raise RuntimeError("missing simplejson")
        if not isinstance(obj,bytes):
            obj = bytes(obj)
        try:
            obj.decode(self.db_codec)
        except:
            obj = obj.decode('latin1').encode(self.db_codec)
        return self.adapt(obj)

    def represent_exceptions(self, obj, fieldtype):
        return None

    def lastrowid(self, table):
        return None

    def rowslice(self, rows, minimum=0, maximum=None):
        """
        By default this function does nothing;
        overload when db does not do slicing.
        """
        return rows

    def parse_value(self, value, field_type, blob_decode=True):
        if field_type != 'blob' and isinstance(value, str):
            try:
                value = value.decode(self.db._db_codec)
            except Exception:
                pass
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        if isinstance(field_type, SQLCustomType):
            value = field_type.decoder(value)
        if not isinstance(field_type, str) or value is None:
            return value
        elif field_type in ('string', 'text', 'password', 'upload', 'dict'):
            return value
        elif field_type.startswith('geo'):
            return value
        elif field_type == 'blob' and not blob_decode:
            return value
        else:
            key = REGEX_TYPE.match(field_type).group(0)
            return self.parsemap[key](value,field_type)

    def parse_reference(self, value, field_type):
        referee = field_type[10:].strip()
        if not '.' in referee:
            value = Reference(value)
            value._table, value._record = self.db[referee], None
        return value

    def parse_boolean(self, value, field_type):
        return value == self.TRUE or str(value)[:1].lower() == 't'

    def parse_date(self, value, field_type):
        if isinstance(value, datetime.datetime):
            return value.date()
        if not isinstance(value, (datetime.date,datetime.datetime)):
            (y, m, d) = map(int, str(value)[:10].strip().split('-'))
            value = datetime.date(y, m, d)
        return value

    def parse_time(self, value, field_type):
        if not isinstance(value, datetime.time):
            time_items = map(int,str(value)[:8].strip().split(':')[:3])
            if len(time_items) == 3:
                (h, mi, s) = time_items
            else:
                (h, mi, s) = time_items + [0]
            value = datetime.time(h, mi, s)
        return value

    def parse_datetime(self, value, field_type):
        if not isinstance(value, datetime.datetime):
            value = str(value)
            date_part,time_part,timezone = value[:10],value[11:19],value[19:]
            if '+' in timezone:
                ms,tz = timezone.split('+')
                h,m = tz.split(':')
                dt = datetime.timedelta(seconds=3600*int(h)+60*int(m))
            elif '-' in timezone:
                ms,tz = timezone.split('-')
                h,m = tz.split(':')
                dt = -datetime.timedelta(seconds=3600*int(h)+60*int(m))
            else:
                dt = None
            (y, m, d) = map(int,date_part.split('-'))
            time_parts = time_part and time_part.split(':')[:3] or (0,0,0)
            while len(time_parts)<3: time_parts.append(0)
            time_items = map(int,time_parts)
            (h, mi, s) = time_items
            value = datetime.datetime(y, m, d, h, mi, s)
            if dt:
                value = value + dt
        return value

    def parse_blob(self, value, field_type):
        return base64.b64decode(str(value))

    def parse_decimal(self, value, field_type):
        decimals = int(field_type[8:-1].split(',')[-1])
        if self.dbengine in ('sqlite', 'spatialite'):
            value = ('%.' + str(decimals) + 'f') % value
        if not isinstance(value, decimal.Decimal):
            value = decimal.Decimal(str(value))
        return value

    def parse_list_integers(self, value, field_type):
        if not isinstance(self, NoSQLAdapter):
            value = bar_decode_integer(value)
        return value

    def parse_list_references(self, value, field_type):
        if not isinstance(self, NoSQLAdapter):
            value = bar_decode_integer(value)
        return [self.parse_reference(r, field_type[5:]) for r in value]

    def parse_list_strings(self, value, field_type):
        if not isinstance(self, NoSQLAdapter):
            value = bar_decode_string(value)
        return value

    def parse_id(self, value, field_type):
        return long(value)

    def parse_integer(self, value, field_type):
        return long(value)

    def parse_double(self, value, field_type):
        return float(value)

    def parse_json(self, value, field_type):
        if not self.native_json:
            if not isinstance(value, basestring):
                raise RuntimeError('json data not a string')
            if isinstance(value, unicode):
                value = value.encode('utf-8')
            if have_serializers:
                value = serializers.loads_json(value)
            elif simplejson:
                value = simplejson.loads(value)
            else:
                raise RuntimeError("missing simplejson")
        return value

    def build_parsemap(self):
        self.parsemap = {
            'id':self.parse_id,
            'integer':self.parse_integer,
            'bigint':self.parse_integer,
            'float':self.parse_double,
            'double':self.parse_double,
            'reference':self.parse_reference,
            'boolean':self.parse_boolean,
            'date':self.parse_date,
            'time':self.parse_time,
            'datetime':self.parse_datetime,
            'blob':self.parse_blob,
            'decimal':self.parse_decimal,
            'json':self.parse_json,
            'list:integer':self.parse_list_integers,
            'list:reference':self.parse_list_references,
            'list:string':self.parse_list_strings,
            }

    def parse(self, rows, fields, colnames, blob_decode=True,
              cacheable = False):
        db = self.db
        virtualtables = []
        new_rows = []
        tmps = []
        for colname in colnames:
            if not REGEX_TABLE_DOT_FIELD.match(colname):
                tmps.append(None)
            else:
                (tablename, _the_sep_, fieldname) = colname.partition('.')
                table = db[tablename]
                field = table[fieldname]
                ft = field.type
                tmps.append((tablename,fieldname,table,field,ft))
        for (i,row) in enumerate(rows):
            new_row = Row()
            for (j,colname) in enumerate(colnames):
                value = row[j]
                tmp = tmps[j]
                if tmp:
                    (tablename,fieldname,table,field,ft) = tmp
                    if tablename in new_row:
                        colset = new_row[tablename]
                    else:
                        colset = new_row[tablename] = Row()
                        if tablename not in virtualtables:
                            virtualtables.append(tablename)
                    value = self.parse_value(value,ft,blob_decode)
                    if field.filter_out:
                        value = field.filter_out(value)
                    colset[fieldname] = value

                    # for backward compatibility
                    if ft=='id' and fieldname!='id' and \
                            not 'id' in table.fields:
                        colset['id'] = value

                    if ft == 'id' and not cacheable:
                        # temporary hack to deal with
                        # GoogleDatastoreAdapter
                        # references
                        if isinstance(self, GoogleDatastoreAdapter):
                            id = value.key.id() if self.use_ndb else value.key().id_or_name()
                            colset[fieldname] = id
                            colset.gae_item = value
                        else:
                            id = value
                        colset.update_record = RecordUpdater(colset,table,id)
                        colset.delete_record = RecordDeleter(table,id)
                        if table._db._lazy_tables:
                            colset['__get_lazy_reference__'] = LazyReferenceGetter(table, id)
                        for rfield in table._referenced_by:
                            referee_link = db._referee_name and \
                                db._referee_name % dict(
                                table=rfield.tablename,field=rfield.name)
                            if referee_link and not referee_link in colset:
                                colset[referee_link] = LazySet(rfield,id)
                else:
                    if not '_extra' in new_row:
                        new_row['_extra'] = Row()
                    new_row['_extra'][colname] = \
                        self.parse_value(value,
                                         fields[j].type,blob_decode)
                    new_column_name = \
                        REGEX_SELECT_AS_PARSER.search(colname)
                    if not new_column_name is None:
                        column_name = new_column_name.groups(0)
                        setattr(new_row,column_name[0],value)
            new_rows.append(new_row)
        rowsobj = Rows(db, new_rows, colnames, rawrows=rows)


        for tablename in virtualtables:
            table = db[tablename]
            fields_virtual = [(f,v) for (f,v) in table.iteritems()
                              if isinstance(v,FieldVirtual)]
            fields_lazy = [(f,v) for (f,v) in table.iteritems()
                           if isinstance(v,FieldMethod)]
            if fields_virtual or fields_lazy:
                for row in rowsobj.records:
                    box = row[tablename]
                    for f,v in fields_virtual:
                        try:
                            box[f] = v.f(row)
                        except AttributeError:
                            pass # not enough fields to define virtual field
                    for f,v in fields_lazy:
                        try:
                            box[f] = (v.handler or VirtualCommand)(v.f,row)
                        except AttributeError:
                            pass # not enough fields to define virtual field

            ### old style virtual fields
            for item in table.virtualfields:
                try:
                    rowsobj = rowsobj.setvirtualfields(**{tablename:item})
                except (KeyError, AttributeError):
                    # to avoid breaking virtualfields when partial select
                    pass
        return rowsobj

    def common_filter(self, query, tablenames):
        tenant_fieldname = self.db._request_tenant

        for tablename in tablenames:
            table = self.db[tablename]

            # deal with user provided filters
            if table._common_filter != None:
                query = query & table._common_filter(query)

            # deal with multi_tenant filters
            if tenant_fieldname in table:
                default = table[tenant_fieldname].default
                if not default is None:
                    newquery = table[tenant_fieldname] == default
                    if query is None:
                        query = newquery
                    else:
                        query = query & newquery
        return query

    def CASE(self,query,t,f):
        def represent(x):
            types = {type(True):'boolean',type(0):'integer',type(1.0):'double'}
            if x is None: return 'NULL'
            elif isinstance(x,Expression): return str(x)
            else: return self.represent(x,types.get(type(x),'string'))
        return Expression(self.db,'CASE WHEN %s THEN %s ELSE %s END' % \
                              (self.expand(query),represent(t),represent(f)))

###################################################################################
# List of all the available adapters; they all extend BaseAdapter.
###################################################################################

class SQLiteAdapter(BaseAdapter):
    drivers = ('sqlite2','sqlite3')

    can_select_for_update = None    # support ourselves with BEGIN TRANSACTION

    def EXTRACT(self,field,what):
        return "web2py_extract('%s',%s)" % (what, self.expand(field))

    @staticmethod
    def web2py_extract(lookup, s):
        table = {
            'year': (0, 4),
            'month': (5, 7),
            'day': (8, 10),
            'hour': (11, 13),
            'minute': (14, 16),
            'second': (17, 19),
            }
        try:
            if lookup != 'epoch':
                (i, j) = table[lookup]
                return int(s[i:j])
            else:
                return time.mktime(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S').timetuple())
        except:
            return None

    @staticmethod
    def web2py_regexp(expression, item):
        return re.compile(expression).search(item) is not None

    def __init__(self, db, uri, pool_size=0, folder=None, db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "sqlite"
        self.uri = uri
        self.adapter_args = adapter_args
        if do_connect: self.find_driver(adapter_args)
        self.pool_size = 0
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        path_encoding = sys.getfilesystemencoding() \
            or locale.getdefaultlocale()[1] or 'utf8'
        if uri.startswith('sqlite:memory'):
            self.dbpath = ':memory:'
        else:
            self.dbpath = uri.split('://',1)[1]
            if self.dbpath[0] != '/':
                if PYTHON_VERSION[0] == 2:
                    self.dbpath = pjoin(
                        self.folder.decode(path_encoding).encode('utf8'), self.dbpath)
                else:
                    self.dbpath = pjoin(self.folder, self.dbpath)
        if not 'check_same_thread' in driver_args:
            driver_args['check_same_thread'] = False
        if not 'detect_types' in driver_args and do_connect:
            driver_args['detect_types'] = self.driver.PARSE_DECLTYPES
        def connector(dbpath=self.dbpath, driver_args=driver_args):
            return self.driver.Connection(dbpath, **driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.connection.create_function('web2py_extract', 2,
                                        SQLiteAdapter.web2py_extract)
        self.connection.create_function("REGEXP", 2,
                                        SQLiteAdapter.web2py_regexp)

        if self.adapter_args.get('foreign_keys',True):
            self.execute('PRAGMA foreign_keys=ON;')

    def _truncate(self, table, mode=''):
        tablename = table._tablename
        return ['DELETE FROM %s;' % tablename,
                "DELETE FROM sqlite_sequence WHERE name='%s';" % tablename]

    def lastrowid(self, table):
        return self.cursor.lastrowid

    def REGEXP(self,first,second):
        return '(%s REGEXP %s)' % (self.expand(first),
                                   self.expand(second,'string'))

    def select(self, query, fields, attributes):
        """
        Simulate SELECT ... FOR UPDATE with BEGIN IMMEDIATE TRANSACTION.
        Note that the entire database, rather than one record, is locked
        (it will be locked eventually anyway by the following UPDATE).
        """
        if attributes.get('for_update', False) and not 'cache' in attributes:
            self.execute('BEGIN IMMEDIATE TRANSACTION;')
        return super(SQLiteAdapter, self).select(query, fields, attributes)

class SpatiaLiteAdapter(SQLiteAdapter):
    drivers = ('sqlite3','sqlite2')

    types = copy.copy(BaseAdapter.types)
    types.update(geometry='GEOMETRY')

    def __init__(self, db, uri, pool_size=0, folder=None, db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, srid=4326, after_connection=None):
        self.db = db
        self.dbengine = "spatialite"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args)
        self.pool_size = 0
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        self.srid = srid
        path_encoding = sys.getfilesystemencoding() \
            or locale.getdefaultlocale()[1] or 'utf8'
        if uri.startswith('spatialite:memory'):
            self.dbpath = ':memory:'
        else:
            self.dbpath = uri.split('://',1)[1]
            if self.dbpath[0] != '/':
                self.dbpath = pjoin(
                    self.folder.decode(path_encoding).encode('utf8'), self.dbpath)
        if not 'check_same_thread' in driver_args:
            driver_args['check_same_thread'] = False
        if not 'detect_types' in driver_args and do_connect:
            driver_args['detect_types'] = self.driver.PARSE_DECLTYPES
        def connector(dbpath=self.dbpath, driver_args=driver_args):
            return self.driver.Connection(dbpath, **driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.connection.enable_load_extension(True)
        # for Windows, rename libspatialite-2.dll to libspatialite.dll
        # Linux uses libspatialite.so
        # Mac OS X uses libspatialite.dylib
        libspatialite = SPATIALLIBS[platform.system()]
        self.execute(r'SELECT load_extension("%s");' % libspatialite)

        self.connection.create_function('web2py_extract', 2,
                                        SQLiteAdapter.web2py_extract)
        self.connection.create_function("REGEXP", 2,
                                        SQLiteAdapter.web2py_regexp)

    # GIS functions

    def ST_ASGEOJSON(self, first, second):
        return 'AsGeoJSON(%s,%s,%s)' %(self.expand(first),
            second['precision'], second['options'])

    def ST_ASTEXT(self, first):
        return 'AsText(%s)' %(self.expand(first))

    def ST_CONTAINS(self, first, second):
        return 'Contains(%s,%s)' %(self.expand(first),
                                   self.expand(second, first.type))

    def ST_DISTANCE(self, first, second):
        return 'Distance(%s,%s)' %(self.expand(first),
                                   self.expand(second, first.type))

    def ST_EQUALS(self, first, second):
        return 'Equals(%s,%s)' %(self.expand(first),
                                 self.expand(second, first.type))

    def ST_INTERSECTS(self, first, second):
        return 'Intersects(%s,%s)' %(self.expand(first),
                                     self.expand(second, first.type))

    def ST_OVERLAPS(self, first, second):
        return 'Overlaps(%s,%s)' %(self.expand(first),
                                   self.expand(second, first.type))

    def ST_SIMPLIFY(self, first, second):
        return 'Simplify(%s,%s)' %(self.expand(first),
                                   self.expand(second, 'double'))

    def ST_TOUCHES(self, first, second):
        return 'Touches(%s,%s)' %(self.expand(first),
                                  self.expand(second, first.type))

    def ST_WITHIN(self, first, second):
        return 'Within(%s,%s)' %(self.expand(first),
                                 self.expand(second, first.type))

    def represent(self, obj, fieldtype):
        field_is_type = fieldtype.startswith
        if field_is_type('geo'):
            srid = 4326 # Spatialite default srid for geometry
            geotype, parms = fieldtype[:-1].split('(')
            parms = parms.split(',')
            if len(parms) >= 2:
                schema, srid = parms[:2]
#             if field_is_type('geometry'):
            value = "ST_GeomFromText('%s',%s)" %(obj, srid)
#             elif field_is_type('geography'):
#                 value = "ST_GeogFromText('SRID=%s;%s')" %(srid, obj)
#             else:
#                 raise SyntaxError, 'Invalid field type %s' %fieldtype
            return value
        return BaseAdapter.represent(self, obj, fieldtype)


class JDBCSQLiteAdapter(SQLiteAdapter):
    drivers = ('zxJDBC_sqlite',)

    def __init__(self, db, uri, pool_size=0, folder=None, db_codec='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "sqlite"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        path_encoding = sys.getfilesystemencoding() \
            or locale.getdefaultlocale()[1] or 'utf8'
        if uri.startswith('sqlite:memory'):
            self.dbpath = ':memory:'
        else:
            self.dbpath = uri.split('://',1)[1]
            if self.dbpath[0] != '/':
                self.dbpath = pjoin(
                    self.folder.decode(path_encoding).encode('utf8'), self.dbpath)
        def connector(dbpath=self.dbpath,driver_args=driver_args):
            return self.driver.connect(
                self.driver.getConnection('jdbc:sqlite:'+dbpath),
                **driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        # FIXME http://www.zentus.com/sqlitejdbc/custom_functions.html for UDFs
        self.connection.create_function('web2py_extract', 2,
                                        SQLiteAdapter.web2py_extract)

    def execute(self, a):
        return self.log_execute(a)


class MySQLAdapter(BaseAdapter):
    drivers = ('MySQLdb','pymysql', 'mysqlconnector')

    commit_on_alter_table = True
    support_distributed_transaction = True
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'LONGTEXT',
        'json': 'LONGTEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'LONGBLOB',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'DOUBLE',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'DATETIME',
        'id': 'INT AUTO_INCREMENT NOT NULL',
        'reference': 'INT, INDEX %(index_name)s (%(field_name)s), FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'LONGTEXT',
        'list:string': 'LONGTEXT',
        'list:reference': 'LONGTEXT',
        'big-id': 'BIGINT AUTO_INCREMENT NOT NULL',
        'big-reference': 'BIGINT, INDEX %(index_name)s (%(field_name)s), FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        }

    QUOTE_TEMPLATE = "`%s`"

    def varquote(self,name):
        return varquote_aux(name,'`%s`')

    def RANDOM(self):
        return 'RAND()'

    def SUBSTRING(self,field,parameters):
        return 'SUBSTRING(%s,%s,%s)' % (self.expand(field),
                                        parameters[0], parameters[1])

    def EPOCH(self, first):
        return "UNIX_TIMESTAMP(%s)" % self.expand(first)

    def CONCAT(self, *items):
        return 'CONCAT(%s)' % ','.join(self.expand(x,'string') for x in items)

    def REGEXP(self,first,second):
        return '(%s REGEXP %s)' % (self.expand(first),
                                   self.expand(second,'string'))

    def _drop(self,table,mode):
        # breaks db integrity but without this mysql does not drop table
        table_rname = table._rname or table
        return ['SET FOREIGN_KEY_CHECKS=0;','DROP TABLE %s;' % table_rname,
                'SET FOREIGN_KEY_CHECKS=1;']

    def _insert_empty(self, table):
        return 'INSERT INTO %s VALUES (DEFAULT);' % table

    def distributed_transaction_begin(self,key):
        self.execute('XA START;')

    def prepare(self,key):
        self.execute("XA END;")
        self.execute("XA PREPARE;")

    def commit_prepared(self,ley):
        self.execute("XA COMMIT;")

    def rollback_prepared(self,key):
        self.execute("XA ROLLBACK;")

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>[^?]+)(\?set_encoding=(?P<charset>\w+))?$')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "mysql"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError(
                "Invalid URI string in DAL: %s" % self.uri)
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        port = int(m.group('port') or '3306')
        charset = m.group('charset') or 'utf8'
        driver_args.update(db=db,
                           user=credential_decoder(user),
                           passwd=credential_decoder(password),
                           host=host,
                           port=port,
                           charset=charset)


        def connector(driver_args=driver_args):
            return self.driver.connect(**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.execute('SET FOREIGN_KEY_CHECKS=1;')
        self.execute("SET sql_mode='NO_BACKSLASH_ESCAPES';")

    def lastrowid(self,table):
        self.execute('select last_insert_id();')
        return int(self.cursor.fetchone()[0])


class PostgreSQLAdapter(BaseAdapter):
    drivers = ('psycopg2','pg8000')

    support_distributed_transaction = True
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'TEXT',
        'json': 'TEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BYTEA',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INTEGER',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT8',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'SERIAL PRIMARY KEY',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'TEXT',
        'list:string': 'TEXT',
        'list:reference': 'TEXT',
        'geometry': 'GEOMETRY',
        'geography': 'GEOGRAPHY',
        'big-id': 'BIGSERIAL PRIMARY KEY',
        'big-reference': 'BIGINT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',

        }

    QUOTE_TEMPLATE = '"%s"'

    def varquote(self,name):
        return varquote_aux(name,'"%s"')

    def adapt(self,obj):
        if self.driver_name == 'psycopg2':
            return psycopg2_adapt(obj).getquoted()
        elif self.driver_name == 'pg8000':
            return "'%s'" % str(obj).replace("%","%%").replace("'","''")
        else:
            return "'%s'" % str(obj).replace("'","''")

    def sequence_name(self,table):
        return '%s_id_seq' % table

    def RANDOM(self):
        return 'RANDOM()'

    def ADD(self, first, second):
        t = first.type
        if t in ('text','string','password', 'json', 'upload','blob'):
            return '(%s || %s)' % (self.expand(first), self.expand(second, t))
        else:
            return '(%s + %s)' % (self.expand(first), self.expand(second, t))

    def distributed_transaction_begin(self,key):
        return

    def prepare(self,key):
        self.execute("PREPARE TRANSACTION '%s';" % key)

    def commit_prepared(self,key):
        self.execute("COMMIT PREPARED '%s';" % key)

    def rollback_prepared(self,key):
        self.execute("ROLLBACK PREPARED '%s';" % key)

    def create_sequence_and_triggers(self, query, table, **args):
        # following lines should only be executed if table._sequence_name does not exist
        # self.execute('CREATE SEQUENCE %s;' % table._sequence_name)
        # self.execute("ALTER TABLE %s ALTER COLUMN %s SET DEFAULT NEXTVAL('%s');" \
        #              % (table._tablename, table._fieldname, table._sequence_name))
        self.execute(query)

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:@]+)(\:(?P<port>[0-9]+))?/(?P<db>[^\?]+)(\?sslmode=(?P<sslmode>.+))?$')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, srid=4326,
                 after_connection=None):
        self.db = db
        self.dbengine = "postgres"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.srid = srid
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError("Invalid URI string in DAL")
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        port = m.group('port') or '5432'
        sslmode = m.group('sslmode')
        if sslmode:
            msg = ("dbname='%s' user='%s' host='%s' "
                   "port=%s password='%s' sslmode='%s'") \
                   % (db, user, host, port, password, sslmode)
        else:
            msg = ("dbname='%s' user='%s' host='%s' "
                   "port=%s password='%s'") \
                   % (db, user, host, port, password)
        # choose diver according uri
        if self.driver:
            self.__version__ = "%s %s" % (self.driver.__name__,
                                          self.driver.__version__)
        else:
            self.__version__ = None
        def connector(msg=msg,driver_args=driver_args):
            return self.driver.connect(msg,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.connection.set_client_encoding('UTF8')
        self.execute("SET standard_conforming_strings=on;")
        self.try_json()

    def lastrowid(self,table):
        self.execute("""select currval('"%s"')""" % table._sequence_name)
        return int(self.cursor.fetchone()[0])

    def try_json(self):
        # check JSON data type support
        # (to be added to after_connection)
        if self.driver_name == "pg8000":
            supports_json = self.connection.server_version >= "9.2.0"
        elif (self.driver_name == "psycopg2") and \
             (self.driver.__version__ >= "2.0.12"):
            supports_json = self.connection.server_version >= 90200
        elif self.driver_name == "zxJDBC":
            supports_json = self.connection.dbversion >= "9.2.0"
        else: supports_json = None
        if supports_json:
            self.types["json"] = "JSON"
            self.native_json = True
        else: LOGGER.debug("Your database version does not support the JSON data type (using TEXT instead)")

    def LIKE(self,first,second):
        args = (self.expand(first), self.expand(second,'string'))
        if not first.type in ('string', 'text', 'json'):
            return '(%s LIKE %s)' % (
                self.CAST(args[0], 'CHAR(%s)' % first.length), args[1])
        else:
            return '(%s LIKE %s)' % args

    def ILIKE(self,first,second):
        args = (self.expand(first), self.expand(second,'string'))
        if not first.type in ('string', 'text', 'json'):
            return '(%s LIKE %s)' % (
                self.CAST(args[0], 'CHAR(%s)' % first.length), args[1])
        else:
            return '(%s ILIKE %s)' % args

    def REGEXP(self,first,second):
        return '(%s ~ %s)' % (self.expand(first),
                              self.expand(second,'string'))

    def STARTSWITH(self,first,second):
        return '(%s ILIKE %s)' % (self.expand(first),
                                  self.expand(second+'%','string'))

    def ENDSWITH(self,first,second):
        return '(%s ILIKE %s)' % (self.expand(first),
                                  self.expand('%'+second,'string'))

    # GIS functions

    def ST_ASGEOJSON(self, first, second):
        """
        http://postgis.org/docs/ST_AsGeoJSON.html
        """
        return 'ST_AsGeoJSON(%s,%s,%s,%s)' %(second['version'],
            self.expand(first), second['precision'], second['options'])

    def ST_ASTEXT(self, first):
        """
        http://postgis.org/docs/ST_AsText.html
        """
        return 'ST_AsText(%s)' %(self.expand(first))

    def ST_X(self, first):
        """
        http://postgis.org/docs/ST_X.html
        """
        return 'ST_X(%s)' %(self.expand(first))

    def ST_Y(self, first):
        """
        http://postgis.org/docs/ST_Y.html
        """
        return 'ST_Y(%s)' %(self.expand(first))

    def ST_CONTAINS(self, first, second):
        """
        http://postgis.org/docs/ST_Contains.html
        """
        return 'ST_Contains(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_DISTANCE(self, first, second):
        """
        http://postgis.org/docs/ST_Distance.html
        """
        return 'ST_Distance(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_EQUALS(self, first, second):
        """
        http://postgis.org/docs/ST_Equals.html
        """
        return 'ST_Equals(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_INTERSECTS(self, first, second):
        """
        http://postgis.org/docs/ST_Intersects.html
        """
        return 'ST_Intersects(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_OVERLAPS(self, first, second):
        """
        http://postgis.org/docs/ST_Overlaps.html
        """
        return 'ST_Overlaps(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_SIMPLIFY(self, first, second):
        """
        http://postgis.org/docs/ST_Simplify.html
        """
        return 'ST_Simplify(%s,%s)' %(self.expand(first), self.expand(second, 'double'))

    def ST_TOUCHES(self, first, second):
        """
        http://postgis.org/docs/ST_Touches.html
        """
        return 'ST_Touches(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_WITHIN(self, first, second):
        """
        http://postgis.org/docs/ST_Within.html
        """
        return 'ST_Within(%s,%s)' %(self.expand(first), self.expand(second, first.type))

    def represent(self, obj, fieldtype):
        field_is_type = fieldtype.startswith
        if field_is_type('geo'):
            srid = 4326 # postGIS default srid for geometry
            geotype, parms = fieldtype[:-1].split('(')
            parms = parms.split(',')
            if len(parms) >= 2:
                schema, srid = parms[:2]
            if field_is_type('geometry'):
                value = "ST_GeomFromText('%s',%s)" %(obj, srid)
            elif field_is_type('geography'):
                value = "ST_GeogFromText('SRID=%s;%s')" %(srid, obj)
#             else:
#                 raise SyntaxError('Invalid field type %s' %fieldtype)
            return value
        return BaseAdapter.represent(self, obj, fieldtype)

class NewPostgreSQLAdapter(PostgreSQLAdapter):
    drivers = ('psycopg2','pg8000')

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'TEXT',
        'json': 'TEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BYTEA',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INTEGER',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT8',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'SERIAL PRIMARY KEY',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'BIGINT[]',
        'list:string': 'TEXT[]',
        'list:reference': 'BIGINT[]',
        'geometry': 'GEOMETRY',
        'geography': 'GEOGRAPHY',
        'big-id': 'BIGSERIAL PRIMARY KEY',
        'big-reference': 'BIGINT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        }

    def parse_list_integers(self, value, field_type):
        return value

    def parse_list_references(self, value, field_type):
        return [self.parse_reference(r, field_type[5:]) for r in value]

    def parse_list_strings(self, value, field_type):
        return value

    def represent(self, obj, fieldtype):
        field_is_type = fieldtype.startswith
        if field_is_type('list:'):
            if not obj:
                obj = []
            elif not isinstance(obj, (list, tuple)):
                obj = [obj]
            if field_is_type('list:string'):
                obj = map(str,obj)
            else:
                obj = map(int,obj)
            return 'ARRAY[%s]' % ','.join(repr(item) for item in obj)
        return BaseAdapter.represent(self, obj, fieldtype)


class JDBCPostgreSQLAdapter(PostgreSQLAdapter):
    drivers = ('zxJDBC',)

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None    ):
        self.db = db
        self.dbengine = "postgres"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError("Invalid URI string in DAL")
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        port = m.group('port') or '5432'
        msg = ('jdbc:postgresql://%s:%s/%s' % (host, port, db), user, password)
        def connector(msg=msg,driver_args=driver_args):
            return self.driver.connect(*msg,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.connection.set_client_encoding('UTF8')
        self.execute('BEGIN;')
        self.execute("SET CLIENT_ENCODING TO 'UNICODE';")
        self.try_json()


class OracleAdapter(BaseAdapter):
    drivers = ('cx_Oracle',)

    commit_on_alter_table = False
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR2(%(length)s)',
        'text': 'CLOB',
        'json': 'CLOB',
        'password': 'VARCHAR2(%(length)s)',
        'blob': 'CLOB',
        'upload': 'VARCHAR2(%(length)s)',
        'integer': 'INT',
        'bigint': 'NUMBER',
        'float': 'FLOAT',
        'double': 'BINARY_DOUBLE',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'CHAR(8)',
        'datetime': 'DATE',
        'id': 'NUMBER PRIMARY KEY',
        'reference': 'NUMBER, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'CLOB',
        'list:string': 'CLOB',
        'list:reference': 'CLOB',
        'big-id': 'NUMBER PRIMARY KEY',
        'big-reference': 'NUMBER, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        }

    def sequence_name(self,tablename):
        return '%s_sequence' % tablename

    def trigger_name(self,tablename):
        return '%s_trigger' % tablename

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    def RANDOM(self):
        return 'dbms_random.value'

    def NOT_NULL(self,default,field_type):
        return 'DEFAULT %s NOT NULL' % self.represent(default,field_type)

    def _drop(self,table,mode):
        sequence_name = table._sequence_name
        return ['DROP TABLE %s %s;' % (table, mode), 'DROP SEQUENCE %s;' % sequence_name]

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            if len(sql_w) > 1:
                sql_w_row = sql_w + ' AND w_row > %i' % lmin
            else:
                sql_w_row = 'WHERE w_row > %i' % lmin
            return 'SELECT %s %s FROM (SELECT w_tmp.*, ROWNUM w_row FROM (SELECT %s FROM %s%s%s) w_tmp WHERE ROWNUM<=%i) %s %s %s;' % (sql_s, sql_f, sql_f, sql_t, sql_w, sql_o, lmax, sql_t, sql_w_row, sql_o)
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def constraint_name(self, tablename, fieldname):
        constraint_name = BaseAdapter.constraint_name(self, tablename, fieldname)
        if len(constraint_name)>30:
            constraint_name = '%s_%s__constraint' % (tablename[:10], fieldname[:7])
        return constraint_name

    def represent_exceptions(self, obj, fieldtype):
        if fieldtype == 'blob':
            obj = base64.b64encode(str(obj))
            return ":CLOB('%s')" % obj
        elif fieldtype == 'date':
            if isinstance(obj, (datetime.date, datetime.datetime)):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
            return "to_date('%s','yyyy-mm-dd')" % obj
        elif fieldtype == 'datetime':
            if isinstance(obj, datetime.datetime):
                obj = obj.isoformat()[:19].replace('T',' ')
            elif isinstance(obj, datetime.date):
                obj = obj.isoformat()[:10]+' 00:00:00'
            else:
                obj = str(obj)
            return "to_date('%s','yyyy-mm-dd hh24:mi:ss')" % obj
        return None

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "oracle"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        if not 'threaded' in driver_args:
            driver_args['threaded']=True
        def connector(uri=ruri,driver_args=driver_args):
            return self.driver.connect(uri,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS';")
        self.execute("ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS';")

    oracle_fix = re.compile("[^']*('[^']*'[^']*)*\:(?P<clob>CLOB\('([^']+|'')*'\))")

    def execute(self, command, args=None):
        args = args or []
        i = 1
        while True:
            m = self.oracle_fix.match(command)
            if not m:
                break
            command = command[:m.start('clob')] + str(i) + command[m.end('clob'):]
            args.append(m.group('clob')[6:-2].replace("''", "'"))
            i += 1
        if command[-1:]==';':
            command = command[:-1]
        return self.log_execute(command, args)

    def create_sequence_and_triggers(self, query, table, **args):
        tablename = table._tablename
        id_name = table._id.name
        sequence_name = table._sequence_name
        trigger_name = table._trigger_name
        self.execute(query)
        self.execute('CREATE SEQUENCE %s START WITH 1 INCREMENT BY 1 NOMAXVALUE MINVALUE -1;' % sequence_name)
        self.execute("""
            CREATE OR REPLACE TRIGGER %(trigger_name)s BEFORE INSERT ON %(tablename)s FOR EACH ROW
            DECLARE
                curr_val NUMBER;
                diff_val NUMBER;
                PRAGMA autonomous_transaction;
            BEGIN
                IF :NEW.%(id)s IS NOT NULL THEN
                    EXECUTE IMMEDIATE 'SELECT %(sequence_name)s.nextval FROM dual' INTO curr_val;
                    diff_val := :NEW.%(id)s - curr_val - 1;
                    IF diff_val != 0 THEN
                      EXECUTE IMMEDIATE 'alter sequence %(sequence_name)s increment by '|| diff_val;
                      EXECUTE IMMEDIATE 'SELECT %(sequence_name)s.nextval FROM dual' INTO curr_val;
                      EXECUTE IMMEDIATE 'alter sequence %(sequence_name)s increment by 1';
                    END IF;
                END IF;
                SELECT %(sequence_name)s.nextval INTO :NEW.%(id)s FROM DUAL;
            END;
        """ % dict(trigger_name=trigger_name, tablename=tablename,
                   sequence_name=sequence_name,id=id_name))

    def lastrowid(self,table):
        sequence_name = table._sequence_name
        self.execute('SELECT %s.currval FROM dual;' % sequence_name)
        return long(self.cursor.fetchone()[0])

    #def parse_value(self, value, field_type, blob_decode=True):
    #    if blob_decode and isinstance(value, cx_Oracle.LOB):
    #        try:
    #            value = value.read()
    #        except self.driver.ProgrammingError:
    #            # After a subsequent fetch the LOB value is not valid anymore
    #            pass
    #    return BaseAdapter.parse_value(self, value, field_type, blob_decode)

    def _fetchall(self):
        if any(x[1]==cx_Oracle.CLOB for x in self.cursor.description):
            return [tuple([(c.read() if type(c) == cx_Oracle.LOB else c) \
                               for c in r]) for r in self.cursor]
        else:
            return self.cursor.fetchall()

class MSSQLAdapter(BaseAdapter):
    drivers = ('pyodbc',)
    T_SEP = 'T'

    QUOTE_TEMPLATE = "[%s]"

    types = {
        'boolean': 'BIT',
        'string': 'VARCHAR(%(length)s)',
        'text': 'TEXT',
        'json': 'TEXT',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'IMAGE',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATETIME',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'INT IDENTITY PRIMARY KEY',
        'reference': 'INT NULL, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'TEXT',
        'list:string': 'TEXT',
        'list:reference': 'TEXT',
        'geometry': 'geometry',
        'geography': 'geography',
        'big-id': 'BIGINT IDENTITY PRIMARY KEY',
        'big-reference': 'BIGINT NULL, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        }

    def concat_add(self,tablename):
        return '; ALTER TABLE %s ADD ' % tablename

    def varquote(self,name):
        return varquote_aux(name,'[%s]')

    def EXTRACT(self,field,what):
        return "DATEPART(%s,%s)" % (what, self.expand(field))

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    def RANDOM(self):
        return 'NEWID()'

    def ALLOW_NULL(self):
        return ' NULL'

    def CAST(self, first, second):
        return first # apparently no cast necessary in MSSQL

    def SUBSTRING(self,field,parameters):
        return 'SUBSTRING(%s,%s,%s)' % (self.expand(field), parameters[0], parameters[1])

    def PRIMARY_KEY(self,key):
        return 'PRIMARY KEY CLUSTERED (%s)' % key

    def AGGREGATE(self, first, what):
        if what == 'LENGTH':
            what = 'LEN'
        return "%s(%s)" % (what, self.expand(first))


    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_s += ' TOP %i' % lmax
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    TRUE = 1
    FALSE = 0

    REGEX_DSN = re.compile('^(?P<dsn>.+)$')
    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>[^\?]+)(\?(?P<urlargs>.*))?$')
    REGEX_ARGPATTERN = re.compile('(?P<argkey>[^=]+)=(?P<argvalue>[^&]*)')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, srid=4326,
                 after_connection=None):
        self.db = db
        self.dbengine = "mssql"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.srid = srid
        self.find_or_make_work_folder()
        # ## read: http://bytes.com/groups/python/460325-cx_oracle-utf8
        ruri = uri.split('://',1)[1]
        if '@' not in ruri:
            try:
                m = self.REGEX_DSN.match(ruri)
                if not m:
                    raise SyntaxError(
                        'Parsing uri string(%s) has no result' % self.uri)
                dsn = m.group('dsn')
                if not dsn:
                    raise SyntaxError('DSN required')
            except SyntaxError:
                e = sys.exc_info()[1]
                LOGGER.error('NdGpatch error')
                raise e
            # was cnxn = 'DSN=%s' % dsn
            cnxn = dsn
        else:
            m = self.REGEX_URI.match(ruri)
            if not m:
                raise SyntaxError(
                    "Invalid URI string in DAL: %s" % self.uri)
            user = credential_decoder(m.group('user'))
            if not user:
                raise SyntaxError('User required')
            password = credential_decoder(m.group('password'))
            if not password:
                password = ''
            host = m.group('host')
            if not host:
                raise SyntaxError('Host name required')
            db = m.group('db')
            if not db:
                raise SyntaxError('Database name required')
            port = m.group('port') or '1433'
            # Parse the optional url name-value arg pairs after the '?'
            # (in the form of arg1=value1&arg2=value2&...)
            # Default values (drivers like FreeTDS insist on uppercase parameter keys)
            argsdict = { 'DRIVER':'{SQL Server}' }
            urlargs = m.group('urlargs') or ''
            for argmatch in self.REGEX_ARGPATTERN.finditer(urlargs):
                argsdict[str(argmatch.group('argkey')).upper()] = argmatch.group('argvalue')
            urlargs = ';'.join(['%s=%s' % (ak, av) for (ak, av) in argsdict.iteritems()])
            cnxn = 'SERVER=%s;PORT=%s;DATABASE=%s;UID=%s;PWD=%s;%s' \
                % (host, port, db, user, password, urlargs)
        def connector(cnxn=cnxn,driver_args=driver_args):
            return self.driver.connect(cnxn,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def lastrowid(self,table):
        #self.execute('SELECT @@IDENTITY;')
        self.execute('SELECT SCOPE_IDENTITY();')
        return long(self.cursor.fetchone()[0])

    def rowslice(self,rows,minimum=0,maximum=None):
        if maximum is None:
            return rows[minimum:]
        return rows[minimum:maximum]

    def EPOCH(self, first):
        return "DATEDIFF(second, '1970-01-01 00:00:00', %s)" % self.expand(first)

    def CONCAT(self, *items):
        return '(%s)' % ' + '.join(self.expand(x,'string') for x in items)

    # GIS Spatial Extensions

    # No STAsGeoJSON in MSSQL

    def ST_ASTEXT(self, first):
        return '%s.STAsText()' %(self.expand(first))

    def ST_CONTAINS(self, first, second):
        return '%s.STContains(%s)=1' %(self.expand(first), self.expand(second, first.type))

    def ST_DISTANCE(self, first, second):
        return '%s.STDistance(%s)' %(self.expand(first), self.expand(second, first.type))

    def ST_EQUALS(self, first, second):
        return '%s.STEquals(%s)=1' %(self.expand(first), self.expand(second, first.type))

    def ST_INTERSECTS(self, first, second):
        return '%s.STIntersects(%s)=1' %(self.expand(first), self.expand(second, first.type))

    def ST_OVERLAPS(self, first, second):
        return '%s.STOverlaps(%s)=1' %(self.expand(first), self.expand(second, first.type))

    # no STSimplify in MSSQL

    def ST_TOUCHES(self, first, second):
        return '%s.STTouches(%s)=1' %(self.expand(first), self.expand(second, first.type))

    def ST_WITHIN(self, first, second):
        return '%s.STWithin(%s)=1' %(self.expand(first), self.expand(second, first.type))

    def represent(self, obj, fieldtype):
        field_is_type = fieldtype.startswith
        if field_is_type('geometry'):
            srid = 0 # MS SQL default srid for geometry
            geotype, parms = fieldtype[:-1].split('(')
            if parms:
                srid = parms
            return "geometry::STGeomFromText('%s',%s)" %(obj, srid)
        elif fieldtype == 'geography':
            srid = 4326 # MS SQL default srid for geography
            geotype, parms = fieldtype[:-1].split('(')
            if parms:
                srid = parms
            return "geography::STGeomFromText('%s',%s)" %(obj, srid)
#             else:
#                 raise SyntaxError('Invalid field type %s' %fieldtype)
            return "geometry::STGeomFromText('%s',%s)" %(obj, srid)
        return BaseAdapter.represent(self, obj, fieldtype)


class MSSQL3Adapter(MSSQLAdapter):
    """ experimental support for pagination in MSSQL"""
    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            if lmin == 0:
                sql_s += ' TOP %i' % lmax
                return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)
            lmin += 1
            sql_o_inner = sql_o[sql_o.find('ORDER BY ')+9:]
            sql_g_inner = sql_o[:sql_o.find('ORDER BY ')]
            sql_f_outer = ['f_%s' % f for f in range(len(sql_f.split(',')))]
            sql_f_inner = [f for f in sql_f.split(',')]
            sql_f_iproxy = ['%s AS %s' % (o, n) for (o, n) in zip(sql_f_inner, sql_f_outer)]
            sql_f_iproxy = ', '.join(sql_f_iproxy)
            sql_f_oproxy = ', '.join(sql_f_outer)
            return 'SELECT %s %s FROM (SELECT %s ROW_NUMBER() OVER (ORDER BY %s) AS w_row, %s FROM %s%s%s) TMP WHERE w_row BETWEEN %i AND %s;' % (sql_s,sql_f_oproxy,sql_s,sql_f,sql_f_iproxy,sql_t,sql_w,sql_g_inner,lmin,lmax)
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s,sql_f,sql_t,sql_w,sql_o)
    def rowslice(self,rows,minimum=0,maximum=None):
        return rows

class MSSQL4Adapter(MSSQLAdapter):
    """ support for true pagination in MSSQL >= 2012"""

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            if lmin == 0:
                #top is still slightly faster, especially because
                #web2py's default to fetch references is to not specify
                #an orderby clause
                sql_s += ' TOP %i' % lmax
            else:
                if not sql_o:
                    #if there is no orderby, we can't use the brand new statements
                    #that being said, developer chose its own poison, so be it random
                    sql_o += ' ORDER BY %s' % self.RANDOM()
                sql_o += ' OFFSET %i ROWS FETCH NEXT %i ROWS ONLY' % (lmin, lmax - lmin)
        return 'SELECT %s %s FROM %s%s%s;' % \
                (sql_s, sql_f, sql_t, sql_w, sql_o)

    def rowslice(self,rows,minimum=0,maximum=None):
        return rows

class MSSQL2Adapter(MSSQLAdapter):
    drivers = ('pyodbc',)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'NVARCHAR(%(length)s)',
        'text': 'NTEXT',
        'json': 'NTEXT',
        'password': 'NVARCHAR(%(length)s)',
        'blob': 'IMAGE',
        'upload': 'NVARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATETIME',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'INT IDENTITY PRIMARY KEY',
        'reference': 'INT, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'NTEXT',
        'list:string': 'NTEXT',
        'list:reference': 'NTEXT',
        'big-id': 'BIGINT IDENTITY PRIMARY KEY',
        'big-reference': 'BIGINT, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        }

    def represent(self, obj, fieldtype):
        value = BaseAdapter.represent(self, obj, fieldtype)
        if fieldtype in ('string','text', 'json') and value[:1]=="'":
            value = 'N'+value
        return value

    def execute(self,a):
        return self.log_execute(a.decode('utf8'))

class VerticaAdapter(MSSQLAdapter):
    drivers = ('pyodbc',)
    T_SEP = ' '

    types = {
        'boolean': 'BOOLEAN',
        'string': 'VARCHAR(%(length)s)',
        'text': 'BYTEA',
        'json': 'VARCHAR(%(length)s)',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BYTEA',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'DOUBLE PRECISION',
        'decimal': 'DECIMAL(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'DATETIME',
        'id': 'IDENTITY',
        'reference': 'INT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'BYTEA',
        'list:string': 'BYTEA',
        'list:reference': 'BYTEA',
        'big-reference': 'BIGINT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        }


    def EXTRACT(self, first, what):
        return "DATE_PART('%s', TIMESTAMP %s)" % (what, self.expand(first))

    def _truncate(self, table, mode=''):
        tablename = table._tablename
        return ['TRUNCATE %s %s;' % (tablename, mode or '')]

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_o += ' LIMIT %i OFFSET %i' % (lmax - lmin, lmin)
        return 'SELECT %s %s FROM %s%s%s;' % \
            (sql_s, sql_f, sql_t, sql_w, sql_o)

    def lastrowid(self,table):
        self.execute('SELECT LAST_INSERT_ID();')
        return long(self.cursor.fetchone()[0])

    def execute(self, a):
        return self.log_execute(a)

class SybaseAdapter(MSSQLAdapter):
    drivers = ('Sybase',)

    types = {
        'boolean': 'BIT',
        'string': 'CHAR VARYING(%(length)s)',
        'text': 'TEXT',
        'json': 'TEXT',
        'password': 'CHAR VARYING(%(length)s)',
        'blob': 'IMAGE',
        'upload': 'CHAR VARYING(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATETIME',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'INT IDENTITY PRIMARY KEY',
        'reference': 'INT NULL, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'TEXT',
        'list:string': 'TEXT',
        'list:reference': 'TEXT',
        'geometry': 'geometry',
        'geography': 'geography',
        'big-id': 'BIGINT IDENTITY PRIMARY KEY',
        'big-reference': 'BIGINT NULL, CONSTRAINT %(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        }


    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, srid=4326,
                 after_connection=None):
        self.db = db
        self.dbengine = "sybase"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.srid = srid
        self.find_or_make_work_folder()
        # ## read: http://bytes.com/groups/python/460325-cx_oracle-utf8
        ruri = uri.split('://',1)[1]
        if '@' not in ruri:
            try:
                m = self.REGEX_DSN.match(ruri)
                if not m:
                    raise SyntaxError(
                        'Parsing uri string(%s) has no result' % self.uri)
                dsn = m.group('dsn')
                if not dsn:
                    raise SyntaxError('DSN required')
            except SyntaxError:
                e = sys.exc_info()[1]
                LOGGER.error('NdGpatch error')
                raise e
        else:
            m = self.REGEX_URI.match(uri)
            if not m:
                raise SyntaxError(
                    "Invalid URI string in DAL: %s" % self.uri)
            user = credential_decoder(m.group('user'))
            if not user:
                raise SyntaxError('User required')
            password = credential_decoder(m.group('password'))
            if not password:
                password = ''
            host = m.group('host')
            if not host:
                raise SyntaxError('Host name required')
            db = m.group('db')
            if not db:
                raise SyntaxError('Database name required')
            port = m.group('port') or '1433'

            dsn = 'sybase:host=%s:%s;dbname=%s' % (host,port,db)

            driver_args.update(user = credential_decoder(user),
                               password = credential_decoder(password))

        def connector(dsn=dsn,driver_args=driver_args):
            return self.driver.connect(dsn,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()


class FireBirdAdapter(BaseAdapter):
    drivers = ('kinterbasdb','firebirdsql','fdb','pyodbc')

    commit_on_alter_table = False
    support_distributed_transaction = True
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'BLOB SUB_TYPE 1',
        'json': 'BLOB SUB_TYPE 1',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB SUB_TYPE 0',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INTEGER',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'DOUBLE PRECISION',
        'decimal': 'DECIMAL(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INTEGER PRIMARY KEY',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'BLOB SUB_TYPE 1',
        'list:string': 'BLOB SUB_TYPE 1',
        'list:reference': 'BLOB SUB_TYPE 1',
        'big-id': 'BIGINT PRIMARY KEY',
        'big-reference': 'BIGINT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        }

    def sequence_name(self,tablename):
        return 'genid_%s' % tablename

    def trigger_name(self,tablename):
        return 'trg_id_%s' % tablename

    def RANDOM(self):
        return 'RAND()'

    def EPOCH(self, first):
        return "DATEDIFF(second, '1970-01-01 00:00:00', %s)" % self.expand(first)

    def NOT_NULL(self,default,field_type):
        return 'DEFAULT %s NOT NULL' % self.represent(default,field_type)

    def SUBSTRING(self,field,parameters):
        return 'SUBSTRING(%s from %s for %s)' % (self.expand(field), parameters[0], parameters[1])

    def LENGTH(self, first):
        return "CHAR_LENGTH(%s)" % self.expand(first)

    def CONTAINS(self,first,second,case_sensitive=False):
        if first.type.startswith('list:'):
            second = Expression(None,self.CONCAT('|',Expression(
                        None,self.REPLACE(second,('|','||'))),'|'))
        return '(%s CONTAINING %s)' % (self.expand(first),
                                       self.expand(second, 'string'))

    def _drop(self,table,mode):
        sequence_name = table._sequence_name
        return ['DROP TABLE %s %s;' % (table, mode), 'DROP GENERATOR %s;' % sequence_name]

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_s = ' FIRST %i SKIP %i %s' % (lmax - lmin, lmin, sql_s)
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def _truncate(self,table,mode = ''):
        return ['DELETE FROM %s;' % table._tablename,
                'SET GENERATOR %s TO 0;' % table._sequence_name]

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+?)(\?set_encoding=(?P<charset>\w+))?$')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "firebird"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError("Invalid URI string in DAL: %s" % self.uri)
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        port = int(m.group('port') or 3050)
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        charset = m.group('charset') or 'UTF8'
        driver_args.update(dsn='%s/%s:%s' % (host,port,db),
                           user = credential_decoder(user),
                           password = credential_decoder(password),
                           charset = charset)

        def connector(driver_args=driver_args):
            return self.driver.connect(**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def create_sequence_and_triggers(self, query, table, **args):
        tablename = table._tablename
        sequence_name = table._sequence_name
        trigger_name = table._trigger_name
        self.execute(query)
        self.execute('create generator %s;' % sequence_name)
        self.execute('set generator %s to 0;' % sequence_name)
        self.execute('create trigger %s for %s active before insert position 0 as\nbegin\nif(new.id is null) then\nbegin\nnew.id = gen_id(%s, 1);\nend\nend;' % (trigger_name, tablename, sequence_name))

    def lastrowid(self,table):
        sequence_name = table._sequence_name
        self.execute('SELECT gen_id(%s, 0) FROM rdb$database' % sequence_name)
        return long(self.cursor.fetchone()[0])


class FireBirdEmbeddedAdapter(FireBirdAdapter):
    drivers = ('kinterbasdb','firebirdsql','fdb','pyodbc')

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<path>[^\?]+)(\?set_encoding=(?P<charset>\w+))?$')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "firebird"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError(
                "Invalid URI string in DAL: %s" % self.uri)
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        pathdb = m.group('path')
        if not pathdb:
            raise SyntaxError('Path required')
        charset = m.group('charset')
        if not charset:
            charset = 'UTF8'
        host = ''
        driver_args.update(host=host,
                           database=pathdb,
                           user=credential_decoder(user),
                           password=credential_decoder(password),
                           charset=charset)

        def connector(driver_args=driver_args):
            return self.driver.connect(**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

class InformixAdapter(BaseAdapter):
    drivers = ('informixdb',)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'BLOB SUB_TYPE 1',
        'json': 'BLOB SUB_TYPE 1',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB SUB_TYPE 0',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INTEGER',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'DOUBLE PRECISION',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'CHAR(8)',
        'datetime': 'DATETIME',
        'id': 'SERIAL',
        'reference': 'INTEGER REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'BLOB SUB_TYPE 1',
        'list:string': 'BLOB SUB_TYPE 1',
        'list:reference': 'BLOB SUB_TYPE 1',
        'big-id': 'BIGSERIAL',
        'big-reference': 'BIGINT REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': 'REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s CONSTRAINT FK_%(table_name)s_%(field_name)s',
        'reference TFK': 'FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s CONSTRAINT TFK_%(table_name)s_%(field_name)s',
        }

    def RANDOM(self):
        return 'Random()'

    def NOT_NULL(self,default,field_type):
        return 'DEFAULT %s NOT NULL' % self.represent(default,field_type)

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            fetch_amt = lmax - lmin
            dbms_version = int(self.connection.dbms_version.split('.')[0])
            if lmin and (dbms_version >= 10):
                # Requires Informix 10.0+
                sql_s += ' SKIP %d' % (lmin, )
            if fetch_amt and (dbms_version >= 9):
                # Requires Informix 9.0+
                sql_s += ' FIRST %d' % (fetch_amt, )
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def represent_exceptions(self, obj, fieldtype):
        if fieldtype == 'date':
            if isinstance(obj, (datetime.date, datetime.datetime)):
                obj = obj.isoformat()[:10]
            else:
                obj = str(obj)
            return "to_date('%s','%%Y-%%m-%%d')" % obj
        elif fieldtype == 'datetime':
            if isinstance(obj, datetime.datetime):
                obj = obj.isoformat()[:19].replace('T',' ')
            elif isinstance(obj, datetime.date):
                obj = obj.isoformat()[:10]+' 00:00:00'
            else:
                obj = str(obj)
            return "to_date('%s','%%Y-%%m-%%d %%H:%%M:%%S')" % obj
        return None

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>.+)$')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "informix"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError(
                "Invalid URI string in DAL: %s" % self.uri)
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        user = credential_decoder(user)
        password = credential_decoder(password)
        dsn = '%s@%s' % (db,host)
        driver_args.update(user=user,password=password,autocommit=True)
        def connector(dsn=dsn,driver_args=driver_args):
            return self.driver.connect(dsn,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def execute(self,command):
        if command[-1:]==';':
            command = command[:-1]
        return self.log_execute(command)

    def lastrowid(self,table):
        return self.cursor.sqlerrd[1]

class InformixSEAdapter(InformixAdapter):
    """ work in progress """

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        return 'SELECT %s %s FROM %s%s%s;' % \
            (sql_s, sql_f, sql_t, sql_w, sql_o)

    def rowslice(self,rows,minimum=0,maximum=None):
        if maximum is None:
            return rows[minimum:]
        return rows[minimum:maximum]

class DB2Adapter(BaseAdapter):
    drivers = ('pyodbc',)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'CLOB',
        'json': 'CLOB',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'REAL',
        'double': 'DOUBLE',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY NOT NULL',
        'reference': 'INT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'CLOB',
        'list:string': 'CLOB',
        'list:reference': 'CLOB',
        'big-id': 'BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY NOT NULL',
        'big-reference': 'BIGINT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s',
        }

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    def RANDOM(self):
        return 'RAND()'

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_o += ' FETCH FIRST %i ROWS ONLY' % lmax
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def represent_exceptions(self, obj, fieldtype):
        if fieldtype == 'blob':
            obj = base64.b64encode(str(obj))
            return "BLOB('%s')" % obj
        elif fieldtype == 'datetime':
            if isinstance(obj, datetime.datetime):
                obj = obj.isoformat()[:19].replace('T','-').replace(':','.')
            elif isinstance(obj, datetime.date):
                obj = obj.isoformat()[:10]+'-00.00.00'
            return "'%s'" % obj
        return None

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "db2"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://', 1)[1]
        def connector(cnxn=ruri,driver_args=driver_args):
            return self.driver.connect(cnxn,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def execute(self,command):
        if command[-1:]==';':
            command = command[:-1]
        return self.log_execute(command)

    def lastrowid(self,table):
        self.execute('SELECT DISTINCT IDENTITY_VAL_LOCAL() FROM %s;' % table)
        return long(self.cursor.fetchone()[0])

    def rowslice(self,rows,minimum=0,maximum=None):
        if maximum is None:
            return rows[minimum:]
        return rows[minimum:maximum]


class TeradataAdapter(BaseAdapter):
    drivers = ('pyodbc',)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'VARCHAR(2000)',
        'json': 'VARCHAR(4000)',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'BLOB',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'REAL',
        'double': 'DOUBLE',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        # Modified Constraint syntax for Teradata.
        # Teradata does not support ON DELETE.
        'id': 'INT GENERATED ALWAYS AS IDENTITY',  # Teradata Specific
        'reference': 'INT',
        'list:integer': 'VARCHAR(4000)',
        'list:string': 'VARCHAR(4000)',
        'list:reference': 'VARCHAR(4000)',
        'big-id': 'BIGINT GENERATED ALWAYS AS IDENTITY',  # Teradata Specific
        'big-reference': 'BIGINT',
        'reference FK': ' REFERENCES %(foreign_key)s',
        'reference TFK': ' FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s)',
        }

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "teradata"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://', 1)[1]
        def connector(cnxn=ruri,driver_args=driver_args):
            return self.driver.connect(cnxn,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def close(self,action='commit',really=True):
        # Teradata does not implicitly close off the cursor
        # leading to SQL_ACTIVE_STATEMENTS limit errors
        self.cursor.close()
        ConnectionPool.close(self, action, really)

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    # Similar to MSSQL, Teradata can't specify a range (for Pageby)
    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            sql_s += ' TOP %i' % lmax
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def _truncate(self, table, mode=''):
        tablename = table._tablename
        return ['DELETE FROM %s ALL;' % (tablename)]

INGRES_SEQNAME='ii***lineitemsequence' # NOTE invalid database object name
                                       # (ANSI-SQL wants this form of name
                                       # to be a delimited identifier)

class IngresAdapter(BaseAdapter):
    drivers = ('pyodbc',)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'CLOB',
        'json': 'CLOB',
        'password': 'VARCHAR(%(length)s)',  ## Not sure what this contains utf8 or nvarchar. Or even bytes?
        'blob': 'BLOB',
        'upload': 'VARCHAR(%(length)s)',  ## FIXME utf8 or nvarchar... or blob? what is this type?
        'integer': 'INTEGER4', # or int8...
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT8',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'ANSIDATE',
        'time': 'TIME WITHOUT TIME ZONE',
        'datetime': 'TIMESTAMP WITHOUT TIME ZONE',
        'id': 'int not null unique with default next value for %s' % INGRES_SEQNAME,
        'reference': 'INT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'CLOB',
        'list:string': 'CLOB',
        'list:reference': 'CLOB',
        'big-id': 'bigint not null unique with default next value for %s' % INGRES_SEQNAME,
        'big-reference': 'BIGINT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s', ## FIXME TODO
        }

    def LEFT_JOIN(self):
        return 'LEFT OUTER JOIN'

    def RANDOM(self):
        return 'RANDOM()'

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            fetch_amt = lmax - lmin
            if fetch_amt:
                sql_s += ' FIRST %d ' % (fetch_amt, )
            if lmin:
                # Requires Ingres 9.2+
                sql_o += ' OFFSET %d' % (lmin, )
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "ingres"
        self._driver = pyodbc
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        connstr = uri.split(':', 1)[1]
        # Simple URI processing
        connstr = connstr.lstrip()
        while connstr.startswith('/'):
            connstr = connstr[1:]
        if '=' in connstr:
            # Assume we have a regular ODBC connection string and just use it
            ruri  = connstr
        else:
            # Assume only (local) dbname is passed in with OS auth
            database_name = connstr
            default_driver_name = 'Ingres'
            vnode = '(local)'
            servertype = 'ingres'
            ruri = 'Driver={%s};Server=%s;Database=%s' % (default_driver_name, vnode, database_name)
        def connector(cnxn=ruri,driver_args=driver_args):
            return self.driver.connect(cnxn,**driver_args)

        self.connector = connector

        # TODO if version is >= 10, set types['id'] to Identity column, see http://community.actian.com/wiki/Using_Ingres_Identity_Columns
        if do_connect: self.reconnect()

    def create_sequence_and_triggers(self, query, table, **args):
        # post create table auto inc code (if needed)
        # modify table to btree for performance....
        # Older Ingres releases could use rule/trigger like Oracle above.
        if hasattr(table,'_primarykey'):
            modify_tbl_sql = 'modify %s to btree unique on %s' % \
                (table._tablename,
                 ', '.join(["'%s'" % x for x in table.primarykey]))
            self.execute(modify_tbl_sql)
        else:
            tmp_seqname='%s_iisq' % table._tablename
            query=query.replace(INGRES_SEQNAME, tmp_seqname)
            self.execute('create sequence %s' % tmp_seqname)
            self.execute(query)
            self.execute('modify %s to btree unique on %s' % (table._tablename, 'id'))


    def lastrowid(self,table):
        tmp_seqname='%s_iisq' % table
        self.execute('select current value for %s' % tmp_seqname)
        return long(self.cursor.fetchone()[0]) # don't really need int type cast here...


class IngresUnicodeAdapter(IngresAdapter):

    drivers = ('pyodbc',)

    types = {
        'boolean': 'CHAR(1)',
        'string': 'NVARCHAR(%(length)s)',
        'text': 'NCLOB',
        'json': 'NCLOB',
        'password': 'NVARCHAR(%(length)s)',  ## Not sure what this contains utf8 or nvarchar. Or even bytes?
        'blob': 'BLOB',
        'upload': 'VARCHAR(%(length)s)',  ## FIXME utf8 or nvarchar... or blob? what is this type?
        'integer': 'INTEGER4', # or int8...
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'FLOAT8',
        'decimal': 'NUMERIC(%(precision)s,%(scale)s)',
        'date': 'ANSIDATE',
        'time': 'TIME WITHOUT TIME ZONE',
        'datetime': 'TIMESTAMP WITHOUT TIME ZONE',
        'id': 'INTEGER4 not null unique with default next value for %s'% INGRES_SEQNAME,
        'reference': 'INTEGER4, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'NCLOB',
        'list:string': 'NCLOB',
        'list:reference': 'NCLOB',
        'big-id': 'BIGINT not null unique with default next value for %s'% INGRES_SEQNAME,
        'big-reference': 'BIGINT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference FK': ', CONSTRAINT FK_%(constraint_name)s FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'reference TFK': ' CONSTRAINT FK_%(foreign_table)s_PK FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_table)s (%(foreign_key)s) ON DELETE %(on_delete_action)s', ## FIXME TODO
        }

class SAPDBAdapter(BaseAdapter):
    drivers = ('sapdb',)

    support_distributed_transaction = False
    types = {
        'boolean': 'CHAR(1)',
        'string': 'VARCHAR(%(length)s)',
        'text': 'LONG',
        'json': 'LONG',
        'password': 'VARCHAR(%(length)s)',
        'blob': 'LONG',
        'upload': 'VARCHAR(%(length)s)',
        'integer': 'INT',
        'bigint': 'BIGINT',
        'float': 'FLOAT',
        'double': 'DOUBLE PRECISION',
        'decimal': 'FIXED(%(precision)s,%(scale)s)',
        'date': 'DATE',
        'time': 'TIME',
        'datetime': 'TIMESTAMP',
        'id': 'INT PRIMARY KEY',
        'reference': 'INT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        'list:integer': 'LONG',
        'list:string': 'LONG',
        'list:reference': 'LONG',
        'big-id': 'BIGINT PRIMARY KEY',
        'big-reference': 'BIGINT, FOREIGN KEY (%(field_name)s) REFERENCES %(foreign_key)s ON DELETE %(on_delete_action)s',
        }

    def sequence_name(self,table):
        return '%s_id_Seq' % table

    def select_limitby(self, sql_s, sql_f, sql_t, sql_w, sql_o, limitby):
        if limitby:
            (lmin, lmax) = limitby
            if len(sql_w) > 1:
                sql_w_row = sql_w + ' AND w_row > %i' % lmin
            else:
                sql_w_row = 'WHERE w_row > %i' % lmin
            return '%s %s FROM (SELECT w_tmp.*, ROWNO w_row FROM (SELECT %s FROM %s%s%s) w_tmp WHERE ROWNO=%i) %s %s %s;' % (sql_s, sql_f, sql_f, sql_t, sql_w, sql_o, lmax, sql_t, sql_w_row, sql_o)
        return 'SELECT %s %s FROM %s%s%s;' % (sql_s, sql_f, sql_t, sql_w, sql_o)

    def create_sequence_and_triggers(self, query, table, **args):
        # following lines should only be executed if table._sequence_name does not exist
        self.execute('CREATE SEQUENCE %s;' % table._sequence_name)
        self.execute("ALTER TABLE %s ALTER COLUMN %s SET DEFAULT NEXTVAL('%s');" \
                         % (table._tablename, table._id.name, table._sequence_name))
        self.execute(query)

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:@]+)(\:(?P<port>[0-9]+))?/(?P<db>[^\?]+)(\?sslmode=(?P<sslmode>.+))?$')


    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "sapdb"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError("Invalid URI string in DAL")
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        def connector(user=user, password=password, database=db,
                    host=host, driver_args=driver_args):
            return self.driver.Connection(user, password, database,
                                          host, **driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def lastrowid(self,table):
        self.execute("select %s.NEXTVAL from dual" % table._sequence_name)
        return long(self.cursor.fetchone()[0])

class CubridAdapter(MySQLAdapter):
    drivers = ('cubriddb',)

    REGEX_URI = re.compile('^(?P<user>[^:@]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:/]+)(\:(?P<port>[0-9]+))?/(?P<db>[^?]+)(\?set_encoding=(?P<charset>\w+))?$')

    def __init__(self, db, uri, pool_size=0, folder=None, db_codec='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.dbengine = "cubrid"
        self.uri = uri
        if do_connect: self.find_driver(adapter_args,uri)
        self.pool_size = pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.find_or_make_work_folder()
        ruri = uri.split('://',1)[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError(
                "Invalid URI string in DAL: %s" % self.uri)
        user = credential_decoder(m.group('user'))
        if not user:
            raise SyntaxError('User required')
        password = credential_decoder(m.group('password'))
        if not password:
            password = ''
        host = m.group('host')
        if not host:
            raise SyntaxError('Host name required')
        db = m.group('db')
        if not db:
            raise SyntaxError('Database name required')
        port = int(m.group('port') or '30000')
        charset = m.group('charset') or 'utf8'
        user = credential_decoder(user)
        passwd = credential_decoder(password)
        def connector(host=host,port=port,db=db,
                    user=user,passwd=password,driver_args=driver_args):
            return self.driver.connect(host,port,db,user,passwd,**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        self.execute('SET FOREIGN_KEY_CHECKS=1;')
        self.execute("SET sql_mode='NO_BACKSLASH_ESCAPES';")


######## GAE MySQL ##########

class DatabaseStoredFile:

    web2py_filesystem = False

    def escape(self,obj):
        return self.db._adapter.escape(obj)

    def __init__(self,db,filename,mode):
        if not db._adapter.dbengine in ('mysql', 'postgres', 'sqlite'):
            raise RuntimeError("only MySQL/Postgres/SQLite can store metadata .table files in database for now")
        self.db = db
        self.filename = filename
        self.mode = mode
        if not self.web2py_filesystem:
            if db._adapter.dbengine == 'mysql':
                sql = "CREATE TABLE IF NOT EXISTS web2py_filesystem (path VARCHAR(255), content LONGTEXT, PRIMARY KEY(path) ) ENGINE=InnoDB;"
            elif db._adapter.dbengine in ('postgres', 'sqlite'):
                sql = "CREATE TABLE IF NOT EXISTS web2py_filesystem (path VARCHAR(255), content TEXT, PRIMARY KEY(path));"
            self.db.executesql(sql)
            DatabaseStoredFile.web2py_filesystem = True
        self.p=0
        self.data = ''
        if mode in ('r','rw','a'):
            query = "SELECT content FROM web2py_filesystem WHERE path='%s'" \
                % filename
            rows = self.db.executesql(query)
            if rows:
                self.data = rows[0][0]
            elif exists(filename):
                datafile = open(filename, 'r')
                try:
                    self.data = datafile.read()
                finally:
                    datafile.close()
            elif mode in ('r','rw'):
                raise RuntimeError("File %s does not exist" % filename)

    def read(self, bytes):
        data = self.data[self.p:self.p+bytes]
        self.p += len(data)
        return data

    def readline(self):
        i = self.data.find('\n',self.p)+1
        if i>0:
            data, self.p = self.data[self.p:i], i
        else:
            data, self.p = self.data[self.p:], len(self.data)
        return data

    def write(self,data):
        self.data += data

    def close_connection(self):
        if self.db is not None:
            self.db.executesql(
                "DELETE FROM web2py_filesystem WHERE path='%s'" % self.filename)
            query = "INSERT INTO web2py_filesystem(path,content) VALUES ('%s','%s')"\
                % (self.filename, self.data.replace("'","''"))
            self.db.executesql(query)
            self.db.commit()
            self.db = None

    def close(self):
        self.close_connection()

    @staticmethod
    def exists(db, filename):
        if exists(filename):
            return True
        query = "SELECT path FROM web2py_filesystem WHERE path='%s'" % filename
        try:
            if db.executesql(query):
                return True
        except Exception, e:
            if not (db._adapter.isOperationalError(e) or
                    db._adapter.isProgrammingError(e)):
                raise
            # no web2py_filesystem found?
            tb = traceback.format_exc()
            LOGGER.error("Could not retrieve %s\n%s" % (filename, tb))
        return False


class UseDatabaseStoredFile:

    def file_exists(self, filename):
        return DatabaseStoredFile.exists(self.db,filename)

    def file_open(self, filename, mode='rb', lock=True):
        return DatabaseStoredFile(self.db,filename,mode)

    def file_close(self, fileobj):
        fileobj.close_connection()

    def file_delete(self,filename):
        query = "DELETE FROM web2py_filesystem WHERE path='%s'" % filename
        self.db.executesql(query)
        self.db.commit()

class GoogleSQLAdapter(UseDatabaseStoredFile,MySQLAdapter):
    uploads_in_blob = True

    REGEX_URI = re.compile('^(?P<instance>.*)/(?P<db>.*)$')

    def __init__(self, db, uri='google:sql://realm:domain/database',
                 pool_size=0, folder=None, db_codec='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):

        self.db = db
        self.dbengine = "mysql"
        self.uri = uri
        self.pool_size = pool_size
        self.db_codec = db_codec
        self._after_connection = after_connection
        if do_connect: self.find_driver(adapter_args, uri)
        self.folder = folder or pjoin('$HOME',THREAD_LOCAL.folder.split(
                os.sep+'applications'+os.sep,1)[1])
        ruri = uri.split("://")[1]
        m = self.REGEX_URI.match(ruri)
        if not m:
            raise SyntaxError("Invalid URI string in SQLDB: %s" % self.uri)
        instance = credential_decoder(m.group('instance'))
        self.dbstring = db = credential_decoder(m.group('db'))
        driver_args['instance'] = instance
        if not 'charset' in driver_args:
            driver_args['charset'] = 'utf8'
        self.createdb = createdb = adapter_args.get('createdb',True)
        if not createdb:
            driver_args['database'] = db
        def connector(driver_args=driver_args):
            return rdbms.connect(**driver_args)
        self.connector = connector
        if do_connect: self.reconnect()

    def after_connection(self):
        if self.createdb:
            # self.execute('DROP DATABASE %s' % self.dbstring)
            self.execute('CREATE DATABASE IF NOT EXISTS %s' % self.dbstring)
            self.execute('USE %s' % self.dbstring)
        self.execute("SET FOREIGN_KEY_CHECKS=1;")
        self.execute("SET sql_mode='NO_BACKSLASH_ESCAPES';")

    def execute(self, command, *a, **b):
        return self.log_execute(command.decode('utf8'), *a, **b)

    def find_driver(self,adapter_args,uri=None):
        self.adapter_args = adapter_args
        self.driver = "google"

class NoSQLAdapter(BaseAdapter):
    can_select_for_update = False

    @staticmethod
    def to_unicode(obj):
        if isinstance(obj, str):
            return obj.decode('utf8')
        elif not isinstance(obj, unicode):
            return unicode(obj)
        return obj

    def id_query(self, table):
        return table._id > 0

    def represent(self, obj, fieldtype):
        field_is_type = fieldtype.startswith
        if isinstance(obj, CALLABLETYPES):
            obj = obj()
        if isinstance(fieldtype, SQLCustomType):
            return fieldtype.encoder(obj)
        if isinstance(obj, (Expression, Field)):
            raise SyntaxError("non supported on GAE")
        if self.dbengine == 'google:datastore':
            if isinstance(fieldtype, gae.Property):
                return obj
        is_string = isinstance(fieldtype,str)
        is_list = is_string and field_is_type('list:')
        if is_list:
            if not obj:
                obj = []
            if not isinstance(obj, (list, tuple)):
                obj = [obj]
        if obj == '' and not \
                (is_string and fieldtype[:2] in ['st','te', 'pa','up']):
            return None
        if not obj is None:
            if isinstance(obj, list) and not is_list:
                obj = [self.represent(o, fieldtype) for o in obj]
            elif fieldtype in ('integer','bigint','id'):
                obj = long(obj)
            elif fieldtype == 'double':
                obj = float(obj)
            elif is_string and field_is_type('reference'):
                if isinstance(obj, (Row, Reference)):
                    obj = obj['id']
                obj = long(obj)
            elif fieldtype == 'boolean':
                if obj and not str(obj)[0].upper() in '0F':
                    obj = True
                else:
                    obj = False
            elif fieldtype == 'date':
                if not isinstance(obj, datetime.date):
                    (y, m, d) = map(int,str(obj).strip().split('-'))
                    obj = datetime.date(y, m, d)
                elif isinstance(obj,datetime.datetime):
                    (y, m, d) = (obj.year, obj.month, obj.day)
                    obj = datetime.date(y, m, d)
            elif fieldtype == 'time':
                if not isinstance(obj, datetime.time):
                    time_items = map(int,str(obj).strip().split(':')[:3])
                    if len(time_items) == 3:
                        (h, mi, s) = time_items
                    else:
                        (h, mi, s) = time_items + [0]
                    obj = datetime.time(h, mi, s)
            elif fieldtype == 'datetime':
                if not isinstance(obj, datetime.datetime):
                    (y, m, d) = map(int,str(obj)[:10].strip().split('-'))
                    time_items = map(int,str(obj)[11:].strip().split(':')[:3])
                    while len(time_items)<3:
                        time_items.append(0)
                    (h, mi, s) = time_items
                    obj = datetime.datetime(y, m, d, h, mi, s)
            elif fieldtype == 'blob':
                pass
            elif fieldtype == 'json':
                if isinstance(obj, basestring):
                    obj = self.to_unicode(obj)
                    if have_serializers:
                        obj = serializers.loads_json(obj)
                    elif simplejson:
                        obj = simplejson.loads(obj)
                    else:
                        raise RuntimeError("missing simplejson")
            elif is_string and field_is_type('list:string'):
                return map(self.to_unicode,obj)
            elif is_list:
                return map(int,obj)
            else:
                obj = self.to_unicode(obj)
        return obj

    def _insert(self,table,fields):
        return 'insert %s in %s' % (fields, table)

    def _count(self,query,distinct=None):
        return 'count %s' % repr(query)

    def _select(self,query,fields,attributes):
        return 'select %s where %s' % (repr(fields), repr(query))

    def _delete(self,tablename, query):
        return 'delete %s where %s' % (repr(tablename),repr(query))

    def _update(self,tablename,query,fields):
        return 'update %s (%s) where %s' % (repr(tablename),
                                            repr(fields),repr(query))

    def commit(self):
        """
        remember: no transactions on many NoSQL
        """
        pass

    def rollback(self):
        """
        remember: no transactions on many NoSQL
        """
        pass

    def close_connection(self):
        """
        remember: no transactions on many NoSQL
        """
        pass


    # these functions should never be called!
    def OR(self,first,second): raise SyntaxError("Not supported")
    def AND(self,first,second): raise SyntaxError("Not supported")
    def AS(self,first,second): raise SyntaxError("Not supported")
    def ON(self,first,second): raise SyntaxError("Not supported")
    def STARTSWITH(self,first,second=None): raise SyntaxError("Not supported")
    def ENDSWITH(self,first,second=None): raise SyntaxError("Not supported")
    def ADD(self,first,second): raise SyntaxError("Not supported")
    def SUB(self,first,second): raise SyntaxError("Not supported")
    def MUL(self,first,second): raise SyntaxError("Not supported")
    def DIV(self,first,second): raise SyntaxError("Not supported")
    def LOWER(self,first): raise SyntaxError("Not supported")
    def UPPER(self,first): raise SyntaxError("Not supported")
    def EXTRACT(self,first,what): raise SyntaxError("Not supported")
    def LENGTH(self, first): raise SyntaxError("Not supported")
    def AGGREGATE(self,first,what): raise SyntaxError("Not supported")
    def LEFT_JOIN(self): raise SyntaxError("Not supported")
    def RANDOM(self): raise SyntaxError("Not supported")
    def SUBSTRING(self,field,parameters):  raise SyntaxError("Not supported")
    def PRIMARY_KEY(self,key):  raise SyntaxError("Not supported")
    def ILIKE(self,first,second): raise SyntaxError("Not supported")
    def drop(self,table,mode):  raise SyntaxError("Not supported")
    def alias(self,table,alias): raise SyntaxError("Not supported")
    def migrate_table(self,*a,**b): raise SyntaxError("Not supported")
    def distributed_transaction_begin(self,key): raise SyntaxError("Not supported")
    def prepare(self,key): raise SyntaxError("Not supported")
    def commit_prepared(self,key): raise SyntaxError("Not supported")
    def rollback_prepared(self,key): raise SyntaxError("Not supported")
    def concat_add(self,table): raise SyntaxError("Not supported")
    def constraint_name(self, table, fieldname): raise SyntaxError("Not supported")
    def create_sequence_and_triggers(self, query, table, **args): pass
    def log_execute(self,*a,**b): raise SyntaxError("Not supported")
    def execute(self,*a,**b): raise SyntaxError("Not supported")
    def represent_exceptions(self, obj, fieldtype): raise SyntaxError("Not supported")
    def lastrowid(self,table): raise SyntaxError("Not supported")
    def rowslice(self,rows,minimum=0,maximum=None): raise SyntaxError("Not supported")


class GAEF(object):
    def __init__(self,name,op,value,apply):
        self.name=name=='id' and '__key__' or name
        self.op=op
        self.value=value
        self.apply=apply
    def __repr__(self):
        return '(%s %s %s:%s)' % (self.name, self.op, repr(self.value), type(self.value))

class GoogleDatastoreAdapter(NoSQLAdapter):
    """
    NDB:

    You can enable NDB by using adapter_args:

    db = DAL('google:datastore', adapter_args={'ndb_settings':ndb_settings, 'use_ndb':True})

    ndb_settings is optional and can be used for per model caching settings.
    It must be a dict in this form:
    ndb_settings = {<table_name>:{<variable_name>:<variable_value>}}
    See: https://developers.google.com/appengine/docs/python/ndb/cache
    """

    uploads_in_blob = True
    types = {}

    def file_exists(self, filename): pass
    def file_open(self, filename, mode='rb', lock=True): pass
    def file_close(self, fileobj): pass

    REGEX_NAMESPACE = re.compile('.*://(?P<namespace>.+)')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.use_ndb = ('use_ndb' in adapter_args) and adapter_args['use_ndb']
        if self.use_ndb is True:
            self.types.update({
                'boolean': ndb.BooleanProperty,
                'string': (lambda **kwargs: ndb.StringProperty(**kwargs)),
                'text': ndb.TextProperty,
                'json': ndb.TextProperty,
                'password': ndb.StringProperty,
                'blob': ndb.BlobProperty,
                'upload': ndb.StringProperty,
                'integer': ndb.IntegerProperty,
                'bigint': ndb.IntegerProperty,
                'float': ndb.FloatProperty,
                'double': ndb.FloatProperty,
                'decimal': NDBDecimalProperty,
                'date': ndb.DateProperty,
                'time': ndb.TimeProperty,
                'datetime': ndb.DateTimeProperty,
                'id': None,
                'reference': ndb.IntegerProperty,
                'list:string': (lambda **kwargs: ndb.StringProperty(repeated=True,default=None, **kwargs)),
                'list:integer': (lambda **kwargs: ndb.IntegerProperty(repeated=True,default=None, **kwargs)),
                'list:reference': (lambda **kwargs: ndb.IntegerProperty(repeated=True,default=None, **kwargs)),
                })
        else:
            self.types.update({
                'boolean': gae.BooleanProperty,
                'string': (lambda **kwargs: gae.StringProperty(multiline=True, **kwargs)),
                'text': gae.TextProperty,
                'json': gae.TextProperty,
                'password': gae.StringProperty,
                'blob': gae.BlobProperty,
                'upload': gae.StringProperty,
                'integer': gae.IntegerProperty,
                'bigint': gae.IntegerProperty,
                'float': gae.FloatProperty,
                'double': gae.FloatProperty,
                'decimal': GAEDecimalProperty,
                'date': gae.DateProperty,
                'time': gae.TimeProperty,
                'datetime': gae.DateTimeProperty,
                'id': None,
                'reference': gae.IntegerProperty,
                'list:string': (lambda **kwargs: gae.StringListProperty(default=None, **kwargs)),
                'list:integer': (lambda **kwargs: gae.ListProperty(int,default=None, **kwargs)),
                'list:reference': (lambda **kwargs: gae.ListProperty(int,default=None, **kwargs)),
                })
        self.db = db
        self.uri = uri
        self.dbengine = 'google:datastore'
        self.folder = folder
        db['_lastsql'] = ''
        self.db_codec = 'UTF-8'
        self._after_connection = after_connection
        self.pool_size = 0
        match = self.REGEX_NAMESPACE.match(uri)
        if match:
            namespace_manager.set_namespace(match.group('namespace'))
        self.keyfunc = (self.use_ndb and ndb.Key) or Key.from_path

        self.ndb_settings = None
        if 'ndb_settings' in adapter_args:
            self.ndb_settings = adapter_args['ndb_settings']

    def parse_id(self, value, field_type):
        return value

    def create_table(self,table,migrate=True,fake_migrate=False, polymodel=None):
        myfields = {}
        for field in table:
            if isinstance(polymodel,Table) and field.name in polymodel.fields():
                continue
            attr = {}
            if isinstance(field.custom_qualifier, dict):
                #this is custom properties to add to the GAE field declartion
                attr = field.custom_qualifier
            field_type = field.type
            if isinstance(field_type, SQLCustomType):
                ftype = self.types[field_type.native or field_type.type](**attr)
            elif isinstance(field_type, ((self.use_ndb and ndb.Property) or gae.Property)):
                ftype = field_type
            elif field_type.startswith('id'):
                continue
            elif field_type.startswith('decimal'):
                precision, scale = field_type[7:].strip('()').split(',')
                precision = int(precision)
                scale = int(scale)
                dec_cls = (self.use_ndb and NDBDecimalProperty) or GAEDecimalProperty
                ftype = dec_cls(precision, scale, **attr)
            elif field_type.startswith('reference'):
                if field.notnull:
                    attr = dict(required=True)
                referenced = field_type[10:].strip()
                ftype = self.types[field_type[:9]](referenced, **attr)
            elif field_type.startswith('list:reference'):
                if field.notnull:
                    attr['required'] = True
                referenced = field_type[15:].strip()
                ftype = self.types[field_type[:14]](**attr)
            elif field_type.startswith('list:'):
                ftype = self.types[field_type](**attr)
            elif not field_type in self.types\
                 or not self.types[field_type]:
                raise SyntaxError('Field: unknown field type: %s' % field_type)
            else:
                ftype = self.types[field_type](**attr)
            myfields[field.name] = ftype
        if not polymodel:
            model_cls = (self.use_ndb and ndb.Model) or gae.Model
            table._tableobj =  classobj(table._tablename, (model_cls, ), myfields)
            if self.use_ndb:
                # Set NDB caching variables
                if self.ndb_settings and (table._tablename in self.ndb_settings):
                    for k, v in self.ndb_settings.iteritems():
                        setattr(table._tableobj, k, v)
        elif polymodel==True:
            pm_cls = (self.use_ndb and NDBPolyModel) or PolyModel
            table._tableobj = classobj(table._tablename, (pm_cls, ), myfields)
        elif isinstance(polymodel,Table):
            table._tableobj = classobj(table._tablename, (polymodel._tableobj, ), myfields)
        else:
            raise SyntaxError("polymodel must be None, True, a table or a tablename")
        return None

    def expand(self,expression,field_type=None):
        if isinstance(expression,Field):
            if expression.type in ('text', 'blob', 'json'):
                raise SyntaxError('AppEngine does not index by: %s' % expression.type)
            return expression.name
        elif isinstance(expression, (Expression, Query)):
            if not expression.second is None:
                return expression.op(expression.first, expression.second)
            elif not expression.first is None:
                return expression.op(expression.first)
            else:
                return expression.op()
        elif field_type:
                return self.represent(expression,field_type)
        elif isinstance(expression,(list,tuple)):
            return ','.join([self.represent(item,field_type) for item in expression])
        else:
            return str(expression)

    ### TODO from gql.py Expression
    def AND(self,first,second):
        a = self.expand(first)
        b = self.expand(second)
        if b[0].name=='__key__' and a[0].name!='__key__':
            return b+a
        return a+b

    def EQ(self,first,second=None):
        if isinstance(second, Key):
            return [GAEF(first.name,'=',second,lambda a,b:a==b)]
        return [GAEF(first.name,'=',self.represent(second,first.type),lambda a,b:a==b)]

    def NE(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'!=',self.represent(second,first.type),lambda a,b:a!=b)]
        else:
            if not second is None:
                second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'!=',second,lambda a,b:a!=b)]

    def LT(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'<',self.represent(second,first.type),lambda a,b:a<b)]
        else:
            second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'<',second,lambda a,b:a<b)]

    def LE(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'<=',self.represent(second,first.type),lambda a,b:a<=b)]
        else:
            second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'<=',second,lambda a,b:a<=b)]

    def GT(self,first,second=None):
        if first.type != 'id' or second==0 or second == '0':
            return [GAEF(first.name,'>',self.represent(second,first.type),lambda a,b:a>b)]
        else:
            second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'>',second,lambda a,b:a>b)]

    def GE(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'>=',self.represent(second,first.type),lambda a,b:a>=b)]
        else:
            second = Key.from_path(first._tablename, long(second))
            return [GAEF(first.name,'>=',second,lambda a,b:a>=b)]

    def INVERT(self,first):
        return '-%s' % first.name

    def COMMA(self,first,second):
        return '%s, %s' % (self.expand(first),self.expand(second))

    def BELONGS(self,first,second=None):
        if not isinstance(second,(list, tuple, set)):
            raise SyntaxError("Not supported")
        if not self.use_ndb:
            if isinstance(second,set):
                second = list(second)
        if first.type == 'id':
            second = [Key.from_path(first._tablename, int(i)) for i in second]
        return [GAEF(first.name,'in',second,lambda a,b:a in b)]

    def CONTAINS(self,first,second,case_sensitive=False):
        # silently ignoring: GAE can only do case sensitive matches!
        if not first.type.startswith('list:'):
            raise SyntaxError("Not supported")
        return [GAEF(first.name,'=',self.expand(second,first.type[5:]),lambda a,b:b in a)]

    def NOT(self,first):
        nops = { self.EQ: self.NE,
                 self.NE: self.EQ,
                 self.LT: self.GE,
                 self.GT: self.LE,
                 self.LE: self.GT,
                 self.GE: self.LT}
        if not isinstance(first,Query):
            raise SyntaxError("Not suported")
        nop = nops.get(first.op,None)
        if not nop:
            raise SyntaxError("Not suported %s" % first.op.__name__)
        first.op = nop
        return self.expand(first)

    def truncate(self,table,mode):
        self.db(self.db._adapter.id_query(table)).delete()

    GAE_FILTER_OPTIONS = {
        '=': lambda q, t, p, v: q.filter(getattr(t,p) == v),
        '>': lambda q, t, p, v: q.filter(getattr(t,p) > v),
        '<': lambda q, t, p, v: q.filter(getattr(t,p) < v),
        '<=': lambda q, t, p, v: q.filter(getattr(t,p) <= v),
        '>=': lambda q, t, p, v: q.filter(getattr(t,p) >= v),
        '!=': lambda q, t, p, v: q.filter(getattr(t,p) != v),
        'in': lambda q, t, p, v: q.filter(getattr(t,p).IN(v)),
        }

    def filter(self, query, tableobj, prop, op, value):
        return self.GAE_FILTER_OPTIONS[op](query, tableobj, prop, value)

    def select_raw(self,query,fields=None,attributes=None):
        db = self.db
        fields = fields or []
        attributes = attributes or {}
        args_get = attributes.get
        new_fields = []
        for item in fields:
            if isinstance(item,SQLALL):
                new_fields += item._table
            else:
                new_fields.append(item)
        fields = new_fields
        if query:
            tablename = self.get_table(query)
        elif fields:
            tablename = fields[0].tablename
            query = db._adapter.id_query(fields[0].table)
        else:
            raise SyntaxError("Unable to determine a tablename")

        if query:
            if use_common_filters(query):
                query = self.common_filter(query,[tablename])

        #tableobj is a GAE/NDB Model class (or subclass)
        tableobj = db[tablename]._tableobj
        filters = self.expand(query)

        projection = None
        if len(db[tablename].fields) == len(fields):
            #getting all fields, not a projection query
            projection = None
        elif args_get('projection') == True:
            projection = []
            for f in fields:
                if f.type in ['text', 'blob', 'json']:
                    raise SyntaxError(
                        "text and blob field types not allowed in projection queries")
                else:
                    projection.append(f.name)
        elif args_get('filterfields') == True:
            projection = []
            for f in fields:
                projection.append(f.name)

        # real projection's can't include 'id'.
        # it will be added to the result later
        query_projection = [
            p for p in projection if \
                p != db[tablename]._id.name] if projection and \
                args_get('projection') == True\
                else None

        cursor = None
        if isinstance(args_get('reusecursor'), str):
            cursor = args_get('reusecursor')
        if self.use_ndb:
            qo = ndb.QueryOptions(projection=query_projection, cursor=cursor)
            items = tableobj.query(default_options=qo)
        else:
            items = gae.Query(tableobj, projection=query_projection,
                          cursor=cursor)

        for filter in filters:
            if args_get('projection') == True and \
               filter.name in query_projection and \
               filter.op in ['=', '<=', '>=']:
                raise SyntaxError(
                    "projection fields cannot have equality filters")
            if filter.name=='__key__' and filter.op=='>' and filter.value==0:
                continue
            elif filter.name=='__key__' and filter.op=='=':
                if filter.value==0:
                    items = []
                elif isinstance(filter.value, (self.use_ndb and ndb.Key) or Key):
                    # key qeuries return a class instance,
                    # can't use projection
                    # extra values will be ignored in post-processing later
                    item = filter.value.get() if self.use_ndb else tableobj.get(filter.value)
                    items = (item and [item]) or []
                else:
                    # key qeuries return a class instance,
                    # can't use projection
                    # extra values will be ignored in post-processing later
                    item = tableobj.get_by_id(filter.value)
                    items = (item and [item]) or []
            elif isinstance(items,list): # i.e. there is a single record!
                items = [i for i in items if filter.apply(
                        getattr(item,filter.name),filter.value)]
            else:
                if filter.name=='__key__' and filter.op != 'in':
                    if self.use_ndb:
                        items.order(tableobj._key)
                    else:
                        items.order('__key__')
                items = self.filter(items, tableobj, filter.name, 
                                    filter.op, filter.value) \
                                    if self.use_ndb else \
                        items.filter('%s %s' % (filter.name,filter.op), 
                                     filter.value)

        if not isinstance(items,list):
            if args_get('left', None):
                raise SyntaxError('Set: no left join in appengine')
            if args_get('groupby', None):
                raise SyntaxError('Set: no groupby in appengine')
            orderby = args_get('orderby', False)
            if orderby:
                ### THIS REALLY NEEDS IMPROVEMENT !!!
                if isinstance(orderby, (list, tuple)):
                    orderby = xorify(orderby)
                if isinstance(orderby,Expression):
                    orderby = self.expand(orderby)
                orders = orderby.split(', ')
                for order in orders:
                    if self.use_ndb:
                        #TODO There must be a better way
                        def make_order(o):
                            s = str(o)
                            desc = s[0] == '-'
                            s = (desc and s[1:]) or s
                            return  (desc and  -getattr(tableobj, s)) or getattr(tableobj, s)
                        _order = {'-id':-tableobj._key,'id':tableobj._key}.get(order)
                        if _order is None:
                            _order = make_order(order)
                        items = items.order(_order)
                    else:
                        order={'-id':'-__key__','id':'__key__'}.get(order,order)
                        items = items.order(order)
            if args_get('limitby', None):
                (lmin, lmax) = attributes['limitby']
                (limit, offset) = (lmax - lmin, lmin)
                if self.use_ndb:
                    rows, cursor, more = items.fetch_page(limit,offset=offset)
                else:
                    rows =  items.fetch(limit,offset=offset)
                #cursor is only useful if there was a limit and we didn't return
                # all results
                if args_get('reusecursor'):
                    db['_lastcursor'] = cursor if self.use_ndb else items.cursor()
                items = rows
        return (items, tablename, projection or db[tablename].fields)

    def select(self,query,fields,attributes):
        """
        This is the GAE version of select.  some notes to consider:
         - db['_lastsql'] is not set because there is not SQL statement string
           for a GAE query
         - 'nativeRef' is a magical fieldname used for self references on GAE
         - optional attribute 'projection' when set to True will trigger
           use of the GAE projection queries.  note that there are rules for
           what is accepted imposed by GAE: each field must be indexed,
           projection queries cannot contain blob or text fields, and you
           cannot use == and also select that same field.  see https://developers.google.com/appengine/docs/python/datastore/queries#Query_Projection
         - optional attribute 'filterfields' when set to True web2py will only
           parse the explicitly listed fields into the Rows object, even though
           all fields are returned in the query.  This can be used to reduce
           memory usage in cases where true projection queries are not
           usable.
         - optional attribute 'reusecursor' allows use of cursor with queries
           that have the limitby attribute.  Set the attribute to True for the
           first query, set it to the value of db['_lastcursor'] to continue
           a previous query.  The user must save the cursor value between
           requests, and the filters must be identical.  It is up to the user
           to follow google's limitations: https://developers.google.com/appengine/docs/python/datastore/queries#Query_Cursors
        """

        (items, tablename, fields) = self.select_raw(query,fields,attributes)
        # self.db['_lastsql'] = self._select(query,fields,attributes)
        rows = [[(t==self.db[tablename]._id.name and item) or \
                 (t=='nativeRef' and item) or getattr(item, t) \
                     for t in fields] for item in items]
        colnames = ['%s.%s' % (tablename, t) for t in fields]
        processor = attributes.get('processor',self.parse)
        return processor(rows,fields,colnames,False)

    def count(self,query,distinct=None,limit=None):
        if distinct:
            raise RuntimeError("COUNT DISTINCT not supported")
        (items, tablename, fields) = self.select_raw(query)
        # self.db['_lastsql'] = self._count(query)
        try:
            return len(items)
        except TypeError:
            return items.count(limit=limit)

    def delete(self,tablename, query):
        """
        This function was changed on 2010-05-04 because according to
        http://code.google.com/p/googleappengine/issues/detail?id=3119
        GAE no longer supports deleting more than 1000 records.
        """
        # self.db['_lastsql'] = self._delete(tablename,query)
        (items, tablename, fields) = self.select_raw(query)
        # items can be one item or a query
        if not isinstance(items,list):
            #use a keys_only query to ensure that this runs as a datastore
            # small operations
            leftitems = items.fetch(1000, keys_only=True)
            counter = 0
            while len(leftitems):
                counter += len(leftitems)
                if self.use_ndb:
                    ndb.delete_multi(leftitems)
                else:
                    gae.delete(leftitems)
                leftitems = items.fetch(1000, keys_only=True)
        else:
            counter = len(items)
            if self.use_ndb:
                ndb.delete_multi([item.key for item in items])
            else:
                gae.delete(items)
        return counter

    def update(self,tablename,query,update_fields):
        # self.db['_lastsql'] = self._update(tablename,query,update_fields)
        (items, tablename, fields) = self.select_raw(query)
        counter = 0
        for item in items:
            for field, value in update_fields:
                setattr(item, field.name, self.represent(value,field.type))
            item.put()
            counter += 1
        LOGGER.info(str(counter))
        return counter

    def insert(self,table,fields):
        dfields=dict((f.name,self.represent(v,f.type)) for f,v in fields)
        # table._db['_lastsql'] = self._insert(table,fields)
        tmp = table._tableobj(**dfields)
        tmp.put()
        key = tmp.key if self.use_ndb else tmp.key()
        rid = Reference(key.id())
        (rid._table, rid._record, rid._gaekey) = (table, None, key)
        return rid

    def bulk_insert(self,table,items):
        parsed_items = []
        for item in items:
            dfields=dict((f.name,self.represent(v,f.type)) for f,v in item)
            parsed_items.append(table._tableobj(**dfields))
        if self.use_ndb:
            ndb.put_multi(parsed_items)
        else:
            gae.put(parsed_items)
        return True

def uuid2int(uuidv):
    return uuid.UUID(uuidv).int

def int2uuid(n):
    return str(uuid.UUID(int=n))

class CouchDBAdapter(NoSQLAdapter):
    drivers = ('couchdb',)

    uploads_in_blob = True
    types = {
                'boolean': bool,
                'string': str,
                'text': str,
                'json': str,
                'password': str,
                'blob': str,
                'upload': str,
                'integer': long,
                'bigint': long,
                'float': float,
                'double': float,
                'date': datetime.date,
                'time': datetime.time,
                'datetime': datetime.datetime,
                'id': long,
                'reference': long,
                'list:string': list,
                'list:integer': list,
                'list:reference': list,
        }

    def file_exists(self, filename): pass
    def file_open(self, filename, mode='rb', lock=True): pass
    def file_close(self, fileobj): pass

    def expand(self,expression,field_type=None):
        if isinstance(expression,Field):
            if expression.type=='id':
                return "%s._id" % expression.tablename
        return BaseAdapter.expand(self,expression,field_type)

    def AND(self,first,second):
        return '(%s && %s)' % (self.expand(first),self.expand(second))

    def OR(self,first,second):
        return '(%s || %s)' % (self.expand(first),self.expand(second))

    def EQ(self,first,second):
        if second is None:
            return '(%s == null)' % self.expand(first)
        return '(%s == %s)' % (self.expand(first),self.expand(second,first.type))

    def NE(self,first,second):
        if second is None:
            return '(%s != null)' % self.expand(first)
        return '(%s != %s)' % (self.expand(first),self.expand(second,first.type))

    def COMMA(self,first,second):
        return '%s + %s' % (self.expand(first),self.expand(second))

    def represent(self, obj, fieldtype):
        value = NoSQLAdapter.represent(self, obj, fieldtype)
        if fieldtype=='id':
            return repr(str(long(value)))
        elif fieldtype in ('date','time','datetime','boolean'):
            return serializers.json(value)
        return repr(not isinstance(value,unicode) and value \
                        or value and value.encode('utf8'))

    def __init__(self,db,uri='couchdb://127.0.0.1:5984',
                 pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.db = db
        self.uri = uri
        if do_connect: self.find_driver(adapter_args)
        self.dbengine = 'couchdb'
        self.folder = folder
        db['_lastsql'] = ''
        self.db_codec = 'UTF-8'
        self._after_connection = after_connection
        self.pool_size = pool_size

        url='http://'+uri[10:]
        def connector(url=url,driver_args=driver_args):
            return self.driver.Server(url,**driver_args)
        self.reconnect(connector,cursor=False)

    def create_table(self, table, migrate=True, fake_migrate=False, polymodel=None):
        if migrate:
            try:
                self.connection.create(table._tablename)
            except:
                pass

    def insert(self,table,fields):
        id = uuid2int(web2py_uuid())
        ctable = self.connection[table._tablename]
        values = dict((k.name,self.represent(v,k.type)) for k,v in fields)
        values['_id'] = str(id)
        ctable.save(values)
        return id

    def _select(self,query,fields,attributes):
        if not isinstance(query,Query):
            raise SyntaxError("Not Supported")
        for key in set(attributes.keys())-SELECT_ARGS:
            raise SyntaxError('invalid select attribute: %s' % key)
        new_fields=[]
        for item in fields:
            if isinstance(item,SQLALL):
                new_fields += item._table
            else:
                new_fields.append(item)
        def uid(fd):
            return fd=='id' and '_id' or fd
        def get(row,fd):
            return fd=='id' and long(row['_id']) or row.get(fd,None)
        fields = new_fields
        tablename = self.get_table(query)
        fieldnames = [f.name for f in (fields or self.db[tablename])]
        colnames = ['%s.%s' % (tablename,k) for k in fieldnames]
        fields = ','.join(['%s.%s' % (tablename,uid(f)) for f in fieldnames])
        fn="(function(%(t)s){if(%(query)s)emit(%(order)s,[%(fields)s]);})" %\
            dict(t=tablename,
                 query=self.expand(query),
                 order='%s._id' % tablename,
                 fields=fields)
        return fn, colnames

    def select(self,query,fields,attributes):
        if not isinstance(query,Query):
            raise SyntaxError("Not Supported")
        fn, colnames = self._select(query,fields,attributes)
        tablename = colnames[0].split('.')[0]
        ctable = self.connection[tablename]
        rows = [cols['value'] for cols in ctable.query(fn)]
        processor = attributes.get('processor',self.parse)
        return processor(rows,fields,colnames,False)

    def delete(self,tablename,query):
        if not isinstance(query,Query):
            raise SyntaxError("Not Supported")
        if query.first.type=='id' and query.op==self.EQ:
            id = query.second
            tablename = query.first.tablename
            assert(tablename == query.first.tablename)
            ctable = self.connection[tablename]
            try:
                del ctable[str(id)]
                return 1
            except couchdb.http.ResourceNotFound:
                return 0
        else:
            tablename = self.get_table(query)
            rows = self.select(query,[self.db[tablename]._id],{})
            ctable = self.connection[tablename]
            for row in rows:
                del ctable[str(row.id)]
            return len(rows)

    def update(self,tablename,query,fields):
        if not isinstance(query,Query):
            raise SyntaxError("Not Supported")
        if query.first.type=='id' and query.op==self.EQ:
            id = query.second
            tablename = query.first.tablename
            ctable = self.connection[tablename]
            try:
                doc = ctable[str(id)]
                for key,value in fields:
                    doc[key.name] = self.represent(value,self.db[tablename][key.name].type)
                ctable.save(doc)
                return 1
            except couchdb.http.ResourceNotFound:
                return 0
        else:
            tablename = self.get_table(query)
            rows = self.select(query,[self.db[tablename]._id],{})
            ctable = self.connection[tablename]
            table = self.db[tablename]
            for row in rows:
                doc = ctable[str(row.id)]
                for key,value in fields:
                    doc[key.name] = self.represent(value,table[key.name].type)
                ctable.save(doc)
            return len(rows)

    def count(self,query,distinct=None):
        if distinct:
            raise RuntimeError("COUNT DISTINCT not supported")
        if not isinstance(query,Query):
            raise SyntaxError("Not Supported")
        tablename = self.get_table(query)
        rows = self.select(query,[self.db[tablename]._id],{})
        return len(rows)

def cleanup(text):
    """
    validates that the given text is clean: only contains [0-9a-zA-Z_]
    """
    if not REGEX_ALPHANUMERIC.match(text):
        raise SyntaxError('invalid table or field name: %s' % text)
    return text

class MongoDBAdapter(NoSQLAdapter):
    native_json = True
    drivers = ('pymongo',)

    uploads_in_blob = False

    types = {
                'boolean': bool,
                'string': str,
                'text': str,
                'json': str,
                'password': str,
                'blob': str,
                'upload': str,
                'integer': long,
                'bigint': long,
                'float': float,
                'double': float,
                'date': datetime.date,
                'time': datetime.time,
                'datetime': datetime.datetime,
                'id': long,
                'reference': long,
                'list:string': list,
                'list:integer': list,
                'list:reference': list,
        }

    error_messages = {"javascript_needed": "This must yet be replaced" +
                      " with javascript in order to work."}

    def __init__(self,db,uri='mongodb://127.0.0.1:5984/db',
                 pool_size=0, folder=None, db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):

        self.db = db
        self.uri = uri
        if do_connect: self.find_driver(adapter_args)
        import random
        from bson.objectid import ObjectId
        from bson.son import SON
        import pymongo.uri_parser

        m = pymongo.uri_parser.parse_uri(uri)

        self.SON = SON
        self.ObjectId = ObjectId
        self.random = random

        self.dbengine = 'mongodb'
        self.folder = folder
        db['_lastsql'] = ''
        self.db_codec = 'UTF-8'
        self._after_connection = after_connection
        self.pool_size = pool_size
        #this is the minimum amount of replicates that it should wait
        # for on insert/update
        self.minimumreplication = adapter_args.get('minimumreplication',0)
        # by default all inserts and selects are performand asynchronous,
        # but now the default is
        # synchronous, except when overruled by either this default or
        # function parameter
        self.safe = adapter_args.get('safe',True)
        # load user setting for uploads in blob storage
        self.uploads_in_blob = adapter_args.get('uploads_in_blob', False)

        if isinstance(m,tuple):
            m = {"database" : m[1]}
        if m.get('database')==None:
            raise SyntaxError("Database is required!")

        def connector(uri=self.uri,m=m):
            # Connection() is deprecated
            if hasattr(self.driver, "MongoClient"):
                Connection = self.driver.MongoClient
            else:
                Connection = self.driver.Connection
            return Connection(uri)[m.get('database')]

        self.reconnect(connector,cursor=False)

    def object_id(self, arg=None):
        """ Convert input to a valid Mongodb ObjectId instance

        self.object_id("<random>") -> ObjectId (not unique) instance """
        if not arg:
            arg = 0
        if isinstance(arg, basestring):
            # we assume an integer as default input
            rawhex = len(arg.replace("0x", "").replace("L", "")) == 24
            if arg.isdigit() and (not rawhex):
                arg = int(arg)
            elif arg == "<random>":
                arg = int("0x%sL" % \
                "".join([self.random.choice("0123456789abcdef") \
                for x in range(24)]), 0)
            elif arg.isalnum():
                if not arg.startswith("0x"):
                    arg = "0x%s" % arg
                try:
                    arg = int(arg, 0)
                except ValueError, e:
                    raise ValueError(
                            "invalid objectid argument string: %s" % e)
            else:
                raise ValueError("Invalid objectid argument string. " +
                                 "Requires an integer or base 16 value")
        elif isinstance(arg, self.ObjectId):
            return arg

        if not isinstance(arg, (int, long)):
            raise TypeError("object_id argument must be of type " +
                            "ObjectId or an objectid representable integer")
        hexvalue = hex(arg)[2:].rstrip('L').zfill(24)
        return self.ObjectId(hexvalue)

    def parse_reference(self, value, field_type):
        # here we have to check for ObjectID before base parse
        if isinstance(value, self.ObjectId):
            value = long(str(value), 16)
        return super(MongoDBAdapter,
                     self).parse_reference(value, field_type)

    def parse_id(self, value, field_type):
        if isinstance(value, self.ObjectId):
            value = long(str(value), 16)
        return super(MongoDBAdapter,
                     self).parse_id(value, field_type)

    def represent(self, obj, fieldtype):
        # the base adatpter does not support MongoDB ObjectId
        if isinstance(obj, self.ObjectId):
            value = obj
        else:
            value = NoSQLAdapter.represent(self, obj, fieldtype)
        if isinstance(obj, (list, tuple)) and \
                (not fieldtype == "json" or fieldtype.startswith('list:')):
            return value
        # reference types must be convert to ObjectID
        if fieldtype  =='date':
            if value == None:
                return value
            # this piece of data can be stripped off based on the fieldtype
            t = datetime.time(0, 0, 0)
            # mongodb doesn't has a date object and so it must datetime,
            # string or integer
            return datetime.datetime.combine(value, t)
        elif fieldtype == 'time':
            if value == None:
                return value
            # this piece of data can be stripped of based on the fieldtype
            d = datetime.date(2000, 1, 1)
            # mongodb doesn't has a  time object and so it must datetime,
            # string or integer
            return datetime.datetime.combine(d, value)
        elif fieldtype == "blob":
            if value== None:
                return value
            from bson import Binary
            if not isinstance(value, Binary):
                if not isinstance(value, basestring):
                    return Binary(str(value))
                return Binary(value)
            return value
        elif (isinstance(fieldtype, basestring) and
              fieldtype.startswith('list:')):
            if fieldtype.startswith('list:reference'):
                newval = []
                for v in value:
                    newval.append(self.object_id(v))
                return newval
            return value
        elif ((isinstance(fieldtype, basestring) and
               fieldtype.startswith("reference")) or
               (isinstance(fieldtype, Table)) or fieldtype=="id"):
            value = self.object_id(value)
        return value

    def create_table(self, table, migrate=True, fake_migrate=False,
                     polymodel=None, isCapped=False):
        if isCapped:
            raise RuntimeError("Not implemented")

    def count(self, query, distinct=None, snapshot=True):
        if distinct:
            raise RuntimeError("COUNT DISTINCT not supported")
        if not isinstance(query,Query):
            raise SyntaxError("Not Supported")
        tablename = self.get_table(query)
        return long(self.select(query,[self.db[tablename]._id], {},
                                count=True,snapshot=snapshot)['count'])
        # Maybe it would be faster if we just implemented the pymongo
        # .count() function which is probably quicker?
        # therefor call __select() connection[table].find(query).count()
        # Since this will probably reduce the return set?

    def expand(self, expression, field_type=None):
        if isinstance(expression, Query):
            # any query using 'id':=
            # set name as _id (as per pymongo/mongodb primary key)
            # convert second arg to an objectid field
            # (if its not already)
            # if second arg is 0 convert to objectid
            if isinstance(expression.first,Field) and \
                    ((expression.first.type == 'id') or \
                    ("reference" in expression.first.type)):
                if expression.first.type == 'id':
                    expression.first.name = '_id'
                # cast to Mongo ObjectId
                if isinstance(expression.second, (tuple, list, set)):
                    expression.second = [self.object_id(item) for
                                         item in expression.second]
                else:
                    expression.second = self.object_id(expression.second)
                result = expression.op(expression.first, expression.second)

        if isinstance(expression, Field):
            if expression.type=='id':
                result = "_id"
            else:
                result =  expression.name
        elif isinstance(expression, (Expression, Query)):
            if not expression.second is None:
                result = expression.op(expression.first, expression.second)
            elif not expression.first is None:
                result = expression.op(expression.first)
            elif not isinstance(expression.op, str):
                result = expression.op()
            else:
                result = expression.op
        elif field_type:
            result = self.represent(expression,field_type)
        elif isinstance(expression,(list,tuple)):
            result = ','.join(self.represent(item,field_type) for
                              item in expression)
        else:
            result = expression
        return result

    def drop(self, table, mode=''):
        ctable = self.connection[table._tablename]
        ctable.drop()

    def truncate(self, table, mode, safe=None):
        if safe == None:
            safe=self.safe
        ctable = self.connection[table._tablename]
        ctable.remove(None, safe=True)

    def _select(self, query, fields, attributes):
        if 'for_update' in attributes:
            logging.warn('mongodb does not support for_update')
        for key in set(attributes.keys())-set(('limitby',
                                               'orderby','for_update')):
            if attributes[key]!=None:
                logging.warn('select attribute not implemented: %s' % key)

        new_fields=[]
        mongosort_list = []

        # try an orderby attribute
        orderby = attributes.get('orderby', False)
        limitby = attributes.get('limitby', False)
        # distinct = attributes.get('distinct', False)
        if orderby:
            if isinstance(orderby, (list, tuple)):
                orderby = xorify(orderby)

            # !!!! need to add 'random'
            for f in self.expand(orderby).split(','):
                if f.startswith('-'):
                    mongosort_list.append((f[1:], -1))
                else:
                    mongosort_list.append((f, 1))
        if limitby:
            limitby_skip, limitby_limit = limitby[0], int(limitby[1])
        else:
            limitby_skip = limitby_limit = 0

        mongofields_dict = self.SON()
        mongoqry_dict = {}
        for item in fields:
            if isinstance(item, SQLALL):
                new_fields += item._table
            else:
                new_fields.append(item)
        fields = new_fields
        if isinstance(query,Query):
            tablename = self.get_table(query)
        elif len(fields) != 0:
            tablename = fields[0].tablename
        else:
            raise SyntaxError("The table name could not be found in " +
                              "the query nor from the select statement.")
        mongoqry_dict = self.expand(query)
        fields = fields or self.db[tablename]
        for field in fields:
            mongofields_dict[field.name] = 1

        return tablename, mongoqry_dict, mongofields_dict, mongosort_list, \
            limitby_limit, limitby_skip

    def select(self, query, fields, attributes, count=False,
               snapshot=False):
        # TODO: support joins
        tablename, mongoqry_dict, mongofields_dict, mongosort_list, \
        limitby_limit, limitby_skip = self._select(query, fields, attributes)
        ctable = self.connection[tablename]

        if count:
            return {'count' : ctable.find(
                    mongoqry_dict, mongofields_dict,
                    skip=limitby_skip, limit=limitby_limit,
                    sort=mongosort_list, snapshot=snapshot).count()}
        else:
            # pymongo cursor object
            mongo_list_dicts = ctable.find(mongoqry_dict,
                                mongofields_dict, skip=limitby_skip,
                                limit=limitby_limit, sort=mongosort_list,
                                snapshot=snapshot)
        rows = []
        # populate row in proper order
        # Here we replace ._id with .id to follow the standard naming
        colnames = []
        newnames = []
        for field in fields:
            colname = str(field)
            colnames.append(colname)
            tablename, fieldname = colname.split(".")
            if fieldname == "_id":
                # Mongodb reserved uuid key
                field.name = "id"
            newnames.append(".".join((tablename, field.name)))

        for record in mongo_list_dicts:
            row=[]
            for colname in colnames:
                tablename, fieldname = colname.split(".")
                # switch to Mongo _id uuids for retrieving
                # record id's
                if fieldname == "id": fieldname = "_id"
                if fieldname in record:
                    value = record[fieldname]
                else:
                    value = None
                row.append(value)
            rows.append(row)

        processor = attributes.get('processor', self.parse)
        result = processor(rows, fields, newnames, False)
        return result

    def _insert(self, table, fields):
        values = dict()
        for k, v in fields:
            if not k.name in ["id", "safe"]:
                fieldname = k.name
                fieldtype = table[k.name].type
                values[fieldname] = self.represent(v, fieldtype)
        return values

    # Safe determines whether a asynchronious request is done or a
    # synchronious action is done
    # For safety, we use by default synchronous requests
    def insert(self, table, fields, safe=None):
        if safe==None:
            safe = self.safe
        ctable = self.connection[table._tablename]
        values = self._insert(table, fields)
        ctable.insert(values, safe=safe)
        return long(str(values['_id']), 16)

    #this function returns a dict with the where clause and update fields
    def _update(self, tablename, query, fields):
        if not isinstance(query, Query):
            raise SyntaxError("Not Supported")
        filter = None
        if query:
            filter = self.expand(query)
        # do not try to update id fields to avoid backend errors
        modify = {'$set': dict((k.name, self.represent(v, k.type)) for
                  k, v in fields if (not k.name in ("_id", "id")))}
        return modify, filter

    def update(self, tablename, query, fields, safe=None):
        if safe == None:
            safe = self.safe
        # return amount of adjusted rows or zero, but no exceptions
        # @ related not finding the result
        if not isinstance(query, Query):
            raise RuntimeError("Not implemented")
        amount = self.count(query, False)
        modify, filter = self._update(tablename, query, fields)
        try:
            result = self.connection[tablename].update(filter,
                       modify, multi=True, safe=safe)
            if safe:
                try:
                    # if result count is available fetch it
                    return result["n"]
                except (KeyError, AttributeError, TypeError):
                    return amount
            else:
                return amount
        except Exception, e:
            # TODO Reverse update query to verifiy that the query succeded
            raise RuntimeError("uncaught exception when updating rows: %s" % e)

    def _delete(self, tablename, query):
        if not isinstance(query, Query):
            raise RuntimeError("query type %s is not supported" % \
                               type(query))
        return self.expand(query)

    def delete(self, tablename, query, safe=None):
        if safe is None:
            safe = self.safe
        amount = 0
        amount = self.count(query, False)
        filter = self._delete(tablename, query)
        self.connection[tablename].remove(filter, safe=safe)
        return amount

    def bulk_insert(self, table, items):
        return [self.insert(table,item) for item in items]

    ## OPERATORS
    def INVERT(self, first):
        #print "in invert first=%s" % first
        return '-%s' % self.expand(first)

    # TODO This will probably not work:(
    def NOT(self, first):
        return {'$not': self.expand(first)}

    def AND(self,first,second):
        # pymongo expects: .find({'$and': [{'x':'1'}, {'y':'2'}]})
        return {'$and': [self.expand(first),self.expand(second)]}

    def OR(self,first,second):
        # pymongo expects: .find({'$or': [{'name':'1'}, {'name':'2'}]})
        return {'$or': [self.expand(first),self.expand(second)]}

    def BELONGS(self, first, second):
        if isinstance(second, str):
            return {self.expand(first) : {"$in" : [ second[:-1]]} }
        elif second==[] or second==() or second==set():
            return {1:0}
        items = [self.expand(item, first.type) for item in second]
        return {self.expand(first) : {"$in" : items} }

    def EQ(self,first,second=None):
        result = {}
        result[self.expand(first)] = self.expand(second)
        return result

    def NE(self, first, second=None):
        result = {}
        result[self.expand(first)] = {'$ne': self.expand(second)}
        return result

    def LT(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s < None" % first)
        result = {}
        result[self.expand(first)] = {'$lt': self.expand(second)}
        return result

    def LE(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s <= None" % first)
        result = {}
        result[self.expand(first)] = {'$lte': self.expand(second)}
        return result

    def GT(self,first,second):
        result = {}
        result[self.expand(first)] = {'$gt': self.expand(second)}
        return result

    def GE(self,first,second=None):
        if second is None:
            raise RuntimeError("Cannot compare %s >= None" % first)
        result = {}
        result[self.expand(first)] = {'$gte': self.expand(second)}
        return result

    def ADD(self, first, second):
        raise NotImplementedError(self.error_messages["javascript_needed"])
        return '%s + %s' % (self.expand(first),
                            self.expand(second, first.type))

    def SUB(self, first, second):
        raise NotImplementedError(self.error_messages["javascript_needed"])
        return '(%s - %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def MUL(self, first, second):
        raise NotImplementedError(self.error_messages["javascript_needed"])
        return '(%s * %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def DIV(self, first, second):
        raise NotImplementedError(self.error_messages["javascript_needed"])
        return '(%s / %s)' % (self.expand(first),
                              self.expand(second, first.type))

    def MOD(self, first, second):
        raise NotImplementedError(self.error_messages["javascript_needed"])
        return '(%s %% %s)' % (self.expand(first),
                               self.expand(second, first.type))

    def AS(self, first, second):
        raise NotImplementedError(self.error_messages["javascript_needed"])
        return '%s AS %s' % (self.expand(first), second)

    # We could implement an option that simulates a full featured SQL
    # database. But I think the option should be set explicit or
    # implemented as another library.
    def ON(self, first, second):
        raise NotImplementedError("This is not possible in NoSQL" +
                                  " but can be simulated with a wrapper.")
        return '%s ON %s' % (self.expand(first), self.expand(second))

    # BLOW ARE TWO IMPLEMENTATIONS OF THE SAME FUNCITONS
    # WHICH ONE IS BEST?

    def COMMA(self, first, second):
        return '%s, %s' % (self.expand(first), self.expand(second))

    def LIKE(self, first, second):
        #escaping regex operators?
        return {self.expand(first): ('%s' % \
                self.expand(second, 'string').replace('%','/'))}

    def ILIKE(self, first, second):
        val = second if isinstance(second,self.ObjectId) else {
            '$regex': second.replace('%', ''), '$options': 'i'}
        return {self.expand(first): val}

    def STARTSWITH(self, first, second):
        #escaping regex operators?
        return {self.expand(first): ('/^%s/' % \
        self.expand(second, 'string'))}

    def ENDSWITH(self, first, second):
        #escaping regex operators?
        return {self.expand(first): ('/%s^/' % \
        self.expand(second, 'string'))}

    def CONTAINS(self, first, second, case_sensitive=False):
        # silently ignore, only case sensitive
        # There is a technical difference, but mongodb doesn't support
        # that, but the result will be the same
        val = second if isinstance(second,self.ObjectId) else \
            {'$regex':".*" + re.escape(self.expand(second, 'string')) + ".*"}
        return {self.expand(first) : val}

    def LIKE(self, first, second):
        import re
        return {self.expand(first): {'$regex': \
                re.escape(self.expand(second,
                                      'string')).replace('%','.*')}}

    #TODO verify full compatibilty with official SQL Like operator
    def STARTSWITH(self, first, second):
        #TODO  Solve almost the same problem as with endswith
        import re
        return {self.expand(first): {'$regex' : '^' +
                                     re.escape(self.expand(second,
                                                           'string'))}}

    #TODO verify full compatibilty with official SQL Like operator
    def ENDSWITH(self, first, second):
        #escaping regex operators?
        #TODO if searched for a name like zsa_corbitt and the function
        # is endswith('a') then this is also returned.
        # Aldo it end with a t
        import re
        return {self.expand(first): {'$regex': \
        re.escape(self.expand(second, 'string')) + '$'}}

    #TODO verify full compatibilty with official oracle contains operator
    def CONTAINS(self, first, second, case_sensitive=False):
        # silently ignore, only case sensitive
        #There is a technical difference, but mongodb doesn't support
        # that, but the result will be the same
        #TODO contains operators need to be transformed to Regex
        return {self.expand(first) : {'$regex': \
        ".*" + re.escape(self.expand(second, 'string')) + ".*"}}


class IMAPAdapter(NoSQLAdapter):
    drivers = ('imaplib',)

    """ IMAP server adapter

      This class is intended as an interface with
    email IMAP servers to perform simple queries in the
    web2py DAL query syntax, so email read, search and
    other related IMAP mail services (as those implemented
    by brands like Google(r), and Yahoo!(r)
    can be managed from web2py applications.

    The code uses examples by Yuji Tomita on this post:
    http://yuji.wordpress.com/2011/06/22/python-imaplib-imap-example-with-gmail/#comment-1137
    and is based in docs for Python imaplib, python email
    and email IETF's (i.e. RFC2060 and RFC3501)

    This adapter was tested with a small set of operations with Gmail(r). Other
    services requests could raise command syntax and response data issues.

    It creates its table and field names "statically",
    meaning that the developer should leave the table and field
    definitions to the DAL instance by calling the adapter's
    .define_tables() method. The tables are defined with the
    IMAP server mailbox list information.

    .define_tables() returns a dictionary mapping dal tablenames
    to the server mailbox names with the following structure:

    {<tablename>: str <server mailbox name>}

    Here is a list of supported fields:

    Field       Type            Description
    ################################################################
    uid         string
    answered    boolean        Flag
    created     date
    content     list:string    A list of dict text or html parts
    to          string
    cc          string
    bcc         string
    size        integer        the amount of octets of the message*
    deleted     boolean        Flag
    draft       boolean        Flag
    flagged     boolean        Flag
    sender      string
    recent      boolean        Flag
    seen        boolean        Flag
    subject     string
    mime        string         The mime header declaration
    email       string         The complete RFC822 message**
    attachments <type list>    Each non text part as dict
    encoding    string         The main detected encoding

    *At the application side it is measured as the length of the RFC822
    message string

    WARNING: As row id's are mapped to email sequence numbers,
    make sure your imap client web2py app does not delete messages
    during select or update actions, to prevent
    updating or deleting different messages.
    Sequence numbers change whenever the mailbox is updated.
    To avoid this sequence numbers issues, it is recommended the use
    of uid fields in query references (although the update and delete
    in separate actions rule still applies).

    # This is the code recommended to start imap support
    # at the app's model:

    imapdb = DAL("imap://user:password@server:port", pool_size=1) # port 993 for ssl
    imapdb.define_tables()

    Here is an (incomplete) list of possible imap commands:

    # Count today's unseen messages
    # smaller than 6000 octets from the
    # inbox mailbox

    q = imapdb.INBOX.seen == False
    q &= imapdb.INBOX.created == datetime.date.today()
    q &= imapdb.INBOX.size < 6000
    unread = imapdb(q).count()

    # Fetch last query messages
    rows = imapdb(q).select()

    # it is also possible to filter query select results with limitby and
    # sequences of mailbox fields

    set.select(<fields sequence>, limitby=(<int>, <int>))

    # Mark last query messages as seen
    messages = [row.uid for row in rows]
    seen = imapdb(imapdb.INBOX.uid.belongs(messages)).update(seen=True)

    # Delete messages in the imap database that have mails from mr. Gumby

    deleted = 0
    for mailbox in imapdb.tables
        deleted += imapdb(imapdb[mailbox].sender.contains("gumby")).delete()

    # It is possible also to mark messages for deletion instead of ereasing them
    # directly with set.update(deleted=True)


    # This object give access
    # to the adapter auto mailbox
    # mapped names (which native
    # mailbox has what table name)

    imapdb.mailboxes <dict> # tablename, server native name pairs

    # To retrieve a table native mailbox name use:
    imapdb.<table>.mailbox

    ### New features v2.4.1:

    # Declare mailboxes statically with tablename, name pairs
    # This avoids the extra server names retrieval

    imapdb.define_tables({"inbox": "INBOX"})

    # Selects without content/attachments/email columns will only
    # fetch header and flags

    imapdb(q).select(imapdb.INBOX.sender, imapdb.INBOX.subject)
    """

    types = {
                'string': str,
                'text': str,
                'date': datetime.date,
                'datetime': datetime.datetime,
                'id': long,
                'boolean': bool,
                'integer': int,
                'bigint': long,
                'blob': str,
                'list:string': str,
        }

    dbengine = 'imap'

    REGEX_URI = re.compile('^(?P<user>[^:]+)(\:(?P<password>[^@]*))?@(?P<host>[^\:@]+)(\:(?P<port>[0-9]+))?$')

    def __init__(self,
                 db,
                 uri,
                 pool_size=0,
                 folder=None,
                 db_codec ='UTF-8',
                 credential_decoder=IDENTITY,
                 driver_args={},
                 adapter_args={},
                 do_connect=True,
                 after_connection=None):

        # db uri: user@example.com:password@imap.server.com:123
        # TODO: max size adapter argument for preventing large mail transfers

        self.db = db
        self.uri = uri
        if do_connect: self.find_driver(adapter_args)
        self.pool_size=pool_size
        self.folder = folder
        self.db_codec = db_codec
        self._after_connection = after_connection
        self.credential_decoder = credential_decoder
        self.driver_args = driver_args
        self.adapter_args = adapter_args
        self.mailbox_size = None
        self.static_names = None
        self.charset = sys.getfilesystemencoding()
        # imap class
        self.imap4 = None
        uri = uri.split("://")[1]

        """ MESSAGE is an identifier for sequence number"""

        self.flags = {'deleted': '\\Deleted', 'draft': '\\Draft',
                      'flagged': '\\Flagged', 'recent': '\\Recent',
                      'seen': '\\Seen', 'answered': '\\Answered'}
        self.search_fields = {
            'id': 'MESSAGE', 'created': 'DATE',
            'uid': 'UID', 'sender': 'FROM',
            'to': 'TO', 'cc': 'CC',
            'bcc': 'BCC', 'content': 'TEXT',
            'size': 'SIZE', 'deleted': '\\Deleted',
            'draft': '\\Draft', 'flagged': '\\Flagged',
            'recent': '\\Recent', 'seen': '\\Seen',
            'subject': 'SUBJECT', 'answered': '\\Answered',
            'mime': None, 'email': None,
            'attachments': None
            }

        db['_lastsql'] = ''

        m = self.REGEX_URI.match(uri)
        user = m.group('user')
        password = m.group('password')
        host = m.group('host')
        port = int(m.group('port'))
        over_ssl = False
        if port==993:
            over_ssl = True

        driver_args.update(host=host,port=port, password=password, user=user)
        def connector(driver_args=driver_args):
            # it is assumed sucessful authentication alLways
            # TODO: support direct connection and login tests
            if over_ssl:
                self.imap4 = self.driver.IMAP4_SSL
            else:
                self.imap4 = self.driver.IMAP4
            connection = self.imap4(driver_args["host"], driver_args["port"])
            data = connection.login(driver_args["user"], driver_args["password"])

            # static mailbox list
            connection.mailbox_names = None

            # dummy cursor function
            connection.cursor = lambda : True

            return connection

        self.db.define_tables = self.define_tables
        self.connector = connector
        if do_connect: self.reconnect()

    def reconnect(self, f=None, cursor=True):
        """
        IMAP4 Pool connection method

        imap connection lacks of self cursor command.
        A custom command should be provided as a replacement
        for connection pooling to prevent uncaught remote session
        closing

        """
        if getattr(self,'connection',None) != None:
            return
        if f is None:
            f = self.connector

        if not self.pool_size:
            self.connection = f()
            self.cursor = cursor and self.connection.cursor()
        else:
            POOLS = ConnectionPool.POOLS
            uri = self.uri
            while True:
                GLOBAL_LOCKER.acquire()
                if not uri in POOLS:
                    POOLS[uri] = []
                if POOLS[uri]:
                    self.connection = POOLS[uri].pop()
                    GLOBAL_LOCKER.release()
                    self.cursor = cursor and self.connection.cursor()
                    if self.cursor and self.check_active_connection:
                        try:
                            # check if connection is alive or close it
                            result, data = self.connection.list()
                        except:
                            # Possible connection reset error
                            # TODO: read exception class
                            self.connection = f()
                    break
                else:
                    GLOBAL_LOCKER.release()
                    self.connection = f()
                    self.cursor = cursor and self.connection.cursor()
                    break
        self.after_connection_hook()

    def get_last_message(self, tablename):
        last_message = None
        # request mailbox list to the server if needed.
        if not isinstance(self.connection.mailbox_names, dict):
            self.get_mailboxes()
        try:
            result = self.connection.select(
                self.connection.mailbox_names[tablename])
            last_message = int(result[1][0])
            # Last message must be a positive integer
            if last_message == 0:
                last_message = 1
        except (IndexError, ValueError, TypeError, KeyError):
            e = sys.exc_info()[1]
            LOGGER.debug("Error retrieving the last mailbox" +
                         " sequence number. %s" % str(e))
        return last_message

    def get_uid_bounds(self, tablename):
        if not isinstance(self.connection.mailbox_names, dict):
            self.get_mailboxes()
        # fetch first and last messages
        # return (first, last) messages uid's
        last_message = self.get_last_message(tablename)
        result, data = self.connection.uid("search", None, "(ALL)")
        uid_list = data[0].strip().split()
        if len(uid_list) <= 0:
            return None
        else:
            return (uid_list[0], uid_list[-1])

    def convert_date(self, date, add=None, imf=False):
        if add is None:
            add = datetime.timedelta()
        """ Convert a date object to a string
        with d-Mon-Y style for IMAP or the inverse
        case

        add <timedelta> adds to the date object
        """
        months = [None, "JAN","FEB","MAR","APR","MAY","JUN",
                  "JUL", "AUG","SEP","OCT","NOV","DEC"]
        if isinstance(date, basestring):
            # Prevent unexpected date response format
            try:
                if "," in date:
                    dayname, datestring = date.split(",")
                else:
                    dayname, datestring = None, date
                date_list = datestring.strip().split()
                year = int(date_list[2])
                month = months.index(date_list[1].upper())
                day = int(date_list[0])
                hms = map(int, date_list[3].split(":"))
                return datetime.datetime(year, month, day,
                    hms[0], hms[1], hms[2]) + add
            except (ValueError, AttributeError, IndexError), e:
                LOGGER.error("Could not parse date text: %s. %s" %
                             (date, e))
                return None
        elif isinstance(date, (datetime.date, datetime.datetime)):
            if imf: date_format = "%a, %d %b %Y %H:%M:%S %z"
            else: date_format = "%d-%b-%Y"
            return (date + add).strftime(date_format)
        else:
            return None

    @staticmethod
    def header_represent(f, r):
        from email.header import decode_header
        text, encoding = decode_header(f)[0]
        if encoding:
            text = text.decode(encoding).encode('utf-8')
        return text

    def encode_text(self, text, charset, errors="replace"):
        """ convert text for mail to unicode"""
        if text is None:
            text = ""
        else:
            if isinstance(text, str):
                if charset is None:
                    text = unicode(text, "utf-8", errors)
                else:
                    text = unicode(text, charset, errors)
            else:
                raise Exception("Unsupported mail text type %s" % type(text))
        return text.encode("utf-8")

    def get_charset(self, message):
        charset = message.get_content_charset()
        return charset

    def get_mailboxes(self):
        """ Query the mail database for mailbox names """
        if self.static_names:
            # statically defined mailbox names
            self.connection.mailbox_names = self.static_names
            return self.static_names.keys()

        mailboxes_list = self.connection.list()
        self.connection.mailbox_names = dict()
        mailboxes = list()
        x = 0
        for item in mailboxes_list[1]:
            x = x + 1
            item = item.strip()
            if not "NOSELECT" in item.upper():
                sub_items = item.split("\"")
                sub_items = [sub_item for sub_item in sub_items \
                if len(sub_item.strip()) > 0]
                # mailbox = sub_items[len(sub_items) -1]
                mailbox = sub_items[-1].strip()
                # remove unwanted characters and store original names
                # Don't allow leading non alphabetic characters
                mailbox_name = re.sub('^[_0-9]*', '', re.sub('[^_\w]','',re.sub('[/ ]','_',mailbox)))
                mailboxes.append(mailbox_name)
                self.connection.mailbox_names[mailbox_name] = mailbox

        return mailboxes

    def get_query_mailbox(self, query):
        nofield = True
        tablename = None
        attr = query
        while nofield:
            if hasattr(attr, "first"):
                attr = attr.first
                if isinstance(attr, Field):
                    return attr.tablename
                elif isinstance(attr, Query):
                    pass
                else:
                    return None
            else:
                return None
        return tablename

    def is_flag(self, flag):
        if self.search_fields.get(flag, None) in self.flags.values():
            return True
        else:
            return False

    def define_tables(self, mailbox_names=None):
        """
        Auto create common IMAP fileds

        This function creates fields definitions "statically"
        meaning that custom fields as in other adapters should
        not be supported and definitions handled on a service/mode
        basis (local syntax for Gmail(r), Ymail(r)

        Returns a dictionary with tablename, server native mailbox name
        pairs.
        """
        if mailbox_names:
            # optional statically declared mailboxes
            self.static_names = mailbox_names
        else:
            self.static_names = None
        if not isinstance(self.connection.mailbox_names, dict):
            self.get_mailboxes()

        names = self.connection.mailbox_names.keys()

        for name in names:
            self.db.define_table("%s" % name,
                            Field("uid", writable=False),
                            Field("created", "datetime", writable=False),
                            Field("content", "text", writable=False),
                            Field("to", writable=False),
                            Field("cc", writable=False),
                            Field("bcc", writable=False),
                            Field("sender", writable=False),
                            Field("size", "integer", writable=False),
                            Field("subject", writable=False),
                            Field("mime", writable=False),
                            Field("email", "text", writable=False, readable=False),
                            Field("attachments", "text", writable=False, readable=False),
                            Field("encoding", writable=False),
                            Field("answered", "boolean"),
                            Field("deleted", "boolean"),
                            Field("draft", "boolean"),
                            Field("flagged", "boolean"),
                            Field("recent", "boolean", writable=False),
                            Field("seen", "boolean")
                            )

            # Set a special _mailbox attribute for storing
            # native mailbox names
            self.db[name].mailbox = \
                self.connection.mailbox_names[name]

            # decode quoted printable
            self.db[name].to.represent = self.db[name].cc.represent = \
            self.db[name].bcc.represent = self.db[name].sender.represent = \
            self.db[name].subject.represent = self.header_represent

        # Set the db instance mailbox collections
        self.db.mailboxes = self.connection.mailbox_names
        return self.db.mailboxes

    def create_table(self, *args, **kwargs):
        # not implemented
        # but required by DAL
        pass

    def _select(self, query, fields, attributes):
        if use_common_filters(query):
            query = self.common_filter(query, [self.get_query_mailbox(query),])
        return str(query)

    def select(self, query, fields, attributes):
        """  Search and Fetch records and return web2py rows
        """
        # move this statement elsewhere (upper-level)
        if use_common_filters(query):
            query = self.common_filter(query, [self.get_query_mailbox(query),])

        import email
        # get records from imap server with search + fetch
        # convert results to a dictionary
        tablename = None
        fetch_results = list()

        if isinstance(query, Query):
            tablename = self.get_table(query)
            mailbox = self.connection.mailbox_names.get(tablename, None)
            if mailbox is None:
                 raise ValueError("Mailbox name not found: %s" % mailbox)
            else:
                # select with readonly
                result, selected = self.connection.select(mailbox, True)
                if result != "OK":
                    raise Exception("IMAP error: %s" % selected)
                self.mailbox_size = int(selected[0])
                search_query = "(%s)" % str(query).strip()
                search_result = self.connection.uid("search", None, search_query)
                # Normal IMAP response OK is assumed (change this)
                if search_result[0] == "OK":
                    # For "light" remote server responses just get the first
                    # ten records (change for non-experimental implementation)
                    # However, light responses are not guaranteed with this
                    # approach, just fewer messages.
                    limitby = attributes.get('limitby', None)
                    messages_set = search_result[1][0].split()
                    # descending order
                    messages_set.reverse()
                    if limitby is not None:
                        # TODO: orderby, asc/desc, limitby from complete message set
                        messages_set = messages_set[int(limitby[0]):int(limitby[1])]

                    # keep the requests small for header/flags
                    if any([(field.name in ["content", "size",
                                            "attachments", "email"]) for
                           field in fields]):
                        imap_fields = "(RFC822 FLAGS)"
                    else:
                        imap_fields = "(RFC822.HEADER FLAGS)"

                    if len(messages_set) > 0:
                        # create fetch results object list
                        # fetch each remote message and store it in memmory
                        # (change to multi-fetch command syntax for faster
                        # transactions)
                        for uid in messages_set:
                            # fetch the RFC822 message body
                            typ, data = self.connection.uid("fetch", uid, imap_fields)
                            if typ == "OK":
                                fr = {"message": int(data[0][0].split()[0]),
                                      "uid": long(uid),
                                      "email": email.message_from_string(data[0][1]),
                                      "raw_message": data[0][1]}
                                fr["multipart"] = fr["email"].is_multipart()
                                # fetch flags for the message
                                fr["flags"] = self.driver.ParseFlags(data[1])
                                fetch_results.append(fr)
                            else:
                                # error retrieving the message body
                                raise Exception("IMAP error retrieving the body: %s" % data)
                else:
                    raise Exception("IMAP search error: %s" % search_result[1])
        elif isinstance(query, (Expression, basestring)):
            raise NotImplementedError()
        else:
            raise TypeError("Unexpected query type")

        imapqry_dict = {}
        imapfields_dict = {}

        if len(fields) == 1 and isinstance(fields[0], SQLALL):
            allfields = True
        elif len(fields) == 0:
            allfields = True
        else:
            allfields = False
        if allfields:
            colnames = ["%s.%s" % (tablename, field) for field in self.search_fields.keys()]
        else:
            colnames = ["%s.%s" % (tablename, field.name) for field in fields]

        for k in colnames:
            imapfields_dict[k] = k

        imapqry_list = list()
        imapqry_array = list()
        for fr in fetch_results:
            attachments = []
            content = []
            size = 0
            n = int(fr["message"])
            item_dict = dict()
            message = fr["email"]
            uid = fr["uid"]
            charset = self.get_charset(message)
            flags = fr["flags"]
            raw_message = fr["raw_message"]
            # Return messages data mapping static fields
            # and fetched results. Mapping should be made
            # outside the select function (with auxiliary
            # instance methods)

            # pending: search flags states trough the email message
            # instances for correct output

            # preserve subject encoding (ASCII/quoted printable)

            if "%s.id" % tablename in colnames:
                item_dict["%s.id" % tablename] = n
            if "%s.created" % tablename in colnames:
                item_dict["%s.created" % tablename] = self.convert_date(message["Date"])
            if "%s.uid" % tablename in colnames:
                item_dict["%s.uid" % tablename] = uid
            if "%s.sender" % tablename in colnames:
                # If there is no encoding found in the message header
                # force utf-8 replacing characters (change this to
                # module's defaults). Applies to .sender, .to, .cc and .bcc fields
                item_dict["%s.sender" % tablename] = message["From"]
            if "%s.to" % tablename in colnames:
                item_dict["%s.to" % tablename] = message["To"]
            if "%s.cc" % tablename in colnames:
                if "Cc" in message.keys():
                    item_dict["%s.cc" % tablename] = message["Cc"]
                else:
                    item_dict["%s.cc" % tablename] = ""
            if "%s.bcc" % tablename in colnames:
                if "Bcc" in message.keys():
                    item_dict["%s.bcc" % tablename] = message["Bcc"]
                else:
                    item_dict["%s.bcc" % tablename] = ""
            if "%s.deleted" % tablename in colnames:
                item_dict["%s.deleted" % tablename] = "\\Deleted" in flags
            if "%s.draft" % tablename in colnames:
                item_dict["%s.draft" % tablename] = "\\Draft" in flags
            if "%s.flagged" % tablename in colnames:
                item_dict["%s.flagged" % tablename] = "\\Flagged" in flags
            if "%s.recent" % tablename in colnames:
                item_dict["%s.recent" % tablename] = "\\Recent" in flags
            if "%s.seen" % tablename in colnames:
                item_dict["%s.seen" % tablename] = "\\Seen" in flags
            if "%s.subject" % tablename in colnames:
                item_dict["%s.subject" % tablename] = message["Subject"]
            if "%s.answered" % tablename in colnames:
                item_dict["%s.answered" % tablename] = "\\Answered" in flags
            if "%s.mime" % tablename in colnames:
                item_dict["%s.mime" % tablename] = message.get_content_type()
            if "%s.encoding" % tablename in colnames:
                item_dict["%s.encoding" % tablename] = charset

            # Here goes the whole RFC822 body as an email instance
            # for controller side custom processing
            # The message is stored as a raw string
            # >> email.message_from_string(raw string)
            # returns a Message object for enhanced object processing
            if "%s.email" % tablename in colnames:
                # WARNING: no encoding performed (raw message)
                item_dict["%s.email" % tablename] = raw_message

            # Size measure as suggested in a Velocity Reviews post
            # by Tim Williams: "how to get size of email attachment"
            # Note: len() and server RFC822.SIZE reports doesn't match
            # To retrieve the server size for representation would add a new
            # fetch transaction to the process
            for part in message.walk():
                maintype = part.get_content_maintype()
                if ("%s.attachments" % tablename in colnames) or \
                   ("%s.content" % tablename in colnames):
                    payload = part.get_payload(decode=True)
                    if payload:
                        filename = part.get_filename()
                        values = {"mime": part.get_content_type()}
                        if ((filename or not "text" in maintype) and
                            ("%s.attachments" % tablename in colnames)):
                            values.update({"payload": payload,
                                "filename": filename,
                                "encoding": part.get_content_charset(),
                                "disposition": part["Content-Disposition"]})
                            attachments.append(values)
                        elif (("text" in maintype) and
                              ("%s.content" % tablename in colnames)):
                            values.update({"text": self.encode_text(payload,
                                               self.get_charset(part))})
                            content.append(values)

                if "%s.size" % tablename in colnames:
                    if part is not None:
                        size += len(str(part))
            item_dict["%s.content" % tablename] = content
            item_dict["%s.attachments" % tablename] = attachments
            item_dict["%s.size" % tablename] = size
            imapqry_list.append(item_dict)

        # extra object mapping for the sake of rows object
        # creation (sends an array or lists)
        for item_dict in imapqry_list:
            imapqry_array_item = list()
            for fieldname in colnames:
                imapqry_array_item.append(item_dict[fieldname])
            imapqry_array.append(imapqry_array_item)

        # parse result and return a rows object
        colnames = colnames
        processor = attributes.get('processor',self.parse)
        return processor(imapqry_array, fields, colnames)

    def _insert(self, table, fields):
        def add_payload(message, obj):
            payload = Message()
            encoding = obj.get("encoding", "utf-8")
            if encoding and (encoding.upper() in
                             ("BASE64", "7BIT", "8BIT", "BINARY")):
                payload.add_header("Content-Transfer-Encoding", encoding)
            else:
                payload.set_charset(encoding)
            mime = obj.get("mime", None)
            if mime:
                payload.set_type(mime)
            if "text" in obj:
                payload.set_payload(obj["text"])
            elif "payload" in obj:
                payload.set_payload(obj["payload"])
            if "filename" in obj and obj["filename"]:
                payload.add_header("Content-Disposition",
                    "attachment", filename=obj["filename"])
            message.attach(payload)

        mailbox = table.mailbox
        d = dict(((k.name, v) for k, v in fields))
        date_time = d.get("created") or datetime.datetime.now()
        struct_time = date_time.timetuple()
        if len(d) > 0:
            message = d.get("email", None)
            attachments = d.get("attachments", [])
            content = d.get("content", [])
            flags = " ".join(["\\%s" % flag.capitalize() for flag in
                     ("answered", "deleted", "draft", "flagged",
                      "recent", "seen") if d.get(flag, False)])
            if not message:
                from email.message import Message
                mime = d.get("mime", None)
                charset = d.get("encoding", None)
                message = Message()
                message["from"] = d.get("sender", "")
                message["subject"] = d.get("subject", "")
                message["date"] = self.convert_date(date_time, imf=True)

                if mime:
                    message.set_type(mime)
                if charset:
                    message.set_charset(charset)
                for item in ("to", "cc", "bcc"):
                    value = d.get(item, "")
                    if isinstance(value, basestring):
                        message[item] = value
                    else:
                        message[item] = ";".join([i for i in
                            value])
                if (not message.is_multipart() and
                   (not message.get_content_type().startswith(
                        "multipart"))):
                    if isinstance(content, basestring):
                        message.set_payload(content)
                    elif len(content) > 0:
                        message.set_payload(content[0]["text"])
                else:
                    [add_payload(message, c) for c in content]
                    [add_payload(message, a) for a in attachments]
                message = message.as_string()
            return (mailbox, flags, struct_time, message)
        else:
            raise NotImplementedError("IMAP empty insert is not implemented")

    def insert(self, table, fields):
        values = self._insert(table, fields)
        result, data = self.connection.append(*values)
        if result == "OK":
            uid = int(re.findall("\d+", str(data))[-1])
            return self.db(table.uid==uid).select(table.id).first().id
        else:
            raise Exception("IMAP message append failed: %s" % data)

    def _update(self, tablename, query, fields, commit=False):
        # TODO: the adapter should implement an .expand method
        commands = list()
        if use_common_filters(query):
            query = self.common_filter(query, [tablename,])
        mark = []
        unmark = []
        if query:
            for item in fields:
                field = item[0]
                name = field.name
                value = item[1]
                if self.is_flag(name):
                    flag = self.search_fields[name]
                    if (value is not None) and (flag != "\\Recent"):
                        if value:
                            mark.append(flag)
                        else:
                            unmark.append(flag)
            result, data = self.connection.select(
                self.connection.mailbox_names[tablename])
            string_query = "(%s)" % query
            result, data = self.connection.search(None, string_query)
            store_list = [item.strip() for item in data[0].split()
                          if item.strip().isdigit()]
            # build commands for marked flags
            for number in store_list:
                result = None
                if len(mark) > 0:
                    commands.append((number, "+FLAGS", "(%s)" % " ".join(mark)))
                if len(unmark) > 0:
                    commands.append((number, "-FLAGS", "(%s)" % " ".join(unmark)))
        return commands

    def update(self, tablename, query, fields):
        rowcount = 0
        commands = self._update(tablename, query, fields)
        for command in commands:
            result, data = self.connection.store(*command)
            if result == "OK":
                rowcount += 1
            else:
                raise Exception("IMAP storing error: %s" % data)
        return rowcount

    def _count(self, query, distinct=None):
        raise NotImplementedError()

    def count(self,query,distinct=None):
        counter = 0
        tablename = self.get_query_mailbox(query)
        if query and tablename is not None:
            if use_common_filters(query):
                query = self.common_filter(query, [tablename,])
            result, data = self.connection.select(self.connection.mailbox_names[tablename])
            string_query = "(%s)" % query
            result, data = self.connection.search(None, string_query)
            store_list = [item.strip() for item in data[0].split() if item.strip().isdigit()]
            counter = len(store_list)
        return counter

    def delete(self, tablename, query):
        counter = 0
        if query:
            if use_common_filters(query):
                query = self.common_filter(query, [tablename,])
            result, data = self.connection.select(self.connection.mailbox_names[tablename])
            string_query = "(%s)" % query
            result, data = self.connection.search(None, string_query)
            store_list = [item.strip() for item in data[0].split() if item.strip().isdigit()]
            for number in store_list:
                result, data = self.connection.store(number, "+FLAGS", "(\\Deleted)")
                if result == "OK":
                    counter += 1
                else:
                    raise Exception("IMAP store error: %s" % data)
            if counter > 0:
                result, data = self.connection.expunge()
        return counter

    def BELONGS(self, first, second):
        result = None
        name = self.search_fields[first.name]
        if name == "MESSAGE":
            values = [str(val) for val in second if str(val).isdigit()]
            result = "%s" % ",".join(values).strip()

        elif name == "UID":
            values = [str(val) for val in second if str(val).isdigit()]
            result = "UID %s" % ",".join(values).strip()

        else:
            raise Exception("Operation not supported")
        # result = "(%s %s)" % (self.expand(first), self.expand(second))
        return result

    def CONTAINS(self, first, second, case_sensitive=False):
        # silently ignore, only case sensitive
        result = None
        name = self.search_fields[first.name]

        if name in ("FROM", "TO", "SUBJECT", "TEXT"):
            result = "%s \"%s\"" % (name, self.expand(second))
        else:
            if first.name in ("cc", "bcc"):
                result = "%s \"%s\"" % (first.name.upper(), self.expand(second))
            elif first.name == "mime":
                result = "HEADER Content-Type \"%s\"" % self.expand(second)
            else:
                raise Exception("Operation not supported")
        return result

    def GT(self, first, second):
        result = None
        name = self.search_fields[first.name]
        if name == "MESSAGE":
            last_message = self.get_last_message(first.tablename)
            result = "%d:%d" % (int(self.expand(second)) + 1, last_message)
        elif name == "UID":
            # GT and LT may not return
            # expected sets depending on
            # the uid format implemented
            try:
                pedestal, threshold = self.get_uid_bounds(first.tablename)
            except TypeError:
                e = sys.exc_info()[1]
                LOGGER.debug("Error requesting uid bounds: %s", str(e))
                return ""
            try:
                lower_limit = int(self.expand(second)) + 1
            except (ValueError, TypeError):
                e = sys.exc_info()[1]
                raise Exception("Operation not supported (non integer UID)")
            result = "UID %s:%s" % (lower_limit, threshold)
        elif name == "DATE":
            result = "SINCE %s" % self.convert_date(second, add=datetime.timedelta(1))
        elif name == "SIZE":
            result = "LARGER %s" % self.expand(second)
        else:
            raise Exception("Operation not supported")
        return result

    def GE(self, first, second):
        result = None
        name = self.search_fields[first.name]
        if name == "MESSAGE":
            last_message = self.get_last_message(first.tablename)
            result = "%s:%s" % (self.expand(second), last_message)
        elif name == "UID":
            # GT and LT may not return
            # expected sets depending on
            # the uid format implemented
            try:
                pedestal, threshold = self.get_uid_bounds(first.tablename)
            except TypeError:
                e = sys.exc_info()[1]
                LOGGER.debug("Error requesting uid bounds: %s", str(e))
                return ""
            lower_limit = self.expand(second)
            result = "UID %s:%s" % (lower_limit, threshold)
        elif name == "DATE":
            result = "SINCE %s" % self.convert_date(second)
        else:
            raise Exception("Operation not supported")
        return result

    def LT(self, first, second):
        result = None
        name = self.search_fields[first.name]
        if name == "MESSAGE":
            result = "%s:%s" % (1, int(self.expand(second)) - 1)
        elif name == "UID":
            try:
                pedestal, threshold = self.get_uid_bounds(first.tablename)
            except TypeError:
                e = sys.exc_info()[1]
                LOGGER.debug("Error requesting uid bounds: %s", str(e))
                return ""
            try:
                upper_limit = int(self.expand(second)) - 1
            except (ValueError, TypeError):
                e = sys.exc_info()[1]
                raise Exception("Operation not supported (non integer UID)")
            result = "UID %s:%s" % (pedestal, upper_limit)
        elif name == "DATE":
            result = "BEFORE %s" % self.convert_date(second)
        elif name == "SIZE":
            result = "SMALLER %s" % self.expand(second)
        else:
            raise Exception("Operation not supported")
        return result

    def LE(self, first, second):
        result = None
        name = self.search_fields[first.name]
        if name == "MESSAGE":
            result = "%s:%s" % (1, self.expand(second))
        elif name == "UID":
            try:
                pedestal, threshold = self.get_uid_bounds(first.tablename)
            except TypeError:
                e = sys.exc_info()[1]
                LOGGER.debug("Error requesting uid bounds: %s", str(e))
                return ""
            upper_limit = int(self.expand(second))
            result = "UID %s:%s" % (pedestal, upper_limit)
        elif name == "DATE":
            result = "BEFORE %s" % self.convert_date(second, add=datetime.timedelta(1))
        else:
            raise Exception("Operation not supported")
        return result

    def NE(self, first, second=None):
        if (second is None) and isinstance(first, Field):
            # All records special table query
            if first.type == "id":
                return self.GE(first, 1)
        result = self.NOT(self.EQ(first, second))
        result =  result.replace("NOT NOT", "").strip()
        return result

    def EQ(self,first,second):
        name = self.search_fields[first.name]
        result = None
        if name is not None:
            if name == "MESSAGE":
                # query by message sequence number
                result = "%s" % self.expand(second)
            elif name == "UID":
                result = "UID %s" % self.expand(second)
            elif name == "DATE":
                result = "ON %s" % self.convert_date(second)

            elif name in self.flags.values():
                if second:
                    result = "%s" % (name.upper()[1:])
                else:
                    result = "NOT %s" % (name.upper()[1:])
            else:
                raise Exception("Operation not supported")
        else:
            raise Exception("Operation not supported")
        return result

    def AND(self, first, second):
        result = "%s %s" % (self.expand(first), self.expand(second))
        return result

    def OR(self, first, second):
        result = "OR %s %s" % (self.expand(first), self.expand(second))
        return "%s" % result.replace("OR OR", "OR")

    def NOT(self, first):
        result = "NOT %s" % self.expand(first)
        return result

########################################################################
# end of adapters
########################################################################

ADAPTERS = {
    'sqlite': SQLiteAdapter,
    'spatialite': SpatiaLiteAdapter,
    'sqlite:memory': SQLiteAdapter,
    'spatialite:memory': SpatiaLiteAdapter,
    'mysql': MySQLAdapter,
    'postgres': PostgreSQLAdapter,
    'postgres:psycopg2': PostgreSQLAdapter,
    'postgres:pg8000': PostgreSQLAdapter,
    'postgres2:psycopg2': NewPostgreSQLAdapter,
    'postgres2:pg8000': NewPostgreSQLAdapter,
    'oracle': OracleAdapter,
    'mssql': MSSQLAdapter,
    'mssql2': MSSQL2Adapter,
    'mssql3': MSSQL3Adapter,
    'mssql4' : MSSQL4Adapter,
    'vertica': VerticaAdapter,
    'sybase': SybaseAdapter,
    'db2': DB2Adapter,
    'teradata': TeradataAdapter,
    'informix': InformixAdapter,
    'informix-se': InformixSEAdapter,
    'firebird': FireBirdAdapter,
    'firebird_embedded': FireBirdAdapter,
    'ingres': IngresAdapter,
    'ingresu': IngresUnicodeAdapter,
    'sapdb': SAPDBAdapter,
    'cubrid': CubridAdapter,
    'jdbc:sqlite': JDBCSQLiteAdapter,
    'jdbc:sqlite:memory': JDBCSQLiteAdapter,
    'jdbc:postgres': JDBCPostgreSQLAdapter,
    'gae': GoogleDatastoreAdapter, # discouraged, for backward compatibility
    'google:datastore': GoogleDatastoreAdapter,
    'google:sql': GoogleSQLAdapter,
    'couchdb': CouchDBAdapter,
    'mongodb': MongoDBAdapter,
    'imap': IMAPAdapter
}

def sqlhtml_validators(field):
    """
    Field type validation, using web2py's validators mechanism.

    makes sure the content of a field is in line with the declared
    fieldtype
    """
    db = field.db
    try:
        from gluon import validators
    except ImportError:
        return []
    field_type, field_length = field.type, field.length
    if isinstance(field_type, SQLCustomType):
        if hasattr(field_type, 'validator'):
            return field_type.validator
        else:
            field_type = field_type.type
    elif not isinstance(field_type,str):
        return []
    requires=[]
    def ff(r,id):
        row=r(id)
        if not row:
            return id
        elif hasattr(r, '_format') and isinstance(r._format,str):
            return r._format % row
        elif hasattr(r, '_format') and callable(r._format):
            return r._format(row)
        else:
            return id
    if field_type in (('string', 'text', 'password')):
        requires.append(validators.IS_LENGTH(field_length))
    elif field_type == 'json':
        requires.append(validators.IS_EMPTY_OR(validators.IS_JSON(native_json=field.db._adapter.native_json)))
    elif field_type == 'double' or field_type == 'float':
        requires.append(validators.IS_FLOAT_IN_RANGE(-1e100, 1e100))
    elif field_type == 'integer':
        requires.append(validators.IS_INT_IN_RANGE(-2**31, 2**31))
    elif field_type == 'bigint':
        requires.append(validators.IS_INT_IN_RANGE(-2**63, 2**63))
    elif field_type.startswith('decimal'):
        requires.append(validators.IS_DECIMAL_IN_RANGE(-10**10, 10**10))
    elif field_type == 'date':
        requires.append(validators.IS_DATE())
    elif field_type == 'time':
        requires.append(validators.IS_TIME())
    elif field_type == 'datetime':
        requires.append(validators.IS_DATETIME())
    elif db and field_type.startswith('reference') and \
            field_type.find('.') < 0 and \
            field_type[10:] in db.tables:
        referenced = db[field_type[10:]]
        def repr_ref(id, row=None, r=referenced, f=ff): return f(r, id)
        field.represent = field.represent or repr_ref
        if hasattr(referenced, '_format') and referenced._format:
            requires = validators.IS_IN_DB(db,referenced._id,
                                           referenced._format)
            if field.unique:
                requires._and = validators.IS_NOT_IN_DB(db,field)
            if field.tablename == field_type[10:]:
                return validators.IS_EMPTY_OR(requires)
            return requires
    elif db and field_type.startswith('list:reference') and \
            field_type.find('.') < 0 and \
            field_type[15:] in db.tables:
        referenced = db[field_type[15:]]
        def list_ref_repr(ids, row=None, r=referenced, f=ff):
            if not ids:
                return None
            refs = None
            db, id = r._db, r._id
            if isinstance(db._adapter, GoogleDatastoreAdapter):
                def count(values): return db(id.belongs(values)).select(id)
                rx = range(0, len(ids), 30)
                refs = reduce(lambda a,b:a&b, [count(ids[i:i+30]) for i in rx])
            else:
                refs = db(id.belongs(ids)).select(id)
            return (refs and ', '.join(f(r,x.id) for x in refs) or '')
        field.represent = field.represent or list_ref_repr
        if hasattr(referenced, '_format') and referenced._format:
            requires = validators.IS_IN_DB(db,referenced._id,
                                           referenced._format,multiple=True)
        else:
            requires = validators.IS_IN_DB(db,referenced._id,
                                           multiple=True)
        if field.unique:
            requires._and = validators.IS_NOT_IN_DB(db,field)
        if not field.notnull:
            requires = validators.IS_EMPTY_OR(requires)
        return requires
    elif field_type.startswith('list:'):
        def repr_list(values,row=None): return', '.join(str(v) for v in (values or []))
        field.represent = field.represent or repr_list
    if field.unique:
        requires.insert(0,validators.IS_NOT_IN_DB(db,field))
    sff = ['in', 'do', 'da', 'ti', 'de', 'bo']
    if field.notnull and not field_type[:2] in sff:
        requires.insert(0, validators.IS_NOT_EMPTY())
    elif not field.notnull and field_type[:2] in sff and requires:
        requires[-1] = validators.IS_EMPTY_OR(requires[-1])
    return requires


def bar_escape(item):
    return str(item).replace('|', '||')

def bar_encode(items):
    return '|%s|' % '|'.join(bar_escape(item) for item in items if str(item).strip())

def bar_decode_integer(value):
    if not hasattr(value,'split') and hasattr(value,'read'):
        value = value.read()
    return [long(x) for x in value.split('|') if x.strip()]

def bar_decode_string(value):
    return [x.replace('||', '|') for x in
            REGEX_UNPACK.split(value[1:-1]) if x.strip()]


class Row(object):

    """
    a dictionary that lets you do d['a'] as well as d.a
    this is only used to store a Row
    """

    __init__ = lambda self,*args,**kwargs: self.__dict__.update(*args,**kwargs)

    def __getitem__(self, k):
        key=str(k)
        _extra = self.__dict__.get('_extra', None)
        if _extra is not None:
            v = _extra.get(key, DEFAULT)
            if v != DEFAULT:
                return v
        m = REGEX_TABLE_DOT_FIELD.match(key)
        if m:
            try:
                return ogetattr(self, m.group(1))[m.group(2)]
            except (KeyError,AttributeError,TypeError):
                key = m.group(2)
        try:
            return ogetattr(self, key)
        except (KeyError,AttributeError,TypeError), ae:
            try:
                self[key] = ogetattr(self,'__get_lazy_reference__')(key)
                return self[key]
            except:
                raise ae

    __setitem__ = lambda self, key, value: setattr(self, str(key), value)

    __delitem__ = object.__delattr__

    __copy__ = lambda self: Row(self)

    __call__ = __getitem__


    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except(KeyError, AttributeError, TypeError):
            return self.__dict__.get(key,default)

    has_key = __contains__ = lambda self, key: key in self.__dict__

    __nonzero__ = lambda self: len(self.__dict__)>0

    update = lambda self, *args, **kwargs:  self.__dict__.update(*args, **kwargs)

    keys = lambda self: self.__dict__.keys()

    items = lambda self: self.__dict__.items()

    values = lambda self: self.__dict__.values()

    __iter__ = lambda self: self.__dict__.__iter__()

    iteritems = lambda self: self.__dict__.iteritems()

    __str__ = __repr__ = lambda self: '<Row %s>' % self.as_dict()

    __int__ = lambda self: object.__getattribute__(self,'id')

    __long__ = lambda self: long(object.__getattribute__(self,'id'))

    __getattr__ = __getitem__

    # def __getattribute__(self, key):
    #     try:
    #         return object.__getattribute__(self, key)
    #     except AttributeError, ae:
    #         try:
    #             return self.__get_lazy_reference__(key)
    #         except:
    #             raise ae

    def __eq__(self,other):
        try:
            return self.as_dict() == other.as_dict()
        except AttributeError:
            return False

    def __ne__(self,other):
        return not (self == other)

    def __copy__(self):
        return Row(dict(self))

    def as_dict(self, datetime_to_str=False, custom_types=None):
        SERIALIZABLE_TYPES = [str, unicode, int, long, float, bool, list, dict]
        if isinstance(custom_types,(list,tuple,set)):
            SERIALIZABLE_TYPES += custom_types
        elif custom_types:
            SERIALIZABLE_TYPES.append(custom_types)
        d = dict(self)
        for k in copy.copy(d.keys()):
            v=d[k]
            if d[k] is None:
                continue
            elif isinstance(v,Row):
                d[k]=v.as_dict()
            elif isinstance(v,Reference):
                d[k]=long(v)
            elif isinstance(v,decimal.Decimal):
                d[k]=float(v)
            elif isinstance(v, (datetime.date, datetime.datetime, datetime.time)):
                if datetime_to_str:
                    d[k] = v.isoformat().replace('T',' ')[:19]
            elif not isinstance(v,tuple(SERIALIZABLE_TYPES)):
                del d[k]
        return d

    def as_xml(self, row_name="row", colnames=None, indent='  '):
        def f(row,field,indent='  '):
            if isinstance(row,Row):
                spc = indent+'  \n'
                items = [f(row[x],x,indent+'  ') for x in row]
                return '%s<%s>\n%s\n%s</%s>' % (
                    indent,
                    field,
                    spc.join(item for item in items if item),
                    indent,
                    field)
            elif not callable(row):
                if REGEX_ALPHANUMERIC.match(field):
                    return '%s<%s>%s</%s>' % (indent,field,row,field)
                else:
                    return '%s<extra name="%s">%s</extra>' % \
                        (indent,field,row)
            else:
                return None
        return f(self, row_name, indent=indent)

    def as_json(self, mode="object", default=None, colnames=None,
                serialize=True, **kwargs):
        """
        serializes the row to a JSON object
        kwargs are passed to .as_dict method
        only "object" mode supported

        serialize = False used by Rows.as_json
        TODO: return array mode with query column order

        mode and colnames are not implemented
        """

        item = self.as_dict(**kwargs)
        if serialize:
            if have_serializers:
                return serializers.json(item,
                                        default=default or
                                        serializers.custom_json)
            elif simplejson:
                return simplejson.dumps(item)
            else:
                raise RuntimeError("missing simplejson")
        else:
            return item


################################################################################
# Everything below should be independent of the specifics of the database
# and should work for RDBMs and some NoSQL databases
################################################################################

class SQLCallableList(list):
    def __call__(self):
        return copy.copy(self)

def smart_query(fields,text):
    if not isinstance(fields,(list,tuple)):
        fields = [fields]
    new_fields = []
    for field in fields:
        if isinstance(field,Field):
            new_fields.append(field)
        elif isinstance(field,Table):
            for ofield in field:
                new_fields.append(ofield)
        else:
            raise RuntimeError("fields must be a list of fields")
    fields = new_fields
    field_map = {}
    for field in fields:
        n = field.name.lower()
        if not n in field_map:
            field_map[n] = field
        n = str(field).lower()
        if not n in field_map:
            field_map[n] = field
    constants = {}
    i = 0
    while True:
        m = REGEX_CONST_STRING.search(text)
        if not m: break
        text = text[:m.start()]+('#%i' % i)+text[m.end():]
        constants[str(i)] = m.group()[1:-1]
        i+=1
    text = re.sub('\s+',' ',text).lower()
    for a,b in [('&','and'),
                ('|','or'),
                ('~','not'),
                ('==','='),
                ('<','<'),
                ('>','>'),
                ('<=','<='),
                ('>=','>='),
                ('<>','!='),
                ('=<','<='),
                ('=>','>='),
                ('=','='),
                (' less or equal than ','<='),
                (' greater or equal than ','>='),
                (' equal or less than ','<='),
                (' equal or greater than ','>='),
                (' less or equal ','<='),
                (' greater or equal ','>='),
                (' equal or less ','<='),
                (' equal or greater ','>='),
                (' not equal to ','!='),
                (' not equal ','!='),
                (' equal to ','='),
                (' equal ','='),
                (' equals ','='),
                (' less than ','<'),
                (' greater than ','>'),
                (' starts with ','startswith'),
                (' ends with ','endswith'),
                (' not in ' , 'notbelongs'),
                (' in ' , 'belongs'),
                (' is ','=')]:
        if a[0]==' ':
            text = text.replace(' is'+a,' %s ' % b)
        text = text.replace(a,' %s ' % b)
    text = re.sub('\s+',' ',text).lower()
    text = re.sub('(?P<a>[\<\>\!\=])\s+(?P<b>[\<\>\!\=])','\g<a>\g<b>',text)
    query = field = neg = op = logic = None
    for item in text.split():
        if field is None:
            if item == 'not':
                neg = True
            elif not neg and not logic and item in ('and','or'):
                logic = item
            elif item in field_map:
                field = field_map[item]
            else:
                raise RuntimeError("Invalid syntax")
        elif not field is None and op is None:
            op = item
        elif not op is None:
            if item.startswith('#'):
                if not item[1:] in constants:
                    raise RuntimeError("Invalid syntax")
                value = constants[item[1:]]
            else:
                value = item
                if field.type in ('text', 'string', 'json'):
                    if op == '=': op = 'like'
            if op == '=': new_query = field==value
            elif op == '<': new_query = field<value
            elif op == '>': new_query = field>value
            elif op == '<=': new_query = field<=value
            elif op == '>=': new_query = field>=value
            elif op == '!=': new_query = field!=value
            elif op == 'belongs': new_query = field.belongs(value.split(','))
            elif op == 'notbelongs': new_query = ~field.belongs(value.split(','))
            elif field.type in ('text', 'string', 'json'):
                if op == 'contains': new_query = field.contains(value)
                elif op == 'like': new_query = field.like(value)
                elif op == 'startswith': new_query = field.startswith(value)
                elif op == 'endswith': new_query = field.endswith(value)
                else: raise RuntimeError("Invalid operation")
            elif field._db._adapter.dbengine=='google:datastore' and \
                 field.type in ('list:integer', 'list:string', 'list:reference'):
                if op == 'contains': new_query = field.contains(value)
                else: raise RuntimeError("Invalid operation")
            else: raise RuntimeError("Invalid operation")
            if neg: new_query = ~new_query
            if query is None:
                query = new_query
            elif logic == 'and':
                query &= new_query
            elif logic == 'or':
                query |= new_query
            field = op = neg = logic = None
    return query

class DAL(object):

    """
    an instance of this class represents a database connection

    Example::

       db = DAL('sqlite://test.db')

       or

       db = DAL(**{"uri": ..., "tables": [...]...}) # experimental

       db.define_table('tablename', Field('fieldname1'),
                                    Field('fieldname2'))
    """

    def __new__(cls, uri='sqlite://dummy.db', *args, **kwargs):
        if not hasattr(THREAD_LOCAL,'db_instances'):
            THREAD_LOCAL.db_instances = {}
        if not hasattr(THREAD_LOCAL,'db_instances_zombie'):
            THREAD_LOCAL.db_instances_zombie = {}
        if uri == '<zombie>':
            db_uid = kwargs['db_uid'] # a zombie must have a db_uid!
            if db_uid in THREAD_LOCAL.db_instances:
                db_group = THREAD_LOCAL.db_instances[db_uid]
                db = db_group[-1]
            elif db_uid in THREAD_LOCAL.db_instances_zombie:
                db = THREAD_LOCAL.db_instances_zombie[db_uid]
            else:
                db = super(DAL, cls).__new__(cls)
                THREAD_LOCAL.db_instances_zombie[db_uid] = db
        else:
            db_uid = kwargs.get('db_uid',hashlib_md5(repr(uri)).hexdigest())
            if db_uid in THREAD_LOCAL.db_instances_zombie:
                db = THREAD_LOCAL.db_instances_zombie[db_uid]
                del THREAD_LOCAL.db_instances_zombie[db_uid]
            else:
                db = super(DAL, cls).__new__(cls)
            db_group = THREAD_LOCAL.db_instances.get(db_uid,[])
            db_group.append(db)
            THREAD_LOCAL.db_instances[db_uid] = db_group
        db._db_uid = db_uid
        return db

    @staticmethod
    def set_folder(folder):
        """
        # ## this allows gluon to set a folder for this thread
        # ## <<<<<<<<< Should go away as new DAL replaces old sql.py
        """
        BaseAdapter.set_folder(folder)

    @staticmethod
    def get_instances():
        """
        Returns a dictionary with uri as key with timings and defined tables
        {'sqlite://storage.sqlite': {
            'dbstats': [(select auth_user.email from auth_user, 0.02009)],
            'dbtables': {
                'defined': ['auth_cas', 'auth_event', 'auth_group',
                    'auth_membership', 'auth_permission', 'auth_user'],
                'lazy': '[]'
                }
            }
        }
        """
        dbs = getattr(THREAD_LOCAL,'db_instances',{}).items()
        infos = {}
        for db_uid, db_group in dbs:
            for db in db_group:
                if not db._uri:
                    continue
                k = hide_password(db._adapter.uri)
                infos[k] = dict(
                    dbstats = [(row[0], row[1]) for row in db._timings],
                    dbtables = {'defined': sorted(
                            list(set(db.tables)-set(db._LAZY_TABLES.keys()))),
                                'lazy': sorted(db._LAZY_TABLES.keys())})
        return infos

    @staticmethod
    def distributed_transaction_begin(*instances):
        if not instances:
            return
        thread_key = '%s.%s' % (socket.gethostname(), threading.currentThread())
        keys = ['%s.%i' % (thread_key, i) for (i,db) in instances]
        instances = enumerate(instances)
        for (i, db) in instances:
            if not db._adapter.support_distributed_transaction():
                raise SyntaxError(
                    'distributed transaction not suported by %s' % db._dbname)
        for (i, db) in instances:
            db._adapter.distributed_transaction_begin(keys[i])

    @staticmethod
    def distributed_transaction_commit(*instances):
        if not instances:
            return
        instances = enumerate(instances)
        thread_key = '%s.%s' % (socket.gethostname(), threading.currentThread())
        keys = ['%s.%i' % (thread_key, i) for (i,db) in instances]
        for (i, db) in instances:
            if not db._adapter.support_distributed_transaction():
                raise SyntaxError(
                    'distributed transaction not suported by %s' % db._dbanme)
        try:
            for (i, db) in instances:
                db._adapter.prepare(keys[i])
        except:
            for (i, db) in instances:
                db._adapter.rollback_prepared(keys[i])
            raise RuntimeError('failure to commit distributed transaction')
        else:
            for (i, db) in instances:
                db._adapter.commit_prepared(keys[i])
        return

    def __init__(self, uri=DEFAULT_URI,
                 pool_size=0, folder=None,
                 db_codec='UTF-8', check_reserved=None,
                 migrate=True, fake_migrate=False,
                 migrate_enabled=True, fake_migrate_all=False,
                 decode_credentials=False, driver_args=None,
                 adapter_args=None, attempts=5, auto_import=False,
                 bigint_id=False, debug=False, lazy_tables=False,
                 db_uid=None, do_connect=True,
                 after_connection=None, tables=None):
        """
        Creates a new Database Abstraction Layer instance.

        Keyword arguments:

        :uri: string that contains information for connecting to a database.
               (default: 'sqlite://dummy.db')

                experimental: you can specify a dictionary as uri
                parameter i.e. with
                db = DAL({"uri": "sqlite://storage.sqlite",
                          "tables": {...}, ...})

                for an example of dict input you can check the output
                of the scaffolding db model with

                db.as_dict()

                Note that for compatibility with Python older than
                version 2.6.5 you should cast your dict input keys
                to str due to a syntax limitation on kwarg names.
                for proper DAL dictionary input you can use one of:

                obj = serializers.cast_keys(dict, [encoding="utf-8"])

                or else (for parsing json input)

                obj = serializers.loads_json(data, unicode_keys=False)

        :pool_size: How many open connections to make to the database object.
        :folder: where .table files will be created.
                 automatically set within web2py
                 use an explicit path when using DAL outside web2py
        :db_codec: string encoding of the database (default: 'UTF-8')
        :check_reserved: list of adapters to check tablenames and column names
                         against sql/nosql reserved keywords. (Default None)

        * 'common' List of sql keywords that are common to all database types
                such as "SELECT, INSERT". (recommended)
        * 'all' Checks against all known SQL keywords. (not recommended)
                <adaptername> Checks against the specific adapters list of keywords
                (recommended)
        * '<adaptername>_nonreserved' Checks against the specific adapters
                list of nonreserved keywords. (if available)
        :migrate (defaults to True) sets default migrate behavior for all tables
        :fake_migrate (defaults to False) sets default fake_migrate behavior for all tables
        :migrate_enabled (defaults to True). If set to False disables ALL migrations
        :fake_migrate_all (defaults to False). If sets to True fake migrates ALL tables
        :attempts (defaults to 5). Number of times to attempt connecting
        :auto_import (defaults to False). If set, import automatically table definitions from the
                 databases folder
        :bigint_id (defaults to False): If set, turn on bigint instead of int for id fields
        :lazy_tables (defaults to False): delay table definition until table access
        :after_connection (defaults to None): a callable that will be execute after the connection
        """
        if uri == '<zombie>' and db_uid is not None: return
        if not decode_credentials:
            credential_decoder = lambda cred: cred
        else:
            credential_decoder = lambda cred: urllib.unquote(cred)
        self._folder = folder
        if folder:
            self.set_folder(folder)
        self._uri = uri
        self._pool_size = pool_size
        self._db_codec = db_codec
        self._lastsql = ''
        self._timings = []
        self._pending_references = {}
        self._request_tenant = 'request_tenant'
        self._common_fields = []
        self._referee_name = '%(table)s'
        self._bigint_id = bigint_id
        self._debug = debug
        self._migrated = []
        self._LAZY_TABLES = {}
        self._lazy_tables = lazy_tables
        self._tables = SQLCallableList()
        self._driver_args = driver_args
        self._adapter_args = adapter_args
        self._check_reserved = check_reserved
        self._decode_credentials = decode_credentials
        self._attempts = attempts
        self._do_connect = do_connect

        if not str(attempts).isdigit() or attempts < 0:
            attempts = 5
        if uri:
            uris = isinstance(uri,(list,tuple)) and uri or [uri]
            error = ''
            connected = False
            for k in range(attempts):
                for uri in uris:
                    try:
                        if is_jdbc and not uri.startswith('jdbc:'):
                            uri = 'jdbc:'+uri
                        self._dbname = REGEX_DBNAME.match(uri).group()
                        if not self._dbname in ADAPTERS:
                            raise SyntaxError("Error in URI '%s' or database not supported" % self._dbname)
                        # notice that driver args or {} else driver_args
                        # defaults to {} global, not correct
                        kwargs = dict(db=self,uri=uri,
                                      pool_size=pool_size,
                                      folder=folder,
                                      db_codec=db_codec,
                                      credential_decoder=credential_decoder,
                                      driver_args=driver_args or {},
                                      adapter_args=adapter_args or {},
                                      do_connect=do_connect,
                                      after_connection=after_connection)
                        self._adapter = ADAPTERS[self._dbname](**kwargs)
                        types = ADAPTERS[self._dbname].types
                        # copy so multiple DAL() possible
                        self._adapter.types = copy.copy(types)
                        self._adapter.build_parsemap()
                        if bigint_id:
                            if 'big-id' in types and 'reference' in types:
                                self._adapter.types['id'] = types['big-id']
                                self._adapter.types['reference'] = types['big-reference']
                        connected = True
                        break
                    except SyntaxError:
                        raise
                    except Exception:
                        tb = traceback.format_exc()
                        LOGGER.debug('DEBUG: connect attempt %i, connection error:\n%s' % (k, tb))
                if connected:
                    break
                else:
                    time.sleep(1)
            if not connected:
                raise RuntimeError("Failure to connect, tried %d times:\n%s" % (attempts, tb))
        else:
            self._adapter = BaseAdapter(db=self,pool_size=0,
                                        uri='None',folder=folder,
                                        db_codec=db_codec, after_connection=after_connection)
            migrate = fake_migrate = False
        adapter = self._adapter
        self._uri_hash = hashlib_md5(adapter.uri).hexdigest()
        self.check_reserved = check_reserved
        if self.check_reserved:
            from reserved_sql_keywords import ADAPTERS as RSK
            self.RSK = RSK
        self._migrate = migrate
        self._fake_migrate = fake_migrate
        self._migrate_enabled = migrate_enabled
        self._fake_migrate_all = fake_migrate_all
        if auto_import or tables:
            self.import_table_definitions(adapter.folder,
                                          tables=tables)

    @property
    def tables(self):
        return self._tables

    def import_table_definitions(self, path, migrate=False,
                                 fake_migrate=False, tables=None):
        pattern = pjoin(path,self._uri_hash+'_*.table')
        if tables:
            for table in tables:
                self.define_table(**table)
        else:
            for filename in glob.glob(pattern):
                tfile = self._adapter.file_open(filename, 'r')
                try:
                    sql_fields = pickle.load(tfile)
                    name = filename[len(pattern)-7:-6]
                    mf = [(value['sortable'],
                           Field(key,
                                 type=value['type'],
                                 length=value.get('length',None),
                                 notnull=value.get('notnull',False),
                                 unique=value.get('unique',False))) \
                              for key, value in sql_fields.iteritems()]
                    mf.sort(lambda a,b: cmp(a[0],b[0]))
                    self.define_table(name,*[item[1] for item in mf],
                                      **dict(migrate=migrate,
                                             fake_migrate=fake_migrate))
                finally:
                    self._adapter.file_close(tfile)

    def check_reserved_keyword(self, name):
        """
        Validates ``name`` against SQL keywords
        Uses self.check_reserve which is a list of
        operators to use.
        self.check_reserved
        ['common', 'postgres', 'mysql']
        self.check_reserved
        ['all']
        """
        for backend in self.check_reserved:
            if name.upper() in self.RSK[backend]:
                raise SyntaxError(
                    'invalid table/column name "%s" is a "%s" reserved SQL/NOSQL keyword' % (name, backend.upper()))

    def parse_as_rest(self,patterns,args,vars,queries=None,nested_select=True):
        """
        EXAMPLE:

db.define_table('person',Field('name'),Field('info'))
db.define_table('pet',Field('ownedby',db.person),Field('name'),Field('info'))

@request.restful()
def index():
    def GET(*args,**vars):
        patterns = [
            "/friends[person]",
            "/{person.name}/:field",
            "/{person.name}/pets[pet.ownedby]",
            "/{person.name}/pets[pet.ownedby]/{pet.name}",
            "/{person.name}/pets[pet.ownedby]/{pet.name}/:field",
            ("/dogs[pet]", db.pet.info=='dog'),
            ("/dogs[pet]/{pet.name.startswith}", db.pet.info=='dog'),
            ]
        parser = db.parse_as_rest(patterns,args,vars)
        if parser.status == 200:
            return dict(content=parser.response)
        else:
            raise HTTP(parser.status,parser.error)

    def POST(table_name,**vars):
        if table_name == 'person':
            return db.person.validate_and_insert(**vars)
        elif table_name == 'pet':
            return db.pet.validate_and_insert(**vars)
        else:
            raise HTTP(400)
    return locals()
        """

        db = self
        re1 = REGEX_SEARCH_PATTERN
        re2 = REGEX_SQUARE_BRACKETS

        def auto_table(table,base='',depth=0):
            patterns = []
            for field in db[table].fields:
                if base:
                    tag = '%s/%s' % (base,field.replace('_','-'))
                else:
                    tag = '/%s/%s' % (table.replace('_','-'),field.replace('_','-'))
                f = db[table][field]
                if not f.readable: continue
                if f.type=='id' or 'slug' in field or f.type.startswith('reference'):
                    tag += '/{%s.%s}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type.startswith('boolean'):
                    tag += '/{%s.%s}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type in ('float','double','integer','bigint'):
                    tag += '/{%s.%s.ge}/{%s.%s.lt}' % (table,field,table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type.startswith('list:'):
                    tag += '/{%s.%s.contains}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                elif f.type in ('date','datetime'):
                    tag+= '/{%s.%s.year}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag+='/{%s.%s.month}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag+='/{%s.%s.day}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                if f.type in ('datetime','time'):
                    tag+= '/{%s.%s.hour}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag+='/{%s.%s.minute}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                    tag+='/{%s.%s.second}' % (table,field)
                    patterns.append(tag)
                    patterns.append(tag+'/:field')
                if depth>0:
                    for f in db[table]._referenced_by:
                        tag+='/%s[%s.%s]' % (table,f.tablename,f.name)
                        patterns.append(tag)
                        patterns += auto_table(table,base=tag,depth=depth-1)
            return patterns

        if patterns == 'auto':
            patterns=[]
            for table in db.tables:
                if not table.startswith('auth_'):
                    patterns.append('/%s[%s]' % (table,table))
                    patterns += auto_table(table,base='',depth=1)
        else:
            i = 0
            while i<len(patterns):
                pattern = patterns[i]
                if not isinstance(pattern,str):
                    pattern = pattern[0]
                tokens = pattern.split('/')
                if tokens[-1].startswith(':auto') and re2.match(tokens[-1]):
                    new_patterns = auto_table(tokens[-1][tokens[-1].find('[')+1:-1],
                                              '/'.join(tokens[:-1]))
                    patterns = patterns[:i]+new_patterns+patterns[i+1:]
                    i += len(new_patterns)
                else:
                    i += 1
        if '/'.join(args) == 'patterns':
            return Row({'status':200,'pattern':'list',
                        'error':None,'response':patterns})
        for pattern in patterns:
            basequery, exposedfields = None, []
            if isinstance(pattern,tuple):
                if len(pattern)==2:
                    pattern, basequery = pattern
                elif len(pattern)>2:
                    pattern, basequery, exposedfields = pattern[0:3]
            otable=table=None
            if not isinstance(queries,dict):
                dbset=db(queries)
                if basequery is not None:
                    dbset = dbset(basequery)
            i=0
            tags = pattern[1:].split('/')
            if len(tags)!=len(args):
                continue
            for tag in tags:
                if re1.match(tag):
                    # print 're1:'+tag
                    tokens = tag[1:-1].split('.')
                    table, field = tokens[0], tokens[1]
                    if not otable or table == otable:
                        if len(tokens)==2 or tokens[2]=='eq':
                            query = db[table][field]==args[i]
                        elif tokens[2]=='ne':
                            query = db[table][field]!=args[i]
                        elif tokens[2]=='lt':
                            query = db[table][field]<args[i]
                        elif tokens[2]=='gt':
                            query = db[table][field]>args[i]
                        elif tokens[2]=='ge':
                            query = db[table][field]>=args[i]
                        elif tokens[2]=='le':
                            query = db[table][field]<=args[i]
                        elif tokens[2]=='year':
                            query = db[table][field].year()==args[i]
                        elif tokens[2]=='month':
                            query = db[table][field].month()==args[i]
                        elif tokens[2]=='day':
                            query = db[table][field].day()==args[i]
                        elif tokens[2]=='hour':
                            query = db[table][field].hour()==args[i]
                        elif tokens[2]=='minute':
                            query = db[table][field].minutes()==args[i]
                        elif tokens[2]=='second':
                            query = db[table][field].seconds()==args[i]
                        elif tokens[2]=='startswith':
                            query = db[table][field].startswith(args[i])
                        elif tokens[2]=='contains':
                            query = db[table][field].contains(args[i])
                        else:
                            raise RuntimeError("invalid pattern: %s" % pattern)
                        if len(tokens)==4 and tokens[3]=='not':
                            query = ~query
                        elif len(tokens)>=4:
                            raise RuntimeError("invalid pattern: %s" % pattern)
                        if not otable and isinstance(queries,dict):
                            dbset = db(queries[table])
                            if basequery is not None:
                                dbset = dbset(basequery)
                        dbset=dbset(query)
                    else:
                        raise RuntimeError("missing relation in pattern: %s" % pattern)
                elif re2.match(tag) and args[i]==tag[:tag.find('[')]:
                    ref = tag[tag.find('[')+1:-1]
                    if '.' in ref and otable:
                        table,field = ref.split('.')
                        selfld = '_id'
                        if db[table][field].type.startswith('reference '):
                            refs = [ x.name for x in db[otable] if x.type == db[table][field].type ]
                        else:
                            refs = [ x.name for x in db[table]._referenced_by if x.tablename==otable ]
                        if refs:
                            selfld = refs[0]
                        if nested_select:
                            try:
                                dbset=db(db[table][field].belongs(dbset._select(db[otable][selfld])))
                            except ValueError:
                                return Row({'status':400,'pattern':pattern,
                                            'error':'invalid path','response':None})
                        else:
                            items = [item.id for item in dbset.select(db[otable][selfld])]
                            dbset=db(db[table][field].belongs(items))
                    else:
                        table = ref
                        if not otable and isinstance(queries,dict):
                            dbset = db(queries[table])
                        dbset=dbset(db[table])
                elif tag==':field' and table:
                    # print 're3:'+tag
                    field = args[i]
                    if not field in db[table]: break
                    # hand-built patterns should respect .readable=False as well
                    if not db[table][field].readable:
                        return Row({'status':418,'pattern':pattern,
                                    'error':'I\'m a teapot','response':None})
                    try:
                        distinct = vars.get('distinct', False) == 'True'
                        offset = long(vars.get('offset',None) or 0)
                        limits = (offset,long(vars.get('limit',None) or 1000)+offset)
                    except ValueError:
                        return Row({'status':400,'error':'invalid limits','response':None})
                    items =  dbset.select(db[table][field], distinct=distinct, limitby=limits)
                    if items:
                        return Row({'status':200,'response':items,
                                    'pattern':pattern})
                    else:
                        return Row({'status':404,'pattern':pattern,
                                    'error':'no record found','response':None})
                elif tag != args[i]:
                    break
                otable = table
                i += 1
                if i==len(tags) and table:
                    ofields = vars.get('order',db[table]._id.name).split('|')
                    try:
                        orderby = [db[table][f] if not f.startswith('~') else ~db[table][f[1:]] for f in ofields]
                    except (KeyError, AttributeError):
                        return Row({'status':400,'error':'invalid orderby','response':None})
                    if exposedfields:
                        fields = [field for field in db[table] if str(field).split('.')[-1] in exposedfields and field.readable]
                    else:
                        fields = [field for field in db[table] if field.readable]
                    count = dbset.count()
                    try:
                        offset = long(vars.get('offset',None) or 0)
                        limits = (offset,long(vars.get('limit',None) or 1000)+offset)
                    except ValueError:
                        return Row({'status':400,'error':'invalid limits','response':None})
                    if count > limits[1]-limits[0]:
                        return Row({'status':400,'error':'too many records','response':None})
                    try:
                        response = dbset.select(limitby=limits,orderby=orderby,*fields)
                    except ValueError:
                        return Row({'status':400,'pattern':pattern,
                                    'error':'invalid path','response':None})
                    return Row({'status':200,'response':response,
                                'pattern':pattern,'count':count})
        return Row({'status':400,'error':'no matching pattern','response':None})

    def define_table(
        self,
        tablename,
        *fields,
        **args
        ):
        if not fields and 'fields' in args:
            fields = args.get('fields',())
        if not isinstance(tablename, str):
            if isinstance(tablename, unicode):
                try:
                    tablename = str(tablename)
                except UnicodeEncodeError:
                    raise SyntaxError("invalid unicode table name")
            else:
                raise SyntaxError("missing table name")
        elif hasattr(self,tablename) or tablename in self.tables:
            if not args.get('redefine',False):
                raise SyntaxError('table already defined: %s' % tablename)
        elif tablename.startswith('_') or hasattr(self,tablename) or \
                REGEX_PYTHON_KEYWORDS.match(tablename):
            raise SyntaxError('invalid table name: %s' % tablename)
        elif self.check_reserved:
            self.check_reserved_keyword(tablename)
        else:
            invalid_args = set(args)-TABLE_ARGS
            if invalid_args:
                raise SyntaxError('invalid table "%s" attributes: %s' \
                    % (tablename,invalid_args))
        if self._lazy_tables and not tablename in self._LAZY_TABLES:
            self._LAZY_TABLES[tablename] = (tablename,fields,args)
            table = None
        else:
            table = self.lazy_define_table(tablename,*fields,**args)
        if not tablename in self.tables:
            self.tables.append(tablename)
        return table

    def lazy_define_table(
        self,
        tablename,
        *fields,
        **args
        ):
        args_get = args.get
        common_fields = self._common_fields
        if common_fields:
            fields = list(fields) + list(common_fields)

        table_class = args_get('table_class',Table)
        table = table_class(self, tablename, *fields, **args)
        table._actual = True
        self[tablename] = table
        # must follow above line to handle self references
        table._create_references()
        for field in table:
            if field.requires == DEFAULT:
                field.requires = sqlhtml_validators(field)

        migrate = self._migrate_enabled and args_get('migrate',self._migrate)
        if migrate and not self._uri in (None,'None') \
                or self._adapter.dbengine=='google:datastore':
            fake_migrate = self._fake_migrate_all or \
                args_get('fake_migrate',self._fake_migrate)
            polymodel = args_get('polymodel',None)
            try:
                GLOBAL_LOCKER.acquire()
                self._lastsql = self._adapter.create_table(
                    table,migrate=migrate,
                    fake_migrate=fake_migrate,
                    polymodel=polymodel)
            finally:
                GLOBAL_LOCKER.release()
        else:
            table._dbt = None
        on_define = args_get('on_define',None)
        if on_define: on_define(table)
        return table

    def as_dict(self, flat=False, sanitize=True):
        db_uid = uri = None
        if not sanitize:
            uri, db_uid = (self._uri, self._db_uid)
        db_as_dict = dict(tables=[], uri=uri, db_uid=db_uid,
                          **dict([(k, getattr(self, "_" + k, None))
                          for k in 'pool_size','folder','db_codec',
                          'check_reserved','migrate','fake_migrate',
                          'migrate_enabled','fake_migrate_all',
                          'decode_credentials','driver_args',
                          'adapter_args', 'attempts',
                          'bigint_id','debug','lazy_tables',
                          'do_connect']))
        for table in self:
            db_as_dict["tables"].append(table.as_dict(flat=flat,
                                        sanitize=sanitize))
        return db_as_dict

    def as_xml(self, sanitize=True):
        if not have_serializers:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return serializers.xml(d)

    def as_json(self, sanitize=True):
        if not have_serializers:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return serializers.json(d)

    def as_yaml(self, sanitize=True):
        if not have_serializers:
            raise ImportError("No YAML serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return serializers.yaml(d)

    def __contains__(self, tablename):
        try:
            return tablename in self.tables
        except AttributeError:
            # The instance has no .tables attribute yet
            return False

    has_key = __contains__

    def get(self,key,default=None):
        return self.__dict__.get(key,default)

    def __iter__(self):
        for tablename in self.tables:
            yield self[tablename]

    def __getitem__(self, key):
        return self.__getattr__(str(key))

    def __getattr__(self, key):
        if ogetattr(self,'_lazy_tables') and \
                key in ogetattr(self,'_LAZY_TABLES'):
            tablename, fields, args = self._LAZY_TABLES.pop(key)
            return self.lazy_define_table(tablename,*fields,**args)
        return ogetattr(self, key)

    def __setitem__(self, key, value):
        osetattr(self, str(key), value)

    def __setattr__(self, key, value):
        if key[:1]!='_' and key in self:
            raise SyntaxError(
                'Object %s exists and cannot be redefined' % key)
        osetattr(self,key,value)

    __delitem__ = object.__delattr__

    def __repr__(self):
        if hasattr(self,'_uri'):
            return '<DAL uri="%s">' % hide_password(self._adapter.uri)
        else:
            return '<DAL db_uid="%s">' % self._db_uid

    def smart_query(self,fields,text):
        return Set(self, smart_query(fields,text))

    def __call__(self, query=None, ignore_common_filters=None):
        if isinstance(query,Table):
            query = self._adapter.id_query(query)
        elif isinstance(query,Field):
            query = query!=None
        elif isinstance(query, dict):
            icf = query.get("ignore_common_filters")
            if icf: ignore_common_filters = icf
        return Set(self, query, ignore_common_filters=ignore_common_filters)

    def commit(self):
        self._adapter.commit()

    def rollback(self):
        self._adapter.rollback()

    def close(self):
        self._adapter.close()
        if self._db_uid in THREAD_LOCAL.db_instances:
            db_group = THREAD_LOCAL.db_instances[self._db_uid]
            db_group.remove(self)
            if not db_group:
                del THREAD_LOCAL.db_instances[self._db_uid]

    def executesql(self, query, placeholders=None, as_dict=False,
                   fields=None, colnames=None, as_ordered_dict=False):
        """
        placeholders is optional and will always be None.
        If using raw SQL with placeholders, placeholders may be
        a sequence of values to be substituted in
        or, (if supported by the DB driver), a dictionary with keys
        matching named placeholders in your SQL.

        Added 2009-12-05 "as_dict" optional argument. Will always be
        None when using DAL. If using raw SQL can be set to True and
        the results cursor returned by the DB driver will be converted
        to a sequence of dictionaries keyed with the db field
        names. Tested with SQLite but should work with any database
        since the cursor.description used to get field names is part
        of the Python dbi 2.0 specs. Results returned with
        as_dict=True are the same as those returned when applying
        .to_list() to a DAL query.  If "as_ordered_dict"=True the
        behaviour is the same as when "as_dict"=True with the keys
        (field names) guaranteed to be in the same order as returned
        by the select name executed on the database.

        [{field1: value1, field2: value2}, {field1: value1b, field2: value2b}]

        Added 2012-08-24 "fields" and "colnames" optional arguments. If either
        is provided, the results cursor returned by the DB driver will be
        converted to a DAL Rows object using the db._adapter.parse() method.

        The "fields" argument is a list of DAL Field objects that match the
        fields returned from the DB. The Field objects should be part of one or
        more Table objects defined on the DAL object. The "fields" list can
        include one or more DAL Table objects in addition to or instead of
        including Field objects, or it can be just a single table (not in a
        list). In that case, the Field objects will be extracted from the
        table(s).

        Instead of specifying the "fields" argument, the "colnames" argument
        can be specified as a list of field names in tablename.fieldname format.
        Again, these should represent tables and fields defined on the DAL
        object.

        It is also possible to specify both "fields" and the associated
        "colnames". In that case, "fields" can also include DAL Expression
        objects in addition to Field objects. For Field objects in "fields",
        the associated "colnames" must still be in tablename.fieldname format.
        For Expression objects in "fields", the associated "colnames" can
        be any arbitrary labels.

        Note, the DAL Table objects referred to by "fields" or "colnames" can
        be dummy tables and do not have to represent any real tables in the
        database. Also, note that the "fields" and "colnames" must be in the
        same order as the fields in the results cursor returned from the DB.

        """
        adapter = self._adapter
        if placeholders:
            adapter.execute(query, placeholders)
        else:
            adapter.execute(query)
        if as_dict or as_ordered_dict:
            if not hasattr(adapter.cursor,'description'):
                raise RuntimeError("database does not support executesql(...,as_dict=True)")
            # Non-DAL legacy db query, converts cursor results to dict.
            # sequence of 7-item sequences. each sequence tells about a column.
            # first item is always the field name according to Python Database API specs
            columns = adapter.cursor.description
            # reduce the column info down to just the field names
            fields = colnames or [f[0] for f in columns]
            # will hold our finished resultset in a list
            data = adapter._fetchall()
            # convert the list for each row into a dictionary so it's
            # easier to work with. row['field_name'] rather than row[0]
            if as_ordered_dict:
                _dict = OrderedDict
            else:
                _dict = dict
            return [_dict(zip(fields,row)) for row in data]
        try:
            data = adapter._fetchall()
        except:
            return None
        if fields or colnames:
            fields = [] if fields is None else fields
            if not isinstance(fields, list):
                fields = [fields]
            extracted_fields = []
            for field in fields:
                if isinstance(field, Table):
                    extracted_fields.extend([f for f in field])
                else:
                    extracted_fields.append(field)
            if not colnames:
                colnames = ['%s.%s' % (f.tablename, f.name)
                            for f in extracted_fields]
            data = adapter.parse(
                data, fields=extracted_fields, colnames=colnames)
        return data

    def _remove_references_to(self, thistable):
        for table in self:
            table._referenced_by = [field for field in table._referenced_by
                                    if not field.table==thistable]

    def export_to_csv_file(self, ofile, *args, **kwargs):
        step = long(kwargs.get('max_fetch_rows,',500))
        write_colnames = kwargs['write_colnames'] = \
            kwargs.get("write_colnames", True)
        for table in self.tables:
            ofile.write('TABLE %s\r\n' % table)
            query = self._adapter.id_query(self[table])
            nrows = self(query).count()
            kwargs['write_colnames'] = write_colnames
            for k in range(0,nrows,step):
                self(query).select(limitby=(k,k+step)).export_to_csv_file(
                    ofile, *args, **kwargs)
                kwargs['write_colnames'] = False
            ofile.write('\r\n\r\n')
        ofile.write('END')

    def import_from_csv_file(self, ifile, id_map=None, null='<NULL>',
                             unique='uuid', map_tablenames=None,
                             ignore_missing_tables=False,
                             *args, **kwargs):
        #if id_map is None: id_map={}
        id_offset = {} # only used if id_map is None
        map_tablenames = map_tablenames or {}
        for line in ifile:
            line = line.strip()
            if not line:
                continue
            elif line == 'END':
                return
            elif not line.startswith('TABLE ') or \
                    not line[6:] in self.tables:
                raise SyntaxError('invalid file format')
            else:
                tablename = line[6:]
                tablename = map_tablenames.get(tablename,tablename)
                if tablename is not None and tablename in self.tables:
                    self[tablename].import_from_csv_file(
                        ifile, id_map, null, unique, id_offset,
                        *args, **kwargs)
                elif tablename is None or ignore_missing_tables:
                    # skip all non-empty lines
                    for line in ifile:
                        if not line.strip():
                            break
                else:
                    raise RuntimeError("Unable to import table that does not exist.\nTry db.import_from_csv_file(..., map_tablenames={'table':'othertable'},ignore_missing_tables=True)")


def DAL_unpickler(db_uid):
    return DAL('<zombie>',db_uid=db_uid)

def DAL_pickler(db):
    return DAL_unpickler, (db._db_uid,)

copyreg.pickle(DAL, DAL_pickler, DAL_unpickler)

class SQLALL(object):
    """
    Helper class providing a comma-separated string having all the field names
    (prefixed by table name and '.')

    normally only called from within gluon.sql
    """

    def __init__(self, table):
        self._table = table

    def __str__(self):
        return ', '.join([str(field) for field in self._table])

# class Reference(int):
class Reference(long):

    def __allocate(self):
        if not self._record:
            self._record = self._table[long(self)]
        if not self._record:
            raise RuntimeError(
                "Using a recursive select but encountered a broken reference: %s %d"%(self._table, long(self)))

    def __getattr__(self, key):
        if key == 'id':
            return long(self)
        if key in self._table:
            self.__allocate()
        if self._record:
            return self._record.get(key,None) # to deal with case self.update_record()
        else:
            return None

    def get(self, key, default=None):
        return self.__getattr__(key, default)

    def __setattr__(self, key, value):
        if key.startswith('_'):
            long.__setattr__(self, key, value)
            return
        self.__allocate()
        self._record[key] =  value

    def __getitem__(self, key):
        if key == 'id':
            return long(self)
        self.__allocate()
        return self._record.get(key, None)

    def __setitem__(self,key,value):
        self.__allocate()
        self._record[key] = value


def Reference_unpickler(data):
    return marshal.loads(data)

def Reference_pickler(data):
    try:
        marshal_dump = marshal.dumps(long(data))
    except AttributeError:
        marshal_dump = 'i%s' % struct.pack('<i', long(data))
    return (Reference_unpickler, (marshal_dump,))

copyreg.pickle(Reference, Reference_pickler, Reference_unpickler)

class MethodAdder(object):
    def __init__(self,table):
        self.table = table
    def __call__(self):
        return self.register()
    def __getattr__(self,method_name):
        return self.register(method_name)
    def register(self,method_name=None):
        def _decorated(f):
            instance = self.table
            import types
            method = types.MethodType(f, instance, instance.__class__)
            name = method_name or f.func_name
            setattr(instance, name, method)
            return f
        return _decorated

class Table(object):

    """
    an instance of this class represents a database table

    Example::

        db = DAL(...)
        db.define_table('users', Field('name'))
        db.users.insert(name='me') # print db.users._insert(...) to see SQL
        db.users.drop()
    """

    def __init__(
        self,
        db,
        tablename,
        *fields,
        **args
        ):
        """
        Initializes the table and performs checking on the provided fields.

        Each table will have automatically an 'id'.

        If a field is of type Table, the fields (excluding 'id') from that table
        will be used instead.

        :raises SyntaxError: when a supplied field is of incorrect type.
        """
        self._actual = False # set to True by define_table()
        self._tablename = tablename
        self._ot = None # args.get('rname')
        self._rname = args.get('rname')
        if not self._rname:
            self._sequence_name = args.get('sequence_name') or \
                db and db._adapter.sequence_name(tablename)
        else:
            tb = self._rname[1:-1]
            self._sequence_name = args.get('sequence_name') or \
                db and db._adapter.sequence_name(tb)
        self._trigger_name = args.get('trigger_name') or \
            db and db._adapter.trigger_name(tablename)
        self._common_filter = args.get('common_filter')
        self._format = args.get('format')
        self._singular = args.get(
            'singular',tablename.replace('_',' ').capitalize())
        self._plural = args.get(
            'plural',pluralize(self._singular.lower()).capitalize())
        # horrible but for backard compatibility of appamdin:
        if 'primarykey' in args and args['primarykey'] is not None:
            self._primarykey = args.get('primarykey')

        self._before_insert = []
        self._before_update = [Set.delete_uploaded_files]
        self._before_delete = [Set.delete_uploaded_files]
        self._after_insert = []
        self._after_update = []
        self._after_delete = []

        self.add_method = MethodAdder(self)

        fieldnames,newfields=set(),[]
        _primarykey = getattr(self, '_primarykey', None)
        if _primarykey is not None:
            if not isinstance(_primarykey, list):
                raise SyntaxError(
                    "primarykey must be a list of fields from table '%s'" \
                    % tablename)
            if len(_primarykey)==1:
                self._id = [f for f in fields if isinstance(f,Field) \
                                and f.name==_primarykey[0]][0]
        elif not [f for f in fields if (isinstance(f,Field) and
                  f.type=='id') or (isinstance(f, dict) and
                  f.get("type", None)=="id")]:
            field = Field('id', 'id')
            newfields.append(field)
            fieldnames.add('id')
            self._id = field
        virtual_fields = []
        def include_new(field):
            newfields.append(field)
            fieldnames.add(field.name)
            if field.type=='id':
                self._id = field
        for field in fields:
            if isinstance(field, (FieldMethod, FieldVirtual)):
                virtual_fields.append(field)
            elif isinstance(field, Field) and not field.name in fieldnames:
                if field.db is not None:
                    field = copy.copy(field)
                include_new(field)
            elif isinstance(field, dict) and not field['fieldname'] in fieldnames:
                include_new(Field(**field))
            elif isinstance(field, Table):
                table = field
                for field in table:
                    if not field.name in fieldnames and not field.type=='id':
                        t2 = not table._actual and self._tablename
                        include_new(field.clone(point_self_references_to=t2))
            elif not isinstance(field, (Field, Table)):
                raise SyntaxError(
                    'define_table argument is not a Field or Table: %s' % field)
        fields = newfields
        self._db = db
        tablename = tablename
        self._fields = SQLCallableList()
        self.virtualfields = []
        fields = list(fields)

        if db and db._adapter.uploads_in_blob==True:
            uploadfields = [f.name for f in fields if f.type=='blob']
            for field in fields:
                fn = field.uploadfield
                if isinstance(field, Field) and field.type == 'upload'\
                        and fn is True:
                    fn = field.uploadfield = '%s_blob' % field.name
                if isinstance(fn,str) and not fn in uploadfields:
                    fields.append(Field(fn,'blob',default='',
                                        writable=False,readable=False))

        lower_fieldnames = set()
        reserved = dir(Table) + ['fields']
        if (db and db.check_reserved):
            check_reserved = db.check_reserved_keyword
        else:
            def check_reserved(field_name):
              if field_name in reserved:
                raise SyntaxError("field name %s not allowed" % field_name)
        for field in fields:
            field_name = field.name
            check_reserved(field_name)
            fn_lower = field_name.lower()
            if fn_lower in lower_fieldnames:
                raise SyntaxError("duplicate field %s in table %s" \
                    % (field_name, tablename))
            else:
                lower_fieldnames.add(fn_lower)

            self.fields.append(field_name)
            self[field_name] = field
            if field.type == 'id':
                self['id'] = field
            field.tablename = field._tablename = tablename
            field.table = field._table = self
            field.db = field._db = db
        self.ALL = SQLALL(self)

        if _primarykey is not None:
            for k in _primarykey:
                if k not in self.fields:
                    raise SyntaxError(
                        "primarykey must be a list of fields from table '%s " % tablename)
                else:
                    self[k].notnull = True
        for field in virtual_fields:
            self[field.name] = field

    @property
    def fields(self):
        return self._fields

    def update(self,*args,**kwargs):
        raise RuntimeError("Syntax Not Supported")

    def _enable_record_versioning(self,
                                  archive_db=None,
                                  archive_name = '%(tablename)s_archive',
                                  is_active = 'is_active',
                                  current_record = 'current_record',
                                  current_record_label = None):
        db = self._db
        archive_db = archive_db or db
        archive_name = archive_name % dict(tablename=self._tablename)
        if archive_name in archive_db.tables():
            return # do not try define the archive if already exists
        fieldnames = self.fields()
        same_db = archive_db is db
        field_type = self if same_db else 'bigint'
        clones = []
        for field in self:
            nfk = same_db or not field.type.startswith('reference')
            clones.append(field.clone(
                    unique=False, type=field.type if nfk else 'bigint'))
        archive_db.define_table(
            archive_name,
            Field(current_record,field_type,label=current_record_label),
            *clones,**dict(format=self._format))

        self._before_update.append(
            lambda qset,fs,db=archive_db,an=archive_name,cn=current_record:
                archive_record(qset,fs,db[an],cn))
        if is_active and is_active in fieldnames:
            self._before_delete.append(
                lambda qset: qset.update(is_active=False))
            newquery = lambda query, t=self, name=self._tablename: \
                reduce(AND,[db[tn].is_active == True
                            for tn in db._adapter.tables(query)
                            if tn==name or getattr(db[tn],'_ot',None)==name])
            query = self._common_filter
            if query:
                newquery = query & newquery
            self._common_filter = newquery

    def _validate(self,**vars):
        errors = Row()
        for key,value in vars.iteritems():
            value,error = self[key].validate(value)
            if error:
                errors[key] = error
        return errors

    def _create_references(self):
        db = self._db
        pr = db._pending_references
        self._referenced_by = []
        self._references = []
        for field in self:
            fieldname = field.name
            field_type = field.type
            if isinstance(field_type,str) and field_type[:10] == 'reference ':
                ref = field_type[10:].strip()
                if not ref:
                    SyntaxError('Table: reference to nothing: %s' %ref)
                if '.' in ref:
                    rtablename, throw_it,rfieldname = ref.partition('.')
                else:
                    rtablename, rfieldname = ref, None
                if not rtablename in db:
                    pr[rtablename] = pr.get(rtablename,[]) + [field]
                    continue
                rtable = db[rtablename]
                if rfieldname:
                    if not hasattr(rtable,'_primarykey'):
                        raise SyntaxError(
                            'keyed tables can only reference other keyed tables (for now)')
                    if rfieldname not in rtable.fields:
                        raise SyntaxError(
                            "invalid field '%s' for referenced table '%s' in table '%s'" \
                            % (rfieldname, rtablename, self._tablename))
                    rfield = rtable[rfieldname]
                else:
                    rfield = rtable._id
                rtable._referenced_by.append(field)
                field.referent = rfield
                self._references.append(field)
            else:
                field.referent = None
        if self._tablename in pr:
            referees = pr.pop(self._tablename)
            for referee in referees:
                self._referenced_by.append(referee)


    def _filter_fields(self, record, id=False):
        return dict([(k, v) for (k, v) in record.iteritems() if k
                     in self.fields and (self[k].type!='id' or id)])

    def _build_query(self,key):
        """ for keyed table only """
        query = None
        for k,v in key.iteritems():
            if k in self._primarykey:
                if query:
                    query = query & (self[k] == v)
                else:
                    query = (self[k] == v)
            else:
                raise SyntaxError(
                'Field %s is not part of the primary key of %s' % \
                (k,self._tablename))
        return query

    def __getitem__(self, key):
        if not key:
            return None
        elif isinstance(key, dict):
            """ for keyed table """
            query = self._build_query(key)
            return self._db(query).select(limitby=(0,1), orderby_on_limitby=False).first()
        elif str(key).isdigit() or 'google' in DRIVERS and isinstance(key, Key):
            return self._db(self._id == key).select(limitby=(0,1), orderby_on_limitby=False).first()
        elif key:
            return ogetattr(self, str(key))

    def __call__(self, key=DEFAULT, **kwargs):
        for_update = kwargs.get('_for_update',False)
        if '_for_update' in kwargs: del kwargs['_for_update']

        orderby = kwargs.get('_orderby',None)
        if '_orderby' in kwargs: del kwargs['_orderby']

        if not key is DEFAULT:
            if isinstance(key, Query):
                record = self._db(key).select(
                    limitby=(0,1),for_update=for_update, orderby=orderby, orderby_on_limitby=False).first()
            elif not str(key).isdigit():
                record = None
            else:
                record = self._db(self._id == key).select(
                    limitby=(0,1),for_update=for_update, orderby=orderby, orderby_on_limitby=False).first()
            if record:
                for k,v in kwargs.iteritems():
                    if record[k]!=v: return None
            return record
        elif kwargs:
            query = reduce(lambda a,b:a&b,[self[k]==v for k,v in kwargs.iteritems()])
            return self._db(query).select(limitby=(0,1),for_update=for_update, orderby=orderby, orderby_on_limitby=False).first()
        else:
            return None

    def __setitem__(self, key, value):
        if isinstance(key, dict) and isinstance(value, dict):
            """ option for keyed table """
            if set(key.keys()) == set(self._primarykey):
                value = self._filter_fields(value)
                kv = {}
                kv.update(value)
                kv.update(key)
                if not self.insert(**kv):
                    query = self._build_query(key)
                    self._db(query).update(**self._filter_fields(value))
            else:
                raise SyntaxError(
                    'key must have all fields from primary key: %s'%\
                    (self._primarykey))
        elif str(key).isdigit():
            if key == 0:
                self.insert(**self._filter_fields(value))
            elif self._db(self._id == key)\
                    .update(**self._filter_fields(value)) is None:
                raise SyntaxError('No such record: %s' % key)
        else:
            if isinstance(key, dict):
                raise SyntaxError(
                    'value must be a dictionary: %s' % value)
            osetattr(self, str(key), value)

    __getattr__ = __getitem__

    def __setattr__(self, key, value):
        if key[:1]!='_' and key in self:
            raise SyntaxError('Object exists and cannot be redefined: %s' % key)
        osetattr(self,key,value)

    def __delitem__(self, key):
        if isinstance(key, dict):
            query = self._build_query(key)
            if not self._db(query).delete():
                raise SyntaxError('No such record: %s' % key)
        elif not str(key).isdigit() or \
                not self._db(self._id == key).delete():
            raise SyntaxError('No such record: %s' % key)

    def __contains__(self,key):
        return hasattr(self,key)

    has_key = __contains__

    def items(self):
        return self.__dict__.items()

    def __iter__(self):
        for fieldname in self.fields:
            yield self[fieldname]

    def iteritems(self):
        return self.__dict__.iteritems()


    def __repr__(self):
        return '<Table %s (%s)>' % (self._tablename,','.join(self.fields()))

    def __str__(self):
        if self._ot is not None:
            ot = self._ot
            if 'Oracle' in str(type(self._db._adapter)):
                return '%s %s' % (ot, self._tablename)
            return '%s AS %s' % (ot, self._tablename)
        return self._tablename

    def _drop(self, mode = ''):
        return self._db._adapter._drop(self, mode)

    def drop(self, mode = ''):
        return self._db._adapter.drop(self,mode)

    def _listify(self,fields,update=False):
        new_fields = {} # format: new_fields[name] = (field,value)

        # store all fields passed as input in new_fields
        for name in fields:
            if not name in self.fields:
                if name != 'id':
                    raise SyntaxError(
                        'Field %s does not belong to the table' % name)
            else:
                field = self[name]
                value = fields[name]
                if field.filter_in:
                    value = field.filter_in(value)
                new_fields[name] = (field,value)

        # check all fields that should be in the table but are not passed
        to_compute = []
        for ofield in self:
            name = ofield.name
            if not name in new_fields:
                # if field is supposed to be computed, compute it!
                if ofield.compute: # save those to compute for later
                    to_compute.append((name,ofield))
                # if field is required, check its default value
                elif not update and not ofield.default is None:
                    value = ofield.default
                    fields[name] = value
                    new_fields[name] = (ofield,value)
                # if this is an update, user the update field instead
                elif update and not ofield.update is None:
                    value = ofield.update
                    fields[name] = value
                    new_fields[name] = (ofield,value)
                # if the field is still not there but it should, error
                elif not update and ofield.required:
                    raise RuntimeError(
                        'Table: missing required field: %s' % name)
        # now deal with fields that are supposed to be computed
        if to_compute:
            row = Row(fields)
            for name,ofield in to_compute:
                # try compute it
                try:
                    row[name] = new_value = ofield.compute(row)
                    new_fields[name] = (ofield, new_value)
                except (KeyError, AttributeError):
                    # error silently unless field is required!
                    if ofield.required:
                        raise SyntaxError('unable to compute field: %s' % name)
        return new_fields.values()

    def _attempt_upload(self, fields):
        for field in self:
            if field.type=='upload' and field.name in fields:
                value = fields[field.name]
                if value is not None and not isinstance(value,str):
                    if hasattr(value,'file') and hasattr(value,'filename'):
                        new_name = field.store(value.file,filename=value.filename)
                    elif hasattr(value,'read') and hasattr(value,'name'):
                        new_name = field.store(value,filename=value.name)
                    else:
                        raise RuntimeError("Unable to handle upload")
                    fields[field.name] = new_name

    def _defaults(self, fields):
        "If there are no fields/values specified, return table defaults"
        if not fields:
            fields = {}
            for field in self:
                if field.type != "id":
                    fields[field.name] = field.default
        return fields

    def _insert(self, **fields):
        fields = self._defaults(fields)
        return self._db._adapter._insert(self, self._listify(fields))

    def insert(self, **fields):
        fields = self._defaults(fields)
        self._attempt_upload(fields)
        if any(f(fields) for f in self._before_insert): return 0
        ret =  self._db._adapter.insert(self, self._listify(fields))
        if ret and self._after_insert:
            fields = Row(fields)
            [f(fields,ret) for f in self._after_insert]
        return ret

    def validate_and_insert(self,**fields):
        response = Row()
        response.errors = Row()
        new_fields = copy.copy(fields)
        for key,value in fields.iteritems():
            value,error = self[key].validate(value)
            if error:
                response.errors[key] = "%s" % error
            else:
                new_fields[key] = value
        if not response.errors:
            response.id = self.insert(**new_fields)
        else:
            response.id = None
        return response

    def validate_and_update(self, _key=DEFAULT, **fields):
        response = Row()
        response.errors = Row()
        new_fields = copy.copy(fields)

        for key,value in fields.iteritems():
            value,error = self[key].validate(value)
            if error:
                response.errors[key] = "%s" % error
            else:
                new_fields[key] = value

        if _key is DEFAULT:
           record = self(**values)
        elif isinstance(_key,dict):
            record = self(**_key)
        else:
            record = self(_key)

        if not response.errors and record:
            row = self._db(self._id==_key)
            response.id = row.update(**fields)
        else:
            response.id = None
        return response

    def update_or_insert(self, _key=DEFAULT, **values):
        if _key is DEFAULT:
            record = self(**values)
        elif isinstance(_key,dict):
            record = self(**_key)
        else:
            record = self(_key)
        if record:
            record.update_record(**values)
            newid = None
        else:
            newid = self.insert(**values)
        return newid

    def bulk_insert(self, items):
        """
        here items is a list of dictionaries
        """
        items = [self._listify(item) for item in items]
        if any(f(item) for item in items for f in self._before_insert):return 0
        ret = self._db._adapter.bulk_insert(self,items)
        ret and [[f(item,ret[k]) for k,item in enumerate(items)] for f in self._after_insert]
        return ret

    def _truncate(self, mode = None):
        return self._db._adapter._truncate(self, mode)

    def truncate(self, mode = None):
        return self._db._adapter.truncate(self, mode)

    def import_from_csv_file(
        self,
        csvfile,
        id_map=None,
        null='<NULL>',
        unique='uuid',
        id_offset=None, # id_offset used only when id_map is None
        *args, **kwargs
        ):
        """
        Import records from csv file.
        Column headers must have same names as table fields.
        Field 'id' is ignored.
        If column names read 'table.file' the 'table.' prefix is ignored.
        'unique' argument is a field which must be unique
            (typically a uuid field)
        'restore' argument is default False;
            if set True will remove old values in table first.
        'id_map' if set to None will not map ids.
        The import will keep the id numbers in the restored table.
        This assumes that there is an field of type id that
        is integer and in incrementing order.
        Will keep the id numbers in restored table.
        """

        delimiter = kwargs.get('delimiter', ',')
        quotechar = kwargs.get('quotechar', '"')
        quoting = kwargs.get('quoting', csv.QUOTE_MINIMAL)
        restore = kwargs.get('restore', False)
        if restore:
            self._db[self].truncate()

        reader = csv.reader(csvfile, delimiter=delimiter,
                            quotechar=quotechar, quoting=quoting)
        colnames = None
        if isinstance(id_map, dict):
            if not self._tablename in id_map:
                id_map[self._tablename] = {}
            id_map_self = id_map[self._tablename]

        def fix(field, value, id_map, id_offset):
            list_reference_s='list:reference'
            if value == null:
                value = None
            elif field.type=='blob':
                value = base64.b64decode(value)
            elif field.type=='double' or field.type=='float':
                if not value.strip():
                    value = None
                else:
                    value = float(value)
            elif field.type in ('integer','bigint'):
                if not value.strip():
                    value = None
                else:
                    value = long(value)
            elif field.type.startswith('list:string'):
                value = bar_decode_string(value)
            elif field.type.startswith(list_reference_s):
                ref_table = field.type[len(list_reference_s):].strip()
                if id_map is not None:
                    value = [id_map[ref_table][long(v)] \
                             for v in bar_decode_string(value)]
                else:
                    value = [v for v in bar_decode_string(value)]
            elif field.type.startswith('list:'):
                value = bar_decode_integer(value)
            elif id_map and field.type.startswith('reference'):
                try:
                    value = id_map[field.type[9:].strip()][long(value)]
                except KeyError:
                    pass
            elif id_offset and field.type.startswith('reference'):
                try:
                    value = id_offset[field.type[9:].strip()]+long(value)
                except KeyError:
                    pass
            return (field.name, value)

        def is_id(colname):
            if colname in self:
                return self[colname].type == 'id'
            else:
                return False

        first = True
        unique_idx = None
        for lineno, line in enumerate(reader):
            if not line:
                break
            if not colnames:
                # assume this is the first line of the input, contains colnames
                colnames = [x.split('.',1)[-1] for x in line][:len(line)]
                cols, cid = [], None
                for i,colname in enumerate(colnames):
                    if is_id(colname):
                        cid = i
                    elif colname in self.fields:
                        cols.append((i,self[colname]))
                    if colname == unique:
                        unique_idx = i
            else:
                # every other line contains instead data
                items = []
                for i, field in cols:
                    try:
                        items.append(fix(field, line[i], id_map, id_offset))
                    except ValueError:
                        raise RuntimeError("Unable to parse line:%s field:%s value:'%s'"
                                           % (lineno+1,field,line[i]))

                if not (id_map or cid is None or id_offset is None or unique_idx):
                    csv_id = long(line[cid])
                    curr_id = self.insert(**dict(items))
                    if first:
                        first = False
                        # First curr_id is bigger than csv_id,
                        # then we are not restoring but
                        # extending db table with csv db table
                        id_offset[self._tablename] = (curr_id-csv_id) \
                            if curr_id>csv_id else 0
                    # create new id until we get the same as old_id+offset
                    while curr_id<csv_id+id_offset[self._tablename]:
                        self._db(self._db[self][colnames[cid]] == curr_id).delete()
                        curr_id = self.insert(**dict(items))
                # Validation. Check for duplicate of 'unique' &,
                # if present, update instead of insert.
                elif not unique_idx:
                    new_id = self.insert(**dict(items))
                else:
                    unique_value = line[unique_idx]
                    query = self._db[self][unique] == unique_value
                    record = self._db(query).select().first()
                    if record:
                        record.update_record(**dict(items))
                        new_id = record[self._id.name]
                    else:
                        new_id = self.insert(**dict(items))
                if id_map and cid is not None:
                    id_map_self[long(line[cid])] = new_id

    def as_dict(self, flat=False, sanitize=True):
        table_as_dict = dict(tablename=str(self), fields=[],
        sequence_name=self._sequence_name,
        trigger_name=self._trigger_name,
        common_filter=self._common_filter, format=self._format,
        singular=self._singular, plural=self._plural)

        for field in self:
            if (field.readable or field.writable) or (not sanitize):
                table_as_dict["fields"].append(field.as_dict(
                    flat=flat, sanitize=sanitize))
        return table_as_dict

    def as_xml(self, sanitize=True):
        if not have_serializers:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return serializers.xml(d)

    def as_json(self, sanitize=True):
        if not have_serializers:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return serializers.json(d)

    def as_yaml(self, sanitize=True):
        if not have_serializers:
            raise ImportError("No YAML serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return serializers.yaml(d)

    def with_alias(self, alias):
        return self._db._adapter.alias(self,alias)

    def on(self, query):
        return Expression(self._db,self._db._adapter.ON,self,query)

def archive_record(qset,fs,archive_table,current_record):
    tablenames = qset.db._adapter.tables(qset.query)
    if len(tablenames)!=1: raise RuntimeError("cannot update join")
    table = qset.db[tablenames[0]]
    for row in qset.select():
        fields = archive_table._filter_fields(row)
        fields[current_record] = row.id
        archive_table.insert(**fields)
    return False



class Expression(object):

    def __init__(
        self,
        db,
        op,
        first=None,
        second=None,
        type=None,
        **optional_args
        ):

        self.db = db
        self.op = op
        self.first = first
        self.second = second
        self._table = getattr(first,'_table',None)
        ### self._tablename =  first._tablename ## CHECK
        if not type and first and hasattr(first,'type'):
            self.type = first.type
        else:
            self.type = type
        self.optional_args = optional_args

    def sum(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'SUM', self.type)

    def max(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'MAX', self.type)

    def min(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'MIN', self.type)

    def len(self):
        db = self.db
        return Expression(db, db._adapter.LENGTH, self, None, 'integer')

    def avg(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'AVG', self.type)

    def abs(self):
        db = self.db
        return Expression(db, db._adapter.AGGREGATE, self, 'ABS', self.type)

    def lower(self):
        db = self.db
        return Expression(db, db._adapter.LOWER, self, None, self.type)

    def upper(self):
        db = self.db
        return Expression(db, db._adapter.UPPER, self, None, self.type)

    def replace(self,a,b):
        db = self.db
        return Expression(db, db._adapter.REPLACE, self, (a,b), self.type)

    def year(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'year', 'integer')

    def month(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'month', 'integer')

    def day(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'day', 'integer')

    def hour(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'hour', 'integer')

    def minutes(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'minute', 'integer')

    def coalesce(self,*others):
        db = self.db
        return Expression(db, db._adapter.COALESCE, self, others, self.type)

    def coalesce_zero(self):
        db = self.db
        return Expression(db, db._adapter.COALESCE_ZERO, self, None, self.type)

    def seconds(self):
        db = self.db
        return Expression(db, db._adapter.EXTRACT, self, 'second', 'integer')

    def epoch(self):
        db = self.db
        return Expression(db, db._adapter.EPOCH, self, None, 'integer')

    def __getslice__(self, start, stop):
        db = self.db
        if start < 0:
            pos0 = '(%s - %d)' % (self.len(), abs(start) - 1)
        else:
            pos0 = start + 1

        if stop < 0:
            length = '(%s - %d - %s)' % (self.len(), abs(stop) - 1, pos0)
        elif stop == sys.maxint:
            length = self.len()
        else:
            length = '(%s - %s)' % (stop + 1, pos0)
        return Expression(db,db._adapter.SUBSTRING,
                          self, (pos0, length), self.type)

    def __getitem__(self, i):
        return self[i:i + 1]

    def __str__(self):
        return self.db._adapter.expand(self,self.type)

    def __or__(self, other):  # for use in sortby
        db = self.db
        return Expression(db,db._adapter.COMMA,self,other,self.type)

    def __invert__(self):
        db = self.db
        if hasattr(self,'_op') and self.op == db._adapter.INVERT:
            return self.first
        return Expression(db,db._adapter.INVERT,self,type=self.type)

    def __add__(self, other):
        db = self.db
        return Expression(db,db._adapter.ADD,self,other,self.type)

    def __sub__(self, other):
        db = self.db
        if self.type in ('integer','bigint'):
            result_type = 'integer'
        elif self.type in ['date','time','datetime','double','float']:
            result_type = 'double'
        elif self.type.startswith('decimal('):
            result_type = self.type
        else:
            raise SyntaxError("subtraction operation not supported for type")
        return Expression(db,db._adapter.SUB,self,other,result_type)

    def __mul__(self, other):
        db = self.db
        return Expression(db,db._adapter.MUL,self,other,self.type)

    def __div__(self, other):
        db = self.db
        return Expression(db,db._adapter.DIV,self,other,self.type)

    def __mod__(self, other):
        db = self.db
        return Expression(db,db._adapter.MOD,self,other,self.type)

    def __eq__(self, value):
        db = self.db
        return Query(db, db._adapter.EQ, self, value)

    def __ne__(self, value):
        db = self.db
        return Query(db, db._adapter.NE, self, value)

    def __lt__(self, value):
        db = self.db
        return Query(db, db._adapter.LT, self, value)

    def __le__(self, value):
        db = self.db
        return Query(db, db._adapter.LE, self, value)

    def __gt__(self, value):
        db = self.db
        return Query(db, db._adapter.GT, self, value)

    def __ge__(self, value):
        db = self.db
        return Query(db, db._adapter.GE, self, value)

    def like(self, value, case_sensitive=False):
        db = self.db
        op = case_sensitive and db._adapter.LIKE or db._adapter.ILIKE
        return Query(db, op, self, value)

    def regexp(self, value):
        db = self.db
        return Query(db, db._adapter.REGEXP, self, value)

    def belongs(self, *value, **kwattr):
        """
        Accepts the following inputs:
           field.belongs(1,2)
           field.belongs((1,2))
           field.belongs(query)

        Does NOT accept:
           field.belongs(1)
        """
        db = self.db
        if len(value) == 1:
            value = value[0]
        if isinstance(value,Query):
            value = db(value)._select(value.first._table._id)
        elif not isinstance(value, basestring):
            value = set(value)
            if kwattr.get('null') and None in value:
                value.remove(None)
                return (self == None) | Query(db, db._adapter.BELONGS, self, value)
        return Query(db, db._adapter.BELONGS, self, value)

    def startswith(self, value):
        db = self.db
        if not self.type in ('string', 'text', 'json', 'upload'):
            raise SyntaxError("startswith used with incompatible field type")
        return Query(db, db._adapter.STARTSWITH, self, value)

    def endswith(self, value):
        db = self.db
        if not self.type in ('string', 'text', 'json', 'upload'):
            raise SyntaxError("endswith used with incompatible field type")
        return Query(db, db._adapter.ENDSWITH, self, value)

    def contains(self, value, all=False, case_sensitive=False):
        """
        The case_sensitive parameters is only useful for PostgreSQL
        For other RDMBs it is ignored and contains is always case in-sensitive
        For MongoDB and GAE contains is always case sensitive
        """
        db = self.db
        if isinstance(value,(list, tuple)):
            subqueries = [self.contains(str(v).strip(),case_sensitive=case_sensitive)
                          for v in value if str(v).strip()]
            if not subqueries:
                return self.contains('')
            else:
                return reduce(all and AND or OR,subqueries)
        if not self.type in ('string', 'text', 'json', 'upload') and not self.type.startswith('list:'):
            raise SyntaxError("contains used with incompatible field type")
        return Query(db, db._adapter.CONTAINS, self, value, case_sensitive=case_sensitive)

    def with_alias(self, alias):
        db = self.db
        return Expression(db, db._adapter.AS, self, alias, self.type)

    # GIS expressions

    def st_asgeojson(self, precision=15, options=0, version=1):
        return Expression(self.db, self.db._adapter.ST_ASGEOJSON, self,
                          dict(precision=precision, options=options,
                               version=version), 'string')

    def st_astext(self):
        db = self.db
        return Expression(db, db._adapter.ST_ASTEXT, self, type='string')

    def st_x(self):
        db = self.db
        return Expression(db, db._adapter.ST_X, self, type='string')

    def st_y(self):
        db = self.db
        return Expression(db, db._adapter.ST_Y, self, type='string')

    def st_distance(self, other):
        db = self.db
        return Expression(db,db._adapter.ST_DISTANCE,self,other, 'double')

    def st_simplify(self, value):
        db = self.db
        return Expression(db, db._adapter.ST_SIMPLIFY, self, value, self.type)

    # GIS queries

    def st_contains(self, value):
        db = self.db
        return Query(db, db._adapter.ST_CONTAINS, self, value)

    def st_equals(self, value):
        db = self.db
        return Query(db, db._adapter.ST_EQUALS, self, value)

    def st_intersects(self, value):
        db = self.db
        return Query(db, db._adapter.ST_INTERSECTS, self, value)

    def st_overlaps(self, value):
        db = self.db
        return Query(db, db._adapter.ST_OVERLAPS, self, value)

    def st_touches(self, value):
        db = self.db
        return Query(db, db._adapter.ST_TOUCHES, self, value)

    def st_within(self, value):
        db = self.db
        return Query(db, db._adapter.ST_WITHIN, self, value)

    # for use in both Query and sortby


class SQLCustomType(object):
    """
    allows defining of custom SQL types

    Example::

        decimal = SQLCustomType(
            type ='double',
            native ='integer',
            encoder =(lambda x: int(float(x) * 100)),
            decoder = (lambda x: Decimal("0.00") + Decimal(str(float(x)/100)) )
            )

        db.define_table(
            'example',
            Field('value', type=decimal)
            )

    :param type: the web2py type (default = 'string')
    :param native: the backend type
    :param encoder: how to encode the value to store it in the backend
    :param decoder: how to decode the value retrieved from the backend
    :param validator: what validators to use ( default = None, will use the
        default validator for type)
    """

    def __init__(
        self,
        type='string',
        native=None,
        encoder=None,
        decoder=None,
        validator=None,
        _class=None,
        ):

        self.type = type
        self.native = native
        self.encoder = encoder or (lambda x: x)
        self.decoder = decoder or (lambda x: x)
        self.validator = validator
        self._class = _class or type

    def startswith(self, text=None):
        try:
            return self.type.startswith(self, text)
        except TypeError:
            return False

    def __getslice__(self, a=0, b=100):
        return None

    def __getitem__(self, i):
        return None

    def __str__(self):
        return self._class

class FieldVirtual(object):
    def __init__(self, name, f=None, ftype='string',label=None,table_name=None):
        # for backward compatibility
        (self.name, self.f) = (name, f) if f else ('unknown', name)
        self.type = ftype
        self.label = label or self.name.capitalize().replace('_',' ')
        self.represent = lambda v,r:v
        self.formatter = IDENTITY
        self.comment = None
        self.readable = True
        self.writable = False
        self.requires = None
        self.widget = None
        self.tablename = table_name
        self.filter_out = None
    def __str__(self):
        return '%s.%s' % (self.tablename, self.name)

class FieldMethod(object):
    def __init__(self, name, f=None, handler=None):
        # for backward compatibility
        (self.name, self.f) = (name, f) if f else ('unknown', name)
        self.handler = handler

def list_represent(x,r=None):
    return ', '.join(str(y) for y in x or [])

class Field(Expression):

    Virtual = FieldVirtual
    Method = FieldMethod
    Lazy = FieldMethod # for backward compatibility

    """
    an instance of this class represents a database field

    example::

        a = Field(name, 'string', length=32, default=None, required=False,
            requires=IS_NOT_EMPTY(), ondelete='CASCADE',
            notnull=False, unique=False,
            uploadfield=True, widget=None, label=None, comment=None,
            uploadfield=True, # True means store on disk,
                              # 'a_field_name' means store in this field in db
                              # False means file content will be discarded.
            writable=True, readable=True, update=None, authorize=None,
            autodelete=False, represent=None, uploadfolder=None,
            uploadseparate=False # upload to separate directories by uuid_keys
                                 # first 2 character and tablename.fieldname
                                 # False - old behavior
                                 # True - put uploaded file in
                                 #   <uploaddir>/<tablename>.<fieldname>/uuid_key[:2]
                                 #        directory)
            uploadfs=None     # a pyfilesystem where to store upload

    to be used as argument of DAL.define_table

    allowed field types:
    string, boolean, integer, double, text, blob,
    date, time, datetime, upload, password

    """

    def __init__(
        self,
        fieldname,
        type='string',
        length=None,
        default=DEFAULT,
        required=False,
        requires=DEFAULT,
        ondelete='CASCADE',
        notnull=False,
        unique=False,
        uploadfield=True,
        widget=None,
        label=None,
        comment=None,
        writable=True,
        readable=True,
        update=None,
        authorize=None,
        autodelete=False,
        represent=None,
        uploadfolder=None,
        uploadseparate=False,
        uploadfs=None,
        compute=None,
        custom_store=None,
        custom_retrieve=None,
        custom_retrieve_file_properties=None,
        custom_delete=None,
        filter_in = None,
        filter_out = None,
        custom_qualifier = None,
        map_none = None,
        rname = None
        ):
        self._db = self.db = None # both for backward compatibility
        self.op = None
        self.first = None
        self.second = None
        if isinstance(fieldname, unicode):
            try:
                fieldname = str(fieldname)
            except UnicodeEncodeError:
                raise SyntaxError('Field: invalid unicode field name')
        self.name = fieldname = cleanup(fieldname)
        if not isinstance(fieldname, str) or hasattr(Table, fieldname) or \
                fieldname[0] == '_' or REGEX_PYTHON_KEYWORDS.match(fieldname):
            raise SyntaxError('Field: invalid field name: %s' % fieldname)
        self.type = type if not isinstance(type, (Table,Field)) else 'reference %s' % type
        self.length = length if not length is None else DEFAULTLENGTH.get(self.type,512)
        self.default = default if default!=DEFAULT else (update or None)
        self.required = required  # is this field required
        self.ondelete = ondelete.upper()  # this is for reference fields only
        self.notnull = notnull
        self.unique = unique
        self.uploadfield = uploadfield
        self.uploadfolder = uploadfolder
        self.uploadseparate = uploadseparate
        self.uploadfs = uploadfs
        self.widget = widget
        self.comment = comment
        self.writable = writable
        self.readable = readable
        self.update = update
        self.authorize = authorize
        self.autodelete = autodelete
        self.represent = list_represent if \
            represent==None and type in ('list:integer','list:string') else represent
        self.compute = compute
        self.isattachment = True
        self.custom_store = custom_store
        self.custom_retrieve = custom_retrieve
        self.custom_retrieve_file_properties = custom_retrieve_file_properties
        self.custom_delete = custom_delete
        self.filter_in = filter_in
        self.filter_out = filter_out
        self.custom_qualifier = custom_qualifier
        self.label = label if label!=None else fieldname.replace('_',' ').title()
        self.requires = requires if requires!=None else []
        self.map_none = map_none
        self._rname = rname

    def set_attributes(self,*args,**attributes):
        self.__dict__.update(*args,**attributes)

    def clone(self,point_self_references_to=False,**args):
        field = copy.copy(self)
        if point_self_references_to and \
                field.type == 'reference %s'+field._tablename:
            field.type = 'reference %s' % point_self_references_to
        field.__dict__.update(args)
        return field

    def store(self, file, filename=None, path=None):
        if self.custom_store:
            return self.custom_store(file,filename,path)
        if isinstance(file, cgi.FieldStorage):
            filename = filename or file.filename
            file = file.file
        elif not filename:
            filename = file.name
        filename = os.path.basename(filename.replace('/', os.sep)\
                                        .replace('\\', os.sep))
        m = REGEX_STORE_PATTERN.search(filename)
        extension = m and m.group('e') or 'txt'
        uuid_key = web2py_uuid().replace('-', '')[-16:]
        encoded_filename = base64.b16encode(filename).lower()
        newfilename = '%s.%s.%s.%s' % \
            (self._tablename, self.name, uuid_key, encoded_filename)
        newfilename = newfilename[:(self.length - 1 - len(extension))] + '.' + extension
        self_uploadfield = self.uploadfield
        if isinstance(self_uploadfield,Field):
            blob_uploadfield_name = self_uploadfield.uploadfield
            keys={self_uploadfield.name: newfilename,
                  blob_uploadfield_name: file.read()}
            self_uploadfield.table.insert(**keys)
        elif self_uploadfield == True:
            if path:
                pass
            elif self.uploadfolder:
                path = self.uploadfolder
            elif self.db._adapter.folder:
                path = pjoin(self.db._adapter.folder, '..', 'uploads')
            else:
                raise RuntimeError(
                    "you must specify a Field(...,uploadfolder=...)")
            if self.uploadseparate:
                if self.uploadfs:
                    raise RuntimeError("not supported")
                path = pjoin(path,"%s.%s" %(self._tablename, self.name),
                                    uuid_key[:2])
            if not exists(path):
                os.makedirs(path)
            pathfilename = pjoin(path, newfilename)
            if self.uploadfs:
                dest_file = self.uploadfs.open(newfilename, 'wb')
            else:
                dest_file = open(pathfilename, 'wb')
            try:
                shutil.copyfileobj(file, dest_file)
            except IOError:
                raise IOError(
                    'Unable to store file "%s" because invalid permissions, readonly file system, or filename too long' % pathfilename)
            dest_file.close()
        return newfilename

    def retrieve(self, name, path=None, nameonly=False):
        """
        if nameonly==True return (filename, fullfilename) instead of
        (filename, stream)
        """
        self_uploadfield = self.uploadfield
        if self.custom_retrieve:
            return self.custom_retrieve(name, path)
        import http
        if self.authorize or isinstance(self_uploadfield, str):
            row = self.db(self == name).select().first()
            if not row:
                raise http.HTTP(404)
        if self.authorize and not self.authorize(row):
            raise http.HTTP(403)
        file_properties = self.retrieve_file_properties(name,path)
        filename = file_properties['filename']
        if isinstance(self_uploadfield, str):  # ## if file is in DB
            stream = StringIO.StringIO(row[self_uploadfield] or '')
        elif isinstance(self_uploadfield,Field):
            blob_uploadfield_name = self_uploadfield.uploadfield
            query = self_uploadfield == name
            data = self_uploadfield.table(query)[blob_uploadfield_name]
            stream = StringIO.StringIO(data)
        elif self.uploadfs:
            # ## if file is on pyfilesystem
            stream = self.uploadfs.open(name, 'rb')
        else:
            # ## if file is on regular filesystem
            # this is intentially a sting with filename and not a stream
            # this propagates and allows stream_file_or_304_or_206 to be called
            fullname = pjoin(file_properties['path'],name)
            if nameonly:
                return (filename, fullname)
            stream = open(fullname,'rb')
        return (filename, stream)

    def retrieve_file_properties(self, name, path=None):
        m = REGEX_UPLOAD_PATTERN.match(name)
        if not m or not self.isattachment:
            raise TypeError('Can\'t retrieve %s file properties' % name)
        self_uploadfield = self.uploadfield
        if self.custom_retrieve_file_properties:
            return self.custom_retrieve_file_properties(name, path)
        if m.group('name'):
            try:
                filename = base64.b16decode(m.group('name'), True)
                filename = REGEX_CLEANUP_FN.sub('_', filename)
            except (TypeError, AttributeError):
                filename = name
        else:
            filename = name
        # ## if file is in DB
        if isinstance(self_uploadfield, (str, Field)):
            return dict(path=None,filename=filename)
        # ## if file is on filesystem
        if not path:
            if self.uploadfolder:
                path = self.uploadfolder
            else:
                path = pjoin(self.db._adapter.folder, '..', 'uploads')
        if self.uploadseparate:
            t = m.group('table')
            f = m.group('field')
            u = m.group('uuidkey')
            path = pjoin(path,"%s.%s" % (t,f),u[:2])
        return dict(path=path,filename=filename)


    def formatter(self, value):
        requires = self.requires
        if value is None or not requires:
            return value or self.map_none
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        elif isinstance(requires, tuple):
            requires = list(requires)
        else:
            requires = copy.copy(requires)
        requires.reverse()
        for item in requires:
            if hasattr(item, 'formatter'):
                value = item.formatter(value)
        return value

    def validate(self, value):
        if not self.requires or self.requires == DEFAULT:
            return ((value if value!=self.map_none else None), None)
        requires = self.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        for validator in requires:
            (value, error) = validator(value)
            if error:
                return (value, error)
        return ((value if value!=self.map_none else None), None)

    def count(self, distinct=None):
        return Expression(self.db, self.db._adapter.COUNT, self, distinct, 'integer')

    def as_dict(self, flat=False, sanitize=True):
        attrs = ('name', 'authorize', 'represent', 'ondelete',
        'custom_store', 'autodelete', 'custom_retrieve',
        'filter_out', 'uploadseparate', 'widget', 'uploadfs',
        'update', 'custom_delete', 'uploadfield', 'uploadfolder',
        'custom_qualifier', 'unique', 'writable', 'compute',
        'map_none', 'default', 'type', 'required', 'readable',
        'requires', 'comment', 'label', 'length', 'notnull',
        'custom_retrieve_file_properties', 'filter_in')
        serializable = (int, long, basestring, float, tuple,
                        bool, type(None))

        def flatten(obj):
            if isinstance(obj, dict):
                return dict((flatten(k), flatten(v)) for k, v in
                             obj.items())
            elif isinstance(obj, (tuple, list, set)):
                return [flatten(v) for v in obj]
            elif isinstance(obj, serializable):
                return obj
            elif isinstance(obj, (datetime.datetime,
                                  datetime.date, datetime.time)):
                return str(obj)
            else:
                return None

        d = dict()
        if not (sanitize and not (self.readable or self.writable)):
            for attr in attrs:
               if flat:
                   d.update({attr: flatten(getattr(self, attr))})
               else:
                   d.update({attr: getattr(self, attr)})
            d["fieldname"] = d.pop("name")
        return d

    def as_xml(self, sanitize=True):
        if have_serializers:
            xml = serializers.xml
        else:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return xml(d)

    def as_json(self, sanitize=True):
        if have_serializers:
            json = serializers.json
        else:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return json(d)

    def as_yaml(self, sanitize=True):
        if have_serializers:
            d = self.as_dict(flat=True, sanitize=sanitize)
            return serializers.yaml(d)
        else:
            raise ImportError("No YAML serializers available")

    def __nonzero__(self):
        return True

    def __str__(self):
        try:
            return '%s.%s' % (self.tablename, self.name)
        except:
            return '<no table>.%s' % self.name


class Query(object):

    """
    a query object necessary to define a set.
    it can be stored or can be passed to DAL.__call__() to obtain a Set

    Example::

        query = db.users.name=='Max'
        set = db(query)
        records = set.select()

    """

    def __init__(
        self,
        db,
        op,
        first=None,
        second=None,
        ignore_common_filters = False,
        **optional_args
        ):
        self.db = self._db = db
        self.op = op
        self.first = first
        self.second = second
        self.ignore_common_filters = ignore_common_filters
        self.optional_args = optional_args

    def __repr__(self):
        return '<Query %s>' % BaseAdapter.expand(self.db._adapter,self)

    def __str__(self):
        return str(self.db._adapter.expand(self))

    def __and__(self, other):
        return Query(self.db,self.db._adapter.AND,self,other)

    __rand__ = __and__

    def __or__(self, other):
        return Query(self.db,self.db._adapter.OR,self,other)

    __ror__ = __or__

    def __invert__(self):
        if self.op==self.db._adapter.NOT:
            return self.first
        return Query(self.db,self.db._adapter.NOT,self)

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __ne__(self, other):
        return not (self == other)

    def case(self,t=1,f=0):
        return self.db._adapter.CASE(self,t,f)

    def as_dict(self, flat=False, sanitize=True):
        """Experimental stuff

        This allows to return a plain dictionary with the basic
        query representation. Can be used with json/xml services
        for client-side db I/O

        Example:
        >>> q = db.auth_user.id != 0
        >>> q.as_dict(flat=True)
        {"op": "NE", "first":{"tablename": "auth_user",
                              "fieldname": "id"},
                     "second":0}
        """

        SERIALIZABLE_TYPES = (tuple, dict, set, list, int, long, float,
                              basestring, type(None), bool)
        def loop(d):
            newd = dict()
            for k, v in d.items():
                if k in ("first", "second"):
                    if isinstance(v, self.__class__):
                        newd[k] = loop(v.__dict__)
                    elif isinstance(v, Field):
                        newd[k] = {"tablename": v._tablename,
                                   "fieldname": v.name}
                    elif isinstance(v, Expression):
                        newd[k] = loop(v.__dict__)
                    elif isinstance(v, SERIALIZABLE_TYPES):
                        newd[k] = v
                    elif isinstance(v, (datetime.date,
                                        datetime.time,
                                        datetime.datetime)):
                        newd[k] = unicode(v)
                elif k == "op":
                    if callable(v):
                        newd[k] = v.__name__
                    elif isinstance(v, basestring):
                        newd[k] = v
                    else: pass # not callable or string
                elif isinstance(v, SERIALIZABLE_TYPES):
                    if isinstance(v, dict):
                        newd[k] = loop(v)
                    else: newd[k] = v
            return newd

        if flat:
            return loop(self.__dict__)
        else: return self.__dict__


    def as_xml(self, sanitize=True):
        if have_serializers:
            xml = serializers.xml
        else:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return xml(d)

    def as_json(self, sanitize=True):
        if have_serializers:
            json = serializers.json
        else:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return json(d)

def xorify(orderby):
    if not orderby:
        return None
    orderby2 = orderby[0]
    for item in orderby[1:]:
        orderby2 = orderby2 | item
    return orderby2

def use_common_filters(query):
    return (query and hasattr(query,'ignore_common_filters') and \
                not query.ignore_common_filters)

class Set(object):

    """
    a Set represents a set of records in the database,
    the records are identified by the query=Query(...) object.
    normally the Set is generated by DAL.__call__(Query(...))

    given a set, for example
       set = db(db.users.name=='Max')
    you can:
       set.update(db.users.name='Massimo')
       set.delete() # all elements in the set
       set.select(orderby=db.users.id, groupby=db.users.name, limitby=(0,10))
    and take subsets:
       subset = set(db.users.id<5)
    """

    def __init__(self, db, query, ignore_common_filters = None):
        self.db = db
        self._db = db # for backward compatibility
        self.dquery = None

        # if query is a dict, parse it
        if isinstance(query, dict):
            query = self.parse(query)

        if not ignore_common_filters is None and \
                use_common_filters(query) == ignore_common_filters:
            query = copy.copy(query)
            query.ignore_common_filters = ignore_common_filters
        self.query = query

    def __repr__(self):
        return '<Set %s>' % BaseAdapter.expand(self.db._adapter,self.query)

    def __call__(self, query, ignore_common_filters=False):
        if query is None:
            return self
        elif isinstance(query,Table):
            query = self.db._adapter.id_query(query)
        elif isinstance(query,str):
            query = Expression(self.db,query)
        elif isinstance(query,Field):
            query = query!=None
        if self.query:
            return Set(self.db, self.query & query,
                       ignore_common_filters=ignore_common_filters)
        else:
            return Set(self.db, query,
                       ignore_common_filters=ignore_common_filters)

    def _count(self,distinct=None):
        return self.db._adapter._count(self.query,distinct)

    def _select(self, *fields, **attributes):
        adapter = self.db._adapter
        tablenames = adapter.tables(self.query,
                                    attributes.get('join',None),
                                    attributes.get('left',None),
                                    attributes.get('orderby',None),
                                    attributes.get('groupby',None))
        fields = adapter.expand_all(fields, tablenames)
        return adapter._select(self.query,fields,attributes)

    def _delete(self):
        db = self.db
        tablename = db._adapter.get_table(self.query)
        return db._adapter._delete(tablename,self.query)

    def _update(self, **update_fields):
        db = self.db
        tablename = db._adapter.get_table(self.query)
        fields = db[tablename]._listify(update_fields,update=True)
        return db._adapter._update(tablename,self.query,fields)

    def as_dict(self, flat=False, sanitize=True):
        if flat:
            uid = dbname = uri = None
            codec = self.db._db_codec
            if not sanitize:
                uri, dbname, uid = (self.db._dbname, str(self.db),
                                    self.db._db_uid)
            d = {"query": self.query.as_dict(flat=flat)}
            d["db"] = {"uid": uid, "codec": codec,
                       "name": dbname, "uri": uri}
            return d
        else: return self.__dict__

    def as_xml(self, sanitize=True):
        if have_serializers:
            xml = serializers.xml
        else:
            raise ImportError("No xml serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return xml(d)

    def as_json(self, sanitize=True):
        if have_serializers:
            json = serializers.json
        else:
            raise ImportError("No json serializers available")
        d = self.as_dict(flat=True, sanitize=sanitize)
        return json(d)

    def parse(self, dquery):
        "Experimental: Turn a dictionary into a Query object"
        self.dquery = dquery
        return self.build(self.dquery)

    def build(self, d):
        "Experimental: see .parse()"
        op, first, second = (d["op"], d["first"],
                             d.get("second", None))
        left = right = built = None

        if op in ("AND", "OR"):
            if not (type(first), type(second)) == (dict, dict):
                raise SyntaxError("Invalid AND/OR query")
            if op == "AND":
                built = self.build(first) & self.build(second)
            else: built = self.build(first) | self.build(second)

        elif op == "NOT":
            if first is None:
                raise SyntaxError("Invalid NOT query")
            built = ~self.build(first)
        else:
            # normal operation (GT, EQ, LT, ...)
            for k, v in {"left": first, "right": second}.items():
                if isinstance(v, dict) and v.get("op"):
                    v = self.build(v)
                if isinstance(v, dict) and ("tablename" in v):
                    v = self.db[v["tablename"]][v["fieldname"]]
                if k == "left": left = v
                else: right = v

            if hasattr(self.db._adapter, op):
                opm = getattr(self.db._adapter, op)

            if op == "EQ": built = left == right
            elif op == "NE": built = left != right
            elif op == "GT": built = left > right
            elif op == "GE": built = left >= right
            elif op == "LT": built = left < right
            elif op == "LE": built = left <= right
            elif op in ("JOIN", "LEFT_JOIN", "RANDOM", "ALLOW_NULL"):
                built = Expression(self.db, opm)
            elif op in ("LOWER", "UPPER", "EPOCH", "PRIMARY_KEY",
                        "COALESCE_ZERO", "RAW", "INVERT"):
                built = Expression(self.db, opm, left)
            elif op in ("COUNT", "EXTRACT", "AGGREGATE", "SUBSTRING",
                        "REGEXP", "LIKE", "ILIKE", "STARTSWITH",
                        "ENDSWITH", "ADD", "SUB", "MUL", "DIV",
                        "MOD", "AS", "ON", "COMMA", "NOT_NULL",
                        "COALESCE", "CONTAINS", "BELONGS"):
                built = Expression(self.db, opm, left, right)
            # expression as string
            elif not (left or right): built = Expression(self.db, op)
            else:
                raise SyntaxError("Operator not supported: %s" % op)

        return built

    def isempty(self):
        return not self.select(limitby=(0,1), orderby_on_limitby=False)

    def count(self,distinct=None, cache=None):
        db = self.db
        if cache:
            cache_model, time_expire = cache
            sql = self._count(distinct=distinct)
            key = db._uri + '/' + sql
            if len(key)>200: key = hashlib_md5(key).hexdigest()
            return cache_model(
                key,
                (lambda self=self,distinct=distinct: \
                  db._adapter.count(self.query,distinct)),
                time_expire)
        return db._adapter.count(self.query,distinct)

    def select(self, *fields, **attributes):
        adapter = self.db._adapter
        tablenames = adapter.tables(self.query,
                                    attributes.get('join',None),
                                    attributes.get('left',None),
                                    attributes.get('orderby',None),
                                    attributes.get('groupby',None))
        fields = adapter.expand_all(fields, tablenames)
        return adapter.select(self.query,fields,attributes)

    def nested_select(self,*fields,**attributes):
        return Expression(self.db,self._select(*fields,**attributes))

    def delete(self):
        db = self.db
        tablename = db._adapter.get_table(self.query)
        table = db[tablename]
        if any(f(self) for f in table._before_delete): return 0
        ret = db._adapter.delete(tablename,self.query)
        ret and [f(self) for f in table._after_delete]
        return ret

    def update(self, **update_fields):
        db = self.db
        tablename = db._adapter.get_table(self.query)
        table = db[tablename]
        table._attempt_upload(update_fields)
        if any(f(self,update_fields) for f in table._before_update):
            return 0
        fields = table._listify(update_fields,update=True)
        if not fields:
            raise SyntaxError("No fields to update")
        ret = db._adapter.update("%s" % table,self.query,fields)
        ret and [f(self,update_fields) for f in table._after_update]
        return ret

    def update_naive(self, **update_fields):
        """
        same as update but does not call table._before_update and _after_update
        """
        tablename = self.db._adapter.get_table(self.query)
        table = self.db[tablename]
        fields = table._listify(update_fields,update=True)
        if not fields: raise SyntaxError("No fields to update")

        ret = self.db._adapter.update("%s" % table,self.query,fields)
        return ret

    def validate_and_update(self, **update_fields):
        tablename = self.db._adapter.get_table(self.query)
        response = Row()
        response.errors = Row()
        new_fields = copy.copy(update_fields)
        for key,value in update_fields.iteritems():
            value,error = self.db[tablename][key].validate(value)
            if error:
                response.errors[key] = error
            else:
                new_fields[key] = value
        table = self.db[tablename]
        if response.errors:
            response.updated = None
        else:
            if not any(f(self,new_fields) for f in table._before_update):
                fields = table._listify(new_fields,update=True)
                if not fields: raise SyntaxError("No fields to update")
                ret = self.db._adapter.update(tablename,self.query,fields)
                ret and [f(self,new_fields) for f in table._after_update]
            else:
                ret = 0
            response.updated = ret
        return response

    def delete_uploaded_files(self, upload_fields=None):
        table = self.db[self.db._adapter.tables(self.query)[0]]
        # ## mind uploadfield==True means file is not in DB
        if upload_fields:
            fields = upload_fields.keys()
        else:
            fields = table.fields
        fields = [f for f in fields if table[f].type == 'upload'
                   and table[f].uploadfield == True
                   and table[f].autodelete]
        if not fields:
            return False
        for record in self.select(*[table[f] for f in fields]):
            for fieldname in fields:
                field = table[fieldname]
                oldname = record.get(fieldname, None)
                if not oldname:
                    continue
                if upload_fields and oldname == upload_fields[fieldname]:
                    continue
                if field.custom_delete:
                    field.custom_delete(oldname)
                else:
                    uploadfolder = field.uploadfolder
                    if not uploadfolder:
                        uploadfolder = pjoin(
                            self.db._adapter.folder, '..', 'uploads')
                    if field.uploadseparate:
                        items = oldname.split('.')
                        uploadfolder = pjoin(
                            uploadfolder,
                            "%s.%s" % (items[0], items[1]),
                            items[2][:2])
                    oldpath = pjoin(uploadfolder, oldname)
                    if exists(oldpath):
                        os.unlink(oldpath)
        return False

class RecordUpdater(object):
    def __init__(self, colset, table, id):
        self.colset, self.db, self.tablename, self.id = \
            colset, table._db, table._tablename, id

    def __call__(self, **fields):
        colset, db, tablename, id = self.colset, self.db, self.tablename, self.id
        table = db[tablename]
        newfields = fields or dict(colset)
        for fieldname in newfields.keys():
            if not fieldname in table.fields or table[fieldname].type=='id':
                del newfields[fieldname]
        table._db(table._id==id,ignore_common_filters=True).update(**newfields)
        colset.update(newfields)
        return colset

class RecordDeleter(object):
    def __init__(self, table, id):
        self.db, self.tablename, self.id = table._db, table._tablename, id
    def __call__(self):
        return self.db(self.db[self.tablename]._id==self.id).delete()

class LazyReferenceGetter(object):
    def __init__(self, table, id):
        self.db, self.tablename, self.id = table._db, table._tablename, id
    def __call__(self, other_tablename):
        if self.db._lazy_tables is False:
            raise AttributeError()
        table = self.db[self.tablename]
        other_table = self.db[other_tablename]
        for rfield in table._referenced_by:
            if rfield.table == other_table:
                return LazySet(rfield, self.id)

        raise AttributeError()

class LazySet(object):
    def __init__(self, field, id):
        self.db, self.tablename, self.fieldname, self.id = \
            field.db, field._tablename, field.name, id
    def _getset(self):
        query = self.db[self.tablename][self.fieldname]==self.id
        return Set(self.db,query)
    def __repr__(self):
        return repr(self._getset())
    def __call__(self, query, ignore_common_filters=False):
        return self._getset()(query, ignore_common_filters)
    def _count(self,distinct=None):
        return self._getset()._count(distinct)
    def _select(self, *fields, **attributes):
        return self._getset()._select(*fields,**attributes)
    def _delete(self):
        return self._getset()._delete()
    def _update(self, **update_fields):
        return self._getset()._update(**update_fields)
    def isempty(self):
        return self._getset().isempty()
    def count(self,distinct=None, cache=None):
        return self._getset().count(distinct,cache)
    def select(self, *fields, **attributes):
        return self._getset().select(*fields,**attributes)
    def nested_select(self,*fields,**attributes):
        return self._getset().nested_select(*fields,**attributes)
    def delete(self):
        return self._getset().delete()
    def update(self, **update_fields):
        return self._getset().update(**update_fields)
    def update_naive(self, **update_fields):
        return self._getset().update_naive(**update_fields)
    def validate_and_update(self, **update_fields):
        return self._getset().validate_and_update(**update_fields)
    def delete_uploaded_files(self, upload_fields=None):
        return self._getset().delete_uploaded_files(upload_fields)

class VirtualCommand(object):
    def __init__(self,method,row):
        self.method=method
        self.row=row
    def __call__(self,*args,**kwargs):
        return self.method(self.row,*args,**kwargs)

def lazy_virtualfield(f):
    f.__lazy__ = True
    return f

class Rows(object):

    """
    A wrapper for the return value of a select. It basically represents a table.
    It has an iterator and each row is represented as a dictionary.
    """

    # ## TODO: this class still needs some work to care for ID/OID

    def __init__(
        self,
        db=None,
        records=[],
        colnames=[],
        compact=True,
        rawrows=None
        ):
        self.db = db
        self.records = records
        self.colnames = colnames
        self.compact = compact
        self.response = rawrows

    def __repr__(self):
        return '<Rows (%s)>' % len(self.records)

    def setvirtualfields(self,**keyed_virtualfields):
        """
        db.define_table('x',Field('number','integer'))
        if db(db.x).isempty(): [db.x.insert(number=i) for i in range(10)]

        from gluon.dal import lazy_virtualfield

        class MyVirtualFields(object):
            # normal virtual field (backward compatible, discouraged)
            def normal_shift(self): return self.x.number+1
            # lazy virtual field (because of @staticmethod)
            @lazy_virtualfield
            def lazy_shift(instance,row,delta=4): return row.x.number+delta
        db.x.virtualfields.append(MyVirtualFields())

        for row in db(db.x).select():
            print row.number, row.normal_shift, row.lazy_shift(delta=7)
        """
        if not keyed_virtualfields:
            return self
        for row in self.records:
            for (tablename,virtualfields) in keyed_virtualfields.iteritems():
                attributes = dir(virtualfields)
                if not tablename in row:
                    box = row[tablename] = Row()
                else:
                    box = row[tablename]
                updated = False
                for attribute in attributes:
                    if attribute[0] != '_':
                        method = getattr(virtualfields,attribute)
                        if hasattr(method,'__lazy__'):
                            box[attribute]=VirtualCommand(method,row)
                        elif type(method)==types.MethodType:
                            if not updated:
                                virtualfields.__dict__.update(row)
                                updated = True
                            box[attribute]=method()
        return self

    def __and__(self,other):
        if self.colnames!=other.colnames:
            raise Exception('Cannot & incompatible Rows objects')
        records = self.records+other.records
        return Rows(self.db,records,self.colnames)

    def __or__(self,other):
        if self.colnames!=other.colnames:
            raise Exception('Cannot | incompatible Rows objects')
        records = [record for record in other.records
                   if not record in self.records]
        records = self.records + records
        return Rows(self.db,records,self.colnames)

    def __nonzero__(self):
        if len(self.records):
            return 1
        return 0

    def __len__(self):
        return len(self.records)

    def __getslice__(self, a, b):
        return Rows(self.db,self.records[a:b],self.colnames,compact=self.compact)

    def __getitem__(self, i):
        row = self.records[i]
        keys = row.keys()
        if self.compact and len(keys) == 1 and keys[0] != '_extra':
            return row[row.keys()[0]]
        return row

    def __iter__(self):
        """
        iterator over records
        """

        for i in xrange(len(self)):
            yield self[i]

    def __str__(self):
        """
        serializes the table into a csv file
        """

        s = StringIO.StringIO()
        self.export_to_csv_file(s)
        return s.getvalue()

    def first(self):
        if not self.records:
            return None
        return self[0]

    def last(self):
        if not self.records:
            return None
        return self[-1]

    def find(self,f,limitby=None):
        """
        returns a new Rows object, a subset of the original object,
        filtered by the function f
        """
        if not self:
            return Rows(self.db, [], self.colnames)
        records = []
        if limitby:
            a,b = limitby
        else:
            a,b = 0,len(self)
        k = 0
        for row in self:
            if f(row):
                if a<=k: records.append(row)
                k += 1
                if k==b: break
        return Rows(self.db, records, self.colnames)

    def exclude(self, f):
        """
        removes elements from the calling Rows object, filtered by the function f,
        and returns a new Rows object containing the removed elements
        """
        if not self.records:
            return Rows(self.db, [], self.colnames)
        removed = []
        i=0
        while i<len(self):
            row = self[i]
            if f(row):
                removed.append(self.records[i])
                del self.records[i]
            else:
                i += 1
        return Rows(self.db, removed, self.colnames)

    def sort(self, f, reverse=False):
        """
        returns a list of sorted elements (not sorted in place)
        """
        rows = Rows(self.db,[],self.colnames,compact=False)
        rows.records = sorted(self,key=f,reverse=reverse)
        return rows

    def group_by_value(self, *fields, **args):
        """
        regroups the rows, by one of the fields
        """
        one_result = False
        if 'one_result' in args:
            one_result = args['one_result']

        def build_fields_struct(row, fields, num, groups):
            ''' helper function:
            '''
            if num > len(fields)-1:
                if one_result:
                    return row
                else:
                    return [row]

            key = fields[num]
            value = row[key]

            if value not in groups:
                groups[value] = build_fields_struct(row, fields, num+1, {})
            else:
                struct = build_fields_struct(row, fields, num+1, groups[ value ])

                # still have more grouping to do
                if type(struct) == type(dict()):
                    groups[value].update()
                # no more grouping, first only is off
                elif type(struct) == type(list()):
                    groups[value] += struct
                # no more grouping, first only on
                else:
                    groups[value] = struct

            return groups

        if len(fields) == 0:
            return self

        # if select returned no results
        if not self.records:
            return {}

        grouped_row_group = dict()

        # build the struct
        for row in self:
            build_fields_struct(row, fields, 0, grouped_row_group)

        return grouped_row_group

    def render(self, i=None, fields=None):
        """
        Takes an index and returns a copy of the indexed row with values
        transformed via the "represent" attributes of the associated fields.

        If no index is specified, a generator is returned for iteration
        over all the rows.

        fields -- a list of fields to transform (if None, all fields with
                  "represent" attributes will be transformed).
        """


        if i is None:
            return (self.render(i, fields=fields) for i in range(len(self)))
        import sqlhtml
        row = copy.deepcopy(self.records[i])
        keys = row.keys()
        tables = [f.tablename for f in fields] if fields \
            else [k for k in keys if k != '_extra']
        for table in tables:
            repr_fields = [f.name for f in fields if f.tablename == table] \
                if fields else [k for k in row[table].keys()
                                if (hasattr(self.db[table], k) and
                                    isinstance(self.db[table][k], Field)
                                    and self.db[table][k].represent)]
            for field in repr_fields:
                row[table][field] = sqlhtml.represent(
                    self.db[table][field], row[table][field], row[table])
        if self.compact and len(keys) == 1 and keys[0] != '_extra':
            return row[keys[0]]
        return row

    def as_list(self,
                compact=True,
                storage_to_dict=True,
                datetime_to_str=False,
                custom_types=None):
        """
        returns the data as a list or dictionary.
        :param storage_to_dict: when True returns a dict, otherwise a list(default True)
        :param datetime_to_str: convert datetime fields as strings (default False)
        """
        (oc, self.compact) = (self.compact, compact)
        if storage_to_dict:
            items = [item.as_dict(datetime_to_str, custom_types) for item in self]
        else:
            items = [item for item in self]
        self.compact = compact
        return items


    def as_dict(self,
                key='id',
                compact=True,
                storage_to_dict=True,
                datetime_to_str=False,
                custom_types=None):
        """
        returns the data as a dictionary of dictionaries (storage_to_dict=True) or records (False)

        :param key: the name of the field to be used as dict key, normally the id
        :param compact: ? (default True)
        :param storage_to_dict: when True returns a dict, otherwise a list(default True)
        :param datetime_to_str: convert datetime fields as strings (default False)
        """

        # test for multiple rows
        multi = False
        f = self.first()
        if f and isinstance(key, basestring):
            multi = any([isinstance(v, f.__class__) for v in f.values()])
            if (not "." in key) and multi:
                # No key provided, default to int indices
                def new_key():
                    i = 0
                    while True:
                        yield i
                        i += 1
                key_generator = new_key()
                key = lambda r: key_generator.next()

        rows = self.as_list(compact, storage_to_dict, datetime_to_str, custom_types)
        if isinstance(key,str) and key.count('.')==1:
            (table, field) = key.split('.')
            return dict([(r[table][field],r) for r in rows])
        elif isinstance(key,str):
            return dict([(r[key],r) for r in rows])
        else:
            return dict([(key(r),r) for r in rows])


    def as_trees(self, parent_name='parent_id', children_name='children'):
        roots = []
        drows = {}
        for row in self:
            drows[row.id] = row
            row[children_name] = []
        for row in self:
            parent = row[parent_name]
            if parent is None:
                roots.append(row)
            else:
                drows[parent][children_name].append(row)
        return roots

    def export_to_csv_file(self, ofile, null='<NULL>', *args, **kwargs):
        """
        export data to csv, the first line contains the column names

        :param ofile: where the csv must be exported to
        :param null: how null values must be represented (default '<NULL>')
        :param delimiter: delimiter to separate values (default ',')
        :param quotechar: character to use to quote string values (default '"')
        :param quoting: quote system, use csv.QUOTE_*** (default csv.QUOTE_MINIMAL)
        :param represent: use the fields .represent value (default False)
        :param colnames: list of column names to use (default self.colnames)
                         This will only work when exporting rows objects!!!!
                         DO NOT use this with db.export_to_csv()
        """
        delimiter = kwargs.get('delimiter', ',')
        quotechar = kwargs.get('quotechar', '"')
        quoting = kwargs.get('quoting', csv.QUOTE_MINIMAL)
        represent = kwargs.get('represent', False)
        writer = csv.writer(ofile, delimiter=delimiter,
                            quotechar=quotechar, quoting=quoting)
        colnames = kwargs.get('colnames', self.colnames)
        write_colnames = kwargs.get('write_colnames',True)
        # a proper csv starting with the column names
        if write_colnames:
            writer.writerow(colnames)

        def none_exception(value):
            """
            returns a cleaned up value that can be used for csv export:
            - unicode text is encoded as such
            - None values are replaced with the given representation (default <NULL>)
            """
            if value is None:
                return null
            elif isinstance(value, unicode):
                return value.encode('utf8')
            elif isinstance(value,Reference):
                return long(value)
            elif hasattr(value, 'isoformat'):
                return value.isoformat()[:19].replace('T', ' ')
            elif isinstance(value, (list,tuple)): # for type='list:..'
                return bar_encode(value)
            return value

        for record in self:
            row = []
            for col in colnames:
                if not REGEX_TABLE_DOT_FIELD.match(col):
                    row.append(record._extra[col])
                else:
                    (t, f) = col.split('.')
                    field = self.db[t][f]
                    if isinstance(record.get(t, None), (Row,dict)):
                        value = record[t][f]
                    else:
                        value = record[f]
                    if field.type=='blob' and not value is None:
                        value = base64.b64encode(value)
                    elif represent and field.represent:
                        value = field.represent(value)
                    row.append(none_exception(value))
            writer.writerow(row)

    def xml(self,strict=False,row_name='row',rows_name='rows'):
        """
        serializes the table using sqlhtml.SQLTABLE (if present)
        """

        if strict:
            ncols = len(self.colnames)
            return '<%s>\n%s\n</%s>' % (rows_name,
                '\n'.join(row.as_xml(row_name=row_name,
                                     colnames=self.colnames) for
                          row in self), rows_name)

        import sqlhtml
        return sqlhtml.SQLTABLE(self).xml()

    def as_xml(self,row_name='row',rows_name='rows'):
        return self.xml(strict=True, row_name=row_name, rows_name=rows_name)

    def as_json(self, mode='object', default=None):
        """
        serializes the rows to a JSON list or object with objects
        mode='object' is not implemented (should return a nested
        object structure)
        """

        items = [record.as_json(mode=mode, default=default,
                                serialize=False,
                                colnames=self.colnames) for
                 record in self]

        if have_serializers:
            return serializers.json(items,
                                    default=default or
                                    serializers.custom_json)
        elif simplejson:
            return simplejson.dumps(items)
        else:
            raise RuntimeError("missing simplejson")

    # for consistent naming yet backwards compatible
    as_csv = __str__
    json = as_json


################################################################################
# dummy function used to define some doctests
################################################################################

def test_all():
    """

    >>> if len(sys.argv)<2: db = DAL("sqlite://test.db")
    >>> if len(sys.argv)>1: db = DAL(sys.argv[1])
    >>> tmp = db.define_table('users',\
              Field('stringf', 'string', length=32, required=True),\
              Field('booleanf', 'boolean', default=False),\
              Field('passwordf', 'password', notnull=True),\
              Field('uploadf', 'upload'),\
              Field('blobf', 'blob'),\
              Field('integerf', 'integer', unique=True),\
              Field('doublef', 'double', unique=True,notnull=True),\
              Field('jsonf', 'json'),\
              Field('datef', 'date', default=datetime.date.today()),\
              Field('timef', 'time'),\
              Field('datetimef', 'datetime'),\
              migrate='test_user.table')

   Insert a field

    >>> db.users.insert(stringf='a', booleanf=True, passwordf='p', blobf='0A',\
                       uploadf=None, integerf=5, doublef=3.14,\
                       jsonf={"j": True},\
                       datef=datetime.date(2001, 1, 1),\
                       timef=datetime.time(12, 30, 15),\
                       datetimef=datetime.datetime(2002, 2, 2, 12, 30, 15))
    1

    Drop the table

    >>> db.users.drop()

    Examples of insert, select, update, delete

    >>> tmp = db.define_table('person',\
              Field('name'),\
              Field('birth','date'),\
              migrate='test_person.table')
    >>> person_id = db.person.insert(name='Marco',birth='2005-06-22')
    >>> person_id = db.person.insert(name='Massimo',birth='1971-12-21')

    commented len(db().select(db.person.ALL))
    commented 2

    >>> me = db(db.person.id==person_id).select()[0] # test select
    >>> me.name
    'Massimo'
    >>> db.person[2].name
    'Massimo'
    >>> db.person(2).name
    'Massimo'
    >>> db.person(name='Massimo').name
    'Massimo'
    >>> db.person(db.person.name=='Massimo').name
    'Massimo'
    >>> row = db.person[2]
    >>> row.name == row['name'] == row['person.name'] == row('person.name')
    True
    >>> db(db.person.name=='Massimo').update(name='massimo') # test update
    1
    >>> db(db.person.name=='Marco').select().first().delete_record() # test delete
    1

    Update a single record

    >>> me.update_record(name="Max")
    <Row {'name': 'Max', 'birth': datetime.date(1971, 12, 21), 'id': 2}>
    >>> me.name
    'Max'

    Examples of complex search conditions

    >>> len(db((db.person.name=='Max')&(db.person.birth<'2003-01-01')).select())
    1
    >>> len(db((db.person.name=='Max')&(db.person.birth<datetime.date(2003,01,01))).select())
    1
    >>> len(db((db.person.name=='Max')|(db.person.birth<'2003-01-01')).select())
    1
    >>> me = db(db.person.id==person_id).select(db.person.name)[0]
    >>> me.name
    'Max'

    Examples of search conditions using extract from date/datetime/time

    >>> len(db(db.person.birth.month()==12).select())
    1
    >>> len(db(db.person.birth.year()>1900).select())
    1

    Example of usage of NULL

    >>> len(db(db.person.birth==None).select()) ### test NULL
    0
    >>> len(db(db.person.birth!=None).select()) ### test NULL
    1

    Examples of search conditions using lower, upper, and like

    >>> len(db(db.person.name.upper()=='MAX').select())
    1
    >>> len(db(db.person.name.like('%ax')).select())
    1
    >>> len(db(db.person.name.upper().like('%AX')).select())
    1
    >>> len(db(~db.person.name.upper().like('%AX')).select())
    0

    orderby, groupby and limitby

    >>> people = db().select(db.person.name, orderby=db.person.name)
    >>> order = db.person.name|~db.person.birth
    >>> people = db().select(db.person.name, orderby=order)

    >>> people = db().select(db.person.name, orderby=db.person.name, groupby=db.person.name)

    >>> people = db().select(db.person.name, orderby=order, limitby=(0,100))

    Example of one 2 many relation

    >>> tmp = db.define_table('dog',\
               Field('name'),\
               Field('birth','date'),\
               Field('owner',db.person),\
               migrate='test_dog.table')
    >>> db.dog.insert(name='Snoopy', birth=None, owner=person_id)
    1

    A simple JOIN

    >>> len(db(db.dog.owner==db.person.id).select())
    1

    >>> len(db().select(db.person.ALL, db.dog.name,left=db.dog.on(db.dog.owner==db.person.id)))
    1

    Drop tables

    >>> db.dog.drop()
    >>> db.person.drop()

    Example of many 2 many relation and Set

    >>> tmp = db.define_table('author', Field('name'),\
                            migrate='test_author.table')
    >>> tmp = db.define_table('paper', Field('title'),\
                            migrate='test_paper.table')
    >>> tmp = db.define_table('authorship',\
            Field('author_id', db.author),\
            Field('paper_id', db.paper),\
            migrate='test_authorship.table')
    >>> aid = db.author.insert(name='Massimo')
    >>> pid = db.paper.insert(title='QCD')
    >>> tmp = db.authorship.insert(author_id=aid, paper_id=pid)

    Define a Set

    >>> authored_papers = db((db.author.id==db.authorship.author_id)&(db.paper.id==db.authorship.paper_id))
    >>> rows = authored_papers.select(db.author.name, db.paper.title)
    >>> for row in rows: print row.author.name, row.paper.title
    Massimo QCD

    Example of search condition using  belongs

    >>> set = (1, 2, 3)
    >>> rows = db(db.paper.id.belongs(set)).select(db.paper.ALL)
    >>> print rows[0].title
    QCD

    Example of search condition using nested select

    >>> nested_select = db()._select(db.authorship.paper_id)
    >>> rows = db(db.paper.id.belongs(nested_select)).select(db.paper.ALL)
    >>> print rows[0].title
    QCD

    Example of expressions

    >>> mynumber = db.define_table('mynumber', Field('x', 'integer'))
    >>> db(mynumber).delete()
    0
    >>> for i in range(10): tmp = mynumber.insert(x=i)
    >>> db(mynumber).select(mynumber.x.sum())[0](mynumber.x.sum())
    45

    >>> db(mynumber.x+2==5).select(mynumber.x + 2)[0](mynumber.x + 2)
    5

    Output in csv

    >>> print str(authored_papers.select(db.author.name, db.paper.title)).strip()
    author.name,paper.title\r
    Massimo,QCD

    Delete all leftover tables

    >>> DAL.distributed_transaction_commit(db)

    >>> db.mynumber.drop()
    >>> db.authorship.drop()
    >>> db.author.drop()
    >>> db.paper.drop()
    """
################################################################################
# deprecated since the new DAL; here only for backward compatibility
################################################################################

SQLField = Field
SQLTable = Table
SQLXorable = Expression
SQLQuery = Query
SQLSet = Set
SQLRows = Rows
SQLStorage = Row
SQLDB = DAL
GQLDB = DAL
DAL.Field = Field  # was necessary in gluon/globals.py session.connect
DAL.Table = Table  # was necessary in gluon/globals.py session.connect

################################################################################
# Geodal utils
################################################################################

def geoPoint(x,y):
    return "POINT (%f %f)" % (x,y)

def geoLine(*line):
    return "LINESTRING (%s)" % ','.join("%f %f" % item for item in line)

def geoPolygon(*line):
    return "POLYGON ((%s))" % ','.join("%f %f" % item for item in line)

################################################################################
# run tests
################################################################################

if __name__ == '__main__':
    import doctest
    doctest.testmod()
