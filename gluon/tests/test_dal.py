#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Unit tests for gluon.sql
"""

import sys
import os
if os.path.isdir('gluon'):
    sys.path.append(os.path.realpath('gluon'))
else:
    sys.path.append(os.path.realpath('../'))

import unittest
import datetime
from dal import DAL, Field, Table, SQLALL

ALLOWED_DATATYPES = [
    'string',
    'text',
    'integer',
    'boolean',
    'double',
    'blob',
    'date',
    'time',
    'datetime',
    'upload',
    'password',
    ]


def setUpModule():
    pass

def tearDownModule():
    if os.path.isfile('sql.log'):
        os.unlink('sql.log')


class TestFields(unittest.TestCase):

    def testFieldName(self):

        # Check that Fields cannot start with underscores
        self.assertRaises(SyntaxError, Field, '_abc', 'string')

        # Check that Fields cannot contain punctuation other than underscores
        self.assertRaises(SyntaxError, Field, 'a.bc', 'string')

        # Check that Fields cannot be a name of a method or property of Table
        for x in ['drop', 'on', 'truncate']:
            self.assertRaises(SyntaxError, Field, x, 'string')

        # Check that Fields allows underscores in the body of a field name.
        self.assert_(Field('a_bc', 'string'),
            "Field isn't allowing underscores in fieldnames.  It should.")

    def testFieldTypes(self):

        # Check that string, text, and password default length is 512
        for typ in ['string', 'password']:
            self.assert_(Field('abc', typ).length == 512,
                         "Default length for type '%s' is not 512 or 255" % typ)

        # Check that upload default length is 512
        self.assert_(Field('abc', 'upload').length == 512,
                     "Default length for type 'upload' is not 128")

        # Check that Tables passed in the type creates a reference
        self.assert_(Field('abc', Table(None, 'temp')).type
                      == 'reference temp',
                     'Passing an Table does not result in a reference type.')

    def testFieldLabels(self):

        # Check that a label is successfully built from the supplied fieldname
        self.assert_(Field('abc', 'string').label == 'Abc',
                     'Label built is incorrect')
        self.assert_(Field('abc_def', 'string').label == 'Abc Def',
                     'Label built is incorrect')

    def testFieldFormatters(self):  # Formatter should be called Validator

        # Test the default formatters
        for typ in ALLOWED_DATATYPES:
            f = Field('abc', typ)
            if typ not in ['date', 'time', 'datetime']:
                isinstance(f.formatter('test'), str)
            else:
                isinstance(f.formatter(datetime.datetime.now()), str)

    def testRun(self):
        db = DAL('sqlite:memory:')
        for ft in ['string', 'text', 'password', 'upload', 'blob']:
            db.define_table('t', Field('a', ft, default=''))
            self.assertEqual(db.t.insert(a='x'), 1)
            self.assertEqual(db().select(db.t.a)[0].a, 'x')
            db.t.drop()
        db.define_table('t', Field('a', 'integer', default=1))
        self.assertEqual(db.t.insert(a=3), 1)
        self.assertEqual(db().select(db.t.a)[0].a, 3)
        db.t.drop()
        db.define_table('t', Field('a', 'double', default=1))
        self.assertEqual(db.t.insert(a=3.1), 1)
        self.assertEqual(db().select(db.t.a)[0].a, 3.1)
        db.t.drop()
        db.define_table('t', Field('a', 'boolean', default=True))
        self.assertEqual(db.t.insert(a=True), 1)
        self.assertEqual(db().select(db.t.a)[0].a, True)
        db.t.drop()
        db.define_table('t', Field('a', 'date',
                        default=datetime.date.today()))
        t0 = datetime.date.today()
        self.assertEqual(db.t.insert(a=t0), 1)
        self.assertEqual(db().select(db.t.a)[0].a, t0)
        db.t.drop()
        db.define_table('t', Field('a', 'datetime',
                        default=datetime.datetime.today()))
        t0 = datetime.datetime(
            1971,
            12,
            21,
            10,
            30,
            55,
            0,
            )
        self.assertEqual(db.t.insert(a=t0), 1)
        self.assertEqual(db().select(db.t.a)[0].a, t0)
        db.t.drop()
        db.define_table('t', Field('a', 'time', default='11:30'))
        t0 = datetime.time(10, 30, 55)
        self.assertEqual(db.t.insert(a=t0), 1)
        self.assertEqual(db().select(db.t.a)[0].a, t0)
        db.t.drop()


class TestAll(unittest.TestCase):

    def setUp(self):
        self.pt = Table(None,'PseudoTable',Field('name'),Field('birthdate'))

    def testSQLALL(self):
        ans = 'PseudoTable.id, PseudoTable.name, PseudoTable.birthdate'
        self.assertEqual(str(SQLALL(self.pt)), ans)


class TestTable(unittest.TestCase):

    def testTableCreation(self):

        # Check for error when not passing type other than Field or Table

        self.assertRaises(SyntaxError, Table, None, 'test', None)

        persons = Table(None, 'persons',
                        Field('firstname','string'), 
                        Field('lastname', 'string'))
        
        # Does it have the correct fields?

        self.assert_(set(persons.fields).issuperset(set(['firstname',
                                                         'lastname'])))

        # ALL is set correctly

        self.assert_('persons.firstname, persons.lastname'
                      in str(persons.ALL))

    def testTableAlias(self):
        db = DAL('sqlite:memory:')
        persons = Table(db, 'persons', Field('firstname',
                           'string'), Field('lastname', 'string'))
        aliens = persons.with_alias('aliens')

        # Are the different table instances with the same fields

        self.assert_(persons is not aliens)
        self.assert_(set(persons.fields) == set(aliens.fields))

    def testTableInheritance(self):
        persons = Table(None, 'persons', Field('firstname',
                           'string'), Field('lastname', 'string'))
        customers = Table(None, 'customers',
                             Field('items_purchased', 'integer'),
                             persons)
        self.assert_(set(customers.fields).issuperset(set(
            ['items_purchased', 'firstname', 'lastname'])))


class TestInsert(unittest.TestCase):

    def testRun(self):
        db = DAL('sqlite:memory:')
        db.define_table('t', Field('a'))
        self.assertEqual(db.t.insert(a='1'), 1)
        self.assertEqual(db.t.insert(a='1'), 2)
        self.assertEqual(db.t.insert(a='1'), 3)
        self.assertEqual(db(db.t.a == '1').count(), 3)
        self.assertEqual(db(db.t.a == '1').update(a='2'), 3)
        self.assertEqual(db(db.t.a == '2').count(), 3)
        self.assertEqual(db(db.t.a == '2').delete(), 3)
        db.t.drop()


class TestSelect(unittest.TestCase):

    def testRun(self):
        db = DAL('sqlite:memory:')
        db.define_table('t', Field('a'))
        self.assertEqual(db.t.insert(a='1'), 1)
        self.assertEqual(db.t.insert(a='2'), 2)
        self.assertEqual(db.t.insert(a='3'), 3)
        self.assertEqual(len(db(db.t.id > 0).select()), 3)
        self.assertEqual(db(db.t.id > 0).select(orderby=~db.t.a
                          | db.t.id)[0].a, '3')
        self.assertEqual(len(db(db.t.id > 0).select(limitby=(1, 2))), 1)
        self.assertEqual(db(db.t.id > 0).select(limitby=(1, 2))[0].a,
                         '2')
        self.assertEqual(len(db().select(db.t.ALL)), 3)
        self.assertEqual(len(db(db.t.a == None).select()), 0)
        self.assertEqual(len(db(db.t.a != None).select()), 3)
        self.assertEqual(len(db(db.t.a > '1').select()), 2)
        self.assertEqual(len(db(db.t.a >= '1').select()), 3)
        self.assertEqual(len(db(db.t.a == '1').select()), 1)
        self.assertEqual(len(db(db.t.a != '1').select()), 2)
        self.assertEqual(len(db(db.t.a < '3').select()), 2)
        self.assertEqual(len(db(db.t.a <= '3').select()), 3)
        self.assertEqual(len(db(db.t.a > '1')(db.t.a < '3').select()), 1)
        self.assertEqual(len(db((db.t.a > '1') & (db.t.a < '3')).select()), 1)
        self.assertEqual(len(db((db.t.a > '1') | (db.t.a < '3')).select()), 3)
        self.assertEqual(len(db((db.t.a > '1') & ~(db.t.a > '2')).select()), 1)
        self.assertEqual(len(db(~(db.t.a > '1') & (db.t.a > '2')).select()), 0)
        db.t.drop()


class TestBelongs(unittest.TestCase):

    def testRun(self):
        db = DAL('sqlite:memory:')
        db.define_table('t', Field('a'))
        self.assertEqual(db.t.insert(a='1'), 1)
        self.assertEqual(db.t.insert(a='2'), 2)
        self.assertEqual(db.t.insert(a='3'), 3)
        self.assertEqual(len(db(db.t.a.belongs(('1', '3'))).select()),
                         2)
        self.assertEqual(len(db(db.t.a.belongs(db(db.t.id
                          > 2)._select(db.t.a))).select()), 1)
        self.assertEqual(len(db(db.t.a.belongs(db(db.t.a.belongs(('1',
                         '3')))._select(db.t.a))).select()), 2)
        self.assertEqual(len(db(db.t.a.belongs(db(db.t.a.belongs(db
                         (db.t.a.belongs(('1', '3')))._select(db.t.a)))._select(
                         db.t.a))).select()),
                         2)
        db.t.drop()


class TestLike(unittest.TestCase):

    def testRun(self):
        db = DAL('sqlite:memory:')
        db.define_table('t', Field('a'))
        self.assertEqual(db.t.insert(a='abc'), 1)
        self.assertEqual(len(db(db.t.a.like('a%')).select()), 1)
        self.assertEqual(len(db(db.t.a.like('%b%')).select()), 1)
        self.assertEqual(len(db(db.t.a.like('%c')).select()), 1)
        self.assertEqual(len(db(db.t.a.like('%d%')).select()), 0)
        self.assertEqual(len(db(db.t.a.lower().like('A%')).select()), 1)
        self.assertEqual(len(db(db.t.a.lower().like('%B%')).select()),
                         1)
        self.assertEqual(len(db(db.t.a.lower().like('%C')).select()), 1)
        self.assertEqual(len(db(db.t.a.upper().like('A%')).select()), 1)
        self.assertEqual(len(db(db.t.a.upper().like('%B%')).select()),
                         1)
        self.assertEqual(len(db(db.t.a.upper().like('%C')).select()), 1)
        db.t.drop()


class TestDatetime(unittest.TestCase):

    def testRun(self):
        db = DAL('sqlite:memory:')
        db.define_table('t', Field('a', 'datetime'))
        self.assertEqual(db.t.insert(a=datetime.datetime(1971, 12, 21,
                         11, 30)), 1)
        self.assertEqual(db.t.insert(a=datetime.datetime(1971, 11, 21,
                         10, 30)), 2)
        self.assertEqual(db.t.insert(a=datetime.datetime(1970, 12, 21,
                         9, 30)), 3)
        self.assertEqual(len(db(db.t.a == datetime.datetime(1971, 12,
                         21, 11, 30)).select()), 1)
        self.assertEqual(len(db(db.t.a.year() == 1971).select()), 2)
        self.assertEqual(len(db(db.t.a.month() == 12).select()), 2)
        self.assertEqual(len(db(db.t.a.day() == 21).select()), 3)
        self.assertEqual(len(db(db.t.a.hour() == 11).select()), 1)
        self.assertEqual(len(db(db.t.a.minutes() == 30).select()), 3)
        self.assertEqual(len(db(db.t.a.seconds() == 0).select()), 3)
        db.t.drop()


class TestExpressions(unittest.TestCase):

    def testRun(self):
        db = DAL('sqlite:memory:')
        db.define_table('t', Field('a', 'integer'))
        self.assertEqual(db.t.insert(a=1), 1)
        self.assertEqual(db.t.insert(a=2), 2)
        self.assertEqual(db.t.insert(a=3), 3)
        self.assertEqual(db(db.t.a == 3).update(a=db.t.a + 1), 1)
        self.assertEqual(len(db(db.t.a == 4).select()), 1)
        db.t.drop()


class TestJoin(unittest.TestCase):

    def testRun(self):
        db = DAL('sqlite:memory:')
        db.define_table('t1', Field('a'))
        db.define_table('t2', Field('a'), Field('b', db.t1))
        i1 = db.t1.insert(a='1')
        i2 = db.t1.insert(a='2')
        i3 = db.t1.insert(a='3')
        db.t2.insert(a='4', b=i1)
        db.t2.insert(a='5', b=i2)
        db.t2.insert(a='6', b=i2)
        self.assertEqual(len(db(db.t1.id
                          == db.t2.b).select(orderby=db.t1.a
                          | db.t2.a)), 3)
        self.assertEqual(db(db.t1.id == db.t2.b).select(orderby=db.t1.a
                          | db.t2.a)[2].t1.a, '2')
        self.assertEqual(db(db.t1.id == db.t2.b).select(orderby=db.t1.a
                          | db.t2.a)[2].t2.a, '6')
        self.assertEqual(len(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.a | db.t2.a)), 4)
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.a | db.t2.a)[2].t1.a, '2')
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.a | db.t2.a)[2].t2.a, '6')
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.a | db.t2.a)[3].t1.a, '3')
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.a | db.t2.a)[3].t2.a, None)
        self.assertEqual(len(db().select(db.t1.ALL, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.a | db.t2.a, groupby=db.t1.a)),
                         3)
        self.assertEqual(db().select(db.t1.ALL, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.a | db.t2.a,
                         groupby=db.t1.a)[0]._extra[db.t2.id.count()],
                         1)
        self.assertEqual(db().select(db.t1.ALL, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.a | db.t2.a,
                         groupby=db.t1.a)[1]._extra[db.t2.id.count()],
                         2)
        self.assertEqual(db().select(db.t1.ALL, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.a | db.t2.a,
                         groupby=db.t1.a)[2]._extra[db.t2.id.count()],
                         0)
        db.t1.drop()
        db.t2.drop()


class TestMinMaxSum(unittest.TestCase):

    def testRun(self):
        db = DAL('sqlite:memory:')
        db.define_table('t', Field('a', 'integer'))
        self.assertEqual(db.t.insert(a=1), 1)
        self.assertEqual(db.t.insert(a=2), 2)
        self.assertEqual(db.t.insert(a=3), 3)
        s = db.t.a.min()
        self.assertEqual(db(db.t.id > 0).select(s)[0]._extra[s], 1)
        s = db.t.a.max()
        self.assertEqual(db(db.t.id > 0).select(s)[0]._extra[s], 3)
        s = db.t.a.sum()
        self.assertEqual(db(db.t.id > 0).select(s)[0]._extra[s], 6)
        s = db.t.a.count()
        self.assertEqual(db(db.t.id > 0).select(s)[0]._extra[s], 3)
        db.t.drop()


#class TestCache(unittest.
#    def testRun(self):
#        cache = cache.ram
#        db = DAL('sqlite:memory:')
#        db.define_table('t', Field('a'))
#        db.t.insert(a='1')
#        r1 = db().select(db.t.ALL, cache=(cache, 1000))
#        db.t.insert(a='1')
#        r2 = db().select(db.t.ALL, cache=(cache, 1000))
#        self.assertEqual(r1.response, r2.response)
#        db.t.drop()


class TestMigrations(unittest.TestCase):

    def testRun(self):
        db = DAL('sqlite://.storage.db')
        db.define_table('t', Field('a'), migrate='.storage.table')
        db.commit()
        db = DAL('sqlite://.storage.db')
        db.define_table('t', Field('a'), Field('b'),
                        migrate='.storage.table')
        db.commit()
        db = DAL('sqlite://.storage.db')
        db.define_table('t', Field('a'), Field('b', 'text'),
                        migrate='.storage.table')
        db.commit()
        db = DAL('sqlite://.storage.db')
        db.define_table('t', Field('a'), migrate='.storage.table')
        db.t.drop()
        db.commit()

    def tearDown(self):
        os.unlink('.storage.db')

class TestReferece(unittest.TestCase):

    def testRun(self):
        db = DAL('sqlite:memory:')
        db.define_table('t', Field('name'), Field('a','reference t'))
        db.commit()
        x = db.t.insert(name='max')
        assert x.id == 1
        assert x['id'] == 1
        x.a = x
        assert x.a == 1
        x.update_record()
        y = db.t[1]
        assert y.a == 1
        assert y.a.a.a.a.a.a.name == 'max'
        z=db.t.insert(name='xxx', a = y)
        assert z.a == y.id
        db.t.drop()
        db.commit()

class TestClientLevelOps(unittest.TestCase):

    def testRun(self):
        db = DAL('sqlite:memory:')
        db.define_table('t', Field('a'))
        db.commit()
        db.t.insert(a="test")
        rows1 = db(db.t.id>0).select()
        rows2 = db(db.t.id>0).select()
        rows3 = rows1 & rows2
        assert len(rows3) == 2
        rows4 = rows1 | rows2
        assert len(rows4) == 1
        rows5 = rows1.find(lambda row: row.a=="test")
        assert len(rows5) == 1
        rows6 = rows2.exclude(lambda row: row.a=="test")
        assert len(rows6) == 1
        rows7 = rows5.sort(lambda row: row.a)
        assert len(rows7) == 1
        db.t.drop()
        db.commit()


class TestVirtualFields(unittest.TestCase):

    def testRun(self):
        db = DAL('sqlite:memory:')
        db.define_table('t', Field('a'))
        db.commit()
        db.t.insert(a="test")
        class Compute:
            def a_upper(row): return row.t.a.upper()
        db.t.virtualfields.append(Compute())
        assert db(db.t.id>0).select().first().a_upper == 'TEST'
        db.t.drop()
        db.commit()


if __name__ == '__main__':
    unittest.main()
    tearDownModule()
