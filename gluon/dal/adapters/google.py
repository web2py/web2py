# -*- coding: utf-8 -*-
import os
import re

from .._compat import pjoin
from .._globals import IDENTITY, LOGGER, THREAD_LOCAL
from .._load import classobj, gae, ndb, NDBDecimalProperty, GAEDecimalProperty, \
    namespace_manager, Key, NDBPolyModel, PolyModel, rdbms, have_serializers, \
    serializers, simplejson
from ..objects import Table, Field, Expression, Query
from ..helpers.classes import SQLCustomType, SQLALL, Reference, UseDatabaseStoredFile
from ..helpers.methods import use_common_filters, xorify
from .base import NoSQLAdapter
from .mysql import MySQLAdapter


class GoogleSQLAdapter(UseDatabaseStoredFile, MySQLAdapter):
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

    You can enable NDB by using adapter_args::

        db = DAL('google:datastore', adapter_args={'ndb_settings':ndb_settings, 'use_ndb':True})

    ndb_settings is optional and can be used for per model caching settings.
    It must be a dict in this form::

        ndb_settings = {<table_name>:{<variable_name>:<variable_value>}}

    See: https://developers.google.com/appengine/docs/python/ndb/cache
    """

    MAX_FETCH_LIMIT = 1000000
    uploads_in_blob = True
    types = {}
    # reconnect is not required for Datastore dbs
    reconnect = lambda *args, **kwargs: None

    def file_exists(self, filename): pass
    def file_open(self, filename, mode='rb', lock=True): pass
    def file_close(self, fileobj): pass

    REGEX_NAMESPACE = re.compile('.*://(?P<namespace>.+)')

    def __init__(self,db,uri,pool_size=0,folder=None,db_codec ='UTF-8',
                 credential_decoder=IDENTITY, driver_args={},
                 adapter_args={}, do_connect=True, after_connection=None):
        self.use_ndb = adapter_args.get('use_ndb',uri.startswith('google:datastore+ndb'))
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

    def represent(self, obj, fieldtype):
        if fieldtype == "json":
            if have_serializers:
                return serializers.json(obj)
            elif simplejson:
                return simplejson.dumps(obj)
            else:
                raise Exception("Could not dump json object (missing json library)")
        else:
            return NoSQLAdapter.represent(self, obj, fieldtype)

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
                ftype = self.types[field_type[:9]](**attr)
            elif field_type.startswith('list:reference'):
                if field.notnull:
                    attr['required'] = True
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
                second = self.keyfunc(first._tablename, long(second))
            return [GAEF(first.name,'!=',second,lambda a,b:a!=b)]

    def LT(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'<',self.represent(second,first.type),lambda a,b:a<b)]
        else:
            second = self.keyfunc(first._tablename, long(second))
            return [GAEF(first.name,'<',second,lambda a,b:a<b)]

    def LE(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'<=',self.represent(second,first.type),lambda a,b:a<=b)]
        else:
            second = self.keyfunc(first._tablename, long(second))
            return [GAEF(first.name,'<=',second,lambda a,b:a<=b)]

    def GT(self,first,second=None):
        if first.type != 'id' or second==0 or second == '0':
            return [GAEF(first.name,'>',self.represent(second,first.type),lambda a,b:a>b)]
        else:
            second = self.keyfunc(first._tablename, long(second))
            return [GAEF(first.name,'>',second,lambda a,b:a>b)]

    def GE(self,first,second=None):
        if first.type != 'id':
            return [GAEF(first.name,'>=',self.represent(second,first.type),lambda a,b:a>=b)]
        else:
            second = self.keyfunc(first._tablename, long(second))
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
            second = [self.keyfunc(first._tablename, int(i)) for i in second]
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

    def select_raw(self,query,fields=None,attributes=None,count_only=False):
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

        elif args_get('filterfields') is True:
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

        cursor = args_get('reusecursor')
        cursor = cursor if isinstance(cursor, str) else None
        if self.use_ndb:
            qo = ndb.QueryOptions(projection=query_projection, cursor=cursor)
            items = tableobj.query(default_options=qo)
        else:
            items = gae.Query(tableobj, projection=query_projection, cursor=cursor)

        for filter in filters:
            if (args_get('projection') == True and
                filter.name in query_projection and
                filter.op in ('=', '<=', '>=')):
                raise SyntaxError("projection fields cannot have equality filters")
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
                    items = [item] if item else []
                else:
                    # key qeuries return a class instance,
                    # can't use projection
                    # extra values will be ignored in post-processing later
                    item = tableobj.get_by_id(filter.value)
                    items = [item] if item else []
            elif isinstance(items,list): # i.e. there is a single record!
                items = [i for i in items if filter.apply(
                        getattr(item,filter.name),filter.value)]
            else:
                if filter.name=='__key__' and filter.op != 'in':
                    items.order(tableobj._key) if self.use_ndb else items.order('__key__')
                if self.use_ndb:
                    items = self.filter(items, tableobj, filter.name, filter.op, filter.value)
                else:
                    items = items.filter('%s %s' % (filter.name,filter.op), filter.value)

        if count_only:
            items = [len(items) if isinstance(items,list) else items.count()]
        elif not isinstance(items,list):
            query = items
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
                        query = query.order(_order)
                    else:
                        order={'-id':'-__key__','id':'__key__'}.get(order,order)
                        query = query.order(order)

            if args_get('limitby', None):
                (lmin, lmax) = attributes['limitby']
                limit, fetch_args = lmax-lmin, {'offset':lmin,'keys_only':True}

                if self.use_ndb:
                    keys, cursor, more = query.fetch_page(limit,**fetch_args)
                    items = ndb.get_multi(keys)
                else:
                    keys =  query.fetch(limit, **fetch_args)
                    items = gae.get(keys)
                    cursor = query.cursor()
                #cursor is only useful if there was a limit and we didn't return
                # all results
                if args_get('reusecursor'):
                    db['_lastcursor'] = cursor
            else:
                # if a limit is not specified, always return an iterator
                items = query

        return (items, tablename, projection or db[tablename].fields)

    def select(self,query,fields,attributes):
        """
        This is the GAE version of select. Some notes to consider:
            - db['_lastsql'] is not set because there is not SQL statement string
                for a GAE query
            - 'nativeRef' is a magical fieldname used for self references on GAE
            - optional attribute 'projection' when set to True will trigger
                use of the GAE projection queries.  note that there are rules for
                what is accepted imposed by GAE: each field must be indexed,
                projection queries cannot contain blob or text fields, and you
                cannot use == and also select that same field.
                see https://developers.google.com/appengine/docs/python/datastore/queries#Query_Projection
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
                to follow google's limitations:
                https://developers.google.com/appengine/docs/python/datastore/queries#Query_Cursors
        """

        (items, tablename, fields) = self.select_raw(query,fields,attributes)
        # self.db['_lastsql'] = self._select(query,fields,attributes)
        rows = [[(t==self.db[tablename]._id.name and item) or \
                 (t=='nativeRef' and item) or getattr(item, t) \
                     for t in fields] for item in items]
        colnames = ['%s.%s' % (tablename, t) for t in fields]
        processor = attributes.get('processor',self.parse)
        return processor(rows,fields,colnames,False)

    def parse_list_integers(self, value, field_type):
        return value[:] if self.use_ndb else value

    def parse_list_strings(self, value, field_type):
        return value[:] if self.use_ndb else value

    def count(self,query,distinct=None,limit=None):
        if distinct:
            raise RuntimeError("COUNT DISTINCT not supported")
        (items, tablename, fields) = self.select_raw(query,count_only=True)
        return items[0]

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
