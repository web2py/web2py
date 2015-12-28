import cgi
import copy_reg
from gluon import current, URL, DAL
from gluon.storage import Storage
from gluon.utils import web2py_uuid
from gluon.sanitizer import sanitize

# ################################################################
# New HTML Helpers
# ################################################################

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

# ################################################################
# New XML Helpers
# ################################################################

class XML(TAG):
    """
    use it to wrap a string that contains XML/HTML so that it will not be
    escaped by the template

    Examples:

    >>> XML('<h1>Hello</h1>').xml()
    '<h1>Hello</h1>'
    """

    def __init__(
        self,
        text,
        sanitize=False,
        permitted_tags=[
            'a','b','blockquote','br/','i','li','ol','ul','p','cite',
            'code','pre','img/','h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'table', 'tr', 'td', 'div','strong', 'span'],
        allowed_attributes={
            'a': ['href', 'title', 'target'],
            'img': ['src', 'alt'],
            'blockquote': ['type'],
            'td': ['colspan']},
        ):
        """
        Args:
            text: the XML text
            sanitize: sanitize text using the permitted tags and allowed
                attributes (default False)
            permitted_tags: list of permitted tags (default: simple list of
                tags)
            allowed_attributes: dictionary of allowed attributed (default
                for A, IMG and BlockQuote).
                The key is the tag; the value is a list of allowed attributes.
        """

        if sanitize:
            text = sanitize(text, permitted_tags, allowed_attributes)
        if isinstance(text, unicode):
            text = text.encode('utf8', 'xmlcharrefreplace')
        elif not isinstance(text, str):
            text = str(text)
        self.text = text

    def xml(self):
        return self.text

    def __str__(self):
        return self.text

    def __add__(self, other):
        return '%s%s' % (self, other)

    def __radd__(self, other):
        return '%s%s' % (other, self)

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def __hash__(self):
        return hash(str(self))

    def __getitem__(self, i):
        return str(self)[i]

    def __getslice__(self, i, j):
        return str(self)[i:j]

    def __iter__(self):
        for c in str(self):
            yield c

    def __len__(self):
        return len(str(self))

def XML_unpickle(data):
    return XML(marshal.loads(data))

def XML_pickle(data):
    return XML_unpickle, (marshal.dumps(str(data)),)
copy_reg.pickle(XML, XML_pickle, XML_unpickle)

# ################################################################
# Simple Form Style Function (example for more complex styles)
# ################################################################

def FormStyleDefault(table, vars, errors, readonly, deletable):
    
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
        elif field.type == 'upload':
            control = DIV(INPUT(_type='file', _id=input_id, _name=field.name))
            if value:
                control.append(A('download',
                                 _href=URL('default','download',args=value)))
                control.append(INPUT(_type='checkbox',_value='ON',
                                     _name='_delete_'+field.name))
                control.append('(check to remove)')
        elif hasattr(field.requires, 'options'):
            multiple = field.type.startswith('list:')
            value = value if isinstance(value, list) else [value]
            options = [OPTION(v,_value=k,_selected=(k in value)) 
                       for k,v in field.requires.options()]
            control = SELECT(*options, _id=input_id, _name=field.name,
                              _multiple=multiple)
        else:
            field_type = 'password' if field.type == 'password' else 'text'
            control = INPUT(_type=field_type, _id=input_id, _name=field.name,
                            _value=value, _class=field_class)
            
        form[0].append(TR(TD(LABEL(field.label,_for=input_id)),
                          TD(control,DIV(error,_class='error') if error else ''),
                          TD(field.comment or '')))
        
    td = TD(INPUT(_type='submit',_value='Submit'))
    if deletable:
        td.append(INPUT(_type='checkbox',_value='ON',_name='_delete'))
        td.append('(check to delete)')
    form[0].append(TR(TD(),td,TD()))                         
    return form

# ################################################################
# Form object (replaced SQLFORM)
# ################################################################

class Form(object):
    """
    Usage in web2py controller:

       def index():
           form = Form(db.thing, record=1)
           if form.accepted: ...
           elif form.errors: ...
           else: ...
           return dict(form=form)
           
    Arguments:
    - table: a DAL table or a list of fields (equivalent to old SQLFORM.factory)
    - record: a DAL record or record id
    - readonly: set to True to make a readonly form
    - deletable: set to False to disallow deletion of record
    - formstyle: a function that renders the form using helpers (FormStyleDefault)
    - dbio: set to False to prevent any DB write
    - keepvalues: (NOT IMPLEMENTED)
    - formname: the optional name of this form
    - csrf: set to False to disable CRSF protection
    """
    
    def __init__(self,
                 table, 
                 record=None, 
                 readonly=False, 
                 deletable=True,
                 formstyle=FormStyleDefault, 
                 dbio=True,
                 keepvalues=False,
                 formname=False,
                 csrf=True):

        if isinstance(table, list):
            dbio = False
            # mimic a table from a list of fields without calling define_table
            formname = formname or 'none'
            for field in table: field.tablename = formname
 
        if isinstance(record, (int, long, basestring)):
            record_id = int(str(record))
            self.record = table[record_id]
        else:
            self.record = record

        self.table = table
        self.readonly = readonly
        self.deletable = deletable and not readonly and self.record
        self.formstyle = formstyle
        self.dbio = dbio
        self.keepvalues = True if keepvalues or self.record else False
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
            if self.record:
                self.vars = self.record
        else:
            print post_vars
            self.submitted = True            
            # check for CSRF
            if csrf and self.formname in (session._formkeys or {}):
                self.formkey = session._formkeys[self.formname]                
            # validate fields
            if not csrf or post_vars._formkey == self.formkey:
                if not post_vars._delete:
                    for field in self.table:
                        if field.writable:                            
                            value = post_vars.get(field.name)
                            (value, error) = field.validate(value)
                            if field.type == 'upload':
                                delete = post_vars.get('_delete_'+field.name)
                                if value is not None and hasattr(value,'file'):
                                    value = field.store(value.file, 
                                                        value.filename,
                                                        field.uploadfolder)
                                elif self.record and not delete:
                                    value = self.record.get(field.name)
                                else:
                                    value = None
                            self.vars[field.name] = value
                            if error:
                                self.errors[field.name] = error
                    if self.record:
                        self.vars.id = self.record.id
                    if not self.errors:
                        self.accepted = True
                        if dbio:
                            if self.record:
                                self.record.update_record(**self.vars)
                            else:
                                # warning, should we really insert if record
                                self.vars.id = self.table.insert(**self.vars)
                elif dbio:
                    self.deleted = True
                    self.record.delete_record()
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
                                           self.vars,
                                           self.errors,
                                           self.readonly,
                                           self.deletable)
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
    print(DIV(SPAN('this',STRONG('a test'),XML('1<2')),_id=1,_class="my class"))
