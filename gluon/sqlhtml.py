#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Holds:

- SQLFORM: provide a form for a table (with/without record)
- SQLTABLE: provides a table for a set of records
- form_factory: provides a SQLFORM for an non-db backed table

"""
try:
    from urlparse import parse_qs as psq
except ImportError:
    from cgi import parse_qs as psq
import os
from http import HTTP
from html import XML, SPAN, TAG, A, DIV, CAT, UL, LI, TEXTAREA, BR, IMG, SCRIPT
from html import FORM, INPUT, LABEL, OPTION, SELECT, BUTTON
from html import TABLE, THEAD, TBODY, TR, TD, TH, STYLE
from html import URL, truncate_string, FIELDSET
from dal import DAL, Field, Table, Row, CALLABLETYPES, smart_query, \
    bar_encode, Reference, REGEX_TABLE_DOT_FIELD
from storage import Storage
from utils import md5_hash
from validators import IS_EMPTY_OR, IS_NOT_EMPTY, IS_LIST_OF, IS_DATE, \
    IS_DATETIME, IS_INT_IN_RANGE, IS_FLOAT_IN_RANGE

import datetime
import urllib
import re
import cStringIO
from gluon import current, redirect, A, URL, DIV, H3, UL, LI, SPAN, INPUT
import inspect
import settings
is_gae = settings.global_settings.web2py_runtime_gae

table_field = re.compile('[\w_]+\.[\w_]+')
widget_class = re.compile('^\w*')

def trap_class(_class=None,trap=True):
    return (trap and 'w2p_trap' or '')+(_class and ' '+_class or '')

def represent(field,value,record):
    f = field.represent
    if not callable(f):
        return str(value)
    n = f.func_code.co_argcount-len(f.func_defaults or [])
    if getattr(f, 'im_self', None): n -= 1
    if n==1:
        return f(value)
    elif n==2:
        return f(value,record)
    else:
        raise RuntimeError, "field representation must take 1 or 2 args"

def safe_int(x):
    try:
        return int(x)
    except ValueError:
        return 0

def safe_float(x):
    try:
        return float(x)
    except ValueError:
        return 0

class FormWidget(object):
    """
    helper for SQLFORM to generate form input fields
    (widget), related to the fieldtype
    """

    _class = 'generic-widget'

    @classmethod
    def _attributes(cls, field,
                    widget_attributes, **attributes):
        """
        helper to build a common set of attributes

        :param field: the field involved,
                      some attributes are derived from this
        :param widget_attributes:  widget related attributes
        :param attributes: any other supplied attributes
        """
        attr = dict(
            _id = '%s_%s' % (field._tablename, field.name),
            _class = cls._class or \
                widget_class.match(str(field.type)).group(),
            _name = field.name,
            requires = field.requires,
            )
        attr.update(widget_attributes)
        attr.update(attributes)
        return attr

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates the widget for the field.

        When serialized, will provide an INPUT tag:

        - id = tablename_fieldname
        - class = field.type
        - name = fieldname

        :param field: the field needing the widget
        :param value: value
        :param attributes: any other attributes to be applied
        """

        raise NotImplementedError

class StringWidget(FormWidget):
    _class = 'string'

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates an INPUT text tag.

        see also: :meth:`FormWidget.widget`
        """

        default = dict(
            _type = 'text',
            value = (not value is None and str(value)) or '',
            )
        attr = cls._attributes(field, default, **attributes)

        return INPUT(**attr)


class IntegerWidget(StringWidget):
    _class = 'integer'


class DoubleWidget(StringWidget):
    _class = 'double'


class DecimalWidget(StringWidget):
    _class = 'decimal'


class TimeWidget(StringWidget):
    _class = 'time'


class DateWidget(StringWidget):
    _class = 'date'


class DatetimeWidget(StringWidget):
    _class = 'datetime'


class TextWidget(FormWidget):
    _class = 'text'

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates a TEXTAREA tag.

        see also: :meth:`FormWidget.widget`
        """

        default = dict(value = value)
        attr = cls._attributes(field, default,
                               **attributes)
        return TEXTAREA(**attr)


class BooleanWidget(FormWidget):
    _class = 'boolean'

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates an INPUT checkbox tag.

        see also: :meth:`FormWidget.widget`
        """

        default=dict(_type='checkbox', value=value)
        attr = cls._attributes(field, default,
                               **attributes)
        return INPUT(**attr)


class OptionsWidget(FormWidget):

    @staticmethod
    def has_options(field):
        """
        checks if the field has selectable options

        :param field: the field needing checking
        :returns: True if the field has options
        """

        return hasattr(field.requires, 'options')

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates a SELECT tag, including OPTIONs (only 1 option allowed)

        see also: :meth:`FormWidget.widget`
        """
        default = dict(value=value)
        attr = cls._attributes(field, default,
                               **attributes)
        requires = field.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        if requires:
            if hasattr(requires[0], 'options'):
                options = requires[0].options()
            else:
                raise SyntaxError, 'widget cannot determine options of %s' % field
        opts = [OPTION(v, _value=k) for (k, v) in options]

        return SELECT(*opts, **attr)

class ListWidget(StringWidget):

    @classmethod
    def widget(cls, field, value, **attributes):
        _id = '%s_%s' % (field._tablename, field.name)
        _name = field.name
        if field.type=='list:integer': _class = 'integer'
        else: _class = 'string'
        requires = field.requires if isinstance(field.requires, (IS_NOT_EMPTY, IS_LIST_OF)) else None
        attributes['_style'] = 'list-style:none'
        items=[LI(INPUT(_id=_id, _class=_class, _name=_name,
                        value=v, hideerror=True, requires=requires),
                  **attributes)  for v in value or ['']]
        script=SCRIPT("""
// from http://refactormycode.com/codes/694-expanding-input-list-using-jquery
(function(){
jQuery.fn.grow_input = function() {
  return this.each(function() {
    var ul = this;
    jQuery(ul).find(":text").after('<a href="javascript:void(0)">+</a>').keypress(function (e) { return (e.which == 13) ? pe(ul) : true; }).next().click(function(){ pe(ul) });
  });
};
function pe(ul) {
  var new_line = ml(ul);
  rel(ul);
  new_line.appendTo(ul);
  new_line.find(":text").focus();
  return false;
}
function ml(ul) {
  var line = jQuery(ul).find("li:first").clone(true);
  line.find(':text').val('');
  return line;
}
function rel(ul) {
  jQuery(ul).find("li").each(function() {
    var trimmed = jQuery.trim(jQuery(this.firstChild).val());
    if (trimmed=='') jQuery(this).remove(); else jQuery(this.firstChild).val(trimmed);
  });
}
})();
jQuery(document).ready(function(){jQuery('#%s_grow_input').grow_input();});
""" % _id)
        attributes['_id'] = _id+'_grow_input'
        attributes['_style'] = 'list-style:none'
        return TAG[''](UL(*items,**attributes),script)


class MultipleOptionsWidget(OptionsWidget):

    @classmethod
    def widget(cls, field, value, size=5, **attributes):
        """
        generates a SELECT tag, including OPTIONs (multiple options allowed)

        see also: :meth:`FormWidget.widget`

        :param size: optional param (default=5) to indicate how many rows must
            be shown
        """

        attributes.update(_size=size, _multiple=True)

        return OptionsWidget.widget(field, value, **attributes)


class RadioWidget(OptionsWidget):

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates a TABLE tag, including INPUT radios (only 1 option allowed)

        see also: :meth:`FormWidget.widget`
        """

        attr = cls._attributes(field, {}, **attributes)
        attr['_class'] = attr.get('_class','web2py_radiowidget')

        requires = field.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        if requires:
            if hasattr(requires[0], 'options'):
                options = requires[0].options()
            else:
                raise SyntaxError, 'widget cannot determine options of %s' \
                    % field
        options = [(k, v) for k, v in options if str(v)]
        opts = []
        cols = attributes.get('cols',1)
        totals = len(options)
        mods = totals%cols
        rows = totals/cols
        if mods:
            rows += 1

        #widget style
        wrappers = dict(
            table=(TABLE,TR,TD),
            ul=(DIV,UL,LI),
            divs=(CAT,DIV,DIV)
            )
        parent, child, inner = wrappers[attributes.get('style','table')]

        for r_index in range(rows):
            tds = []
            for k, v in options[r_index*cols:(r_index+1)*cols]:
                checked={'_checked':'checked'} if k==value else {}
                tds.append(inner(INPUT(_type='radio',
                                       _id='%s%s' % (field.name,k),
                                       _name=field.name,
                                       requires=attr.get('requires',None),
                                       hideerror=True, _value=k,
                                       value=value,
                                       **checked),
                                       LABEL(v,_for='%s%s' % (field.name,k))))
            opts.append(child(tds))

        if opts:
            opts[-1][0][0]['hideerror'] = False
        return parent(*opts, **attr)


class CheckboxesWidget(OptionsWidget):

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates a TABLE tag, including INPUT checkboxes (multiple allowed)

        see also: :meth:`FormWidget.widget`
        """

        # was values = re.compile('[\w\-:]+').findall(str(value))
        if isinstance(value, (list, tuple)):
            values = [str(v) for v in value]
        else:
            values = [str(value)]

        attr = cls._attributes(field, {}, **attributes)
        attr['_class'] = attr.get('_class','web2py_checkboxeswidget')

        requires = field.requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        if requires:
            if hasattr(requires[0], 'options'):
                options = requires[0].options()
            else:
                raise SyntaxError, 'widget cannot determine options of %s' \
                    % field

        options = [(k, v) for k, v in options if k != '']
        opts = []
        cols = attributes.get('cols', 1)
        totals = len(options)
        mods = totals % cols
        rows = totals / cols
        if mods:
            rows += 1

        #widget style
        wrappers = dict(
            table=(TABLE,TR,TD),
            ul=(DIV,UL,LI),
            divs=(CAT,DIV,DIV)
            )
        parent, child, inner = wrappers[attributes.get('style','table')]

        for r_index in range(rows):
            tds = []
            for k, v in options[r_index*cols:(r_index+1)*cols]:
                if k in values:
                    r_value = k
                else:
                    r_value = []
                tds.append(inner(INPUT(_type='checkbox',
                                       _id='%s%s' % (field.name,k),
                                       _name=field.name,
                                       requires=attr.get('requires', None),
                                       hideerror=True, _value=k,
                                       value=r_value),
                                       LABEL(v,_for='%s%s' % (field.name,k))))
            opts.append(child(tds))


        if opts:
            opts.append(INPUT(_class="hidden", requires=attr.get('requires', None),
                              _disabled="disabled", _name=field.name,
                              hideerror=False))
        return parent(*opts, **attr)


