#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Takes care of adapting pyDAL to web2py's needs
--------------------------------------------
"""

from pydal import DAL as pyDAL
from pydal import Field
from pydal.objects import Row, Rows, Table, Query, Expression
from pydal import SQLCustomType, geoPoint, geoLine, geoPolygon


def _default_validators(db, field):
    """
    Field type validation, using web2py's validators mechanism.

    makes sure the content of a field is in line with the declared
    fieldtype
    """
    from gluon import validators
    field_type, field_length = field.type, field.length
    requires = []

    def ff(r, id):
        row = r(id)
        if not row:
            return str(id)
        elif hasattr(r, '_format') and isinstance(r._format, str):
            return r._format % row
        elif hasattr(r, '_format') and callable(r._format):
            return r._format(row)
        else:
            return str(id)

    if field_type in (('string', 'text', 'password')):
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
    elif db and field_type.startswith('reference') and \
            field_type.find('.') < 0 and \
            field_type[10:] in db.tables:
        referenced = db[field_type[10:]]

        def repr_ref(id, row=None, r=referenced, f=ff):
            return f(r, id)

        field.represent = field.represent or repr_ref
        if hasattr(referenced, '_format') and referenced._format:
            requires = validators.IS_IN_DB(db, referenced._id,
                                           referenced._format)
            if field.unique:
                requires._and = validators.IS_NOT_IN_DB(db, field)
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
            from pydal.adapters import GoogleDatastoreAdapter
            refs = None
            db, id = r._db, r._id
            if isinstance(db._adapter, GoogleDatastoreAdapter):
                def count(values):
                    return db(id.belongs(values)).select(id)
                rx = range(0, len(ids), 30)
                refs = reduce(lambda a, b: a & b, [count(ids[i:i+30])
                              for i in rx])
            else:
                refs = db(id.belongs(ids)).select(id)
            return (refs and ', '.join(f(r, x.id) for x in refs) or '')

        field.represent = field.represent or list_ref_repr
        if hasattr(referenced, '_format') and referenced._format:
            requires = validators.IS_IN_DB(db, referenced._id,
                                           referenced._format, multiple=True)
        else:
            requires = validators.IS_IN_DB(db, referenced._id,
                                           multiple=True)
        if field.unique:
            requires._and = validators.IS_NOT_IN_DB(db, field)
        if not field.notnull:
            requires = validators.IS_EMPTY_OR(requires)
        return requires
    elif field_type.startswith('list:'):
        def repr_list(values, row=None):
            return', '.join(str(v) for v in (values or []))

        field.represent = field.represent or repr_list

    if field.unique:
        requires.append(validators.IS_NOT_IN_DB(db, field))
    sff = ['in', 'do', 'da', 'ti', 'de', 'bo']
    if field.notnull and not field_type[:2] in sff:
        requires.append(validators.IS_NOT_EMPTY())
    elif not field.notnull and field_type[:2] in sff and requires:
        requires[0] = validators.IS_EMPTY_OR(requires[0])
    return requires

from gluon import serializers as w2p_serializers
from gluon.utils import web2py_uuid
from gluon import sqlhtml


class DAL(pyDAL):
    serializers = w2p_serializers
    validators_method = _default_validators
    uuid = lambda x: web2py_uuid()
    representers = {
        'rows_render': sqlhtml.represent,
        'rows_xml': sqlhtml.SQLTABLE
    }

#: add web2py contrib drivers to pyDAL
from pydal.drivers import DRIVERS
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
