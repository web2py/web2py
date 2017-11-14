#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Takes care of adapting pyDAL to web2py's needs
-----------------------------------------------
"""

from pydal import DAL as DAL
from pydal import Field
from pydal.objects import Row, Rows, Table, Query, Set, Expression
from pydal import SQLCustomType, geoPoint, geoLine, geoPolygon
from pydal.migrator import Migrator, InDBMigrator
from gluon.serializers import custom_json, xml
from gluon.utils import web2py_uuid
from gluon import sqlhtml
from pydal.drivers import DRIVERS


def _default_validators(db, field):
    """
    Field type validation, using web2py's validators mechanism.

    makes sure the content of a field is in line with the declared
    fieldtype
    """
    from gluon import validators
    field_type, field_length = field.type, field.length
    requires = []

    if isinstance(field.options, list) and field.requires:
        requires = validators.IS_IN_SET(field.options, multiple=field_type.startswith('list:'))
    elif field.regex and not field.requires:
        requires.append(validators.IS_REGEX(regex))
    elif field_type in (('string', 'text', 'password')):
        requires.append(validators.IS_LENGTH(field_length))
    elif field_type == 'json':
        requires.append(validators.IS_EMPTY_OR(validators.IS_JSON()))
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
    elif db and field_type.startswith('reference'):
        if field_type.find('.') < 0 and field_type[10:] in db.tables:
            referenced = db[field_type[10:]]
            if hasattr(referenced, '_format') and referenced._format:
                requires = validators.IS_IN_DB(db, referenced._id,referenced._format)
            else:
                requires = validators.IS_IN_DB(db, referenced._id)
        elif field_type.find('.') > 0 and field_type[10:].split('.')[0] in db.tables:
            table_field = field_type[10:].split('.')
            table_name=table_field[0]
            field_name=table_field[1]
            referenced = db[table_name]
            if hasattr(referenced, '_format') and referenced._format:
                requires = validators.IS_IN_DB(db, referenced[field_name],referenced._format)
            else:
                requires = validators.IS_IN_DB(db, referenced[field_name])
        if field.unique:
            requires._and = validators.IS_NOT_IN_DB(db, field)
        if not field.notnull:
            requires = validators.IS_EMPTY_OR(requires)
        return requires
    elif db and field_type.startswith('list:reference'):
        if field_type.find('.') < 0 and field_type[15:] in db.tables:
            referenced = db[field_type[15:]]
            if hasattr(referenced, '_format') and referenced._format:
                requires = validators.IS_IN_DB(db, referenced._id,
                                               referenced._format, multiple=True)
            else:
                requires = validators.IS_IN_DB(db, referenced._id,
                                               multiple=True)
        elif field_type.find('.') > 0 and field_type[15:].split('.')[0] in db.tables:
            table_field = field_type[15:].split('.')
            table_name=table_field[0]
            field_name=table_field[1]
            referenced = db[table_name]
            if hasattr(referenced, '_format') and referenced._format:
                requires = validators.IS_IN_DB(db, referenced[field_name],
                                               referenced._format, multiple=True)
            else:
                requires = validators.IS_IN_DB(db, referenced[field_name],
                                               multiple=True)
        if field.unique:
            requires._and = validators.IS_NOT_IN_DB(db, field)
        if not field.notnull:
            requires = validators.IS_EMPTY_OR(requires)
        return requires    
    # does not get here for reference and list:reference
    if isinstance(requires, list):
        if field.unique:
            requires.insert(0, validators.IS_NOT_IN_DB(db, field))
        excluded_fields = ['string', 'upload', 'text', 'password', 'boolean']
        if (field.notnull or field.unique) and field_type not in excluded_fields:
            requires.insert(0, validators.IS_NOT_EMPTY())
        elif not field.notnull and not field.unique and requires:
            null = null='' if field.type in ('string', 'text', 'password') else None
            requires[0] = validators.IS_EMPTY_OR(requires[0], null=null)
    return requires

DAL.serializers = {'json': custom_json, 'xml': xml}
DAL.validators_method = _default_validators
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