class PasswordWidget(FormWidget):
    _class = 'password'

    DEFAULT_PASSWORD_DISPLAY = 8*('*')

    @classmethod
    def widget(cls, field, value, **attributes):
        """
        generates a INPUT password tag.
        If a value is present it will be shown as a number of '*', not related
        to the length of the actual value.

        see also: :meth:`FormWidget.widget`
        """

        default=dict(
            _type='password',
            _value=(value and cls.DEFAULT_PASSWORD_DISPLAY) or '',
            )
        attr = cls._attributes(field, default, **attributes)

        return INPUT(**attr)


class UploadWidget(FormWidget):
    _class = 'upload'

    DEFAULT_WIDTH = '150px'
    ID_DELETE_SUFFIX = '__delete'
    GENERIC_DESCRIPTION = 'file'
    DELETE_FILE = 'delete'

    @classmethod
    def widget(cls, field, value, download_url=None, **attributes):
        """
        generates a INPUT file tag.

        Optionally provides an A link to the file, including a checkbox so
        the file can be deleted.
        All is wrapped in a DIV.

        see also: :meth:`FormWidget.widget`

        :param download_url: Optional URL to link to the file (default = None)
        """

        default=dict(_type='file',)
        attr = cls._attributes(field, default, **attributes)

        inp = INPUT(**attr)

        if download_url and value:
            if callable(download_url):
                url = download_url(value)
            else:
                url = download_url + '/' + value
            (br, image) = ('', '')
            if UploadWidget.is_image(value):
                br = BR()
                image = IMG(_src = url, _width = cls.DEFAULT_WIDTH)

            requires = attr["requires"]
            if requires == [] or isinstance(requires, IS_EMPTY_OR):
                inp = DIV(inp, '[',
                          A(current.T(UploadWidget.GENERIC_DESCRIPTION), _href = url),
                          '|',
                          INPUT(_type='checkbox',
                                _name=field.name + cls.ID_DELETE_SUFFIX,
                                _id=field.name + cls.ID_DELETE_SUFFIX),
                                LABEL(current.T(cls.DELETE_FILE),
                                     _for=field.name + cls.ID_DELETE_SUFFIX),
                                ']', br, image)
            else:
                inp = DIV(inp, '[',
                          A(cls.GENERIC_DESCRIPTION, _href = url),
                          ']', br, image)
        return inp

    @classmethod
    def represent(cls, field, value, download_url=None):
        """
        how to represent the file:

        - with download url and if it is an image: <A href=...><IMG ...></A>
        - otherwise with download url: <A href=...>file</A>
        - otherwise: file

        :param field: the field
        :param value: the field value
        :param download_url: url for the file download (default = None)
        """

        inp = cls.GENERIC_DESCRIPTION

        if download_url and value:
            if callable(download_url):
                url = download_url(value)
            else:
                url = download_url + '/' + value
            if cls.is_image(value):
                inp = IMG(_src = url, _width = cls.DEFAULT_WIDTH)
            inp = A(inp, _href = url)

        return inp

    @staticmethod
    def is_image(value):
        """
        Tries to check if the filename provided references to an image

        Checking is based on filename extension. Currently recognized:
           gif, png, jp(e)g, bmp

        :param value: filename
        """

        extension = value.split('.')[-1].lower()
        if extension in ['gif', 'png', 'jpg', 'jpeg', 'bmp']:
            return True
        return False


class AutocompleteWidget(object):
    _class = 'string'

    def __init__(self, request, field, id_field=None, db=None,
                 orderby=None, limitby=(0,10), distinct=False,
                 keyword='_autocomplete_%(tablename)s_%(fieldname)s',
                 min_length=2, help_fields=None, help_string=None):

        self.help_fields = help_fields or []
        self.help_string = help_string
        if self.help_fields and not self.help_string:
            self.help_string = ' '.join('%%(%s)s' for f in self.help_fields)

        self.request = request
        self.keyword = keyword % dict(tablename=field.tablename,
                                      fieldname=field.name)
        self.db = db or field._db
        self.orderby = orderby
        self.limitby = limitby
        self.distinct = distinct
        self.min_length = min_length
        self.fields=[field]
        if id_field:
            self.is_reference = True
            self.fields.append(id_field)
        else:
            self.is_reference = False
        if hasattr(request,'application'):
            self.url = URL(args=request.args)
            self.callback()
        else:
            self.url = request

    def callback(self):
        if self.keyword in self.request.vars:
            field = self.fields[0]
            if is_gae:
                rows = self.db(field.__ge__(self.request.vars[self.keyword])&field.__lt__(self.request.vars[self.keyword]+ u'\ufffd')).select(orderby=self.orderby,limitby=self.limitby,*self.fields)
            else:
                rows = self.db(field.like(self.request.vars[self.keyword]+'%')).select(orderby=self.orderby,limitby=self.limitby,distinct=self.distinct,*self.fields)
            if rows:
                if self.is_reference:
                    id_field = self.fields[1]
                    if self.help_fields:
                        options = [OPTION(self.help_string % dict([(h.name,s[h.name]) for h in self.fields[:1]+self.help_fields]),
                                          _value=s[id_field.name], _selected=(k==0)) for k,s in enumerate(rows)]
                    else:
                        options = [OPTION(s[field.name],_value=s[id_field.name],
                                          _selected=(k==0)) for k,s in enumerate(rows)]
                    raise HTTP(200,SELECT(_id=self.keyword,_class='autocomplete',
                                          _size=len(rows),_multiple=(len(rows)==1),
                                          *options).xml())
                else:
                    raise HTTP(200,SELECT(_id=self.keyword,_class='autocomplete',
                                          _size=len(rows),_multiple=(len(rows)==1),
                                          *[OPTION(s[field.name],
                                                   _selected=(k==0)) \
                                                for k,s in enumerate(rows)]).xml())
            else:
                raise HTTP(200,'')

    def __call__(self,field,value,**attributes):
        default = dict(
            _type = 'text',
            value = (not value is None and str(value)) or '',
            )
        attr = StringWidget._attributes(field, default, **attributes)
        div_id = self.keyword+'_div'
        attr['_autocomplete']='off'
        if self.is_reference:
            key2 = self.keyword+'_aux'
            key3 = self.keyword+'_auto'
            attr['_class']='string'
            name = attr['_name']
            if 'requires' in attr: del attr['requires']
            attr['_name'] = key2
            value = attr['value']
            record = self.db(self.fields[1]==value).select(self.fields[0]).first()
            attr['value'] = record and record[self.fields[0].name]
            attr['_onblur']="jQuery('#%(div_id)s').delay(1000).fadeOut('slow');" % \
                dict(div_id=div_id,u='F'+self.keyword)
            attr['_onkeyup'] = "jQuery('#%(key3)s').val('');var e=event.which?event.which:event.keyCode; function %(u)s(){jQuery('#%(id)s').val(jQuery('#%(key)s :selected').text());jQuery('#%(key3)s').val(jQuery('#%(key)s').val())}; if(e==39) %(u)s(); else if(e==40) {if(jQuery('#%(key)s option:selected').next().length)jQuery('#%(key)s option:selected').attr('selected',null).next().attr('selected','selected'); %(u)s();} else if(e==38) {if(jQuery('#%(key)s option:selected').prev().length)jQuery('#%(key)s option:selected').attr('selected',null).prev().attr('selected','selected'); %(u)s();} else if(jQuery('#%(id)s').val().length>=%(min_length)s) jQuery.get('%(url)s?%(key)s='+escape(jQuery('#%(id)s').val()),function(data){if(data=='')jQuery('#%(key3)s').val('');else{jQuery('#%(id)s').next('.error').hide();jQuery('#%(div_id)s').html(data).show().focus();jQuery('#%(div_id)s select').css('width',jQuery('#%(id)s').css('width'));jQuery('#%(key3)s').val(jQuery('#%(key)s').val());jQuery('#%(key)s').change(%(u)s);jQuery('#%(key)s').click(%(u)s);};}); else jQuery('#%(div_id)s').fadeOut('slow');" % \
                dict(url=self.url,min_length=self.min_length,
                     key=self.keyword,id=attr['_id'],key2=key2,key3=key3,
                     name=name,div_id=div_id,u='F'+self.keyword)
            if self.min_length==0:
                attr['_onfocus'] = attr['_onkeyup']
            return TAG[''](INPUT(**attr),INPUT(_type='hidden',_id=key3,_value=value,
                                               _name=name,requires=field.requires),
                           DIV(_id=div_id,_style='position:absolute;'))
        else:
            attr['_name']=field.name
            attr['_onblur']="jQuery('#%(div_id)s').delay(1000).fadeOut('slow');" % \
                dict(div_id=div_id,u='F'+self.keyword)
            attr['_onkeyup'] = "var e=event.which?event.which:event.keyCode; function %(u)s(){jQuery('#%(id)s').val(jQuery('#%(key)s').val())}; if(e==39) %(u)s(); else if(e==40) {if(jQuery('#%(key)s option:selected').next().length)jQuery('#%(key)s option:selected').attr('selected',null).next().attr('selected','selected'); %(u)s();} else if(e==38) {if(jQuery('#%(key)s option:selected').prev().length)jQuery('#%(key)s option:selected').attr('selected',null).prev().attr('selected','selected'); %(u)s();} else if(jQuery('#%(id)s').val().length>=%(min_length)s) jQuery.get('%(url)s?%(key)s='+escape(jQuery('#%(id)s').val()),function(data){jQuery('#%(id)s').next('.error').hide();jQuery('#%(div_id)s').html(data).show().focus();jQuery('#%(div_id)s select').css('width',jQuery('#%(id)s').css('width'));jQuery('#%(key)s').change(%(u)s);jQuery('#%(key)s').click(%(u)s);}); else jQuery('#%(div_id)s').fadeOut('slow');" % \
                dict(url=self.url,min_length=self.min_length,
                     key=self.keyword,id=attr['_id'],div_id=div_id,u='F'+self.keyword)
            if self.min_length==0:
                attr['_onfocus'] = attr['_onkeyup']
            return TAG[''](INPUT(**attr),DIV(_id=div_id,_style='position:absolute;'))

def formstyle_table3cols(form, fields):
    ''' 3 column table - default '''
    table = TABLE()
    for id, label, controls, help in fields:
        _help = TD(help, _class='w2p_fc')
        _controls = TD(controls, _class='w2p_fw')
        _label = TD(label, _class='w2p_fl')
        table.append(TR(_label, _controls, _help, _id=id))
    return table

def formstyle_table2cols(form, fields):
    ''' 2 column table '''
    table = TABLE()
    for id, label, controls, help in fields:
        _help = TD(help, _class='w2p_fc', _width='50%')
        _controls = TD(controls, _class='w2p_fw', _colspan='2')
        _label = TD(label, _class='w2p_fl', _width='50%')
        table.append(TR(_label, _help,  _id=id+'1', _class='even'))
        table.append(TR(_controls, _id=id+'2', _class='odd'))
    return table

def formstyle_divs(form, fields):
    ''' divs only '''
    table = TAG['']()
    for id, label, controls, help in fields:
        _help = DIV(help, _class='w2p_fc')
        _controls = DIV(controls, _class='w2p_fw')
        _label = DIV(label, _class='w2p_fl')
        table.append(DIV(_label, _controls, _help, _id=id))
    return table

