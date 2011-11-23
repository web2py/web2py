#!/usr/bin/python
# -*- coding: latin-1 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"Simple XML manipulation"

__author__ = "Mariano Reingart (reingart@gmail.com)"
__copyright__ = "Copyright (C) 2008/009 Mariano Reingart"
__license__ = "LGPL 3.0"
__version__ = "1.02c"

import xml.dom.minidom
from decimal import Decimal
import datetime
import time

DEBUG = False

# Functions to serialize/unserialize special immutable types:
datetime_u = lambda s: datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
datetime_m = lambda dt: dt.isoformat('T')
date_u = lambda s: datetime.datetime.strptime(s[0:10], "%Y-%m-%d").date()
date_m = lambda d: d.strftime("%Y-%m-%d")
time_u = lambda s: datetime.datetime.strptime(s, "%H:%M:%S").time()
time_m = lambda d: d.strftime("%H%M%S")
bool_u = lambda s: {'0':False, 'false': False, '1': True, 'true': True}[s]

# aliases:
class Alias():
    def __init__(self, py_type, xml_type):
        self.py_type, self.xml_type = py_type, xml_type
    def __call__(self, value):
        return self.py_type(value)
    def __repr__(self):
        return "<alias '%s' for '%s'>" % (self.xml_type, self.py_type)

byte = Alias(str,'byte')
short = Alias(int,'short')
double = Alias(float,'double')
integer = Alias(long,'integer')
DateTime = datetime.datetime
Date = datetime.date
Time = datetime.time

# Define convertion function (python type): xml schema type
TYPE_MAP = {str:'string',unicode:'string',
            bool:'boolean', short:'short', byte:'byte',
            int:'int', long:'long', integer:'integer',
            float:'float', double:'double',
            Decimal:'decimal',
            datetime.datetime:'dateTime', datetime.date:'date',
            }
TYPE_MARSHAL_FN = {datetime.datetime:datetime_m, datetime.date:date_m,}
TYPE_UNMARSHAL_FN = {datetime.datetime:datetime_u, datetime.date:date_u,
                     bool:bool_u,
            }


class OrderedDict(dict):
    "Minimal ordered dictionary for xsd:sequences"
    def __init__(self):
        self.__keys = []
        self.array = False
    def __setitem__(self, key, value):
        if key not in self.__keys:
            self.__keys.append(key)
        dict.__setitem__(self, key, value)
    def insert(self, key, value, index=0):
        if key not in self.__keys:
            self.__keys.insert(index, key)
        dict.__setitem__(self, key, value)
    def __delitem__(self, key):
        if key in self.__keys:
            self.__keys.remove(key)
        dict.__delitem__(self, key)
    def __iter__(self):
        return iter(self.__keys)
    def keys(self):
        return self.__keys
    def items(self):
        return [(key, self[key]) for key in self.__keys]
    def update(self, other):
        for k,v in other.items():
            self[k] = v
        if isinstance(other, OrderedDict):
            self.array = other.array
    def __str__(self):
        return "*%s*" % dict.__str__(self)
    def __repr__(self):
        s= "*{%s}*" % ", ".join(['%s: %s' % (repr(k),repr(v)) for k,v in self.items()])
        if self.array and False:
            s = "[%s]" % s
        return s


