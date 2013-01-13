#!/usr/bin/env python
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
__version__ = "1.03a"

import datetime
import logging
import re
import time
import warnings
import xml.dom.minidom
from decimal import Decimal

log = logging.getLogger(__name__)
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARNING)

DEBUG = False

try:
    _strptime = datetime.datetime.strptime
except AttributeError:  # python2.4
    _strptime = lambda s, fmt: datetime.datetime(*(time.strptime(s, fmt)[:6]))


# Functions to serialize/deserialize special immutable types:
def datetime_u(s):
    fmt = "%Y-%m-%dT%H:%M:%S"
    try:
        return _strptime(s, fmt)
    except ValueError:
        try:
            # strip utc offset
            if s[-3] == ":" and s[-6] in (' ', '-', '+'):
                warnings.warn('removing unsupported UTC offset', RuntimeWarning) 
                s = s[:-6]
            # parse microseconds
            try:
                return _strptime(s, fmt + ".%f")
            except:
                return _strptime(s, fmt)
        except ValueError:
            # strip microseconds (not supported in this platform)
            if "." in s:
                warnings.warn('removing unsuppported microseconds', RuntimeWarning) 
                s = s[:s.index(".")]
            return _strptime(s, fmt)
                
datetime_m = lambda dt: dt.isoformat('T')
date_u = lambda s: _strptime(s[0:10], "%Y-%m-%d").date()
date_m = lambda d: d.strftime("%Y-%m-%d")
time_u = lambda s: _strptime(s, "%H:%M:%S").time()
time_m = lambda d: d.strftime("%H%M%S")
bool_u = lambda s: {'0':False, 'false': False, '1': True, 'true': True}[s]
bool_m = lambda s: {False: 'false', True: 'true'}[s]

# aliases:
class Alias(object):
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
TYPE_MAP = {
    str:'string',
    unicode:'string',
    bool:'boolean', 
    short:'short', 
    byte:'byte',
    int:'int', 
    long:'long', 
    integer:'integer', 
    float:'float', 
    double:'double',
    Decimal:'decimal',
    datetime.datetime:'dateTime', 
    datetime.date:'date',
}
TYPE_MARSHAL_FN = {
    datetime.datetime:datetime_m, 
    datetime.date:date_m,
    bool:bool_m
}
TYPE_UNMARSHAL_FN = {
    datetime.datetime:datetime_u, 
    datetime.date:date_u,
    bool:bool_u, 
    str:unicode,
}

