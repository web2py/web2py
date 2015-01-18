# -*- coding: utf-8 -*-

import decimal
import re

from ._globals import LOGGER


# verify presence of web2py modules
try:
    from collections import OrderedDict
except:
    from gluon.contrib.ordereddict import OrderedDict

try:
    from gluon.utils import web2py_uuid
except (ImportError, SystemError):
    import uuid
    def web2py_uuid(): return str(uuid.uuid4())

try:
    import portalocker
    have_portalocker = True
except ImportError:
    portalocker = None
    have_portalocker = False

try:
    from gluon import serializers
    have_serializers = True
    simplejson = None
except ImportError:
    serializers = None
    have_serializers = False
    try:
        import json as simplejson
    except ImportError:
        try:
            import gluon.contrib.simplejson as simplejson
        except ImportError:
            simplejson = None


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
    classobj = None
    gae = None
    ndb = None
    namespace_manager = rdbms = None
    Key = None
    PolyModel = NDBPolyModel = None

if not 'google' in DRIVERS:

    try:
        from pysqlite2 import dbapi2 as sqlite2
        DRIVERS.append('sqlite2')
    except ImportError:
        LOGGER.debug('no SQLite drivers pysqlite2.dbapi2')

    try:
        from sqlite3 import dbapi2 as sqlite3
        DRIVERS.append('sqlite3')
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
        DRIVERS.append('pymysql')
    except ImportError:
        LOGGER.debug('no MySQL driver pymysql')

    try:
        import MySQLdb
        DRIVERS.append('MySQLdb')
    except ImportError:
        LOGGER.debug('no MySQL driver MySQLDB')

    try:
        import mysql.connector as mysqlconnector
        DRIVERS.append("mysqlconnector")
    except ImportError:
        LOGGER.debug("no driver mysql.connector")

    try:
        import psycopg2
        from psycopg2.extensions import adapt as psycopg2_adapt
        DRIVERS.append('psycopg2')
    except ImportError:
        psycopg2_adapt = None
        LOGGER.debug('no PostgreSQL driver psycopg2')

    try:
        # first try contrib driver, then from site-packages (if installed)
        try:
            import gluon.contrib.pg8000.dbapi as pg8000
        except ImportError:
            import pg8000.dbapi as pg8000
        DRIVERS.append('pg8000')
    except ImportError:
        LOGGER.debug('no PostgreSQL driver pg8000')

    try:
        import cx_Oracle
        DRIVERS.append('cx_Oracle')
    except ImportError:
        cx_Oracle = None
        LOGGER.debug('no Oracle driver cx_Oracle')

    try:
        try:
            import pyodbc
        except ImportError:
            try:
                import gluon.contrib.pypyodbc as pyodbc
            except Exception, e:
                raise ImportError(str(e))
        DRIVERS.append('pyodbc')
        #DRIVERS.append('DB2(pyodbc)')
        #DRIVERS.append('Teradata(pyodbc)')
        #DRIVERS.append('Ingres(pyodbc)')
    except ImportError:
        pyodbc = None
        LOGGER.debug('no MSSQL/DB2/Teradata/Ingres driver pyodbc')

    try:
        import ibm_db_dbi
        DRIVERS.append('ibm_db_dbi')
    except ImportError:
        LOGGER.debug('no DB2 driver ibm_db_dbi')

    try:
        import Sybase
        DRIVERS.append('Sybase')
    except ImportError:
        LOGGER.debug('no Sybase driver')

    try:
        import kinterbasdb
        DRIVERS.append('kinterbasdb')
        #DRIVERS.append('Firebird(kinterbasdb)')
    except ImportError:
        LOGGER.debug('no Firebird/Interbase driver kinterbasdb')

    try:
        import fdb
        DRIVERS.append('fdb')
    except ImportError:
        LOGGER.debug('no Firebird driver fdb')

    try:
        import firebirdsql
        DRIVERS.append('firebirdsql')
    except ImportError:
        LOGGER.debug('no Firebird driver firebirdsql')

    try:
        import informixdb
        DRIVERS.append('informixdb')
        LOGGER.warning('Informix support is experimental')
    except ImportError:
        LOGGER.debug('no Informix driver informixdb')

    try:
        import sapdb
        DRIVERS.append('sapdb')
        LOGGER.warning('SAPDB support is experimental')
    except ImportError:
        LOGGER.debug('no SAP driver sapdb')

    try:
        import cubriddb
        DRIVERS.append('cubriddb')
        LOGGER.warning('Cubrid support is experimental')
    except ImportError:
        LOGGER.debug('no Cubrid driver cubriddb')

    try:
        from com.ziclix.python.sql import zxJDBC
        import java.sql
        # Try sqlite jdbc driver from http://www.zentus.com/sqlitejdbc/
        from org.sqlite import JDBC # required by java.sql; ensure we have it
        zxJDBC_sqlite = java.sql.DriverManager
        DRIVERS.append('zxJDBC')
        #DRIVERS.append('SQLite(zxJDBC)')
        LOGGER.warning('zxJDBC support is experimental')
        is_jdbc = True
    except ImportError:
        LOGGER.debug('no SQLite/PostgreSQL driver zxJDBC')
        is_jdbc = False

    try:
        import couchdb
        DRIVERS.append('couchdb')
    except ImportError:
        couchdb = None
        LOGGER.debug('no Couchdb driver couchdb')

    try:
        import pymongo
        DRIVERS.append('pymongo')
    except:
        LOGGER.debug('no MongoDB driver pymongo')

    try:
        import imaplib
        DRIVERS.append('imaplib')
    except:
        LOGGER.debug('no IMAP driver imaplib')

    GAEDecimalProperty = None
    NDBDecimalProperty = None
else:
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

    psycopg2_adapt = None
    cx_Oracle = None
    pyodbc = None
    couchdb = None


def get_driver(name):
    return globals().get(name)
