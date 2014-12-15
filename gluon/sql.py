#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
| This file is part of the web2py Web Framework
| Developed by Massimo Di Pierro <mdipierro@cs.depaul.edu>,
| limodou <limodou@gmail.com> and srackham <srackham@gmail.com>.
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Just for backward compatibility
--------------------------------
"""
__all__ = ['DAL', 'Field', 'DRIVERS']

from dal import DAL, Field, SQLCustomType
from gluon.pydal.base import BaseAdapter
from gluon.pydal.drivers import DRIVERS
from gluon.pydal.objects import Table, Query, Set, Expression, Row, Rows
from gluon.pydal.helpers.classes import SQLALL

SQLDB = DAL
GQLDB = DAL
SQLField = Field
SQLTable = Table
SQLXorable = Expression
SQLQuery = Query
SQLSet = Set
SQLRows = Rows
SQLStorage = Row
