from gluon.dal import DAL
from gluon.storage import Storage
from gluon.utils import web2py_uuid
try:
    # web3py
    from gluon.current import current
    from gluon.url import URL
    from gluon.helpers import *
except:
    # web2py
    from gluon import current
    from gluon.html import *



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
                 hidden=None,
                 csrf=True):

        if isinstance(table, list):
            dbio = False
            # mimic a table from a list of fields without calling define_table
            formname = formname or 'none'
            for field in table: field.tablename = getattr(field,'tablename',formname)

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
        self.hidden = hidden
        self.formkey = None

        request = current.request

        if readonly or request.method=='GET':
            if self.record:
                self.vars = self.record
        else:
            post_vars = request.post_vars
            print post_vars
            self.submitted = True
            # check for CSRF
            if csrf and self.formname in (current.session._formkeys or {}):
                self.formkey = current.session._formkeys[self.formname]
            # validate fields
            if not csrf or post_vars._formkey == self.formkey:
                if not post_vars._delete:
                    for field in self.table:
                        if field.writable:
                            value = post_vars.get(field.name)
                            # FIX THIS deal with set_self_id before validate
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
                            self.update_or_insert()
                elif dbio:
                    self.deleted = True
                    self.record.delete_record()
        # store key for future CSRF
        if csrf:
            session = current.session
            if not session._formkeys:
                session._formkeys = {}
            if self.formname not in current.session._formkeys:
                session._formkeys[self.formname] = web2py_uuid()
            self.formkey = session._formkeys[self.formname]

    def update_or_insert(self):
        if self.record:
            self.record.update_record(**self.vars)
        else:
            # warning, should we really insert if record
            self.vars.id = self.table.insert(**self.vars)

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
            for key in self.hidden or {}:
                cached_helper.append(INPUT(_type='hidden',_name=key,
                                           _value=self.hidden[key]))
            self.cached_helper = cached_helper
        return cached_helper

    def xml(self):
        return self.helper().xml()

    def __unicode__(self):
        return self.xml()

    def __str__(self):
        return self.xml().encode('utf8')
