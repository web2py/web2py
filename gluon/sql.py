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

from dal import DAL, Field, Table, Query, Set, Expression, Row, Rows, DRIVERS, BaseAdapter, SQLField, SQLTable, SQLXorable, SQLQuery, SQLSet, SQLRows, SQLStorage, SQLDB, GQLDB, SQLALL, SQLCustomType