def formstyle_ul(form, fields):
    ''' unordered list '''
    table = UL()
    for id, label, controls, help in fields:
        _help = DIV(help, _class='w2p_fc')
        _controls = DIV(controls, _class='w2p_fw')
        _label = DIV(label, _class='w2p_fl')
        table.append(LI(_label, _controls, _help, _id=id))
    return table

def formstyle_bootstrap(form, fields):
    ''' bootstrap format form layout '''
    form['_class'] = 'form-horizontal'
    parent = FIELDSET()
    for id, label, controls, help in fields:
        # wrappers
        _help = SPAN(help, _class='help-inline')
        # embed _help into _controls
        _controls = DIV(controls, _help, _class='controls')
        # submit unflag by default
        _submit = False

        if isinstance(controls, INPUT):
            controls.add_class('input-xlarge')
            if controls['_type'] == 'submit':
                # flag submit button
                _submit = True
                controls['_class'] = 'btn btn-primary'

        if isinstance(controls, SELECT):
            controls.add_class('input-xlarge')

        if isinstance(controls, TEXTAREA):
            controls.add_class('input-xlarge')

        if isinstance(label, LABEL):
            label['_class'] = 'control-label'

        if _submit:
            # submit button has unwrapped label and controls, different class
            parent.append(DIV(label, controls, _class='form-actions'))
            # unflag submit (possible side effect)
            _submit = False
        else:
            # unwrapped label
            parent.append(DIV(label, _controls, _class='control-group'))
    return parent

class SQLFORM(FORM):

    """
    SQLFORM is used to map a table (and a current record) into an HTML form

    given a SQLTable stored in db.table

    generates an insert form::

        SQLFORM(db.table)

    generates an update form::

        record=db.table[some_id]
        SQLFORM(db.table, record)

    generates an update with a delete button::

        SQLFORM(db.table, record, deletable=True)

    if record is an int::

        record=db.table[record]

    optional arguments:

    :param fields: a list of fields that should be placed in the form,
        default is all.
    :param labels: a dictionary with labels for each field, keys are the field
        names.
    :param col3: a dictionary with content for an optional third column
            (right of each field). keys are field names.
    :param linkto: the URL of a controller/function to access referencedby
        records
            see controller appadmin.py for examples
    :param upload: the URL of a controller/function to download an uploaded file
            see controller appadmin.py for examples

    any named optional attribute is passed to the <form> tag
            for example _class, _id, _style, _action, _method, etc.

    """

    # usability improvements proposal by fpp - 4 May 2008 :
    # - correct labels (for points to field id, not field name)
    # - add label for delete checkbox
    # - add translatable label for record ID
    # - add third column to right of fields, populated from the col3 dict

    widgets = Storage(dict(
        string = StringWidget,
        text = TextWidget,
        password = PasswordWidget,
        integer = IntegerWidget,
        double = DoubleWidget,
        decimal = DecimalWidget,
        time = TimeWidget,
        date = DateWidget,
        datetime = DatetimeWidget,
        upload = UploadWidget,
        boolean = BooleanWidget,
        blob = None,
        options = OptionsWidget,
        multiple = MultipleOptionsWidget,
        radio = RadioWidget,
        checkboxes = CheckboxesWidget,
        autocomplete = AutocompleteWidget,
        list = ListWidget,
        ))


    formstyles = Storage(dict(
        table3cols = formstyle_table3cols,
        table2cols = formstyle_table2cols,
        divs = formstyle_divs,
        ul = formstyle_ul,
        bootstrap = formstyle_bootstrap,
        ))

    FIELDNAME_REQUEST_DELETE = 'delete_this_record'
    FIELDKEY_DELETE_RECORD = 'delete_record'
    ID_LABEL_SUFFIX = '__label'
    ID_ROW_SUFFIX = '__row'

    def assert_status(self, status, request_vars):
        if not status and self.record and self.errors:
            ### if there are errors in update mode
            # and some errors refers to an already uploaded file
            # delete error if
            # - user not trying to upload a new file
            # - there is existing file and user is not trying to delete it
            # this is because removing the file may not pass validation
            for key in self.errors.keys():
                if key in self.table \
                        and self.table[key].type == 'upload' \
                        and request_vars.get(key, None) in (None, '') \
                        and self.record[key] \
                        and not key + UploadWidget.ID_DELETE_SUFFIX in request_vars:
                    del self.errors[key]
            if not self.errors:
                status = True
        return status

    def __init__(
        self,
        table,
        record = None,
        deletable = False,
        linkto = None,
        upload = None,
        fields = None,
        labels = None,
        col3 = {},
        submit_button = 'Submit',
        delete_label = 'Check to delete',
        showid = True,
        readonly = False,
        comments = True,
        keepopts = [],
        ignore_rw = False,
        record_id = None,
        formstyle = 'table3cols',
        buttons = ['submit'],
        separator = ': ',
        **attributes
        ):
        """
        SQLFORM(db.table,
               record=None,
               fields=['name'],
               labels={'name': 'Your name'},
               linkto=URL(f='table/db/')
        """
        T = current.T

        self.ignore_rw = ignore_rw
        self.formstyle = formstyle
        self.readonly = readonly

        nbsp = XML('&nbsp;') # Firefox2 does not display fields with blanks
        FORM.__init__(self, *[], **attributes)
        ofields = fields
        keyed = hasattr(table,'_primarykey') # for backward compatibility

        # if no fields are provided, build it from the provided table
        # will only use writable or readable fields, unless forced to ignore
        if fields is None:
            fields = [f.name for f in table if 
                      (ignore_rw or f.writable or f.readable) and 
                      (readonly or not f.compute)]
        self.fields = fields

        # make sure we have an id
        if self.fields[0] != table.fields[0] and \
                isinstance(table,Table) and not keyed:
            self.fields.insert(0, table.fields[0])

        self.table = table

        # try to retrieve the indicated record using its id
        # otherwise ignore it
        if record and isinstance(record, (int, long, str, unicode)):
            if not str(record).isdigit():
                raise HTTP(404, "Object not found")
            record = table._db(table._id == record).select().first()
            if not record:
                raise HTTP(404, "Object not found")
        self.record = record

        self.record_id = record_id
        if keyed:
            self.record_id = dict([(k,record and str(record[k]) or None) \
                                       for k in table._primarykey])
        self.field_parent = {}
        xfields = []
        self.fields = fields
        self.custom = Storage()
        self.custom.dspval = Storage()
        self.custom.inpval = Storage()
        self.custom.label = Storage()
        self.custom.comment = Storage()
        self.custom.widget = Storage()
        self.custom.linkto = Storage()

        # default id field name
        if not keyed:
            self.id_field_name = table._id.name
        else:
            self.id_field_name = table._primarykey[0] ### only works if one key

        sep = separator or ''

        for fieldname in self.fields:
            if fieldname.find('.') >= 0:
                continue

            field = self.table[fieldname]
            comment = None

            if comments:
                comment = col3.get(fieldname, field.comment)
            if comment is None:
                comment = ''
            self.custom.comment[fieldname] = comment

            if not labels is None and fieldname in labels:
                label = labels[fieldname]
            else:
                label = field.label
            self.custom.label[fieldname] = label

            field_id = '%s_%s' % (table._tablename, fieldname)

            label = LABEL(label, label and sep, _for=field_id,
                          _id=field_id+SQLFORM.ID_LABEL_SUFFIX)

            row_id = field_id+SQLFORM.ID_ROW_SUFFIX
            if field.type == 'id':
                self.custom.dspval.id = nbsp
                self.custom.inpval.id = ''
                widget = ''

                # store the id field name (for legacy databases)
                self.id_field_name = field.name

                if record:
                    if showid and field.name in record and field.readable:
                        v = record[field.name]
                        widget = SPAN(v, _id=field_id)
                        self.custom.dspval.id = str(v)
                        xfields.append((row_id,label, widget,comment))
                    self.record_id = str(record[field.name])
                self.custom.widget.id = widget
                continue


            if readonly and not ignore_rw and not field.readable:
                continue

            if record:
                default = record[fieldname]
            else:
                default = field.default
                if isinstance(default,CALLABLETYPES):
                    default=default()

            cond = readonly or \
                (not ignore_rw and not field.writable and field.readable)

            if default and not cond:
                default = field.formatter(default)
            dspval = default
            inpval = default

            if cond:

                # ## if field.represent is available else
                # ## ignore blob and preview uploaded images
                # ## format everything else

                if field.represent:
                    inp = represent(field,default,record)
                elif field.type in ['blob']:
                    continue
                elif field.type == 'upload':
                    inp = UploadWidget.represent(field, default, upload)
                elif field.type == 'boolean':
                    inp = self.widgets.boolean.widget(field, default, _disabled=True)
                else:
                    inp = field.formatter(default)
            elif field.type == 'upload':
                if hasattr(field, 'widget') and field.widget:
                    inp = field.widget(field, default, upload)
                else:
                    inp = self.widgets.upload.widget(field, default, upload)
            elif hasattr(field, 'widget') and field.widget:
                inp = field.widget(field, default)
            elif field.type == 'boolean':
                inp = self.widgets.boolean.widget(field, default)
                if default:
                    inpval = 'checked'
                else:
                    inpval = ''
            elif OptionsWidget.has_options(field):
                if not field.requires.multiple:
                    inp = self.widgets.options.widget(field, default)
                else:
                    inp = self.widgets.multiple.widget(field, default)
                if fieldname in keepopts:
                    inpval = TAG[''](*inp.components)
            elif field.type.startswith('list:'):
                inp = self.widgets.list.widget(field,default)
            elif field.type == 'text':
                inp = self.widgets.text.widget(field, default)
            elif field.type == 'password':
                inp = self.widgets.password.widget(field, default)
                if self.record:
                    dspval = PasswordWidget.DEFAULT_PASSWORD_DISPLAY
                else:
                    dspval = ''
            elif field.type == 'blob':
                continue
            else:
                field_type = widget_class.match(str(field.type)).group()
                field_type = field_type in self.widgets and field_type or 'string'
                inp = self.widgets[field_type].widget(field, default)

            xfields.append((row_id,label,inp,comment))
            self.custom.dspval[fieldname] = dspval or nbsp
            self.custom.inpval[fieldname] = inpval or ''
            self.custom.widget[fieldname] = inp

        # if a record is provided and found, as is linkto
        # build a link
        if record and linkto:
            db = linkto.split('/')[-1]
            for rfld in table._referenced_by:
                if keyed:
                    query = urllib.quote('%s.%s==%s' % (db,rfld,record[rfld.type[10:].split('.')[1]]))
                else:
                    query = urllib.quote('%s.%s==%s' % (db,rfld,record[self.id_field_name]))
                lname = olname = '%s.%s' % (rfld.tablename, rfld.name)
                if ofields and not olname in ofields:
                    continue
                if labels and lname in labels:
                    lname = labels[lname]
                widget = A(lname,
                           _class='reference',
                           _href='%s/%s?query=%s' % (linkto, rfld.tablename, query))
                xfields.append((olname.replace('.', '__')+SQLFORM.ID_ROW_SUFFIX,
                                '',widget,col3.get(olname,'')))
                self.custom.linkto[olname.replace('.', '__')] = widget