class SimpleXMLElement(object):
    "Simple XML manipulation (simil PHP)"

    def __init__(self, text = None, elements = None, document = None, namespace = None, prefix=None):
        self.__ns = namespace
        self.__prefix = prefix
        if text:
            try:
                self.__document = xml.dom.minidom.parseString(text)
            except:
                if DEBUG: print text
                raise
            self.__elements = [self.__document.documentElement]
        else:
            self.__elements = elements
            self.__document = document

    def add_child(self,name,text=None,ns=True):
        "Adding a child tag to a node"
        if not ns or not self.__ns:
            if DEBUG: print "adding %s" % (name)
            element = self.__document.createElement(name)
        else:
            if DEBUG: print "adding %s ns %s %s" % (name, self.__ns,ns)
            if self.__prefix:
                element = self.__document.createElementNS(self.__ns, "%s:%s" % (self.__prefix, name))
            else:
                element = self.__document.createElementNS(self.__ns, name)
        if text:
            if isinstance(text, unicode):
                element.appendChild(self.__document.createTextNode(text))
            else:
                element.appendChild(self.__document.createTextNode(str(text)))
        self._element.appendChild(element)
        return SimpleXMLElement(
                    elements=[element],
                    document=self.__document,
                    namespace=self.__ns,
                    prefix=self.__prefix)

    def __setattr__(self, tag, text):
        "Add text child tag node (short form)"
        if tag.startswith("_"):
            object.__setattr__(self, tag, text)
        else:
            if DEBUG: print "__setattr__(%s,%s)" % (tag, text)
            self.add_child(tag,text)

    def add_comment(self, data):
        "Add an xml comment to this child"
        comment = self.__document.createComment(data)
        self._element.appendChild(comment)

    def as_xml(self,filename=None,pretty=False):
        "Return the XML representation of the document"
        if not pretty:
            return self.__document.toxml('UTF-8')
        else:
            return self.__document.toprettyxml(encoding='UTF-8')

    def __repr__(self):
        "Return the XML representation of this tag"
        return self._element.toxml('UTF-8')

    def get_name(self):
        "Return the tag name of this node"
        return self._element.tagName

    def get_local_name(self):
        "Return the tag loca name (prefix:name) of this node"
        return self._element.localName

    def get_prefix(self):
        "Return the namespace prefix of this node"
        return self._element.prefix

    def get_namespace_uri(self, ns):
        "Return the namespace uri for a prefix"
        v = self.__document.documentElement.attributes['xmlns:%s' % ns]
        return v.value

    def attributes(self):
        "Return a dict of attributes for this tag"
        #TODO: use slice syntax [:]?
        return self._element.attributes

    def __getitem__(self, item):
        "Return xml tag attribute value or a slice of attributes (iter)"
        if DEBUG: print "__getitem__(%s)" % item
        if isinstance(item,basestring):
            if self._element.hasAttribute(item):
                return self._element.attributes[item].value
        elif isinstance(item, slice):
            # return a list with name:values
            return self._element.attributes.items()[item]
        else:
            # return element by index (position)
            element = self.__elements[item]
            return SimpleXMLElement(
                    elements=[element],
                    document=self.__document,
                    namespace=self.__ns,
                    prefix=self.__prefix)

    def add_attribute(self, name, value):
        "Set an attribute value from a string"
        self._element.setAttribute(name, value)

    def __setitem__(self, item, value):
        "Set an attribute value"
        if isinstance(item,basestring):
            self.add_attribute(item, value)
        elif isinstance(item, slice):
            # set multiple attributes at once
            for k, v in value.items():
                self.add_attribute(k, v)

    def __call__(self, tag=None, ns=None, children=False, error=True):
        "Search (even in child nodes) and return a child tag by name"
        try:
            if tag is None:
                # if no name given, iterate over siblings (same level)
                return self.__iter__()
            if children:
                # future: filter children? by ns?
                return self.children()
            elements = None
            if isinstance(tag, int):
                # return tag by index
                elements=[self.__elements[tag]]
            if ns and not elements:
                for ns_uri in isinstance(ns, (tuple, list)) and ns or (ns, ):
                    if DEBUG: print "searching %s by ns=%s" % (tag,ns_uri)
                    elements = self._element.getElementsByTagNameNS(ns_uri, tag)
                    if elements:
                        break
            if self.__ns and not elements:
                if DEBUG: print "searching %s by ns=%s" % (tag, self.__ns)
                elements = self._element.getElementsByTagNameNS(self.__ns, tag)
            if not elements:
                if DEBUG: print "searching %s " % (tag)
                elements = self._element.getElementsByTagName(tag)
            if not elements:
                if DEBUG: print self._element.toxml()
                if error:
                    raise AttributeError("No elements found")
                else:
                    return
            return SimpleXMLElement(
                elements=elements,
                document=self.__document,
                namespace=self.__ns,
                prefix=self.__prefix)
        except AttributeError, e:
            raise AttributeError("Tag not found: %s (%s)" % (tag, str(e)))

    def __getattr__(self, tag):
        "Shortcut for __call__"
        return self.__call__(tag)

    def __iter__(self):
        "Iterate over xml tags at this level"
        try:
            for __element in self.__elements:
                yield SimpleXMLElement(
                    elements=[__element],
                    document=self.__document,
                    namespace=self.__ns,
                    prefix=self.__prefix)
        except:
            raise

    def __dir__(self):
        "List xml children tags names"
        return [node.tagName for node
                in self._element.childNodes
                if node.nodeType != node.TEXT_NODE]

    def children(self):
        "Return xml children tags element"
        elements=[__element for __element in self._element.childNodes
                          if __element.nodeType == __element.ELEMENT_NODE]
        if not elements:
            return None
            #raise IndexError("Tag %s has no children" % self._element.tagName)
        return SimpleXMLElement(
                elements=elements,
                document=self.__document,
                namespace=self.__ns,
                prefix=self.__prefix)

    def __len__(self):
        "Return elements count"
        return len(self.__elements)

    def __contains__( self, item):
        "Search for a tag name in this element or child nodes"
        return self._element.getElementsByTagName(item)

    def __unicode__(self):
        "Returns the unicode text nodes of the current element"
        if self._element.childNodes:
            rc = u""
            for node in self._element.childNodes:
                if node.nodeType == node.TEXT_NODE:
                    rc = rc + node.data
            return rc
        return ''

    def __str__(self):
        "Returns the str text nodes of the current element"
        return unicode(self).encode("utf8","ignore")

    def __int__(self):
        "Returns the integer value of the current element"
        return int(self.__str__())

    def __float__(self):
        "Returns the float value of the current element"
        try:
            return float(self.__str__())
        except:
            raise IndexError(self._element.toxml())

    _element = property(lambda self: self.__elements[0])

    def unmarshall(self, types):
        "Convert to python values the current serialized xml element"
        # types is a dict of {tag name: convertion function}
        # example: types={'p': {'a': int,'b': int}, 'c': [{'d':str}]}
        #   expected xml: <p><a>1</a><b>2</b></p><c><d>hola</d><d>chau</d>
        #   returnde value: {'p': {'a':1,'b':2}, `'c':[{'d':'hola'},{'d':'chau'}]}
        d = {}
        for node in self():
            name = str(node.get_local_name())
            try:
                fn = types[name]
            except (KeyError, ), e:
                raise TypeError("Tag: %s invalid" % (name,))
            if isinstance(fn,list):
                value = []
                children = node.children()
                for child in children and children() or []:
                    value.append(child.unmarshall(fn[0]))
            elif isinstance(fn,dict):
                children = node.children()
                value = children and children.unmarshall(fn)
            else:
                if fn is None: # xsd:anyType not unmarshalled
                    value = node
                elif str(node) or fn == str:
                    try:
                        # get special desserialization function (if any)
                        fn = TYPE_UNMARSHAL_FN.get(fn,fn)
                        value = fn(unicode(node))
                    except (ValueError, TypeError), e:
                        raise ValueError("Tag: %s: %s" % (name, unicode(e)))
                else:
                    value = None
            d[name] = value
        return d

    def marshall(self, name, value, add_child=True, add_comments=False, ns=False):
        "Analize python value and add the serialized XML element using tag name"
        if isinstance(value, dict):  # serialize dict (<key>value</key>)
            child = add_child and self.add_child(name,ns=ns) or self
            for k,v in value.items():
                child.marshall(k, v, add_comments=add_comments, ns=ns)
        elif isinstance(value, tuple):  # serialize tuple (<key>value</key>)
            child = add_child and self.add_child(name,ns=ns) or self
            for k,v in value:
                getattr(self,name).marshall(k, v, add_comments=add_comments, ns=ns)
        elif isinstance(value, list): # serialize lists
            child=self.add_child(name,ns=ns)
            if add_comments:
                child.add_comment("Repetitive array of:")
            for t in value:
                child.marshall(name,t, False, add_comments=add_comments, ns=ns)
        elif isinstance(value, basestring): # do not convert strings or unicodes
            self.add_child(name,value,ns=ns)
        elif value is None: # sent a empty tag?
            self.add_child(name,ns=ns)
        elif value in TYPE_MAP.keys():
            # add commented placeholders for simple tipes (for examples/help only)
            child = self.add_child(name,ns=ns)
            child.add_comment(TYPE_MAP[value])
        else: # the rest of object types are converted to string
            # get special serialization function (if any)
            fn = TYPE_MARSHAL_FN.get(type(value),str)
            self.add_child(name,fn(value),ns=ns)

    def import_node(self, other):
        x = self.__document.importNode(other._element, True)  # deep copy
        self._element.appendChild(x)


if __name__ == "__main__":
    span = SimpleXMLElement('<span><a href="python.org.ar">pyar</a><prueba><i>1</i><float>1.5</float></prueba></span>')
    assert str(span.a)==str(span('a'))==str(span.a(0))=="pyar"
    assert span.a['href']=="python.org.ar"
    assert int(span.prueba.i)==1 and float(span.prueba.float)==1.5
    span1 = SimpleXMLElement('<span><a href="google.com">google</a><a>yahoo</a><a>hotmail</a></span>')
    assert [str(a) for a in span1.a()] == ['google', 'yahoo', 'hotmail']
    span1.add_child('a','altavista')
    span1.b = "ex msn"
    d = {'href':'http://www.bing.com/', 'alt': 'Bing'}
    span1.b[:] = d
    assert sorted([(k,v) for k,v in span1.b[:]]) == sorted(d.items())
    print span1.as_xml()
    assert 'b' in span1
    span.import_node(span1)
    print span.as_xml()

