import json
from collections import OrderedDict
from gluon import URL, IS_SLUG

# compliant with https://github.com/collection-json/spec
# also compliant with http://code.ge/media-types/collection-next-json/

"""

Example controller:

def api():
    from gluon.contrib.hypermedia import Collection
    rules = {
        'thing': {
            'GET':{'query':None,'fields':['id', 'name']},
            'POST':{'query':None,'fields':['name']},
            'PUT':{'query':None,'fields':['name']},
            'DELETE':{'query':None},
            },
        'attr': {
            'GET':{'query':None,'fields':['id', 'name', 'thing']},
            'POST':{'query':None,'fields':['name', 'thing']},
            'PUT':{'query':None,'fields':['name', 'thing']},
            'DELETE':{'query':None},
            },
        }
    return Collection(db).process(request,response,rules)

"""

__all__ = ['Collection']

class Collection(object):

    VERSION = '1.0'
    MAXITEMS = 100

    def __init__(self,db, extensions=True, compact=False):
        self.db = db
        self.extensions = extensions
        self.compact = compact

    def row2data(self,table,row):
        """ converts a DAL Row object into a collection.item """
        data = []
        if self.compact:
            for fieldname in (self.table_rules.get('fields') or table.fields):
                field = table[fieldname]
                if not (field.type.startswith('reference ') or
                        field.type.startswith('list:reference ')) and field.name in row:
                    data.append(row[field.name])
        else:
            for fieldname in (self.table_rules.get('fields') or table.fields):
                field = table[fieldname]
                if not (field.type.startswith('reference ') or
                        field.type.startswith('list:reference ')) and field.name in row:
                    data.append({'name':field.name,'value':row[field.name],'prompt':field.label})
        return data

    def row2links(self,table,row):
        """ converts a DAL Row object into a set of links referencing the row """
        links = []
        for field in table._referenced_by:
            if field._tablename in self.rules:
                if row:
                    href = URL(args=field._tablename,vars={field.name:row.id},scheme=True)
                else:
                    href = URL(args=field._tablename,scheme=True)+'?%s={id}' % field.name
                links.append({'rel':str(field),'href':href,'prompt':str(field)})
        # should this be supported?
        for rel,build in (self.table_rules.get('links',{}).items()):
            links.append({'rel':rel,'href':build(row),'prompt':rel})
        # not sure
        return links

    def table2template(self,table):
        """ confeverts a table into its form template """
        data = []
        for fieldname in (self.table_rules['fields'] or table.fields):
            field = table[fieldname]
            info = {'name': field.name, 'value': '', 'prompt': field.label}
            rules = self.rules[table._tablename]
            # https://github.com/collection-json/extensions/blob/master/template-validation.md
            info['type'] = str(field.type) # FIX THIS
            if hasattr(field,'regexp_validator'):
                info['regexp'] = field.regexp_validator
            info['required'] = field.required
            info['post_writable'] = field.name in rules['POST']['fields']
            info['put_writable'] = field.name in rules['PUT']['fields']
            info['options'] = {} # FIX THIS
            data.append(info)
        return {'data':data}

    def request2query(self,table,vars):
        """ parses a request and converts it into a query """
        if len(self.request.args)>1:
            vars.id = self.request.args[1]

        fieldnames = table.fields
        queries = [table]
        limitby = [0,self.MAXITEMS+1]
        orderby = 'id'
        for key,value in vars.items():
            if key=='_offset':
                limitby[0] = int(value) # MAY FAIL
            elif key == '_limit': 
                limitby[1] = int(value)+1 # MAY FAIL
            elif key=='_orderby':
                orderby = value                
            elif key in fieldnames:
                queries.append(table[key] == value)
            elif key.endswith('.eq') and key[:-3] in fieldnames: # for completeness (useless)
                queries.append(table[key[:-3]] == value)
            elif key.endswith('.lt') and key[:-3] in fieldnames:
                queries.append(table[key[:-3]] < value)
            elif key.endswith('.le') and key[:-3] in fieldnames:
                queries.append(table[key[:-3]] <= value)
            elif key.endswith('.gt') and key[:-3] in fieldnames:
                queries.append(table[key[:-3]] > value)
            elif key.endswith('.ge') and key[:-3] in fieldnames:
                queries.append(table[key[:-3]] >= value)
            elif key.endswith('.contains') and key[:-9] in fieldnames:
                queries.append(table[key[:-9]].contains(value))
            elif key.endswith('.startswith') and key[:-11] in fieldnames:
                queries.append(table[key[:-11]].startswith(value))
            elif key.endswith('.ne') and key[:-3] in fieldnames:
                queries.append(table[key][:-3] != value)
            else:
                raise ValueError("Invalid Query")
        filter_query = self.table_rules.get('query')
        if filter_query:
            queries.append(filter_query)
        query = reduce(lambda a,b:a&b,queries[1:]) if len(queries)>1 else queries[0]
        orderby = [table[f] if f[0]!='~' else ~table[f[1:]] for f in orderby.split(',')]        
        return (query, limitby, orderby)

    def table2queries(self,table, href):
        """ generates a set of collection.queries examples for the table """
        data = []
        for fieldname in (self.table_rules.get('fields') or table.fields):
            data.append({'name':fieldname,'value':''}) 
            if self.extensions:
                data.append({'name':fieldname+'.ne','value':''}) # NEW !!!
                data.append({'name':fieldname+'.lt','value':''})
                data.append({'name':fieldname+'.le','value':''})
                data.append({'name':fieldname+'.gt','value':''})
                data.append({'name':fieldname+'.ge','value':''})
                if table[fieldname].type in ['string','text']:
                    data.append({'name':fieldname+'.contains','value':''})
                    data.append({'name':fieldname+'.startswith','value':''})
                data.append({'name':'_limitby','value':''})
                data.append({'name':'_offset','value':''})
                data.append({'name':'_orderby','value':''})
        return [{'rel' : 'search', 'href' : href, 'prompt' : 'Search', 'data' : data}]

    def process(self,request,response,rules=None):
        """ the main method, processes a request, filters by rules and produces a JSON response """
        self.request = request
        self.rules = rules
        db = self.db
        tablename = request.args(0)
        r = OrderedDict()
        r['version'] = self.VERSION
        tablenames = rules.keys() if rules else db.tables
        # if there is no tables
        if not tablename:
            r['href'] = URL(scheme=True),
            # https://github.com/collection-json/extensions/blob/master/model.md
            r['links'] = [{'rel' : t, 'href' : URL(args=t,scheme=True), 'model':t} 
                          for t in tablenames]
            response.headers['Content-Type'] = 'application/vnd.collection+json'
            return response.json({'collection':r})
        # or if the tablenames is invalid
        if not tablename in tablenames:
            return self.error(400,'BAD REQUEST','Invalid table name')
        # of if the method is invalid
        if not request.env.request_method in rules[tablename]:
            return self.error(400,'BAD REQUEST','Method not recognized')
        # get the rules
        self.table_rules = rules[tablename][request.env.request_method]
        # process GET
        if request.env.request_method=='GET':
            table = db[tablename]
            r['href'] = URL(args=tablename)        
            r['items'] = items = []
            try:
                (query, limitby, orderby) = self.request2query(table,request.get_vars)
                fields = [table[fn] for fn in (self.table_rules.get('fields') or table.fields)]
                fields = filter(lambda field: field.readable, fields)
                rows = db(query).select(*fields,**dict(limitby=limitby, orderby=orderby))
            except:
                db.rollback()
                return self.error(400,'BAD REQUEST','Invalid Query')
            r['items_found'] = db(query).count()
            delta = limitby[1]-limitby[0]-1
            r['links'] = self.row2links(table,None) if self.compact else []
            for row in rows[:delta]:
                id = row.id
                for name in ('slug','fullname','title','name'):
                    if name in row:
                        href = URL(args=(tablename,id,IS_SLUG.urlify(row[name])),scheme=True)
                        break
                else:
                    href = URL(args=(tablename,id),scheme=True)
                if self.compact:
                    items.append(self.row2data(table,row))
                else:
                    items.append({
                            'href':href,
                            'data':self.row2data(table,row),
                            'links':self.row2links(table,row)
                            });
            if self.extensions and len(rows)>delta:
                vars = dict(request.get_vars)
                vars['_offset'] = limitby[1]-1
                vars['_limit'] = limitby[1]-1+delta
                r['links'].append({'rel':'next',
                                   'href':URL(args=request.args,vars=vars,scheme=True)})
            data = []
            if not self.compact:
                r['queries'] = self.table2queries(table, r['href'])
            r['template'] = self.table2template(table)
            response.headers['Content-Type'] = 'application/vnd.collection+json'
            return response.json({'collection':r})
        # process DELETE
        elif request.env.request_method=='DELETE':
            table = db[tablename] 
            if not request.get_vars:
                return self.error(400, "BAD REQUEST", "Nothing to delete")
            else:
                try:
                    (query, limitby, orderby) = self.request2query(table, request.vars)
                    n = db(query).delete() # MAY FAIL
                    response.status = '204'
                    return ''
                except:
                    db.rollback()
                    return self.error(400,'BAD REQUEST','Invalid Query')
            return response.json(r)
        # process POST and PUT (on equal footing!)
        elif request.env.request_method in ('POST','PUT'): # we treat them the same!
            table = db[tablename] 
            if not request.post_vars:
                body = request.body().read()
                if body:
                    try:
                        body = json.loads(data) # MAY FAIL                         
                        request.post_vars = dict((i['name'],i['value']) for i in body.data)
                    except:
                        return self.error(400,'BAD REQUEST','Invalid body')
                    request.vars.update(request.post_vars)                    
            if request.get_vars or len(request.args)>1: # update
                # ADD validate fields and return error
                try:
                    (query, limitby, orderby) = self.request2query(table, request.get_vars)
                    fields = filter(lambda (fn,value):table[fn].writable,request.post_vars.items())
                    n = db(query).update(**dict(fields)) # MAY FAIL
                    response.status = '200'
                    return ''
                except:
                    db.rollback()
                    return self.error(400,'BAD REQUEST','Invalid Query')
            else: # create
                # ADD validate fields and return error
                try:
                    fields = filter(lambda (fn,value):table[fn].writable,request.post_vars.items())
                    id = table.insert(**dict(fields)) # MAY FAIL
                    response.status = '201'
                    response.headers['location'] = URL(args=(tablename,id),scheme=True)
                    return ''
                except:
                    db.rollback()
                    return self.error(400,'BAD REQUEST','Invalid Query')

    def error(self,code="400", title="BAD REQUEST", message="UNKNOWN", form_errors={}):
        r = DefaultDict({
                "version" : self.VERSION,
                "href" : URL(args=request.args,vars=request.vars),    
                "error" : {
                    "title" : title,
                    "code" : code,
                    "message" : message}})
        if self.extensions and form_errors:
            # https://github.com/collection-json/extensions/blob/master/errors.md
            r['errors'] = errors = {}
            for key, value in form_errors:
                errors[key] = [{'title':'Validation Error','code':'','message':value}]
                response.headers['Content-Type'] = 'application/vnd.collection+json'
        response.status = '400'
        return response.json({'collection':r})

example_rules = {
    'thing': {
        'GET':{'query':None,'fields':['id', 'name']},
        'POST':{'query':None,'fields':['name']},
        'PUT':{'query':None,'fields':['name']},
        'DELETE':{'query':None},
        },
    'attr': {
        'GET':{'query':None,'fields':['id', 'name', 'thing']},
        'POST':{'query':None,'fields':['name', 'thing']},
        'PUT':{'query':None,'fields':['name', 'thing']},
        'DELETE':{'query':None},
        },
    }