#                 </block>

        # when deletable, add delete? checkbox
        self.custom.deletable = ''
        if record and deletable:
            widget = INPUT(_type='checkbox',
                            _class='delete',
                            _id=self.FIELDKEY_DELETE_RECORD,
                            _name=self.FIELDNAME_REQUEST_DELETE,
                            )
            xfields.append((self.FIELDKEY_DELETE_RECORD+SQLFORM.ID_ROW_SUFFIX,
                            LABEL(
                                delete_label,separator,
                                _for=self.FIELDKEY_DELETE_RECORD,
                                _id=self.FIELDKEY_DELETE_RECORD+SQLFORM.ID_LABEL_SUFFIX),
                            widget,
                            col3.get(self.FIELDKEY_DELETE_RECORD, '')))
            self.custom.deletable = widget

        # when writable, add submit button
        self.custom.submit = ''
        if not readonly:
            if 'submit' in buttons:
                widget = self.custom.submit = INPUT(_type='submit',
                               _value=T(submit_button))
            elif buttons:
                widget = self.custom.submit = DIV(*buttons)
            if self.custom.submit:
                xfields.append(('submit_record' + SQLFORM.ID_ROW_SUFFIX,
                                '', widget, col3.get('submit_button', '')))

        # if a record is provided and found
        # make sure it's id is stored in the form
        if record:
            if not self['hidden']:
                self['hidden'] = {}
            if not keyed:
                self['hidden']['id'] = record[table._id.name]

        (begin, end) = self._xml()
        self.custom.begin = XML("<%s %s>" % (self.tag, begin))
        self.custom.end = XML("%s</%s>" % (end, self.tag))
        table = self.createform(xfields)
        self.components = [table]

    def createform(self, xfields):
        if isinstance(self.formstyle, basestring):
            if self.formstyle in SQLFORM.formstyles:
                self.formstyle = SQLFORM.formstyles[self.formstyle]
            else:
                raise RuntimeError, 'formstyle not found'

        if callable(self.formstyle):
            # backward compatibility, 4 argument function is the old style
            args, varargs, keywords, defaults = inspect.getargspec(self.formstyle)
            if defaults and len(args) - len(defaults) == 4 or len(args) == 4:
                table = TABLE()
                for id,a,b,c in xfields:
                    raw_b = self.field_parent[id] = b
                    newrows = self.formstyle(id,a,raw_b,c)
                    if type(newrows).__name__ != "tuple":
                        newrows = [newrows]
                    for newrow in newrows:
                        table.append(newrow)
            else:
                for id,a,b,c in xfields:
                    self.field_parent[id] = b
                table = self.formstyle(self, xfields)
        else:
            raise RuntimeError, 'formstyle not supported'
        return table

    def accepts(
        self,
        request_vars,
        session=None,
        formname='%(tablename)s/%(record_id)s',
        keepvalues=None,
        onvalidation=None,
        dbio=True,
        hideerror=False,
        detect_record_change=False,
        ):

        """
        similar FORM.accepts but also does insert, update or delete in DAL.
        but if detect_record_change == True than:
          form.record_changed = False (record is properly validated/submitted)
          form.record_changed = True (record cannot be submitted because changed)
        elseif detect_record_change == False than:
          form.record_changed = None
        """

        if keepvalues is None:
            keepvalues = True if self.record else False

        if self.readonly: return False

        if request_vars.__class__.__name__ == 'Request':
            request_vars = request_vars.post_vars

        keyed = hasattr(self.table,'_primarykey')

        # implement logic to detect whether record exist but has been modified
        # server side
        self.record_changed = None
        if detect_record_change:
            if self.record:
                self.record_changed = False
                serialized = '|'.join(str(self.record[k]) for k in self.table.fields())
                self.record_hash = md5_hash(serialized)

        # logic to deal with record_id for keyed tables
        if self.record:
            if keyed:
                formname_id = '.'.join(str(self.record[k])
                                       for k in self.table._primarykey
                                       if hasattr(self.record,k))
                record_id = dict((k, request_vars.get(k,None)) \
                                     for k in self.table._primarykey)
            else:
                (formname_id, record_id) = (self.record[self.id_field_name],
                                            request_vars.get('id', None))
            keepvalues = True
        else:
            if keyed:
                formname_id = 'create'
                record_id = dict([(k, None) for k in self.table._primarykey])
            else:
                (formname_id, record_id) = ('create', None)

        if not keyed and isinstance(record_id, (list, tuple)):
            record_id = record_id[0]

        if formname:
            formname = formname % dict(tablename = self.table._tablename,
                                       record_id = formname_id)

        # ## THIS IS FOR UNIQUE RECORDS, read IS_NOT_IN_DB

        for fieldname in self.fields:
            field = self.table[fieldname]
            requires = field.requires or []
            if not isinstance(requires, (list, tuple)):
                requires = [requires]
            [item.set_self_id(self.record_id) for item in requires
            if hasattr(item, 'set_self_id') and self.record_id]

        # ## END

        fields = {}
        for key in self.vars:
            fields[key] = self.vars[key]

        ret = FORM.accepts(
            self,
            request_vars,
            session,
            formname,
            keepvalues,
            onvalidation,
            hideerror=hideerror,
            )

        self.deleted = \
            request_vars.get(self.FIELDNAME_REQUEST_DELETE, False)

        self.custom.end = TAG[''](self.hidden_fields(), self.custom.end)

        auch = record_id and self.errors and self.deleted

        # auch is true when user tries to delete a record
        # that does not pass validation, yet it should be deleted

        if not ret and not auch:
            for fieldname in self.fields:
                field = self.table[fieldname]
                ### this is a workaround! widgets should always have default not None!
                if not field.widget and field.type.startswith('list:') and \
                        not OptionsWidget.has_options(field):
                    field.widget = self.widgets.list.widget
                if hasattr(field, 'widget') and field.widget and fieldname in request_vars:
                    if fieldname in self.vars:
                        value = self.vars[fieldname]
                    elif self.record:
                        value = self.record[fieldname]
                    else:
                        value = self.table[fieldname].default
                    if field.type.startswith('list:') and \
                            isinstance(value, str):
                        value = [value]
                    row_id = '%s_%s%s' % (self.table, fieldname, SQLFORM.ID_ROW_SUFFIX)
                    widget = field.widget(field, value)
                    self.field_parent[row_id].components = [ widget ]
                    self.field_parent[row_id]._traverse(False, hideerror)
                    self.custom.widget[ fieldname ] = widget
            self.accepted = ret
            return ret

        if record_id and str(record_id) != str(self.record_id):
            raise SyntaxError, 'user is tampering with form\'s record_id: ' \
                '%s != %s' % (record_id, self.record_id)

        if record_id and dbio and not keyed:
            self.vars.id = self.record[self.id_field_name]

        if self.deleted and self.custom.deletable:
            if dbio:
                if keyed:
                    qry = reduce(lambda x, y: x & y,
                                 [self.table[k] == record_id[k] \
                                      for k in self.table._primarykey])
                else:
                    qry = self.table._id == self.record[self.id_field_name]
                self.table._db(qry).delete()
            self.errors.clear()
            for component in self.elements('input, select, textarea'):
                component['_disabled'] = True
            self.accepted = True
            return True

        for fieldname in self.fields:
            if not fieldname in self.table.fields:
                continue

            if not self.ignore_rw and not self.table[fieldname].writable:
                ### this happens because FORM has no knowledge of writable
                ### and thinks that a missing boolean field is a None
                if self.table[fieldname].type == 'boolean' and \
                    self.vars.get(fieldname, True) is None:
                    del self.vars[fieldname]
                continue

            field = self.table[fieldname]
            if field.type == 'id':
                continue
            if field.type == 'boolean':
                if self.vars.get(fieldname, False):
                    self.vars[fieldname] = fields[fieldname] = True
                else:
                    self.vars[fieldname] = fields[fieldname] = False
            elif field.type == 'password' and self.record\
                and request_vars.get(fieldname, None) == \
                    PasswordWidget.DEFAULT_PASSWORD_DISPLAY:
                continue  # do not update if password was not changed
            elif field.type == 'upload':
                f = self.vars[fieldname]
                fd = '%s__delete' % fieldname
                if f == '' or f is None:
                    if self.vars.get(fd, False):
                        f = self.table[fieldname].default or ''
                        fields[fieldname] = f
                    elif self.record:
                        if self.record[fieldname]:
                            fields[fieldname] = self.record[fieldname]
                        else:
                            f = self.table[fieldname].default or ''
                            fields[fieldname] = f
                    else:
                        fields[fieldname] = ''
                    self.vars[fieldname] = fields[fieldname]
                    if not f:
                        continue
                    else:
                        f = os.path.join(current.request.folder,
                                         os.path.normpath(f))
                        source_file = open(f, 'rb')
                        original_filename  = os.path.split(f)[1]
                elif hasattr(f, 'file'):
                    (source_file, original_filename) = (f.file, f.filename)
                elif isinstance(f, (str, unicode)):
                    ### do not know why this happens, it should not
                    (source_file, original_filename) = \
                        (cStringIO.StringIO(f), 'file.txt')
                newfilename = field.store(source_file, original_filename,
                                          field.uploadfolder)
                # this line was for backward compatibility but problematic
                # self.vars['%s_newfilename' % fieldname] = newfilename
                fields[fieldname] = newfilename
                if isinstance(field.uploadfield, str):
                    fields[field.uploadfield] = source_file.read()
                # proposed by Hamdy (accept?) do we need fields at this point?
                self.vars[fieldname] = fields[fieldname]
                continue
            elif fieldname in self.vars:
                fields[fieldname] = self.vars[fieldname]
            elif field.default is None and field.type != 'blob':
                self.errors[fieldname] = 'no data'
                self.accepted = False
                return False
            value = fields.get(fieldname,None)
            if field.type == 'list:string':
                if not isinstance(value, (tuple, list)):
                    fields[fieldname] = value and [value] or []
            elif isinstance(field.type,str) and field.type.startswith('list:'):
                if not isinstance(value, list):
                    fields[fieldname] = [safe_int(x) for x in (value and [value] or [])]
            elif field.type == 'integer':
                if not value is None:
                    fields[fieldname] = safe_int(value)
            elif field.type.startswith('reference'):
                if not value is None and isinstance(self.table, Table) and not keyed:
                    fields[fieldname] = safe_int(value)
            elif field.type == 'double':
                if not value is None:
                    fields[fieldname] = safe_float(value)

        for fieldname in self.vars:
            if fieldname != 'id' and fieldname in self.table.fields\
                 and not fieldname in fields and not fieldname\
                 in request_vars:
                fields[fieldname] = self.vars[fieldname]

        if dbio:
            if 'delete_this_record' in fields:
                # this should never happen but seems to happen to some
                del fields['delete_this_record']
            for field in self.table:
                if not field.name in fields and field.writable is False \
                        and field.update is None and field.compute is None:
                    if record_id and self.record:
                        fields[field.name] = self.record[field.name]
                    elif not self.table[field.name].default is None:
                        fields[field.name] = self.table[field.name].default
            if keyed:
                if reduce(lambda x, y: x and y, record_id.values()): # if record_id
                    if fields:
                        qry = reduce(lambda x, y: x & y,
                            [self.table[k] == self.record[k] for k in self.table._primarykey])
                        self.table._db(qry).update(**fields)
                else:
                    pk = self.table.insert(**fields)
                    if pk:
                        self.vars.update(pk)
                    else:
                        ret = False
            else:
                if record_id:
                    self.vars.id = self.record[self.id_field_name]
                    if fields:
                        self.table._db(self.table._id == self.record[self.id_field_name]).update(**fields)
                else:
                    self.vars.id = self.table.insert(**fields)
        self.accepted = ret
        return ret

    AUTOTYPES = {
        type(''): ('string', None),
        type(True): ('boolean', None),
        type(1): ('integer', IS_INT_IN_RANGE(-1e12,+1e12)),
        type(1.0): ('double', IS_INT_IN_RANGE(-1e12,+1e12)),
        type([]): ('list:string', None),
        type(datetime.date.today()): ('date', IS_DATE()),
        type(datetime.datetime.today()): ('datetime', IS_DATETIME())
        }

    @staticmethod
    def dictform(dictionary,**kwargs):
        fields = []
        for key,value in sorted(dictionary.items()):
            t, requires = SQLFORM.AUTOTYPES.get(type(value),(None,None))
            if t:
                fields.append(Field(key,t,requires=requires,
                                    default=value))
        return SQLFORM.factory(*fields,**kwargs)

    @staticmethod
    def smartdictform(session,name,filename=None,query=None,**kwargs):
        import os
        if query:
            session[name] = query.db(query).select().first().as_dict()
        elif os.path.exists(filename):
            env = {'datetime':datetime}
            session[name] = eval(open(filename).read(),{},env)
        form = SQLFORM.dictform(session[name])
        if form.process().accepted:
            session[name].update(form.vars)
            if query:
                query.db(query).update(**form.vars)
            else:
                open(filename,'w').write(repr(session[name]))
        return form

    @staticmethod
    def factory(*fields, **attributes):
        """
        generates a SQLFORM for the given fields.

        Internally will build a non-database based data model
        to hold the fields.
        """
        # Define a table name, this way it can be logical to our CSS.
        # And if you switch from using SQLFORM to SQLFORM.factory
        # your same css definitions will still apply.

        table_name = attributes.get('table_name', 'no_table')

        # So it won't interfear with SQLDB.define_table
        if 'table_name' in attributes:
            del attributes['table_name']

        return SQLFORM(DAL(None).define_table(table_name, *fields),
                       **attributes)

    @staticmethod
    def build_query(fields,keywords):
        request = current.request
        if isinstance(keywords,(tuple,list)):
           keywords = keywords[0]
           request.vars.keywords = keywords
        key = keywords.strip()
        if key and not ' ' in key and not '"' in key and not "'" in key:
            SEARCHABLE_TYPES = ('string','text','list:string')
            parts = [field.contains(key) for field in fields if field.type in SEARCHABLE_TYPES]
        else:
            parts = None
        if parts:
            return reduce(lambda a,b: a|b,parts)
        else:
            return smart_query(fields,key)

    @staticmethod
    def search_menu(fields,search_options=None):
        T = current.T
        search_options = search_options or {
            'string':['=','!=','<','>','<=','>=','starts with','contains'],
            'text':['=','!=','<','>','<=','>=','starts with','contains'],
            'date':['=','!=','<','>','<=','>='],
            'time':['=','!=','<','>','<=','>='],
            'datetime':['=','!=','<','>','<=','>='],
            'integer':['=','!=','<','>','<=','>='],
            'double':['=','!=','<','>','<=','>='],
            'boolean':['=','!=']}
        if fields[0]._db._adapter.dbengine=='google:datastore':
            search_options['string'] = ['=','!=','<','>','<=','>=']
            search_options['text'] = ['=','!=','<','>','<=','>=']
        criteria = []
        selectfields = []
        for field in fields:
            name = str(field).replace('.','-')
            options = search_options.get(field.type,None)
            if options:
                label = isinstance(field.label,str) and T(field.label) or field.label
                selectfields.append(OPTION(label, _value=str(field)))
                operators = SELECT(*[T(option) for option in options])
                if field.type=='boolean':
                    value_input = SELECT(
                        OPTION(T("True"),_value="T"),
                        OPTION(T("False"),_value="F"),
                        _id="w2p_value_"+name)
                else:
                    value_input = INPUT(_type='text',
                                        _id="w2p_value_"+name,
                                        _class=field.type)
                new_button = INPUT(
                    _type="button", _value=T('New'),_class="btn",
                    _onclick="w2p_build_query('new','%s')" % field)
                and_button = INPUT(
                    _type="button", _value=T('And'),_class="btn",
                    _onclick="w2p_build_query('and','%s')" % field)
                or_button = INPUT(
                    _type="button", _value=T('Or'),_class="btn",
                    _onclick="w2p_build_query('or','%s')" % field)
                close_button = INPUT(
                    _type="button", _value=T('Close'),_class="btn",
                    _onclick="jQuery('#w2p_query_panel').slideUp()")

                criteria.append(DIV(
                        operators,value_input,new_button,
                        and_button,or_button,close_button,
                        _id='w2p_field_%s' % name,
                        _class='w2p_query_row hidden',
                        _style='display:inline'))
                                
        criteria.insert(0,SELECT(
                _id="w2p_query_fields",
                _onchange="jQuery('.w2p_query_row').hide();jQuery('#w2p_field_'+jQuery('#w2p_query_fields').val().replace('.','-')).show();",
                _style='float:left',
                *selectfields))

        fadd = SCRIPT("""
        jQuery('#w2p_query_panel input,#w2p_query_panel select').css('width','auto');
        jQuery(function(){web2py_ajax_fields('#w2p_query_panel');});
        function w2p_build_query(aggregator,a) {
          var b=a.replace('.','-');
          var option = jQuery('#w2p_field_'+b+' select').val();
          var value = jQuery('#w2p_value_'+b).val().replace('"','\\\\"');
          var s=a+' '+option+' "'+value+'"';
          var k=jQuery('#web2py_keywords');
          var v=k.val();
          if(aggregator=='new') k.val(s); else k.val((v?(v+' '+ aggregator +' '):'')+s);
        }
        """)
        return CAT(
            DIV(_id="w2p_query_panel",_class='hidden',*criteria),fadd)
                       


    @staticmethod
    def grid(query,
             fields=None,
             field_id=None,
             left=None,
             headers={},
             orderby=None,
             groupby=None,
             searchable=True,
             sortable=True,
             paginate=20,
             deletable=True,
             editable=True,
             details=True,
             selectable=None,
             create=True,
             csv=True,
             links=None,
             links_in_grid=True,
             upload = '<default>',
             args=[],
             user_signature = True,
             maxtextlengths={},
             maxtextlength=20,
             onvalidation=None,
             oncreate=None,
             onupdate=None,
             ondelete=None,
             sorter_icons=(XML('&#x2191;'),XML('&#x2193;')),
             ui = 'web2py',
             showbuttontext=True,
             _class="web2py_grid",
             formname='web2py_grid',
             search_widget='default',
             ignore_rw = False,
             formstyle = 'table3cols',
             exportclasses = None,
             formargs={},
             createargs={},
             editargs={},
             viewargs={},
            ):

        # jQuery UI ThemeRoller classes (empty if ui is disabled)
        if ui == 'jquery-ui':
            ui = dict(widget='ui-widget',
                      header='ui-widget-header',
                      content='ui-widget-content',
                      default='ui-state-default',
                      cornerall='ui-corner-all',
                      cornertop='ui-corner-top',
                      cornerbottom='ui-corner-bottom',
                      button='ui-button-text-icon-primary',
                      buttontext='ui-button-text',
                      buttonadd='ui-icon ui-icon-plusthick',
                      buttonback='ui-icon ui-icon-arrowreturnthick-1-w',
                      buttonexport='ui-icon ui-icon-transferthick-e-w',
                      buttondelete='ui-icon ui-icon-trash',
                      buttonedit='ui-icon ui-icon-pencil',
                      buttontable='ui-icon ui-icon-triangle-1-e',
                      buttonview='ui-icon ui-icon-zoomin',
                      )
        elif ui == 'web2py':
            ui = dict(widget='',
                      header='',
                      content='',
                      default='',
                      cornerall='',
                      cornertop='',
                      cornerbottom='',
                      button='button btn',
                      buttontext='buttontext button',
                      buttonadd='icon plus icon-plus',
                      buttonback='icon leftarrow icon-arrow-left',
                      buttonexport='icon downarrow icon-download',
                      buttondelete='icon trash icon-trash',
                      buttonedit='icon pen icon-pencil',
                      buttontable='icon rightarrow icon-arrow-right',
                      buttonview='icon magnifier icon-zoom-in',
                      )
        elif not isinstance(ui,dict):
            raise RuntimeError,'SQLFORM.grid ui argument must be a dictionary'

        db = query._db
        T = current.T
        request = current.request
        session = current.session
        response = current.response
        wenabled = (not user_signature or (session.auth and session.auth.user))
        create = wenabled and create
        editable = wenabled and editable
        deletable = wenabled and deletable

        def url(**b):
            b['args'] = args+b.get('args',[])
            b['hash_vars']=False
            b['user_signature'] = user_signature
            return URL(**b)

        def url2(**b):
            b['args'] = request.args+b.get('args',[])
            b['hash_vars']=False
            b['user_signature'] = user_signature
            return URL(**b)

        referrer = session.get('_web2py_grid_referrer_'+formname, url())
        if user_signature:
            if (args != request.args and user_signature and \
                    not URL.verify(request,user_signature=user_signature)) or \
                    (not (session.auth and session.auth.user) and \
                         ('edit' in request.args or \
                              'create' in request.args or \
                              'delete' in request.args)):
                session.flash = T('not authorized')
                redirect(referrer)

        def gridbutton(buttonclass='buttonadd', buttontext='Add',
                       buttonurl=url(args=[]), callback=None,
                       delete=None, trap=True):
            if showbuttontext:
                if callback:
                    return A(SPAN(_class=ui.get(buttonclass)),
                             SPAN(T(buttontext),_title=buttontext,
                                  _class=ui.get('buttontext')),
                             callback=callback,delete=delete,
                             _class=trap_class(ui.get('button'),trap))
                else:
                    return A(SPAN(_class=ui.get(buttonclass)),
                             SPAN(T(buttontext),_title=buttontext,
                                  _class=ui.get('buttontext')),
                             _href=buttonurl,
                             _class=trap_class(ui.get('button'),trap))
            else:
                if callback:
                    return A(SPAN(_class=ui.get(buttonclass)),
                             callback=callback,delete=delete,
                             _title=buttontext,
                             _class=trap_class(ui.get('buttontext'),trap))
                else:
                    return A(SPAN(_class=ui.get(buttonclass)),
                             _href=buttonurl,_title=buttontext,
                             _class=trap_class(ui.get('buttontext'),trap))
        dbset = db(query)
        tablenames = db._adapter.tables(dbset.query)
        if left!=None: tablenames+=db._adapter.tables(left)
        tables = [db[tablename] for tablename in tablenames]
        if not fields:
            fields = reduce(lambda a,b:a+b,
                            [[field for field in table] for table in tables])
        if not field_id:
            field_id = tables[0]._id
        columns = [str(field) for field in fields \
                       if field._tablename in tablenames]

        if not str(field_id) in [str(f) for f in fields]:
            fields.append(field_id)
        table = field_id.table
        tablename = table._tablename
        if upload=='<default>':
            upload = lambda filename: url(args=['download',filename])
            if len(request.args)>1 and request.args[-2]=='download':
                stream = response.download(request,db)
                raise HTTP(200,stream,**response.headers)

        def buttons(edit=False,view=False,record=None):
            buttons = DIV(gridbutton('buttonback', 'Back', referrer),
                          _class='form_header row_buttons %(header)s %(cornertop)s' % ui)
            if edit and (not callable(edit) or edit(record)):
                args = ['edit',table._tablename,request.args[-1]]
                buttons.append(gridbutton('buttonedit', 'Edit',
                                          url(args=args)))
            if view:
                args = ['view',table._tablename,request.args[-1]]
                buttons.append(gridbutton('buttonview', 'View',
                                          url(args=args)))
            if record and links:
                for link in links:
                    if isinstance(link,dict):
                         buttons.append(link['body'](record))
                    elif link(record):
                         buttons.append(link(record))
            return buttons

        formfooter = DIV(
            _class='form_footer row_buttons %(header)s %(cornerbottom)s' % ui)

        create_form = update_form = view_form = search_form = None
        sqlformargs = dict(formargs)

        if create and len(request.args)>1 and request.args[-2] == 'new':
            table = db[request.args[-1]]
            sqlformargs.update(createargs)
            create_form = SQLFORM(
                table, ignore_rw=ignore_rw, formstyle=formstyle,
                _class='web2py_form',
                **sqlformargs)
            create_form.process(formname=formname,
                    next=referrer,
                    onvalidation=onvalidation,
                    onsuccess=oncreate)
            res = DIV(buttons(), create_form, formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            return res

        elif details and len(request.args)>2 and request.args[-3]=='view':
            table = db[request.args[-2]]
            record = table(request.args[-1]) or redirect(URL('error'))
            sqlformargs.update(viewargs)
            view_form = SQLFORM(table, record, upload=upload, ignore_rw=ignore_rw,
                           formstyle=formstyle, readonly=True, _class='web2py_form',
                           **sqlformargs)
            res = DIV(buttons(edit=editable, record=record), view_form,
                      formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            return res
        elif editable and len(request.args)>2 and request.args[-3]=='edit':
            table = db[request.args[-2]]
            record = table(request.args[-1]) or redirect(URL('error'))
            sqlformargs.update(editargs)
            update_form = SQLFORM(table, record, upload=upload, ignore_rw=ignore_rw,
                                formstyle=formstyle, deletable=deletable,
                                _class='web2py_form',
                                submit_button=T('Submit'),
                                delete_label=T('Check to delete'),
                                **sqlformargs)
            update_form.process(formname=formname,
                              onvalidation=onvalidation,
                              onsuccess=onupdate,
                              next=referrer)
            res = DIV(buttons(view=details, record=record),
                      update_form, formfooter, _class=_class)
            res.create_form = create_form
            res.update_form = update_form
            res.view_form = view_form
            res.search_form = search_form
            return res
        elif deletable and len(request.args)>2 and request.args[-3]=='delete':
            table = db[request.args[-2]]
            if ondelete:
                ondelete(table,request.args[-1])
            ret = db(table[table._id.name]==request.args[-1]).delete()
            return ret

        exportManager = dict(
            csv_with_hidden_cols=(ExporterCSV,'CSV (hidden cols)'),
            csv=(ExporterCSV,'CSV'),
            xml=(ExporterXML, 'XML'),
            html=(ExporterHTML, 'HTML'),
            tsv_with_hidden_cols=\
                (ExporterTSV,'TSV (Excel compatible, hidden cols)'),
            tsv=(ExporterTSV, 'TSV (Excel compatible)'))
        if not exportclasses is None:
            exportManager.update(exportclasses)

        export_type = request.vars._export_type
        if export_type:
            order = request.vars.order or ''
            if sortable:
                if order and not order=='None':
                    if order[:1]=='~':
                        sign, rorder = '~', order[1:]
                    else:
                        sign, rorder = '', order
                    tablename,fieldname = rorder.split('.',1)
                    orderby=db[tablename][fieldname]
                    if sign=='~':
                        orderby=~orderby

            table_fields = [f for f in fields if f._tablename in tablenames]
            if export_type in ('csv_with_hidden_cols','tsv_with_hidden_cols'):
                if request.vars.keywords:
                    try:
                        dbset = dbset(SQLFORM.build_query(
                                fields,request.vars.get('keywords','')))
                        rows = dbset.select(cacheable=True)
                    except Exception, e:
                        response.flash = T('Internal Error')
                        rows = []
                else:
                    rows = dbset.select(cacheable=True)
            else:
                rows = dbset.select(left=left,orderby=orderby,
                                    cacheable=True*columns)

            if export_type in exportManager:
                value = exportManager[export_type]
                clazz = value[0] if hasattr(value, '__getitem__') else value
                oExp = clazz(rows)
                filename = '.'.join(('rows', oExp.file_ext))
                response.headers['Content-Type'] = oExp.content_type
                response.headers['Content-Disposition'] = \
                    'attachment;filename='+filename+';'
                raise HTTP(200, oExp.export(),**response.headers)

        elif request.vars.records and not isinstance(
            request.vars.records,list):
            request.vars.records=[request.vars.records]
        elif not request.vars.records:
            request.vars.records=[]

        session['_web2py_grid_referrer_'+formname] = url2(vars=request.vars)
        console = DIV(_class='web2py_console %(header)s %(cornertop)s' % ui)
        error = None
        if searchable:
            sfields = reduce(lambda a,b:a+b,
                             [[f for f in t if f.readable] for t in tables])
            if isinstance(search_widget,dict):
                search_widget = search_widget[tablename]
            if search_widget=='default':
                search_menu = SQLFORM.search_menu(sfields)
                search_widget = lambda sfield, url: DIV(FORM(
                    INPUT(_name='keywords',_value=request.vars.keywords,
                          _id='web2py_keywords',_onfocus="jQuery('#w2p_query_fields').change();jQuery('#w2p_query_panel').slideDown();"),
                    INPUT(_type='submit',_value=T('Search'),_class="btn"),
                    INPUT(_type='submit',_value=T('Clear'),_class="btn",
                          _onclick="jQuery('#web2py_keywords').val('');"),
                    _method="GET",_action=url),search_menu)
            form = search_widget and search_widget(sfields,url()) or ''
            console.append(form)
            keywords = request.vars.get('keywords','')
            try:
                if callable(searchable):
                    subquery = searchable(sfields, keywords)
                else:
                    subquery = SQLFORM.build_query(sfields, keywords)
            except RuntimeError:
                subquery = None
                error = T('Invalid query')
        else:
            subquery = None
        if create:
            console.append(gridbutton(
                    buttonclass='buttonadd',
                    buttontext='Add',
                    buttonurl=url(args=['new',tablename])))

        if subquery:
            dbset = dbset(subquery)
        try:
            if left or groupby:
                c = 'count(*)'
                nrows = dbset.select(c,left=left,cacheable=True,
                                     groupby=groupby).first()[c]
            else:
                nrows = dbset.count()
        except:
            nrows = 0
            error = T('Unsupported query')

        order = request.vars.order or ''
        if sortable:
            if order and not order=='None':
                tablename,fieldname = order.split('~')[-1].split('.',1)
                sort_field = db[tablename][fieldname]
                exception = sort_field.type in ('date','datetime','time')
                if exception:
                    orderby = (order[:1]=='~' and sort_field) or ~sort_field
                else:
                    orderby = (order[:1]=='~' and ~sort_field) or sort_field

        head = TR(_class=ui.get('header'))
        if selectable:
            head.append(TH(_class=ui.get('default')))
        for field in fields:
            if columns and not str(field) in columns: continue
            if not field.readable: continue
            key = str(field)
            header = headers.get(str(field),
                                 hasattr(field,'label') and field.label or key)
            if sortable:
                if key == order:
                    key, marker = '~'+order, sorter_icons[0]
                elif key == order[1:]:
                    marker = sorter_icons[1]
                else:
                    marker = ''
                header = A(header,marker,_href=url(vars=dict(
                            keywords=request.vars.keywords or '',
                            order=key)),_class=trap_class())
            head.append(TH(header, _class=ui.get('default')))

        if links and links_in_grid:
            for link in links:
                if isinstance(link,dict):
                    head.append(TH(link['header'], _class=ui.get('default')))

        # Include extra column for buttons if needed.
        include_buttons_column = (details or editable or deletable or
            (links and links_in_grid and
             not all([isinstance(link, dict) for link in links])))
        if include_buttons_column:
            head.append(TH(_class=ui.get('default')))

        paginator = UL()
        if paginate and paginate<nrows:
            npages,reminder = divmod(nrows,paginate)
            if reminder: npages+=1
            try: page = int(request.vars.page or 1)-1
            except ValueError: page = 0
            limitby = (paginate*page,paginate*(page+1))
            def self_link(name,p):
                d = dict(page=p+1)
                if order: d['order']=order
                if request.vars.keywords: d['keywords']=request.vars.keywords
                return A(name,_href=url(vars=d),_class=trap_class())
            NPAGES = 5 # window is 2*NPAGES
            if page>NPAGES+1:
                paginator.append(LI(self_link('<<',0)))
            if page>NPAGES:
                paginator.append(LI(self_link('<',page-1)))
            pages = range(max(0,page-NPAGES),min(page+NPAGES,npages))
            for p in pages:
                if p == page:
                    paginator.append(LI(A(p+1,_onclick='return false'),
                                        _class=trap_class('current')))
                else:
                    paginator.append(LI(self_link(p+1,p)))
            if page<npages-NPAGES:
                paginator.append(LI(self_link('>',page+1)))
            if page<npages-NPAGES-1:
                paginator.append(LI(self_link('>>',npages-1)))
        else:
            limitby = None

        try:
            table_fields = [f for f in fields if f._tablename in tablenames]
            rows = dbset.select(left=left,orderby=orderby,
                                groupby=groupby,limitby=limitby,
                                cacheable=True,*table_fields)
        except SyntaxError:
            rows = None
            error = T("Query Not Supported")
        if nrows:
            message = error or T('%(nrows)s records found') % dict(nrows=nrows)
            console.append(DIV(message,_class='web2py_counter'))

        if rows:
            htmltable = TABLE(THEAD(head))
            tbody = TBODY()
            numrec=0
            for row in rows:
                if numrec % 2 == 0:
                    classtr = 'even'
                else:
                    classtr = 'odd'
                numrec+=1
                id = row[field_id]
                if id:
                    rid = id
                    if callable(rid): ### can this ever be callable?
                        rid = rid(row)
                    tr = TR(_id=rid, _class='%s %s' % (classtr, 'with_id'))
                else:
                    tr = TR(_class=classtr)
                if selectable:
                    tr.append(INPUT(_type="checkbox",_name="records",_value=id,
                                    value=request.vars.records))
                for field in fields:
                    if not str(field) in columns: continue
                    if not field.readable: continue
                    if field.type=='blob': continue
                    value = row[field]
                    maxlength = maxtextlengths.get(str(field),maxtextlength)
                    if field.represent:
                        try:
                            value=field.represent(value,row)
                        except KeyError:
                            try:
                                value=field.represent(value,row[field._tablename])
                            except KeyError:
                                pass
                    elif field.type=='boolean':
                        value = INPUT(_type="checkbox",_checked = value,
                                      _disabled=True)
                    elif field.type=='upload':
                        if value:
                            if callable(upload):
                                value = A(current.T('file'), _href=upload(value))
                            elif upload:
                                value = A(current.T('file'),
                                          _href='%s/%s' % (upload, value))
                        else:
                            value = ''
                    if isinstance(value,str):
                        value = truncate_string(value,maxlength)
                    elif not isinstance(value,DIV):
                        value = field.formatter(value)
                    tr.append(TD(value))
                row_buttons = TD(_class='row_buttons')
                if links and links_in_grid:
                    for link in links:
                        if isinstance(link, dict):
                            tr.append(TD(link['body'](row)))
                        else:
                            if link(row):
                                row_buttons.append(link(row))
                if include_buttons_column:
                    if details and (not callable(details) or details(row)):
                        row_buttons.append(gridbutton(
                                'buttonview', 'View',
                                url(args=['view',tablename,id])))
                    if editable and (not callable(editable) or editable(row)):
                        row_buttons.append(gridbutton(
                                'buttonedit', 'Edit',
                                url(args=['edit',tablename,id])))
                    if deletable and (not callable(deletable) or deletable(row)):
                        row_buttons.append(gridbutton(
                                'buttondelete', 'Delete',
                                callback=url(args=['delete',tablename,id]),
                                delete='tr'))
                    tr.append(row_buttons)
                tbody.append(tr)
            htmltable.append(tbody)
            htmltable = DIV(htmltable,_style='width:100%;overflow-x:auto')
            if selectable:
                htmltable = FORM(htmltable,INPUT(_type="submit"))
                if htmltable.process(formname=formname).accepted:#
                    htmltable.vars.records = htmltable.vars.records or []
                    htmltable.vars.records = htmltable.vars.records if type(htmltable.vars.records) == list else [htmltable.vars.records]
                    records = [int(r) for r in htmltable.vars.records]
                    selectable(records)
                    redirect(referrer)
        else:
            htmltable = DIV(current.T('No records found'))

        if csv and nrows:
            export_links =[]
            for k,v in sorted(exportManager.items()):
                label = v[1] if hasattr(v, "__getitem__") else k
                link = url2(vars=dict(
                        order=request.vars.order or '',
                        _export_type=k,
                        keywords=request.vars.keywords or ''))
                export_links.append(A(T(label),_href=link))
            export_menu = \
                DIV(T('Export:'),_class="w2p_export_menu",*export_links)
        else:
            export_menu = None

        res = DIV(console,
                  DIV(htmltable,_class="web2py_table"),
                  DIV(paginator,_class=\
                          "web2py_paginator %(header)s %(cornerbottom)s" % ui),
                  _class='%s %s' % (_class, ui.get('widget')))
        if export_menu: res.append(export_menu)
        res.create_form = create_form
        res.update_form = update_form
        res.view_form = view_form
        res.search_form = search_form
        return res

    @staticmethod
    def smartgrid(table, constraints=None, linked_tables=None,
                  links=None, links_in_grid=True,
                  args=None, user_signature=True,
                  divider='>', breadcrumbs_class='',
                  **kwargs):
        """
        @auth.requires_login()
        def index():
            db.define_table('person',Field('name'),format='%(name)s')
            db.define_table('dog',
                Field('name'),Field('owner',db.person),format='%(name)s')
            db.define_table('comment',Field('body'),Field('dog',db.dog))
            if db(db.person).isempty():
                from gluon.contrib.populate import populate
                populate(db.person,300)
                populate(db.dog,300)
                populate(db.comment,1000)
                db.commit()
        form=SQLFORM.smartgrid(db[request.args(0) or 'person']) #***
        return dict(form=form)

        *** builds a complete interface to navigate all tables links
            to the request.args(0)
            table: pagination, search, view, edit, delete,
                   children, parent, etc.

        constraints is a dict {'table',query} that limits which
        records can be accessible
        links is a dict like
           {'tablename':[lambda row: A(....), ...]}
        that will add buttons when table tablename is displayed
        linked_tables is a optional list of tablenames of tables
        to be linked
        """
        request, T = current.request, current.T
        if args is None: args = []

        def url(**b):
            b['args'] = request.args[:nargs]+b.get('args',[])
            b['hash_vars']=False
            b['user_signature'] = user_signature
            return URL(**b)

        db = table._db
        breadcrumbs = []
        if request.args(len(args)) != table._tablename:
            request.args[:]=args+[table._tablename]
        if links is None: links = {}
        if constraints is None: constraints = {}
        field = None
        try:
            nargs = len(args)+1
            previous_tablename,previous_fieldname,previous_id = \
                table._tablename,None,None
            while len(request.args)>nargs:
                key = request.args(nargs)
                if '.' in key:
                    id = request.args(nargs+1)
                    tablename,fieldname = key.split('.',1)
                    table = db[tablename]
                    field = table[fieldname]
                    field.default = id
                    referee = field.type[10:]
                    if referee!=previous_tablename:
                        raise HTTP(400)
                    cond = constraints.get(referee,None)
                    if cond:
                        record = db(db[referee].id==id)(cond).select().first()
                    else:
                        record = db[referee](id)
                    if previous_id:
                        if record[previous_fieldname] != int(previous_id):
                            raise HTTP(400)
                    previous_tablename,previous_fieldname,previous_id = \
                        tablename,fieldname,id
                    try:
                        format = db[referee]._format
                        if callable(format): name = format(record)
                        else: name = format % record
                    except TypeError:
                        name = id
                    nameLink = 'view'
                    breadcrumbs.append(
                        LI(A(T(db[referee]._plural),
                             _class=trap_class(),
                             _href=url()),
                           SPAN(divider,_class='divider'),
                           _class='w2p_grid_breadcrumb_elem'))
                    if kwargs.get('details',True):
                        breadcrumbs.append(
                            LI(A(name,_class=trap_class(),
                                 _href=url(args=['view',referee,id])),
                               SPAN(divider,_class='divider'),
                               _class='w2p_grid_breadcrumb_elem'))
                    nargs+=2
                else:
                    break
            if nargs>len(args)+1:
                query = (field == id)
                if linked_tables is None or referee in linked_tables:
                    field.represent = lambda id,r=None,referee=referee,rep=field.represent: A(callable(rep) and rep(id) or id,_class=trap_class(),_href=url(args=['view',referee,id]))
        except (KeyError,ValueError,TypeError):
            redirect(URL(args=table._tablename))
        if nargs==len(args)+1:
            query = table.id>0

        # filter out data info for displayed table
        if table._tablename in constraints:
            query = query & constraints[table._tablename]
        if isinstance(links,dict):
            links = links.get(table._tablename,[])
        for key in 'columns,orderby,searchable,sortable,paginate,deletable,editable,details,selectable,create,fields'.split(','):
            if isinstance(kwargs.get(key,None),dict):
                if table._tablename in kwargs[key]:
                    kwargs[key] = kwargs[key][table._tablename]
                else:
                    del kwargs[key]
        check = {}
        id_field_name = table._id.name
        for rfield in table._referenced_by:
            if rfield.readable:
                check[rfield.tablename] = \
                    check.get(rfield.tablename,[])+[rfield.name]
        for tablename in sorted(check):
            linked_fieldnames = check[tablename]
            tb = db[tablename]
            multiple_links = len(linked_fieldnames)>1
            for fieldname in linked_fieldnames:
                if linked_tables is None or tablename in linked_tables:
                    t = T(tb._plural) if not multiple_links else \
                        T(tb._plural+'('+fieldname+')')
                    args0 = tablename+'.'+fieldname
                    links.append(
                        lambda row,t=t,nargs=nargs,args0=args0:\
                            A(SPAN(t),_class=trap_class(),_href=url(
                                args=[args0,row[id_field_name]])))

        grid=SQLFORM.grid(query,args=request.args[:nargs],links=links,
                          links_in_grid=links_in_grid,
                          user_signature=user_signature,**kwargs)
        if isinstance(grid,DIV):
            header = table._plural + (field and ' for '+field.name or '')
            breadcrumbs.append(LI(A(T(header),_class=trap_class(),
                                 _href=url()),_class='active w2p_grid_breadcrumb_elem'))
            grid.insert(0,DIV(UL(*breadcrumbs, **{'_class':breadcrumbs_class}),
                              _class='web2py_breadcrumbs'))
        return grid


class SQLTABLE(TABLE):

    """
    given a Rows object, as returned by a db().select(), generates
    an html table with the rows.

    optional arguments:

    :param linkto: URL (or lambda to generate a URL) to edit individual records
    :param upload: URL to download uploaded files
    :param orderby: Add an orderby link to column headers.
    :param headers: dictionary of headers to headers redefinions
                    headers can also be a string to gerenare the headers from data
                    for now only headers="fieldname:capitalize",
                    headers="labels" and headers=None are supported
    :param truncate: length at which to truncate text in table cells.
        Defaults to 16 characters.
    :param columns: a list or dict contaning the names of the columns to be shown
        Defaults to all

    Optional names attributes for passed to the <table> tag

    The keys of headers and columns must be of the form "tablename.fieldname"

    Simple linkto example::

        rows = db.select(db.sometable.ALL)
        table = SQLTABLE(rows, linkto='someurl')

    This will link rows[id] to .../sometable/value_of_id


    More advanced linkto example::

        def mylink(field, type, ref):
            return URL(args=[field])

        rows = db.select(db.sometable.ALL)
        table = SQLTABLE(rows, linkto=mylink)

    This will link rows[id] to
        current_app/current_controlle/current_function/value_of_id

    New Implements: 24 June 2011:
    -----------------------------

    :param selectid: The id you want to select
    :param renderstyle: Boolean render the style with the table

    :param extracolums = [{'label':A('Extra',_href='#'),
                    'class': '', #class name of the header
                    'width':'', #width in pixels or %
                    'content':lambda row, rc: A('Edit',_href='edit/%s'%row.id),
                    'selected': False #agregate class selected to this column
                    }]


    :param headers = {'table.id':{'label':'Id',
                           'class':'', #class name of the header
                           'width':'', #width in pixels or %
                           'truncate': 16, #truncate the content to...
                           'selected': False #agregate class selected to this column
                           },
               'table.myfield':{'label':'My field',
                                'class':'', #class name of the header
                                'width':'', #width in pixels or %
                                'truncate': 16, #truncate the content to...
                                'selected': False #agregate class selected to this column
                                },
               }

    table = SQLTABLE(rows, headers=headers, extracolums=extracolums)


    """

    def __init__(
        self,
        sqlrows,
        linkto=None,
        upload=None,
        orderby=None,
        headers={},
        truncate=16,
        columns=None,
        th_link='',
        extracolumns=None,
        selectid=None,
        renderstyle=False,
        **attributes
        ):

        TABLE.__init__(self, **attributes)

        self.components = []
        self.attributes = attributes
        self.sqlrows = sqlrows
        (components, row) = (self.components, [])
        if not sqlrows:
            return
        if not columns:
            columns = sqlrows.colnames
        if headers=='fieldname:capitalize':
            headers = {}
            for c in columns:
                headers[c] = c.split('.')[-1].replace('_',' ').title()
        elif headers=='labels':
            headers = {}
            for c in columns:
                (t,f) = c.split('.')
                field = sqlrows.db[t][f]
                headers[c] = field.label
        if headers is None:
            headers = {}
        else:
            for c in columns:#new implement dict
                if isinstance(headers.get(c, c), dict):
                    coldict = headers.get(c, c)
                    attrcol = dict()
                    if coldict['width']!="":
                        attrcol.update(_width=coldict['width'])
                    if coldict['class']!="":
                        attrcol.update(_class=coldict['class'])
                    row.append(TH(coldict['label'],**attrcol))
                elif orderby:
                    row.append(TH(A(headers.get(c, c),
                                    _href=th_link+'?orderby=' + c)))
                else:
                    row.append(TH(headers.get(c, c)))

            if extracolumns:#new implement dict
                for c in extracolumns:
                    attrcol = dict()
                    if c['width']!="":
                        attrcol.update(_width=c['width'])
                    if c['class']!="":
                        attrcol.update(_class=c['class'])
                    row.append(TH(c['label'],**attrcol))

            components.append(THEAD(TR(*row)))


        tbody = []
        for (rc, record) in enumerate(sqlrows):
            row = []
            if rc % 2 == 0:
                _class = 'even'
            else:
                _class = 'odd'

            if not selectid is None: #new implement
                if record[self.id_field_name]==selectid:
                    _class += ' rowselected'

            for colname in columns:
                if not table_field.match(colname):
                    if "_extra" in record and colname in record._extra:
                        r = record._extra[colname]
                        row.append(TD(r))
                        continue
                    else:
                        raise KeyError("Column %s not found (SQLTABLE)" % colname)
                (tablename, fieldname) = colname.split('.')
                try:
                    field = sqlrows.db[tablename][fieldname]
                except KeyError:
                    field = None
                if tablename in record \
                        and isinstance(record,Row) \
                        and isinstance(record[tablename],Row):
                    r = record[tablename][fieldname]
                elif fieldname in record:
                    r = record[fieldname]
                else:
                    raise SyntaxError, 'something wrong in Rows object'
                r_old = r
                if not field:
                    pass
                elif linkto and field.type == 'id':
                    try:
                        href = linkto(r, 'table', tablename)
                    except TypeError:
                        href = '%s/%s/%s' % (linkto, tablename, r_old)
                    r = A(r, _href=href)
                elif isinstance(field.type, str) and field.type.startswith('reference'):
                    if linkto:
                        ref = field.type[10:]
                        try:
                            href = linkto(r, 'reference', ref)
                        except TypeError:
                            href = '%s/%s/%s' % (linkto, ref, r_old)
                            if ref.find('.') >= 0:
                                tref,fref = ref.split('.')
                                if hasattr(sqlrows.db[tref],'_primarykey'):
                                    href = '%s/%s?%s' % (linkto, tref, urllib.urlencode({fref:r}))
                        r = A(represent(field,r,record), _href=str(href))
                    elif field.represent:
                        r = represent(field,r,record)
                elif linkto and hasattr(field._table,'_primarykey')\
                        and fieldname in field._table._primarykey:
                    # have to test this with multi-key tables
                    key = urllib.urlencode(dict( [ \
                                ((tablename in record \
                                      and isinstance(record, Row) \
                                      and isinstance(record[tablename], Row)) and
                                 (k, record[tablename][k])) or (k, record[k]) \
                                    for k in field._table._primarykey ] ))
                    r = A(r, _href='%s/%s?%s' % (linkto, tablename, key))
                elif isinstance(field.type, str) and field.type.startswith('list:'):
                    r = represent(field,r or [],record)
                elif field.represent:
                    r = represent(field,r,record)
                elif field.type == 'blob' and r:
                    r = 'DATA'
                elif field.type == 'upload':
                    if upload and r:
                        r = A(current.T('file'), _href='%s/%s' % (upload, r))
                    elif r:
                        r = current.T('file')
                    else:
                        r = ''
                elif field.type in ['string','text']:
                    r = str(field.formatter(r))
                    if headers!={}: #new implement dict
                        if isinstance(headers[colname],dict):
                            if isinstance(headers[colname]['truncate'], int):
                                r = truncate_string(r, headers[colname]['truncate'])
                    elif not truncate is None:
                        r = truncate_string(r, truncate)
                attrcol = dict()#new implement dict
                if headers!={}:
                    if isinstance(headers[colname],dict):
                        colclass=headers[colname]['class']
                        if headers[colname]['selected']:
                            colclass= str(headers[colname]['class'] + " colselected").strip()
                        if colclass!="":
                            attrcol.update(_class=colclass)

                row.append(TD(r,**attrcol))

            if extracolumns:#new implement dict
                for c in extracolumns:
                    attrcol = dict()
                    colclass=c['class']
                    if c['selected']:
                        colclass= str(c['class'] + " colselected").strip()
                    if colclass!="":
                        attrcol.update(_class=colclass)
                    contentfunc = c['content']
                    row.append(TD(contentfunc(record, rc),**attrcol))

            tbody.append(TR(_class=_class, *row))

        if renderstyle:
            components.append(STYLE(self.style()))

        components.append(TBODY(*tbody))


    def style(self):

        css = '''
        table tbody tr.odd {
            background-color: #DFD;
        }
        table tbody tr.even {
            background-color: #EFE;
        }
        table tbody tr.rowselected {
            background-color: #FDD;
        }
        table tbody tr td.colselected {
            background-color: #FDD;
        }
        table tbody tr:hover {
            background: #DDF;
        }
        '''

        return css

form_factory = SQLFORM.factory # for backward compatibility, deprecated


class ExportClass(object):
    label = None
    file_ext = None
    content_type = None

    def __init__(self, rows):
        self.rows = rows

    def represented(self):
        def none_exception(value):
            """
            returns a cleaned up value that can be used for csv export:
            - unicode text is encoded as such
            - None values are replaced with the given representation (default <NULL>)
            """
            if value is None:
                return '<NULL>'
            elif isinstance(value, unicode):
                return value.encode('utf8')
            elif isinstance(value,Reference):
                return int(value)
            elif hasattr(value, 'isoformat'):
                return value.isoformat()[:19].replace('T', ' ')
            elif isinstance(value, (list,tuple)): # for type='list:..'
                return bar_encode(value)
            return value

        represented = []
        for record in self.rows:
            row = []
            for col in self.rows.colnames:
                if not REGEX_TABLE_DOT_FIELD.match(col):
                    row.append(record._extra[col])
                else:
                    (t, f) = col.split('.')
                    field = self.rows.db[t][f]
                    if isinstance(record.get(t, None), (Row,dict)):
                        value = record[t][f]
                    else:
                        value = record[f]
                    if field.type=='blob' and not value is None:
                        value = ''
                    elif field.represent:
                        value = field.represent(value, record)
                    row.append(none_exception(value))

            represented.append(row)
        return represented

    def export(self):
        raise NotImplementedError

class ExporterTSV(ExportClass):

    label = 'TSV'
    file_ext = "csv"
    content_type = "text/tab-separated-values"

    def __init__(self, rows):
        ExportClass.__init__(self, rows)

    def export(self):

        out = cStringIO.StringIO()
        final = cStringIO.StringIO()
        import csv
        writer = csv.writer(out, delimiter='\t')
        import codecs
        final.write(codecs.BOM_UTF16)
        colnames = [a.split('.') for a in self.rows.colnames]
        writer.writerow([unicode(col).encode("utf8") for col in self.rows.colnames])
        data = out.getvalue().decode("utf8")
        data = data.encode("utf-16")
        data = data[2:]
        final.write(data)
        out.truncate(0)
        records = self.represented()
        for row in records:
            writer.writerow([str(col).decode('utf8').encode("utf-8") for col in row])
            data = out.getvalue().decode("utf8")
            data = data.encode("utf-16")
            data = data[2:]
            final.write(data)
            out.truncate(0)
        return str(final.getvalue())

class ExporterCSV(ExportClass):
    label = 'CSV'
    file_ext = "csv"
    content_type = "text/csv"

    def __init__(self, rows):
        ExportClass.__init__(self, rows)

    def export(self):
        return str(self.rows)

class ExporterHTML(ExportClass):
    label = 'HTML'
    file_ext = "html"
    content_type = "text/html"

    def __init__(self, rows):
        ExportClass.__init__(self, rows)

    def export(self):
        out = cStringIO.StringIO()
        out.write('<html>\n<body>\n<table>\n')
        colnames = [a.split('.') for a in self.rows.colnames]
        for row in self.rows.records:
            out.write('<tr>\n')
            for col in colnames:
                out.write('<td>'+str(row[col[0]][col[1]])+'</td>\n')
            out.write('</tr>\n')
        out.write('</table>\n</body>\n</html>')
        return str(out.getvalue())


class ExporterXML(ExportClass):
    label = 'XML'
    file_ext = "xml"
    content_type = "text/xml"

    def __init__(self, rows):
        ExportClass.__init__(self, rows)

    def export(self):
        out = cStringIO.StringIO()
        out.write('<rows>\n')
        colnames = [a.split('.') for a in self.rows.colnames]
        for row in self.rows.records:
            out.write('<row>\n')
            for col in colnames:
                out.write('<%s>'%col+str(row[col[0]][col[1]])+'</%s>\n'%col)
            out.write('</row>\n')
        out.write('</rows>')
        return str(out.getvalue())





