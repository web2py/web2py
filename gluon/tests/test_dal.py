#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Unit tests for gluon.dal
"""

import sys
import os
import glob

import unittest
import datetime
try:
    import cStringIO as StringIO
except:
    from io import StringIO

def fix_sys_path():
    """
    logic to have always the correct sys.path
     '', web2py/gluon, web2py/site-packages, web2py/ ...
    """

    def add_path_first(path):
        sys.path = [path] + [p for p in sys.path if (
            not p == path and not p == (path + '/'))]

    path = os.path.dirname(os.path.abspath(__file__))

    if not os.path.isfile(os.path.join(path,'web2py.py')):
        i = 0
        while i<10:
            i += 1
            if os.path.exists(os.path.join(path,'web2py.py')):
                break
            path = os.path.abspath(os.path.join(path, '..'))

    paths = [path,
             os.path.abspath(os.path.join(path, 'site-packages')),
             os.path.abspath(os.path.join(path, 'gluon')),
             '']
    [add_path_first(path) for path in paths]

fix_sys_path()

from dal import DAL, Field, Table, SQLALL

#for travis-ci
DEFAULT_URI = os.environ.get('DB', 'sqlite:memory')
print 'Testing against %s engine (%s)' % (DEFAULT_URI.partition(':')[0], DEFAULT_URI)


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
    'json',
    ]


def setUpModule():
    pass

def tearDownModule():
    if os.path.isfile('sql.log'):
        os.unlink('sql.log')
    for a in glob.glob('*.table'):
        os.unlink(a)


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

        # Check that string, and password default length is 512
        for typ in ['string', 'password']:
            self.assert_(Field('abc', typ).length == 512,
                         "Default length for type '%s' is not 512 or 255" % typ)

        # Check that upload default length is 512
        self.assert_(Field('abc', 'upload').length == 512,
                     "Default length for type 'upload' is not 512")

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
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        for ft in ['string', 'text', 'password', 'upload', 'blob']:
            db.define_table('tt', Field('aa', ft, default=''))
            self.assertEqual(db.tt.insert(aa='x'), 1)
            self.assertEqual(db().select(db.tt.aa)[0].aa, 'x')
            db.tt.drop()
        db.define_table('tt', Field('aa', 'integer', default=1))
        self.assertEqual(db.tt.insert(aa=3), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, 3)
        db.tt.drop()
        db.define_table('tt', Field('aa', 'double', default=1))
        self.assertEqual(db.tt.insert(aa=3.1), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, 3.1)
        db.tt.drop()
        db.define_table('tt', Field('aa', 'boolean', default=True))
        self.assertEqual(db.tt.insert(aa=True), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, True)
        db.tt.drop()
        db.define_table('tt', Field('aa', 'json', default={}))
        self.assertEqual(db.tt.insert(aa={}), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, {})
        db.tt.drop()
        db.define_table('tt', Field('aa', 'date',
                        default=datetime.date.today()))
        t0 = datetime.date.today()
        self.assertEqual(db.tt.insert(aa=t0), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, t0)
        db.tt.drop()
        db.define_table('tt', Field('aa', 'datetime',
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
        self.assertEqual(db.tt.insert(aa=t0), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, t0)

        ## Row APIs
        row = db().select(db.tt.aa)[0]
        self.assertEqual(db.tt[1].aa,t0)
        self.assertEqual(db.tt['aa'],db.tt.aa)
        self.assertEqual(db.tt(1).aa,t0)
        self.assertTrue(db.tt(1,aa=None)==None)
        self.assertFalse(db.tt(1,aa=t0)==None)
        self.assertEqual(row.aa,t0)
        self.assertEqual(row['aa'],t0)
        self.assertEqual(row['tt.aa'],t0)
        self.assertEqual(row('tt.aa'),t0)

        ## Lazy and Virtual fields
        db.tt.b = Field.Virtual(lambda row: row.tt.aa)
        db.tt.c = Field.Lazy(lambda row: row.tt.aa)
        row = db().select(db.tt.aa)[0]
        self.assertEqual(row.b,t0)
        self.assertEqual(row.c(),t0)

        db.tt.drop()
        db.define_table('tt', Field('aa', 'time', default='11:30'))
        t0 = datetime.time(10, 30, 55)
        self.assertEqual(db.tt.insert(aa=t0), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, t0)
        db.tt.drop()


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
        db = DAL(DEFAULT_URI, check_reserved=['all'])
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
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa'))
        self.assertEqual(db.tt.insert(aa='1'), 1)
        self.assertEqual(db.tt.insert(aa='1'), 2)
        self.assertEqual(db.tt.insert(aa='1'), 3)
        self.assertEqual(db(db.tt.aa == '1').count(), 3)
        self.assertEqual(db(db.tt.aa == '2').isempty(), True)
        self.assertEqual(db(db.tt.aa == '1').update(aa='2'), 3)
        self.assertEqual(db(db.tt.aa == '2').count(), 3)
        self.assertEqual(db(db.tt.aa == '2').isempty(), False)
        self.assertEqual(db(db.tt.aa == '2').delete(), 3)
        self.assertEqual(db(db.tt.aa == '2').isempty(), True)
        db.tt.drop()


class TestSelect(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa'))
        self.assertEqual(db.tt.insert(aa='1'), 1)
        self.assertEqual(db.tt.insert(aa='2'), 2)
        self.assertEqual(db.tt.insert(aa='3'), 3)
        self.assertEqual(db(db.tt.id > 0).count(), 3)
        self.assertEqual(db(db.tt.id > 0).select(orderby=~db.tt.aa
                          | db.tt.id)[0].aa, '3')
        self.assertEqual(len(db(db.tt.id > 0).select(limitby=(1, 2))), 1)
        self.assertEqual(db(db.tt.id > 0).select(limitby=(1, 2))[0].aa,
                         '2')
        self.assertEqual(len(db().select(db.tt.ALL)), 3)
        self.assertEqual(db(db.tt.aa == None).count(), 0)
        self.assertEqual(db(db.tt.aa != None).count(), 3)
        self.assertEqual(db(db.tt.aa > '1').count(), 2)
        self.assertEqual(db(db.tt.aa >= '1').count(), 3)
        self.assertEqual(db(db.tt.aa == '1').count(), 1)
        self.assertEqual(db(db.tt.aa != '1').count(), 2)
        self.assertEqual(db(db.tt.aa < '3').count(), 2)
        self.assertEqual(db(db.tt.aa <= '3').count(), 3)
        self.assertEqual(db(db.tt.aa > '1')(db.tt.aa < '3').count(), 1)
        self.assertEqual(db((db.tt.aa > '1') & (db.tt.aa < '3')).count(), 1)
        self.assertEqual(db((db.tt.aa > '1') | (db.tt.aa < '3')).count(), 3)
        self.assertEqual(db((db.tt.aa > '1') & ~(db.tt.aa > '2')).count(), 1)
        self.assertEqual(db(~(db.tt.aa > '1') & (db.tt.aa > '2')).count(), 0)
        db.tt.drop()

class TestAddMethod(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa'))
        @db.tt.add_method.all
        def select_all(table,orderby=None):
            return table._db(table).select(orderby=orderby)
        self.assertEqual(db.tt.insert(aa='1'), 1)
        self.assertEqual(db.tt.insert(aa='2'), 2)
        self.assertEqual(db.tt.insert(aa='3'), 3)
        self.assertEqual(len(db.tt.all()), 3)
        db.tt.drop()


class TestBelongs(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa'))
        self.assertEqual(db.tt.insert(aa='1'), 1)
        self.assertEqual(db.tt.insert(aa='2'), 2)
        self.assertEqual(db.tt.insert(aa='3'), 3)
        self.assertEqual(db(db.tt.aa.belongs(('1', '3'))).count(),
                         2)
        self.assertEqual(db(db.tt.aa.belongs(db(db.tt.id
                          > 2)._select(db.tt.aa))).count(), 1)
        self.assertEqual(db(db.tt.aa.belongs(db(db.tt.aa.belongs(('1',
                         '3')))._select(db.tt.aa))).count(), 2)
        self.assertEqual(db(db.tt.aa.belongs(db(db.tt.aa.belongs(db
                         (db.tt.aa.belongs(('1', '3')))._select(db.tt.aa)))._select(
                         db.tt.aa))).count(),
                         2)
        db.tt.drop()


class TestContains(unittest.TestCase):
    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa', 'list:string'), Field('bb','string'))
        self.assertEqual(db.tt.insert(aa=['aaa','bbb'],bb='aaa'), 1)
        self.assertEqual(db.tt.insert(aa=['bbb','ddd'],bb='abb'), 2)
        self.assertEqual(db.tt.insert(aa=['eee','aaa'],bb='acc'), 3)
        self.assertEqual(db(db.tt.aa.contains('aaa')).count(), 2)
        self.assertEqual(db(db.tt.aa.contains('bbb')).count(), 2)
        self.assertEqual(db(db.tt.aa.contains('aa')).count(), 0)
        self.assertEqual(db(db.tt.bb.contains('a')).count(), 3)
        self.assertEqual(db(db.tt.bb.contains('b')).count(), 1)
        self.assertEqual(db(db.tt.bb.contains('d')).count(), 0)
        self.assertEqual(db(db.tt.aa.contains(db.tt.bb)).count(), 1)
        db.tt.drop()


class TestLike(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa'))
        self.assertEqual(db.tt.insert(aa='abc'), 1)
        self.assertEqual(db(db.tt.aa.like('a%')).count(), 1)
        self.assertEqual(db(db.tt.aa.like('%b%')).count(), 1)
        self.assertEqual(db(db.tt.aa.like('%c')).count(), 1)
        self.assertEqual(db(db.tt.aa.like('%d%')).count(), 0)
        self.assertEqual(db(db.tt.aa.lower().like('A%')).count(), 1)
        self.assertEqual(db(db.tt.aa.lower().like('%B%')).count(),
                         1)
        self.assertEqual(db(db.tt.aa.lower().like('%C')).count(), 1)
        self.assertEqual(db(db.tt.aa.upper().like('A%')).count(), 1)
        self.assertEqual(db(db.tt.aa.upper().like('%B%')).count(),
                         1)
        self.assertEqual(db(db.tt.aa.upper().like('%C')).count(), 1)
        db.tt.drop()
        db.define_table('tt', Field('aa', 'integer'))
        self.assertEqual(db.tt.insert(aa=1111111111), 1)
        self.assertEqual(db(db.tt.aa.like('1%')).count(), 1)
        self.assertEqual(db(db.tt.aa.like('2%')).count(), 0)
        db.tt.drop()


class TestDatetime(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa', 'datetime'))
        self.assertEqual(db.tt.insert(aa=datetime.datetime(1971, 12, 21,
                         11, 30)), 1)
        self.assertEqual(db.tt.insert(aa=datetime.datetime(1971, 11, 21,
                         10, 30)), 2)
        self.assertEqual(db.tt.insert(aa=datetime.datetime(1970, 12, 21,
                         9, 30)), 3)
        self.assertEqual(db(db.tt.aa == datetime.datetime(1971, 12,
                         21, 11, 30)).count(), 1)
        self.assertEqual(db(db.tt.aa.year() == 1971).count(), 2)
        self.assertEqual(db(db.tt.aa.month() == 12).count(), 2)
        self.assertEqual(db(db.tt.aa.day() == 21).count(), 3)
        self.assertEqual(db(db.tt.aa.hour() == 11).count(), 1)
        self.assertEqual(db(db.tt.aa.minutes() == 30).count(), 3)
        self.assertEqual(db(db.tt.aa.seconds() == 0).count(), 3)
        self.assertEqual(db(db.tt.aa.epoch()<365*24*3600).count(),1)
        db.tt.drop()


class TestExpressions(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa', 'integer'))
        self.assertEqual(db.tt.insert(aa=1), 1)
        self.assertEqual(db.tt.insert(aa=2), 2)
        self.assertEqual(db.tt.insert(aa=3), 3)
        self.assertEqual(db(db.tt.aa == 3).update(aa=db.tt.aa + 1), 1)
        self.assertEqual(db(db.tt.aa == 4).count(), 1)
        self.assertEqual(db(db.tt.aa == -2).count(), 0)
        sum = (db.tt.aa + 1).sum()
        self.assertEqual(db(db.tt.aa == 2).select(sum).first()[sum], 3)
        self.assertEqual(db(db.tt.aa == -2).select(sum).first()[sum], None)
        db.tt.drop()


class TestJoin(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('t1', Field('aa'))
        db.define_table('t2', Field('aa'), Field('b', db.t1))
        i1 = db.t1.insert(aa='1')
        i2 = db.t1.insert(aa='2')
        i3 = db.t1.insert(aa='3')
        db.t2.insert(aa='4', b=i1)
        db.t2.insert(aa='5', b=i2)
        db.t2.insert(aa='6', b=i2)
        self.assertEqual(len(db(db.t1.id
                          == db.t2.b).select(orderby=db.t1.aa
                          | db.t2.aa)), 3)
        self.assertEqual(db(db.t1.id == db.t2.b).select(orderby=db.t1.aa
                          | db.t2.aa)[2].t1.aa, '2')
        self.assertEqual(db(db.t1.id == db.t2.b).select(orderby=db.t1.aa
                          | db.t2.aa)[2].t2.aa, '6')
        self.assertEqual(len(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)), 4)
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)[2].t1.aa, '2')
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)[2].t2.aa, '6')
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)[3].t1.aa, '3')
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)[3].t2.aa, None)
        self.assertEqual(len(db().select(db.t1.aa, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa, groupby=db.t1.aa)),
                         3)
        self.assertEqual(db().select(db.t1.aa, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa,
                         groupby=db.t1.aa)[0]._extra[db.t2.id.count()],
                         1)
        self.assertEqual(db().select(db.t1.aa, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa,
                         groupby=db.t1.aa)[1]._extra[db.t2.id.count()],
                         2)
        self.assertEqual(db().select(db.t1.aa, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa,
                         groupby=db.t1.aa)[2]._extra[db.t2.id.count()],
                         0)
        db.t2.drop()
        db.t1.drop()

        db.define_table('person',Field('name'))
        id = db.person.insert(name="max")
        self.assertEqual(id.name,'max')
        db.define_table('dog',Field('name'),Field('ownerperson','reference person'))
        db.dog.insert(name='skipper',ownerperson=1)
        row = db(db.person.id==db.dog.ownerperson).select().first()
        self.assertEqual(row[db.person.name],'max')
        self.assertEqual(row['person.name'],'max')
        db.dog.drop()
        self.assertEqual(len(db.person._referenced_by),0)
        db.person.drop()

class TestMinMaxSumAvg(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa', 'integer'))
        self.assertEqual(db.tt.insert(aa=1), 1)
        self.assertEqual(db.tt.insert(aa=2), 2)
        self.assertEqual(db.tt.insert(aa=3), 3)
        s = db.tt.aa.min()
        self.assertEqual(db(db.tt.id > 0).select(s)[0]._extra[s], 1)
        self.assertEqual(db(db.tt.id > 0).select(s).first()[s], 1)
        self.assertEqual(db().select(s).first()[s], 1)
        s = db.tt.aa.max()
        self.assertEqual(db().select(s).first()[s], 3)
        s = db.tt.aa.sum()
        self.assertEqual(db().select(s).first()[s], 6)
        s = db.tt.aa.count()
        self.assertEqual(db().select(s).first()[s], 3)
        s = db.tt.aa.avg()
        self.assertEqual(db().select(s).first()[s], 2)
        db.tt.drop()


class TestCache(unittest.TestCase):
    def testRun(self):
        from cache import CacheInRam
        cache = CacheInRam()
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa'))
        db.tt.insert(aa='1')
        r0 = db().select(db.tt.ALL)
        r1 = db().select(db.tt.ALL, cache=(cache, 1000))
        self.assertEqual(len(r0),len(r1))
        r2 = db().select(db.tt.ALL, cache=(cache, 1000))
        self.assertEqual(len(r0),len(r2))
        r3 = db().select(db.tt.ALL, cache=(cache, 1000), cacheable=True)
        self.assertEqual(len(r0),len(r3))
        r4 = db().select(db.tt.ALL, cache=(cache, 1000), cacheable=True)
        self.assertEqual(len(r0),len(r4))
        db.tt.drop()


class TestMigrations(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa'), migrate='.storage.table')
        db.commit()
        db.close()
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa'), Field('b'),
                        migrate='.storage.table')
        db.commit()
        db.close()
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa'), Field('b', 'text'),
                        migrate='.storage.table')
        db.commit()
        db.close()
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa'), migrate='.storage.table')
        db.tt.drop()
        db.commit()
        db.close()

    def tearDown(self):
        if os.path.exists('.storage.db'):
            os.unlink('.storage.db')
        if os.path.exists('.storage.table'):
            os.unlink('.storage.table')

class TestReference(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        if DEFAULT_URI.startswith('mssql'):
            #multiple cascade gotcha
            for key in ['reference','reference FK']:
                db._adapter.types[key]=db._adapter.types[key].replace(
                '%(on_delete_action)s','NO ACTION')
        db.define_table('tt', Field('name'), Field('aa','reference tt'))
        db.commit()
        x = db.tt.insert(name='max')
        assert x.id == 1
        assert x['id'] == 1
        x.aa = x
        assert x.aa == 1
        x.update_record()
        y = db.tt[1]
        assert y.aa == 1
        assert y.aa.aa.aa.aa.aa.aa.name == 'max'
        z=db.tt.insert(name='xxx', aa = y)
        assert z.aa == y.id
        db.tt.drop()
        db.commit()

class TestClientLevelOps(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa'))
        db.commit()
        db.tt.insert(aa="test")
        rows1 = db(db.tt.id>0).select()
        rows2 = db(db.tt.id>0).select()
        rows3 = rows1 & rows2
        assert len(rows3) == 2
        rows4 = rows1 | rows2
        assert len(rows4) == 1
        rows5 = rows1.find(lambda row: row.aa=="test")
        assert len(rows5) == 1
        rows6 = rows2.exclude(lambda row: row.aa=="test")
        assert len(rows6) == 1
        rows7 = rows5.sort(lambda row: row.aa)
        assert len(rows7) == 1
        db.tt.drop()
        db.commit()


class TestVirtualFields(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt', Field('aa'))
        db.commit()
        db.tt.insert(aa="test")
        class Compute:
            def a_upper(row): return row.tt.aa.upper()
        db.tt.virtualfields.append(Compute())
        assert db(db.tt.id>0).select().first().a_upper == 'TEST'
        db.tt.drop()
        db.commit()

class TestComputedFields(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('tt',
                        Field('aa'),
                        Field('bb',default='x'),
                        Field('cc',compute=lambda r: r.aa+r.bb))
        db.commit()
        id = db.tt.insert(aa="z")
        self.assertEqual(db.tt[id].cc,'zx')
        db.tt.drop()
        db.commit()

        # test checking that a compute field can refer to earlier-defined computed fields
        db.define_table('tt',
                        Field('aa'),
                        Field('bb',default='x'),
                        Field('cc',compute=lambda r: r.aa+r.bb),
                        Field('dd',compute=lambda r: r.bb + r.cc))
        db.commit()
        id = db.tt.insert(aa="z")
        self.assertEqual(db.tt[id].dd,'xzx')
        db.tt.drop()
        db.commit()


class TestCommonFilters(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('t1', Field('aa'))
        db.define_table('t2', Field('aa'), Field('b', db.t1))
        i1 = db.t1.insert(aa='1')
        i2 = db.t1.insert(aa='2')
        i3 = db.t1.insert(aa='3')
        db.t2.insert(aa='4', b=i1)
        db.t2.insert(aa='5', b=i2)
        db.t2.insert(aa='6', b=i2)
        db.t1._common_filter = lambda q: db.t1.aa>1
        self.assertEqual(db(db.t1).count(),2)
        self.assertEqual(db(db.t1).count(),2)
        q = db.t2.b==db.t1.id
        self.assertEqual(db(q).count(),2)
        self.assertEqual(db(q).count(),2)
        self.assertEqual(len(db(db.t1).select(left=db.t2.on(q))),3)
        db.t2._common_filter = lambda q: db.t2.aa<6
        self.assertEqual(db(q).count(),1)
        self.assertEqual(db(q).count(),1)
        self.assertEqual(len(db(db.t1).select(left=db.t2.on(q))),2)
        db.t2.drop()
        db.t1.drop()

class TestImportExportFields(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('person', Field('name'))
        db.define_table('pet',Field('friend',db.person),Field('name'))
        for n in range(2):
            db(db.pet).delete()
            db(db.person).delete()
            for k in range(10):
                id = db.person.insert(name=str(k))
                db.pet.insert(friend=id,name=str(k))
        db.commit()
        stream = StringIO.StringIO()
        db.export_to_csv_file(stream)
        db(db.pet).delete()
        db(db.person).delete()
        stream = StringIO.StringIO(stream.getvalue())
        db.import_from_csv_file(stream)
        assert db(db.person.id==db.pet.friend)(db.person.name==db.pet.name).count()==10
        db.pet.drop()
        db.person.drop()
        db.commit()

class TestImportExportUuidFields(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('person', Field('name'),Field('uuid'))
        db.define_table('pet',Field('friend',db.person),Field('name'))
        for n in range(2):
            db(db.pet).delete()
            db(db.person).delete()
            for k in range(10):
                id = db.person.insert(name=str(k),uuid=str(k))
                db.pet.insert(friend=id,name=str(k))
        db.commit()
        stream = StringIO.StringIO()
        db.export_to_csv_file(stream)
        stream = StringIO.StringIO(stream.getvalue())
        db.import_from_csv_file(stream)
        assert db(db.person).count()==10
        assert db(db.person.id==db.pet.friend)(db.person.name==db.pet.name).count()==20
        db.pet.drop()
        db.person.drop()
        db.commit()


class TestDALDictImportExport(unittest.TestCase):

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('person', Field('name', default="Michael"),Field('uuid'))
        db.define_table('pet',Field('friend',db.person),Field('name'))
        dbdict = db.as_dict(flat=True, sanitize=False)
        assert isinstance(dbdict, dict)
        uri = dbdict["uri"]
        assert isinstance(uri, basestring) and uri
        assert len(dbdict["tables"]) == 2
        assert len(dbdict["tables"][0]["fields"]) == 3
        assert dbdict["tables"][0]["fields"][1]["type"] == db.person.name.type
        assert dbdict["tables"][0]["fields"][1]["default"] == db.person.name.default

        db2 = DAL(**dbdict)
        assert len(db.tables) == len(db2.tables)
        assert hasattr(db2, "pet") and isinstance(db2.pet, Table)
        assert hasattr(db2.pet, "friend") and isinstance(db2.pet.friend, Field)
        db.pet.drop()
        db.commit()

        db2.commit()

        have_serializers = True
        try:
            import serializers
            dbjson = db.as_json(sanitize=False)
            assert isinstance(dbjson, basestring) and len(dbjson) > 0

            unicode_keys = True
            if sys.version < "2.6.5":
                unicode_keys = False
            db3 = DAL(**serializers.loads_json(dbjson,
                          unicode_keys=unicode_keys))
            assert hasattr(db3, "person") and hasattr(db3.person, "uuid") and\
            db3.person.uuid.type == db.person.uuid.type
            db3.person.drop()
            db3.commit()
        except ImportError:
            pass

        mpfc = "Monty Python's Flying Circus"
        dbdict4 = {"uri": DEFAULT_URI,
                   "tables":[{"tablename": "tvshow",
                              "fields": [{"fieldname": "name",
                                          "default":mpfc},
                                         {"fieldname": "rating",
                                          "type":"double"}]},
                             {"tablename": "staff",
                              "fields": [{"fieldname": "name",
                                          "default":"Michael"},
                                         {"fieldname": "food",
                                          "default":"Spam"},
                                         {"fieldname": "tvshow",
                                          "type": "reference tvshow"}]}]}
        db4 = DAL(**dbdict4)
        assert "staff" in db4.tables
        assert "name" in db4.staff
        assert db4.tvshow.rating.type == "double"
        assert (db4.tvshow.insert(), db4.tvshow.insert(name="Loriot"),
                db4.tvshow.insert(name="Il Mattatore")) == (1, 2, 3)
        assert db4(db4.tvshow).select().first().id == 1
        assert db4(db4.tvshow).select().first().name == mpfc

        db4.staff.drop()
        db4.tvshow.drop()
        db4.commit()

        dbdict5 = {"uri": DEFAULT_URI}
        db5 = DAL(**dbdict5)
        assert db5.tables in ([], None)
        assert not (str(db5) in ("", None))

        dbdict6 = {"uri": DEFAULT_URI,
                   "tables":[{"tablename": "staff"},
                             {"tablename": "tvshow",
                              "fields": [{"fieldname": "name"},
                                         {"fieldname": "rating", "type":"double"}
                                        ]
                             }]
                  }
        db6 = DAL(**dbdict6)

        assert len(db6["staff"].fields) == 1
        assert "name" in db6["tvshow"].fields

        assert db6.staff.insert() is not None
        assert db6(db6.staff).select().first().id == 1


        db6.staff.drop()
        db6.tvshow.drop()
        db6.commit()


class TestValidateAndInsert(unittest.TestCase):

    def testRun(self):
        import datetime
        from gluon.validators import IS_INT_IN_RANGE
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table('val_and_insert',
                        Field('aa'),
                        Field('bb', 'integer',
                              requires=IS_INT_IN_RANGE(1,5))
                       )
        rtn = db.val_and_insert.validate_and_insert(aa='test1', bb=2)
        self.assertEqual(rtn.id, 1)
        #errors should be empty
        self.assertEqual(len(rtn.errors.keys()), 0)
        #this insert won't pass
        rtn = db.val_and_insert.validate_and_insert(bb="a")
        #the returned id should be None
        self.assertEqual(rtn.id, None)
        #an error message should be in rtn.errors.bb
        self.assertNotEqual(rtn.errors.bb, None)
        #cleanup table
        db.val_and_insert.drop()

class TestSelectAsDict(unittest.TestCase):

    def testSelect(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        db.define_table(
            'a_table',
            Field('b_field'),
            Field('a_field'),
            )
        db.a_table.insert(a_field="aa1", b_field="bb1")
        rtn = db.executesql("SELECT id, b_field, a_field FROM a_table", as_dict=True)
        self.assertEqual(rtn[0]['b_field'], 'bb1')
        rtn = db.executesql("SELECT id, b_field, a_field FROM a_table", as_ordered_dict=True)
        self.assertEqual(rtn[0]['b_field'], 'bb1')
        self.assertEqual(rtn[0].keys(), ['id', 'b_field', 'a_field'])
        db.a_table.drop()


class TestRNameTable(unittest.TestCase):
    #tests for highly experimental rname attribute

    def testSelect(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        rname = db._adapter.QUOTE_TEMPLATE % 'a very complicated tablename'
        db.define_table(
            'easy_name',
            Field('a_field'),
            rname=rname
            )
        rtn = db.easy_name.insert(a_field='a')
        self.assertEqual(rtn.id, 1)
        rtn = db(db.easy_name.a_field == 'a').select()
        self.assertEqual(len(rtn), 1)
        self.assertEqual(rtn[0].id, 1)
        self.assertEqual(rtn[0].a_field, 'a')
        db.easy_name.insert(a_field='b')
        rtn = db(db.easy_name.id > 0).delete()
        self.assertEqual(rtn, 2)
        rtn = db(db.easy_name.id > 0).count()
        self.assertEqual(rtn, 0)
        db.easy_name.insert(a_field='a')
        db.easy_name.insert(a_field='b')
        rtn = db(db.easy_name.id > 0).count()
        self.assertEqual(rtn, 2)
        rtn = db(db.easy_name.a_field == 'a').update(a_field='c')
        rtn = db(db.easy_name.a_field == 'c').count()
        self.assertEqual(rtn, 1)
        rtn = db(db.easy_name.a_field != 'c').count()
        self.assertEqual(rtn, 1)
        avg = db.easy_name.id.avg()
        rtn = db(db.easy_name.id > 0).select(avg)
        self.assertEqual(rtn[0][avg], 3)
        rname = db._adapter.QUOTE_TEMPLATE % 'this is the person table'
        db.define_table(
            'person',
            Field('name', default="Michael"),
            Field('uuid'),
            rname=rname
            )
        rname = db._adapter.QUOTE_TEMPLATE % 'this is the pet table'
        db.define_table(
            'pet',
            Field('friend','reference person'),
            Field('name'),
            rname=rname
            )
        michael = db.person.insert() #default insert
        john = db.person.insert(name='John')
        luke = db.person.insert(name='Luke')

        #michael owns Phippo
        phippo = db.pet.insert(friend=michael, name="Phippo")
        #john owns Dunstin and Gertie
        dunstin = db.pet.insert(friend=john, name="Dunstin")
        gertie = db.pet.insert(friend=john, name="Gertie")

        rtn = db(db.person.id == db.pet.friend).select(orderby=db.person.id|db.pet.id)
        self.assertEqual(len(rtn), 3)
        self.assertEqual(rtn[0].person.id, michael)
        self.assertEqual(rtn[0].person.name, 'Michael')
        self.assertEqual(rtn[0].pet.id, phippo)
        self.assertEqual(rtn[0].pet.name, 'Phippo')
        self.assertEqual(rtn[1].person.id, john)
        self.assertEqual(rtn[1].person.name, 'John')
        self.assertEqual(rtn[1].pet.name, 'Dunstin')
        self.assertEqual(rtn[2].pet.name, 'Gertie')
        #fetch owners, eventually with pet
        #main point is retrieving Luke with no pets
        rtn = db(db.person.id > 0).select(
            orderby=db.person.id|db.pet.id,
            left=db.pet.on(db.person.id == db.pet.friend)
            )
        self.assertEqual(rtn[0].person.id, michael)
        self.assertEqual(rtn[0].person.name, 'Michael')
        self.assertEqual(rtn[0].pet.id, phippo)
        self.assertEqual(rtn[0].pet.name, 'Phippo')
        self.assertEqual(rtn[3].person.name, 'Luke')
        self.assertEqual(rtn[3].person.id, luke)
        self.assertEqual(rtn[3].pet.name, None)
        #lets test a subquery
        subq = db(db.pet.name == "Gertie")._select(db.pet.friend)
        rtn = db(db.person.id.belongs(subq)).select()
        self.assertEqual(rtn[0].id, 2)
        self.assertEqual(rtn[0]('person.name'), 'John')
        #as dict
        rtn = db(db.person.id > 0).select().as_dict()
        self.assertEqual(rtn[1]['name'], 'Michael')
        #as list
        rtn = db(db.person.id > 0).select().as_list()
        self.assertEqual(rtn[0]['name'], 'Michael')
        #isempty
        rtn = db(db.person.id > 0).isempty()
        self.assertEqual(rtn, False)
        #join argument
        rtn = db(db.person).select(orderby=db.person.id|db.pet.id,
                                   join=db.pet.on(db.person.id==db.pet.friend))
        self.assertEqual(len(rtn), 3)
        self.assertEqual(rtn[0].person.id, michael)
        self.assertEqual(rtn[0].person.name, 'Michael')
        self.assertEqual(rtn[0].pet.id, phippo)
        self.assertEqual(rtn[0].pet.name, 'Phippo')
        self.assertEqual(rtn[1].person.id, john)
        self.assertEqual(rtn[1].person.name, 'John')
        self.assertEqual(rtn[1].pet.name, 'Dunstin')
        self.assertEqual(rtn[2].pet.name, 'Gertie')

        #aliases
        if DEFAULT_URI.startswith('mssql'):
            #multiple cascade gotcha
            for key in ['reference','reference FK']:
                db._adapter.types[key]=db._adapter.types[key].replace(
                '%(on_delete_action)s','NO ACTION')
        rname = db._adapter.QUOTE_TEMPLATE % 'the cubs'
        db.define_table('pet_farm',
            Field('name'),
            Field('father','reference pet_farm'),
            Field('mother','reference pet_farm'),
            rname=rname
        )

        minali = db.pet_farm.insert(name='Minali')
        osbert = db.pet_farm.insert(name='Osbert')
        #they had a cub
        selina = db.pet_farm.insert(name='Selina', father=osbert, mother=minali)

        father = db.pet_farm.with_alias('father')
        mother = db.pet_farm.with_alias('mother')

        #fetch pets with relatives
        rtn = db().select(
            db.pet_farm.name, father.name, mother.name,
            left=[
                father.on(father.id == db.pet_farm.father),
                mother.on(mother.id == db.pet_farm.mother)
            ],
            orderby=db.pet_farm.id
        )

        self.assertEqual(len(rtn), 3)
        self.assertEqual(rtn[0].pet_farm.name, 'Minali')
        self.assertEqual(rtn[0].father.name, None)
        self.assertEqual(rtn[0].mother.name, None)
        self.assertEqual(rtn[1].pet_farm.name, 'Osbert')
        self.assertEqual(rtn[2].pet_farm.name, 'Selina')
        self.assertEqual(rtn[2].father.name, 'Osbert')
        self.assertEqual(rtn[2].mother.name, 'Minali')

        #clean up
        db.pet_farm.drop()
        db.pet.drop()
        db.person.drop()
        db.easy_name.drop()

    def testJoin(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        rname = db._adapter.QUOTE_TEMPLATE % 'this is table t1'
        rname2 = db._adapter.QUOTE_TEMPLATE % 'this is table t2'
        db.define_table('t1', Field('aa'), rname=rname)
        db.define_table('t2', Field('aa'), Field('b', db.t1), rname=rname2)
        i1 = db.t1.insert(aa='1')
        i2 = db.t1.insert(aa='2')
        i3 = db.t1.insert(aa='3')
        db.t2.insert(aa='4', b=i1)
        db.t2.insert(aa='5', b=i2)
        db.t2.insert(aa='6', b=i2)
        self.assertEqual(len(db(db.t1.id
                          == db.t2.b).select(orderby=db.t1.aa
                          | db.t2.aa)), 3)
        self.assertEqual(db(db.t1.id == db.t2.b).select(orderby=db.t1.aa
                          | db.t2.aa)[2].t1.aa, '2')
        self.assertEqual(db(db.t1.id == db.t2.b).select(orderby=db.t1.aa
                          | db.t2.aa)[2].t2.aa, '6')
        self.assertEqual(len(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)), 4)
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)[2].t1.aa, '2')
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)[2].t2.aa, '6')
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)[3].t1.aa, '3')
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)[3].t2.aa, None)
        self.assertEqual(len(db().select(db.t1.aa, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa, groupby=db.t1.aa)),
                         3)
        self.assertEqual(db().select(db.t1.aa, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa,
                         groupby=db.t1.aa)[0]._extra[db.t2.id.count()],
                         1)
        self.assertEqual(db().select(db.t1.aa, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa,
                         groupby=db.t1.aa)[1]._extra[db.t2.id.count()],
                         2)
        self.assertEqual(db().select(db.t1.aa, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa,
                         groupby=db.t1.aa)[2]._extra[db.t2.id.count()],
                         0)
        db.t2.drop()
        db.t1.drop()

        db.define_table('person',Field('name'), rname=rname)
        id = db.person.insert(name="max")
        self.assertEqual(id.name,'max')
        db.define_table('dog',Field('name'),Field('ownerperson','reference person'), rname=rname2)
        db.dog.insert(name='skipper',ownerperson=1)
        row = db(db.person.id==db.dog.ownerperson).select().first()
        self.assertEqual(row[db.person.name],'max')
        self.assertEqual(row['person.name'],'max')
        db.dog.drop()
        self.assertEqual(len(db.person._referenced_by),0)
        db.person.drop()


class TestRNameFields(unittest.TestCase):
    # tests for highly experimental rname attribute
    def testSelect(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        rname = db._adapter.QUOTE_TEMPLATE % 'a very complicated fieldname'
        rname2 = db._adapter.QUOTE_TEMPLATE % 'rrating from 1 to 10'
        db.define_table(
            'easy_name',
            Field('a_field', rname=rname),
            Field('rating', 'integer', rname=rname2, default=2)
            )
        rtn = db.easy_name.insert(a_field='a')
        self.assertEqual(rtn.id, 1)
        rtn = db(db.easy_name.a_field == 'a').select()
        self.assertEqual(len(rtn), 1)
        self.assertEqual(rtn[0].id, 1)
        self.assertEqual(rtn[0].a_field, 'a')
        db.easy_name.insert(a_field='b')
        rtn = db(db.easy_name.id > 0).delete()
        self.assertEqual(rtn, 2)
        rtn = db(db.easy_name.id > 0).count()
        self.assertEqual(rtn, 0)
        db.easy_name.insert(a_field='a')
        db.easy_name.insert(a_field='b')
        rtn = db(db.easy_name.id > 0).count()
        self.assertEqual(rtn, 2)
        rtn = db(db.easy_name.a_field == 'a').update(a_field='c')
        rtn = db(db.easy_name.a_field == 'c').count()
        self.assertEqual(rtn, 1)
        rtn = db(db.easy_name.a_field != 'c').count()
        self.assertEqual(rtn, 1)
        avg = db.easy_name.id.avg()
        rtn = db(db.easy_name.id > 0).select(avg)
        self.assertEqual(rtn[0][avg], 3)

        avg = db.easy_name.rating.avg()
        rtn = db(db.easy_name.id > 0).select(avg)
        self.assertEqual(rtn[0][avg], 2)

        rname = db._adapter.QUOTE_TEMPLATE % 'this is the person name'
        db.define_table(
            'person',
            Field('name', default="Michael", rname=rname),
            Field('uuid')
            )
        rname = db._adapter.QUOTE_TEMPLATE % 'this is the pet name'
        db.define_table(
            'pet',
            Field('friend','reference person'),
            Field('name', rname=rname)
            )
        michael = db.person.insert() #default insert
        john = db.person.insert(name='John')
        luke = db.person.insert(name='Luke')

        #michael owns Phippo
        phippo = db.pet.insert(friend=michael, name="Phippo")
        #john owns Dunstin and Gertie
        dunstin = db.pet.insert(friend=john, name="Dunstin")
        gertie = db.pet.insert(friend=john, name="Gertie")

        rtn = db(db.person.id == db.pet.friend).select(orderby=db.person.id|db.pet.id)
        self.assertEqual(len(rtn), 3)
        self.assertEqual(rtn[0].person.id, michael)
        self.assertEqual(rtn[0].person.name, 'Michael')
        self.assertEqual(rtn[0].pet.id, phippo)
        self.assertEqual(rtn[0].pet.name, 'Phippo')
        self.assertEqual(rtn[1].person.id, john)
        self.assertEqual(rtn[1].person.name, 'John')
        self.assertEqual(rtn[1].pet.name, 'Dunstin')
        self.assertEqual(rtn[2].pet.name, 'Gertie')
        #fetch owners, eventually with pet
        #main point is retrieving Luke with no pets
        rtn = db(db.person.id > 0).select(
            orderby=db.person.id|db.pet.id,
            left=db.pet.on(db.person.id == db.pet.friend)
            )
        self.assertEqual(rtn[0].person.id, michael)
        self.assertEqual(rtn[0].person.name, 'Michael')
        self.assertEqual(rtn[0].pet.id, phippo)
        self.assertEqual(rtn[0].pet.name, 'Phippo')
        self.assertEqual(rtn[3].person.name, 'Luke')
        self.assertEqual(rtn[3].person.id, luke)
        self.assertEqual(rtn[3].pet.name, None)
        #lets test a subquery
        subq = db(db.pet.name == "Gertie")._select(db.pet.friend)
        rtn = db(db.person.id.belongs(subq)).select()
        self.assertEqual(rtn[0].id, 2)
        self.assertEqual(rtn[0]('person.name'), 'John')
        #as dict
        rtn = db(db.person.id > 0).select().as_dict()
        self.assertEqual(rtn[1]['name'], 'Michael')
        #as list
        rtn = db(db.person.id > 0).select().as_list()
        self.assertEqual(rtn[0]['name'], 'Michael')
        #isempty
        rtn = db(db.person.id > 0).isempty()
        self.assertEqual(rtn, False)
        #join argument
        rtn = db(db.person).select(orderby=db.person.id|db.pet.id,
                                   join=db.pet.on(db.person.id==db.pet.friend))
        self.assertEqual(len(rtn), 3)
        self.assertEqual(rtn[0].person.id, michael)
        self.assertEqual(rtn[0].person.name, 'Michael')
        self.assertEqual(rtn[0].pet.id, phippo)
        self.assertEqual(rtn[0].pet.name, 'Phippo')
        self.assertEqual(rtn[1].person.id, john)
        self.assertEqual(rtn[1].person.name, 'John')
        self.assertEqual(rtn[1].pet.name, 'Dunstin')
        self.assertEqual(rtn[2].pet.name, 'Gertie')

        #aliases
        rname = db._adapter.QUOTE_TEMPLATE % 'the cub name'
        if DEFAULT_URI.startswith('mssql'):
            #multiple cascade gotcha
            for key in ['reference','reference FK']:
                db._adapter.types[key]=db._adapter.types[key].replace(
                '%(on_delete_action)s','NO ACTION')
        db.define_table('pet_farm',
            Field('name', rname=rname),
            Field('father','reference pet_farm'),
            Field('mother','reference pet_farm'),
        )

        minali = db.pet_farm.insert(name='Minali')
        osbert = db.pet_farm.insert(name='Osbert')
        #they had a cub
        selina = db.pet_farm.insert(name='Selina', father=osbert, mother=minali)

        father = db.pet_farm.with_alias('father')
        mother = db.pet_farm.with_alias('mother')

        #fetch pets with relatives
        rtn = db().select(
            db.pet_farm.name, father.name, mother.name,
            left=[
                father.on(father.id == db.pet_farm.father),
                mother.on(mother.id == db.pet_farm.mother)
            ],
            orderby=db.pet_farm.id
        )

        self.assertEqual(len(rtn), 3)
        self.assertEqual(rtn[0].pet_farm.name, 'Minali')
        self.assertEqual(rtn[0].father.name, None)
        self.assertEqual(rtn[0].mother.name, None)
        self.assertEqual(rtn[1].pet_farm.name, 'Osbert')
        self.assertEqual(rtn[2].pet_farm.name, 'Selina')
        self.assertEqual(rtn[2].father.name, 'Osbert')
        self.assertEqual(rtn[2].mother.name, 'Minali')

        #clean up
        db.pet_farm.drop()
        db.pet.drop()
        db.person.drop()
        db.easy_name.drop()

    def testRun(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        rname = db._adapter.QUOTE_TEMPLATE % 'a very complicated fieldname'
        for ft in ['string', 'text', 'password', 'upload', 'blob']:
            db.define_table('tt', Field('aa', ft, default='', rname=rname))
            self.assertEqual(db.tt.insert(aa='x'), 1)
            self.assertEqual(db().select(db.tt.aa)[0].aa, 'x')
            db.tt.drop()
        db.define_table('tt', Field('aa', 'integer', default=1, rname=rname))
        self.assertEqual(db.tt.insert(aa=3), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, 3)
        db.tt.drop()
        db.define_table('tt', Field('aa', 'double', default=1, rname=rname))
        self.assertEqual(db.tt.insert(aa=3.1), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, 3.1)
        db.tt.drop()
        db.define_table('tt', Field('aa', 'boolean', default=True, rname=rname))
        self.assertEqual(db.tt.insert(aa=True), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, True)
        db.tt.drop()
        db.define_table('tt', Field('aa', 'json', default={}, rname=rname))
        self.assertEqual(db.tt.insert(aa={}), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, {})
        db.tt.drop()
        db.define_table('tt', Field('aa', 'date',
                        default=datetime.date.today(), rname=rname))
        t0 = datetime.date.today()
        self.assertEqual(db.tt.insert(aa=t0), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, t0)
        db.tt.drop()
        db.define_table('tt', Field('aa', 'datetime',
                        default=datetime.datetime.today(), rname=rname))
        t0 = datetime.datetime(
            1971,
            12,
            21,
            10,
            30,
            55,
            0,
            )
        self.assertEqual(db.tt.insert(aa=t0), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, t0)

        ## Row APIs
        row = db().select(db.tt.aa)[0]
        self.assertEqual(db.tt[1].aa,t0)
        self.assertEqual(db.tt['aa'],db.tt.aa)
        self.assertEqual(db.tt(1).aa,t0)
        self.assertTrue(db.tt(1,aa=None)==None)
        self.assertFalse(db.tt(1,aa=t0)==None)
        self.assertEqual(row.aa,t0)
        self.assertEqual(row['aa'],t0)
        self.assertEqual(row['tt.aa'],t0)
        self.assertEqual(row('tt.aa'),t0)

        ## Lazy and Virtual fields
        db.tt.b = Field.Virtual(lambda row: row.tt.aa)
        db.tt.c = Field.Lazy(lambda row: row.tt.aa)
        row = db().select(db.tt.aa)[0]
        self.assertEqual(row.b,t0)
        self.assertEqual(row.c(),t0)

        db.tt.drop()
        db.define_table('tt', Field('aa', 'time', default='11:30', rname=rname))
        t0 = datetime.time(10, 30, 55)
        self.assertEqual(db.tt.insert(aa=t0), 1)
        self.assertEqual(db().select(db.tt.aa)[0].aa, t0)
        db.tt.drop()

    def testInsert(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        rname = db._adapter.QUOTE_TEMPLATE % 'a very complicated fieldname'
        db.define_table('tt', Field('aa', rname=rname))
        self.assertEqual(db.tt.insert(aa='1'), 1)
        self.assertEqual(db.tt.insert(aa='1'), 2)
        self.assertEqual(db.tt.insert(aa='1'), 3)
        self.assertEqual(db(db.tt.aa == '1').count(), 3)
        self.assertEqual(db(db.tt.aa == '2').isempty(), True)
        self.assertEqual(db(db.tt.aa == '1').update(aa='2'), 3)
        self.assertEqual(db(db.tt.aa == '2').count(), 3)
        self.assertEqual(db(db.tt.aa == '2').isempty(), False)
        self.assertEqual(db(db.tt.aa == '2').delete(), 3)
        self.assertEqual(db(db.tt.aa == '2').isempty(), True)
        db.tt.drop()

    def testJoin(self):
        db = DAL(DEFAULT_URI, check_reserved=['all'])
        rname = db._adapter.QUOTE_TEMPLATE % 'this is field aa'
        rname2 = db._adapter.QUOTE_TEMPLATE % 'this is field b'
        db.define_table('t1', Field('aa', rname=rname))
        db.define_table('t2', Field('aa', rname=rname), Field('b', db.t1, rname=rname2))
        i1 = db.t1.insert(aa='1')
        i2 = db.t1.insert(aa='2')
        i3 = db.t1.insert(aa='3')
        db.t2.insert(aa='4', b=i1)
        db.t2.insert(aa='5', b=i2)
        db.t2.insert(aa='6', b=i2)
        self.assertEqual(len(db(db.t1.id
                          == db.t2.b).select(orderby=db.t1.aa
                          | db.t2.aa)), 3)
        self.assertEqual(db(db.t1.id == db.t2.b).select(orderby=db.t1.aa
                          | db.t2.aa)[2].t1.aa, '2')
        self.assertEqual(db(db.t1.id == db.t2.b).select(orderby=db.t1.aa
                          | db.t2.aa)[2].t2.aa, '6')
        self.assertEqual(len(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)), 4)
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)[2].t1.aa, '2')
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)[2].t2.aa, '6')
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)[3].t1.aa, '3')
        self.assertEqual(db().select(db.t1.ALL, db.t2.ALL,
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa | db.t2.aa)[3].t2.aa, None)
        self.assertEqual(len(db().select(db.t1.aa, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa, groupby=db.t1.aa)),
                         3)
        self.assertEqual(db().select(db.t1.aa, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa,
                         groupby=db.t1.aa)[0]._extra[db.t2.id.count()],
                         1)
        self.assertEqual(db().select(db.t1.aa, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa,
                         groupby=db.t1.aa)[1]._extra[db.t2.id.count()],
                         2)
        self.assertEqual(db().select(db.t1.aa, db.t2.id.count(),
                         left=db.t2.on(db.t1.id == db.t2.b),
                         orderby=db.t1.aa,
                         groupby=db.t1.aa)[2]._extra[db.t2.id.count()],
                         0)
        db.t2.drop()
        db.t1.drop()

        db.define_table('person',Field('name', rname=rname))
        id = db.person.insert(name="max")
        self.assertEqual(id.name,'max')
        db.define_table('dog',Field('name', rname=rname),Field('ownerperson','reference person', rname=rname2))
        db.dog.insert(name='skipper',ownerperson=1)
        row = db(db.person.id==db.dog.ownerperson).select().first()
        self.assertEqual(row[db.person.name],'max')
        self.assertEqual(row['person.name'],'max')
        db.dog.drop()
        self.assertEqual(len(db.person._referenced_by),0)
        db.person.drop()


if __name__ == '__main__':
    unittest.main()
    tearDownModule()