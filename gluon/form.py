import cgi
from gluon import current
from gluon.storage import Storage
from gluon.utils import web2py_uuid

def xmlescape(text):
    return cgi.escape(text, True).replace("'", "&#x27;")

class TAG(object):    

    def __init__(self, name, *children, **attributes):
        self.name = name
        self.children = list(children)
        self.attributes = attributes
        for child in self.children:
            if isinstance(child, TAG):
                child.parent = self

    def xml(self):
        name = self.name
        a = ' '.join('%s="%s"' % 
                     (k[1:], k[1:] if v is True else xmlescape(unicode(v)))
                     for k,v in self.attributes.iteritems() 
                     if k.startswith('_') and not v in (False,None))
        if a:
            a = ' '+a
        if name.endswith('/'):
            return '<%s%s/>' % (name, a)
        else:
            b = ''.join(s.xml() if isinstance(s,TAG) else xmlescape(unicode(s))
                        for s in self.children)
            return '<%s%s>%s</%s>' %(name, a, b, name)
            
    def __unicode__(self):
        return self.xml()

    def __str__(self):
        return self.xml().encode('utf8')

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.children[key]
        else:
            return self.attributes[key]

    def __setitem__(self, key, value):
        if isinstance(key, int):
            self.children[key] = value
        else:
            self.attributes[key] =  value

    def append(self, value):
        self.children.append(value)

    def __delitem__(self,key):
        if isinstance(key, int):
            self.children = self.children[:key]+self.children[key+1:]
        else:
            del self.attributes[key]

    def __len__(self):
        return len(self.children)

    def find(self, query):
        raise NotImplementedError

class METATAG(object):

    def __getattr__(self, name):
        return self(name)

    def __call__(self, name):
        return lambda *children, **attributes: TAG(name, *children, **attributes)

tag = METATAG()

DIV = tag('div')
SPAN = tag('span')
LI = tag('li')
OL = tag('ol')
UL = tag('ul')
A  = tag('a')
H1 = tag('h1')
H2 = tag('h2')
H3 = tag('h3')
H4 = tag('h4')
H5 = tag('h5')
H6 = tag('h6')
EM = tag('em')
TR = tag('tr')
TD = tag('td')
TH = tag('th')
IMG = tag('img/')
FORM = tag('form')
HEAD = tag('head')
BODY = tag('body')
TABLE = tag('table')
INPUT = tag('input/')
LABEL = tag('label')
STRONG = tag('strong')
SELECT = tag('select')
OPTION = tag('option')
TEXTAREA = tag('textarea')

def FormStyleDefault(table, readonly, vars, errors):

    form = FORM(TABLE(),_method='POST',_action='#',_enctype='multipart/form-data')
    for field in table:
        
        input_id = '%s_%s' % (field.tablename, field.name)        
        value = field.formatter(vars.get(field.name))
        error = errors.get(field.name)
        field_class = field.type.split()[0].replace(':','-')

        if field.type == 'blob': # never display blobs (mistake?)
            continue
        elif readonly or field.type=='id':
            if not field.readable:
                continue
            else:
                control = field.represent and field.represent(value) or value or ''
        elif not field.writable:
            continue
        elif field.widget:
            control = field.widget(table, value)
        elif field.type == 'text':
            control = TEXTAREA(value or '', _id=input_id,_name=field.name)
        elif field.type == 'boolean':
            control = INPUT(_type='checkbox', _id=input_id, _name=field.name,
                            _value='ON', _checked = value)
        else:
            field_type = 'password' if field.type == 'password' else 'text'
            control = INPUT(_type=field_type, _id=input_id, _name=field.name,
                            _value=value, _class=field_class)

        form[0].append(TR(TD(LABEL(field.label,_for=input_id)),
                          TD(control,DIV(error,_class='error') if error else ''),
                          TD(field.comment or '')))

    form[0].append(TR(TD(),TD(INPUT(_type='submit')),TD()))
    return form

class Form(object):
    def __init__(self,
                 table, 
                 record_id=None, 
                 readonly=False, 
                 formstyle=FormStyleDefault, 
                 dbio=True,
                 keepvalues=False,
                 formname=False,
                 csrf=True):

        if record_id is None:
            self.record_id = self.record = None
        else:
            try:
                self.record_id, self.record = int(record_id), None
            except TypeError:
                self.record_id, self.record = record_id.id, record_id
            
        self.table = table
        self.readonly = readonly
        self.formstyle = formstyle
        self.dbio = dbio
        self.keepvalues = True if keepvalues or self.record_id else False
        self.csrf = csrf
        self.vars = Storage()
        self.errors = Storage()
        self.submitted = False
        self.deleted = False
        self.accepted = False
        self.cached_helper = False
        self.formname = formname or table._tablename
        self.formkey = None

        request = current.request
        session = current.session
        post_vars = request.post_vars

        if readonly or request.env.request_method=='GET':
            if self.record_id:
                if not self.record:
                    self.record = self.table[self.record_id]
                if self.record:
                    self.vars = self.record
        else:
            self.subitted = True            
            # check for CSRF
            if csrf and self.formname in (session._formkeys or {}):
                self.formkey = session._formkeys[self.formname]                
            # validate fields
            if not csrf or post_vars._formkey == self.formkey:
                for field in self.table:
                    if field.writable:                    
                        value = post_vars.get(field.name)
                        (value, error) = field.validate(value)
                        if value:
                            self.vars[field.name] = value
                            if error:
                                self.errors[field.name] = error
                if not self.errors:
                    self.accepted = True
                    if dbio:
                        n_rec = 0
                        if self.record_id:
                            query = table._id==self.record_id
                            n_rec = table._db(query).update(**self.vars)
                        if n_rec == 0:
                            # warning, should we really insert if record_id
                            self.vars.id = self.table.insert(**self.vars)
        # store key for future CSRF
        if csrf:
            if not session._formkeys:
                session._formkeys = {}
            if self.formname not in session._formkeys:
                session._formkeys[self.formname] = web2py_uuid()
            self.formkey = session._formkeys[self.formname]

    def clear():
        self.vars.clear()
        self.errors.clear()
        for field in self.table:
            self.vars[field.name] = field.default

    def helper(self):
        if not self.cached_helper:
            cached_helper = self.formstyle(self.table, 
                                           self.readonly,
                                           self.vars,
                                           self.errors)
            if self.csrf:
                cached_helper.append(INPUT(_type='hidden',_name='_formkey',
                                           _value=self.formkey))
            self.cached_helper = cached_helper
        return cached_helper

    def xml(self):
        return self.helper().xml()

    def __unicode__(self):
        return self.xml()

    def __str__(self):
        return self.xml().encode('utf8')
    
if __name__=='__main__':
    print(DIV(SPAN('this',STRONG('a test')),_id=1,_class="my class"))