REVERSE_TYPE_MAP = dict([(v,k) for k,v in TYPE_MAP.items()])

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
    
    def __init__(self, text = None, elements = None, document = None, 
                 namespace = None, prefix=None, namespaces_map={}):
        """
        :param namespaces_map: How to map our namespace prefix to that given by the client;
          {prefix: received_prefix}
        """
        self.__namespaces_map = namespaces_map
        _rx = "|".join(namespaces_map.keys()) # {'external': 'ext', 'model': 'mod'} -> 'external|model'
        self.__ns_rx = re.compile(r"^(%s):.*$" % _rx) # And now we build an expression ^(external|model):.*$
                                                      # to find prefixes in all xml nodes i.e.: <model:code>1</model:code>
                                                      # and later change that to <mod:code>1</mod:code>
        self.__ns = namespace
        self.__prefix = prefix
        
        if text is not None:
            try:
                self.__document = xml.dom.minidom.parseString(text)
            except:
                log.error(text)
                raise
            self.__elements = [self.__document.documentElement]
        else:
            self.__elements = elements
            self.__document = document
        
    def add_child(self, name, text=None, ns=True):
        "Adding a child tag to a node"
        if not ns or not self.__ns:
            log.debug('adding %s', name)
            element = self.__document.createElement(name)
        else:
            log.debug('adding %s ns "%s" %s', name, self.__ns, ns)
            if self.__prefix:
                element = self.__document.createElementNS(self.__ns, "%s:%s" % (self.__prefix, name))
            else:
                element = self.__document.createElementNS(self.__ns, name)
        # don't append null tags!
        if text is not None:
            if isinstance(text, unicode):
                element.appendChild(self.__document.createTextNode(text))
            else:
                element.appendChild(self.__document.createTextNode(str(text)))
        self._element.appendChild(element)
        return SimpleXMLElement(
                    elements=[element],
                    document=self.__document,
                    namespace=self.__ns,
                    prefix=self.__prefix,
                    namespaces_map=self.__namespaces_map)
    
    def __setattr__(self, tag, text):
        "Add text child tag node (short form)"
        if tag.startswith("_"):
            object.__setattr__(self, tag, text)
        else:
            log.debug('__setattr__(%s, %s)', tag, text)
            self.add_child(tag, text)

    def __delattr__(self, tag):
        "Remove a child tag (non recursive!)"
        elements=[__element for __element in self._element.childNodes
                          if __element.nodeType == __element.ELEMENT_NODE
                         ]
        for element in elements:
            self._element.removeChild(element)

    def add_comment(self, data):
        "Add an xml comment to this child"
        comment = self.__document.createComment(data)
        self._element.appendChild(comment)

    def as_xml(self, filename=None, pretty=False):
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
        element = self._element
        while element is not None and element.attributes is not None:
            try:
                return element.attributes['xmlns:%s' % ns].value
            except KeyError:
                element = element.parentNode


    def attributes(self):
        "Return a dict of attributes for this tag"
        #TODO: use slice syntax [:]?
        return self._element.attributes

    def __getitem__(self, item):
        "Return xml tag attribute value or a slice of attributes (iter)"
        log.debug('__getitem__(%s)', item)
        if isinstance(item, basestring):
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
                    prefix=self.__prefix,
                    namespaces_map=self.__namespaces_map)
            
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

    def __call__(self, tag=None, ns=None, children=False, root=False,
                 error=True, ):
        "Search (even in child nodes) and return a child tag by name"
        try:
            if root:
                # return entire document
                return SimpleXMLElement(
                    elements=[self.__document.documentElement],
                    document=self.__document,
                    namespace=self.__ns,
                    prefix=self.__prefix,
                    namespaces_map=self.__namespaces_map
                )
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
                    log.debug('searching %s by ns=%s', tag, ns_uri)
                    elements = self._element.getElementsByTagNameNS(ns_uri, tag)
                    if elements: 
                        break
            if self.__ns and not elements:
                log.debug('searching %s by ns=%s', tag, self.__ns)
                elements = self._element.getElementsByTagNameNS(self.__ns, tag)
            if not elements:
                log.debug('searching %s', tag)
                elements = self._element.getElementsByTagName(tag)
            if not elements:
                #log.debug(self._element.toxml())
                if error:
                    raise AttributeError(u"No elements found")
                else:
                    return
            return SimpleXMLElement(
                elements=elements,
                document=self.__document,
                namespace=self.__ns,
                prefix=self.__prefix,
                namespaces_map=self.__namespaces_map)
        except AttributeError, e:
            raise AttributeError(u"Tag not found: %s (%s)" % (tag, unicode(e)))

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
                    prefix=self.__prefix,
                    namespaces_map=self.__namespaces_map)
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
                prefix=self.__prefix,
                namespaces_map=self.__namespaces_map)

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

    def unmarshall(self, types, strict=True):
        "Convert to python values the current serialized xml element"
        # types is a dict of {tag name: convertion function}
        # strict=False to use default type conversion if not specified
        # example: types={'p': {'a': int,'b': int}, 'c': [{'d':str}]}
        #   expected xml: <p><a>1</a><b>2</b></p><c><d>hola</d><d>chau</d>
        #   returnde value: {'p': {'a':1,'b':2}, `'c':[{'d':'hola'},{'d':'chau'}]}
        d = {}
        for node in self():
            name = str(node.get_local_name())
            ref_name_type = None
            # handle multirefs: href="#id0"
            if 'href' in node.attributes().keys():
                href = node['href'][1:]
                for ref_node in self(root=True)("multiRef"):
                    if ref_node['id'] == href:
                        node = ref_node
                        ref_name_type = ref_node['xsi:type'].split(":")[1]
                        break
            try:
                fn = types[name]
            except (KeyError, ), e:
                if node.get_namespace_uri("soapenc"):
                    fn = None # ignore multirefs!
                elif 'xsi:type' in node.attributes().keys():
                    xsd_type = node['xsi:type'].split(":")[1]
                    fn = REVERSE_TYPE_MAP[xsd_type]
                elif strict:
                    raise TypeError(u"Tag: %s invalid (type not found)" % (name,))
                else:
                    # if not strict, use default type conversion
                    fn = unicode
            
            if isinstance(fn, list):
                # append to existing list (if any) - unnested dict arrays -
                value = d.setdefault(name, [])
                children = node.children()
                for child in (children and children() or []): # Readability counts
                    value.append(child.unmarshall(fn[0], strict))
            
            elif isinstance(fn, tuple):
                value = []
                _d = {}
                children = node.children()
                as_dict = len(fn) == 1 and isinstance(fn[0], dict)

                for child in (children and children() or []): # Readability counts
                    if as_dict:
                        _d.update(child.unmarshall(fn[0], strict)) # Merging pairs
                    else:
                        value.append(child.unmarshall(fn[0], strict))
                if as_dict:
                    value.append(_d)

                if name in d:
                    _tmp = list(d[name])
                    _tmp.extend(value)
                    value = tuple(_tmp)
                else:
                    value = tuple(value)
            
            elif isinstance(fn, dict):
                ##if ref_name_type is not None:
                ##    fn = fn[ref_name_type]
                children = node.children()
                value = children and children.unmarshall(fn, strict)
            else:
                if fn is None: # xsd:anyType not unmarshalled
                    value = node
                elif str(node) or fn == str:
                    try:
                        # get special deserialization function (if any)
                        fn = TYPE_UNMARSHAL_FN.get(fn,fn) 
                        if fn == str:
                            # always return an unicode object:
                            value = unicode(node)
                        else:
                            value = fn(unicode(node))
                    except (ValueError, TypeError), e:
                        raise ValueError(u"Tag: %s: %s" % (name, unicode(e)))
                else:
                    value = None
            d[name] = value
        return d
    
    
    def _update_ns(self, name):
        """Replace the defined namespace alias with tohse used by the client."""
        pref = self.__ns_rx.search(name)
        if pref:
            pref = pref.groups()[0]
            try:
                name = name.replace(pref, self.__namespaces_map[pref])
            except KeyError:
                log.warning('Unknown namespace alias %s' % name)
        return name
    
    
    def marshall(self, name, value, add_child=True, add_comments=False, 
                 ns=False, add_children_ns=True):
        "Analize python value and add the serialized XML element using tag name"
        # Change node name to that used by a client
        name = self._update_ns(name)
        
        if isinstance(value, dict):  # serialize dict (<key>value</key>)
            child = add_child and self.add_child(name, ns=ns) or self
            for k,v in value.items():
                if not add_children_ns:
                    ns = False
                child.marshall(k, v, add_comments=add_comments, ns=ns)
        elif isinstance(value, tuple):  # serialize tuple (<key>value</key>)
            child = add_child and self.add_child(name, ns=ns) or self
            if not add_children_ns:
                ns = False
            for k,v in value:
                getattr(self, name).marshall(k, v, add_comments=add_comments, ns=ns)
        elif isinstance(value, list): # serialize lists
            child=self.add_child(name, ns=ns)
            if not add_children_ns:
                ns = False
            if add_comments:
                child.add_comment("Repetitive array of:")
            for t in value:
                child.marshall(name, t, False, add_comments=add_comments, ns=ns)
        elif isinstance(value, basestring): # do not convert strings or unicodes
            self.add_child(name, value,ns=ns)
        elif value is None: # sent a empty tag?
            self.add_child(name, ns=ns)
        elif value in TYPE_MAP.keys():
            # add commented placeholders for simple tipes (for examples/help only)
            child = self.add_child(name, ns=ns) 
            child.add_comment(TYPE_MAP[value])
        else: # the rest of object types are converted to string 
            # get special serialization function (if any)
            fn = TYPE_MARSHAL_FN.get(type(value), str)
            self.add_child(name, fn(value), ns=ns) 

    def import_node(self, other):
        x = self.__document.importNode(other._element, True)  # deep copy
        self._element.appendChild(x)
