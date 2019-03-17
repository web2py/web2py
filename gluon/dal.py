# -*- coding: utf-8 -*-

"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Takes care of adapting pyDAL to web2py's needs
-----------------------------------------------
"""

from pydal import DAL
from pydal import Field
from pydal.objects import Row, Rows, Table, Query, Set, Expression
from pydal import SQLCustomType, geoPoint, geoLine, geoPolygon
from pydal.migrator import Migrator, InDBMigrator
from gluon.serializers import custom_json, xml
from gluon.utils import web2py_uuid
from gluon import sqlhtml
from pydal.drivers import DRIVERS


DAL.serializers = {'json': custom_json, 'xml': xml}
DAL.uuid = lambda x: web2py_uuid()
DAL.representers = {
    'rows_render': sqlhtml.represent,
    'rows_xml': sqlhtml.SQLTABLE
}
DAL.Field = Field
DAL.Table = Table

# add web2py contrib drivers to pyDAL
if not DRIVERS.get('pymysql'):
    try:
        from .contrib import pymysql
        DRIVERS['pymysql'] = pymysql
    except:
        pass
if not DRIVERS.get('pyodbc'):
    try:
        from .contrib import pypyodbc as pyodbc
        DRIVERS['pyodbc'] = pyodbc
    except:
        pass
if not DRIVERS.get('pg8000'):
    try:
        from .contrib import pg8000
        DRIVERS['pg8000'] = pg8000
    except:
        pass
