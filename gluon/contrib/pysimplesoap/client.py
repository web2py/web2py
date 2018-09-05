#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

"""Pythonic simple SOAP Client implementation"""

from __future__ import unicode_literals
import sys
if sys.version > '3':
    unicode = str

try:
    import cPickle as pickle
except ImportError:
    import pickle
import copy
import hashlib
import logging
import os
import tempfile
import warnings

from . import __author__, __copyright__, __license__, __version__, TIMEOUT
from .simplexml import SimpleXMLElement, TYPE_MAP, REVERSE_TYPE_MAP, Struct
from .transport import get_http_wrapper, set_http_wrapper, get_Http
# Utility functions used throughout wsdl_parse, moved aside for readability
from .helpers import Alias, fetch, sort_dict, make_key, process_element, \
                     postprocess_element, get_message, preprocess_schema, \
                     get_local_name, get_namespace_prefix, TYPE_MAP, urlsplit
from .wsse import UsernameToken

log = logging.getLogger(__name__)

class SoapFault(RuntimeError):
    def __init__(self, faultcode, faultstring, detail=None):
        self.faultcode = faultcode
        self.faultstring = faultstring
        self.detail = detail
        RuntimeError.__init__(self, faultcode, faultstring, detail)

    def __unicode__(self):
        return '%s: %s' % (self.faultcode, self.faultstring)

    if sys.version > '3':
        __str__ = __unicode__
    else:
        def __str__(self):
            return self.__unicode__().encode('ascii', 'ignore')

    def __repr__(self):
        return "SoapFault(faultcode = %s, faultstring %s, detail = %s)" % (repr(self.faultcode),
                                                                           repr(self.faultstring),
                                                                           repr(self.detail))


# soap protocol specification & namespace
soap_namespaces = dict(
    soap11='http://schemas.xmlsoap.org/soap/envelope/',
    soap='http://schemas.xmlsoap.org/soap/envelope/',
    soapenv='http://schemas.xmlsoap.org/soap/envelope/',
    soap12='http://www.w3.org/2003/05/soap-env',
    soap12env="http://www.w3.org/2003/05/soap-envelope",
)


class SoapClient(object):
    """Simple SOAP Client (simil PHP)"""
    def __init__(self, location=None, action=None, namespace=None,
                 cert=None, exceptions=True, proxy=None, ns=None,
                 soap_ns=None, wsdl=None, wsdl_basedir='', cache=False, cacert=None,
                 sessions=False, soap_server=None, timeout=TIMEOUT,
                 http_headers=None, trace=False,
                 username=None, password=None,
                 key_file=None, plugins=None, strict=True,
                 ):
        """
        :param http_headers: Additional HTTP Headers; example: {'Host': 'ipsec.example.com'}
        """
        self.certssl = cert
        self.keyssl = key_file
        self.location = location        # server location (url)
        self.action = action            # SOAP base action
        self.namespace = namespace      # message
        self.exceptions = exceptions    # lanzar execpiones? (Soap Faults)
        self.xml_request = self.xml_response = ''
        self.http_headers = http_headers or {}
        self.plugins = plugins or []
        self.strict = strict
        # extract the base directory / url for wsdl relative imports:
        if wsdl and wsdl_basedir == '':
            # parse the wsdl url, strip the scheme and filename
            url_scheme, netloc, path, query, fragment = urlsplit(wsdl)
            wsdl_basedir = os.path.dirname(netloc + path)

        self.wsdl_basedir = wsdl_basedir

        # shortcut to print all debugging info and sent / received xml messages
        if trace:
            if trace is True:
                level = logging.DEBUG           # default logging level
            else:
                level = trace                   # use the provided level
            logging.basicConfig(level=level)
            log.setLevel(level)

        if not soap_ns and not ns:
            self.__soap_ns = 'soap'  # 1.1
        elif not soap_ns and ns:
            self.__soap_ns = 'soapenv'  # 1.2
        else:
            self.__soap_ns = soap_ns

        # SOAP Server (special cases like oracle, jbossas6 or jetty)
        self.__soap_server = soap_server

        # SOAP Header support
        self.__headers = {}         # general headers
        self.__call_headers = None  # Struct to be marshalled for RPC Call

        # check if the Certification Authority Cert is a string and store it
        if cacert and cacert.startswith('-----BEGIN CERTIFICATE-----'):
            fd, filename = tempfile.mkstemp()
            f = os.fdopen(fd, 'w+b', -1)
            log.debug("Saving CA certificate to %s" % filename)
            f.write(cacert)
            cacert = filename
            f.close()
        self.cacert = cacert

        # Create HTTP wrapper
        Http = get_Http()
        self.http = Http(timeout=timeout, cacert=cacert, proxy=proxy, sessions=sessions)
        if username and password:
            if hasattr(self.http, 'add_credentials'):
                self.http.add_credentials(username, password)
        if cert and key_file:
            if hasattr(self.http, 'add_certificate'):
                self.http.add_certificate(key=key_file, cert=cert, domain='')


        # namespace prefix, None to use xmlns attribute or False to not use it:
        self.__ns = ns
        if not ns:
            self.__xml = """<?xml version="1.0" encoding="UTF-8"?>
<%(soap_ns)s:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:%(soap_ns)s="%(soap_uri)s">
<%(soap_ns)s:Header/>
<%(soap_ns)s:Body>
    <%(method)s xmlns="%(namespace)s">
    </%(method)s>
</%(soap_ns)s:Body>
</%(soap_ns)s:Envelope>"""
        else:
            self.__xml = """<?xml version="1.0" encoding="UTF-8"?>
<%(soap_ns)s:Envelope xmlns:%(soap_ns)s="%(soap_uri)s" xmlns:%(ns)s="%(namespace)s">
<%(soap_ns)s:Header/>
<%(soap_ns)s:Body><%(ns)s:%(method)s></%(ns)s:%(method)s></%(soap_ns)s:Body></%(soap_ns)s:Envelope>"""

        # parse wsdl url
        self.services = wsdl and self.wsdl_parse(wsdl, cache=cache)
        self.service_port = None                 # service port for late binding

    def __getattr__(self, attr):
        """Return a pseudo-method that can be called"""
        if not self.services:  # not using WSDL?
            return lambda *args, **kwargs: self.call(attr, *args, **kwargs)
        else:  # using WSDL:
            return lambda *args, **kwargs: self.wsdl_call(attr, *args, **kwargs)

    def call(self, method, *args, **kwargs):
        """Prepare xml request and make SOAP call, returning a SimpleXMLElement.

        If a keyword argument called "headers" is passed with a value of a
        SimpleXMLElement object, then these headers will be inserted into the
        request.
        """
        #TODO: method != input_message
        # Basic SOAP request:
        soap_uri = soap_namespaces[self.__soap_ns]
        xml = self.__xml % dict(method=method,              # method tag name
                                namespace=self.namespace,   # method ns uri
                                ns=self.__ns,               # method ns prefix
                                soap_ns=self.__soap_ns,     # soap prefix & uri
                                soap_uri=soap_uri)
        request = SimpleXMLElement(xml, namespace=self.__ns and self.namespace,
                                        prefix=self.__ns)

        request_headers = kwargs.pop('headers', None)

        # serialize parameters
        if kwargs:
            parameters = list(kwargs.items())
        else:
            parameters = args
        if parameters and isinstance(parameters[0], SimpleXMLElement):
            body = request('Body', ns=list(soap_namespaces.values()),)
            # remove default body parameter (method name)
            delattr(body, method)
            # merge xmlelement parameter ("raw" - already marshalled)
            body.import_node(parameters[0])
        elif parameters:
            # marshall parameters:
            use_ns = None if (self.__soap_server == "jetty" or self.qualified is False) else True
            for k, v in parameters:  # dict: tag=valor
                if hasattr(v, "namespaces") and use_ns:
                    ns = v.namespaces.get(None, True)
                else:
                    ns = use_ns
                getattr(request, method).marshall(k, v, ns=ns)
        elif self.__soap_server in ('jbossas6',):
            # JBossAS-6 requires no empty method parameters!
            delattr(request("Body", ns=list(soap_namespaces.values()),), method)

        # construct header and parameters (if not wsdl given) except wsse
        if self.__headers and not self.services:
            self.__call_headers = dict([(k, v) for k, v in self.__headers.items()
                                        if not k.startswith('wsse:')])
        # always extract WS Security header and send it (backward compatible)
        if 'wsse:Security' in self.__headers and not self.plugins:
            warnings.warn("Replace wsse:Security with UsernameToken plugin",
                          DeprecationWarning)
            self.plugins.append(UsernameToken())

        if self.__call_headers:
            header = request('Header', ns=list(soap_namespaces.values()),)
            for k, v in self.__call_headers.items():
                ##if not self.__ns:
                ##    header['xmlns']
                if isinstance(v, SimpleXMLElement):
                    # allows a SimpleXMLElement to be constructed and inserted
                    # rather than a dictionary. marshall doesn't allow ns: prefixes
                    # in dict key names
                    header.import_node(v)
                else:
                    header.marshall(k, v, ns=self.__ns, add_children_ns=False)
        if request_headers:
            header = request('Header', ns=list(soap_namespaces.values()),)
            for subheader in request_headers.children():
                header.import_node(subheader)

        # do pre-processing using plugins (i.e. WSSE signing)
        for plugin in self.plugins:
            plugin.preprocess(self, request, method, args, kwargs,
                                    self.__headers, soap_uri)

        self.xml_request = request.as_xml()
        self.xml_response = self.send(method, self.xml_request)
        response = SimpleXMLElement(self.xml_response, namespace=self.namespace,
                                    jetty=self.__soap_server in ('jetty',))
        if self.exceptions and response("Fault", ns=list(soap_namespaces.values()), error=False):
            detailXml = response("detail", ns=list(soap_namespaces.values()), error=False)
            detail = None

            if detailXml and detailXml.children():
                if self.services is not None:
                    operation = self.get_operation(method)
                    fault_name = detailXml.children()[0].get_name()
                    # if fault not defined in WSDL, it could be an axis or other 
                    # standard type (i.e. "hostname"), try to convert it to string 
                    fault = operation['faults'].get(fault_name) or unicode
                    detail = detailXml.children()[0].unmarshall(fault, strict=False)
                else:
                    detail = repr(detailXml.children())

            raise SoapFault(unicode(response.faultcode),
                            unicode(response.faultstring),
                            detail)

        # do post-processing using plugins (i.e. WSSE signature verification)
        for plugin in self.plugins:
            plugin.postprocess(self, response, method, args, kwargs,
                                     self.__headers, soap_uri)

        return response

    def send(self, method, xml):
        """Send SOAP request using HTTP"""
        if self.location == 'test': return
        # location = '%s' % self.location #?op=%s" % (self.location, method)
        http_method = str('POST')
        location = str(self.location)

        if self.services:
            soap_action = str(self.action)
        else:
            soap_action = str(self.action) + method

        headers = {
            'Content-type': 'text/xml; charset="UTF-8"',
            'Content-length': str(len(xml)),
        }

        if self.action is not None:
            headers['SOAPAction'] = '"' + soap_action + '"'

        headers.update(self.http_headers)
        log.info("POST %s" % location)
        log.debug('\n'.join(["%s: %s" % (k, v) for k, v in headers.items()]))
        log.debug(xml)

        if sys.version < '3':
            # Ensure http_method, location and all headers are binary to prevent
            # UnicodeError inside httplib.HTTPConnection._send_output.

            # httplib in python3 do the same inside itself, don't need to convert it here
            headers = dict((str(k), str(v)) for k, v in headers.items())

        response, content = self.http.request(
            location, http_method, body=xml, headers=headers)
        self.response = response
        self.content = content

        log.debug('\n'.join(["%s: %s" % (k, v) for k, v in response.items()]))
        log.debug(content)
        return content

    def get_operation(self, method):
        # try to find operation in wsdl file
        soap_ver = self.__soap_ns.startswith('soap12') and 'soap12' or 'soap11'
        if not self.service_port:
            for service_name, service in self.services.items():
                for port_name, port in [port for port in service['ports'].items()]:
                    if port['soap_ver'] == soap_ver:
                        self.service_port = service_name, port_name
                        break
                else:
                    raise RuntimeError('Cannot determine service in WSDL: '
                                       'SOAP version: %s' % soap_ver)
        else:
            port = self.services[self.service_port[0]]['ports'][self.service_port[1]]
        if not self.location:
            self.location = port['location']
        operation = port['operations'].get(method)
        if not operation:
            raise RuntimeError('Operation %s not found in WSDL: '
                               'Service/Port Type: %s' %
                               (method, self.service_port))
        return operation

    def wsdl_call(self, method, *args, **kwargs):
        """Pre and post process SOAP call, input and output parameters using WSDL"""
        return self.wsdl_call_with_args(method, args, kwargs)

    def wsdl_call_with_args(self, method, args, kwargs):
        """Pre and post process SOAP call, input and output parameters using WSDL"""
        soap_uri = soap_namespaces[self.__soap_ns]
        operation = self.get_operation(method)

        # get i/o type declarations:
        input = operation['input']
        output = operation['output']
        header = operation.get('header')
        if 'action' in operation:
            self.action = operation['action']

        if 'namespace' in operation:
            self.namespace = operation['namespace'] or ''
            self.qualified = operation['qualified']

        # construct header and parameters
        if header:
            self.__call_headers = sort_dict(header, self.__headers)
        method, params = self.wsdl_call_get_params(method, input, args, kwargs)

        # call remote procedure
        response = self.call(method, *params)
        # parse results:
        resp = response('Body', ns=soap_uri).children().unmarshall(output, strict=self.strict)
        return resp and list(resp.values())[0]  # pass Response tag children

    def wsdl_call_get_params(self, method, input, args, kwargs):
        """Build params from input and args/kwargs"""
        params = inputname = inputargs = None
        all_args = {}
        if input:
            inputname = list(input.keys())[0]
            inputargs = input[inputname]

        if input and args:
            # convert positional parameters to named parameters:
            d = {}
            for idx, arg in enumerate(args):
                key = list(inputargs.keys())[idx]
                if isinstance(arg, dict):
                    if key not in arg:
                        raise KeyError('Unhandled key %s. use client.help(method)' % key)
                    d[key] = arg[key]
                else:
                    d[key] = arg
            all_args.update({inputname: d})

        if input and (kwargs or all_args):
            if kwargs:
                all_args.update({inputname: kwargs})
            valid, errors, warnings = self.wsdl_validate_params(input, all_args)
            if not valid:
                raise ValueError('Invalid Args Structure. Errors: %s' % errors)
            # sort and filter parameters according to wsdl input structure
            tree = sort_dict(input, all_args)
            root = list(tree.values())[0]
            params = []
            # make a params tuple list suitable for self.call(method, *params)
            for k, v in root.items():
                # fix referenced namespaces as info is lost when calling call
                root_ns = root.namespaces[k]
                if not root.references[k] and isinstance(v, Struct):
                    v.namespaces[None] = root_ns
                params.append((k, v))
            # TODO: check style and document attributes
            if self.__soap_server in ('axis', ):
                # use the operation name
                method = method
            else:
                # use the message (element) name
                method = inputname
        #elif not input:
            #TODO: no message! (see wsmtxca.dummy)
        else:
            params = kwargs and kwargs.items()

        return (method, params)

    def wsdl_validate_params(self, struct, value):
        """Validate the arguments (actual values) for the parameters structure.
           Fail for any invalid arguments or type mismatches."""
        errors = []
        warnings = []
        valid = True

        # Determine parameter type
        if type(struct) == type(value):
            typematch = True
        if not isinstance(struct, dict) and isinstance(value, dict):
            typematch = True    # struct can be a dict or derived (Struct)
        else:
            typematch = False

        if struct == str:
            struct = unicode        # fix for py2 vs py3 string handling

        if not isinstance(struct, (list, dict, tuple)) and struct in TYPE_MAP.keys():
            if not type(value) == struct  and value is not None:
                try:
                    struct(value)       # attempt to cast input to parameter type
                except:
                    valid = False
                    errors.append('Type mismatch for argument value. parameter(%s): %s, value(%s): %s' % (type(struct), struct, type(value), value))

        elif isinstance(struct, list) and len(struct) == 1 and not isinstance(value, list):
            # parameter can have a dict in a list: [{}] indicating a list is allowed, but not needed if only one argument.
            next_valid, next_errors, next_warnings = self.wsdl_validate_params(struct[0], value)
            if not next_valid:
                valid = False
            errors.extend(next_errors)
            warnings.extend(next_warnings)

        # traverse tree
        elif isinstance(struct, dict):
            if struct and value:
                for key in value:
                    if key not in struct:
                        valid = False
                        errors.append('Argument key %s not in parameter. parameter: %s, args: %s' % (key, struct, value))
                    else:
                        next_valid, next_errors, next_warnings = self.wsdl_validate_params(struct[key], value[key])
                        if not next_valid:
                            valid = False
                        errors.extend(next_errors)
                        warnings.extend(next_warnings)
                for key in struct:
                    if key not in value:
                        warnings.append('Parameter key %s not in args. parameter: %s, value: %s' % (key, struct, value))
            elif struct and not value:
                warnings.append('parameter keys not in args. parameter: %s, args: %s' % (struct, value))
            elif not struct and value:
                valid = False
                errors.append('Args keys not in parameter. parameter: %s, args: %s' % (struct, value))
            else:
                pass
        elif isinstance(struct, list):
            struct_list_value = struct[0]
            for item in value:
                next_valid, next_errors, next_warnings = self.wsdl_validate_params(struct_list_value, item)
                if not next_valid:
                    valid = False
                errors.extend(next_errors)
                warnings.extend(next_warnings)
        elif not typematch:
            valid = False
            errors.append('Type mismatch. parameter(%s): %s, value(%s): %s' % (type(struct), struct, type(value), value))

        return (valid, errors, warnings)

    def help(self, method):
        """Return operation documentation and invocation/returned value example"""
        operation = self.get_operation(method)
        input = operation.get('input')
        input = input and input.values() and list(input.values())[0]
        if isinstance(input, dict):
            input = ", ".join("%s=%s" % (k, repr(v)) for k, v in input.items())
        elif isinstance(input, list):
            input = repr(input)
        output = operation.get('output')
        if output:
            output = list(operation['output'].values())[0]
        headers = operation.get('headers') or None
        return "%s(%s)\n -> %s:\n\n%s\nHeaders: %s" % (
            method,
            input or '',
            output and output or '',
            operation.get('documentation', ''),
            headers,
        )

    soap_ns_uris = {
        'http://schemas.xmlsoap.org/wsdl/soap/': 'soap11',
        'http://schemas.xmlsoap.org/wsdl/soap12/': 'soap12',
    }
    wsdl_uri = 'http://schemas.xmlsoap.org/wsdl/'
    xsd_uri = 'http://www.w3.org/2001/XMLSchema'
    xsi_uri = 'http://www.w3.org/2001/XMLSchema-instance'

    def _url_to_xml_tree(self, url, cache, force_download):
        """Unmarshall the WSDL at the given url into a tree of SimpleXMLElement nodes"""
        # Open uri and read xml:
        xml = fetch(url, self.http, cache, force_download, self.wsdl_basedir, self.http_headers)
        # Parse WSDL XML:
        wsdl = SimpleXMLElement(xml, namespace=self.wsdl_uri)

        # Extract useful data:
        self.namespace = ""
        self.documentation = unicode(wsdl('documentation', error=False)) or ''

        # some wsdl are split down in several files, join them:
        imported_wsdls = {}
        for element in wsdl.children() or []:
            if element.get_local_name() in ('import'):
                wsdl_namespace = element['namespace']
                wsdl_location = element['location']
                if wsdl_location is None:
                    log.warning('WSDL location not provided for %s!' % wsdl_namespace)
                    continue
                if wsdl_location in imported_wsdls:
                    log.warning('WSDL %s already imported!' % wsdl_location)
                    continue
                imported_wsdls[wsdl_location] = wsdl_namespace
                log.debug('Importing wsdl %s from %s' % (wsdl_namespace, wsdl_location))
                # Open uri and read xml:
                xml = fetch(wsdl_location, self.http, cache, force_download, self.wsdl_basedir, self.http_headers)
                # Parse imported XML schema (recursively):
                imported_wsdl = SimpleXMLElement(xml, namespace=self.xsd_uri)
                # merge the imported wsdl into the main document:
                wsdl.import_node(imported_wsdl)
                # warning: do not process schemas to avoid infinite recursion!

        return wsdl

    def _xml_tree_to_services(self, wsdl, cache, force_download):
        """Convert SimpleXMLElement tree representation of the WSDL into pythonic objects"""
        # detect soap prefix and uri (xmlns attributes of <definitions>)
        xsd_ns = None
        soap_uris = {}
        for k, v in wsdl[:]:
            if v in self.soap_ns_uris and k.startswith('xmlns:'):
                soap_uris[get_local_name(k)] = v
            if v == self.xsd_uri and k.startswith('xmlns:'):
                xsd_ns = get_local_name(k)

        elements = {}            # element: type def
        messages = {}            # message: element
        port_types = {}          # port_type_name: port_type
        bindings = {}            # binding_name: binding
        services = {}            # service_name: service

        # check axis2 namespace at schema types attributes (europa.eu checkVat)
        if "http://xml.apache.org/xml-soap" in dict(wsdl[:]).values():
            # get the sub-namespace in the first schema element (see issue 8)
            if wsdl('types', error=False):
                schema = wsdl.types('schema', ns=self.xsd_uri)
                attrs = dict(schema[:])
                self.namespace = attrs.get('targetNamespace', self.namespace)
            if not self.namespace or self.namespace == "urn:DefaultNamespace":
                self.namespace = wsdl['targetNamespace'] or self.namespace

        imported_schemas = {}
        global_namespaces = {None: self.namespace}

        # process current wsdl schema (if any, or many if imported):
        # <wsdl:definitions>
        #     <wsdl:types>
        #         <xs:schema>
        #             <xs:element>
        #                 <xs:complexType>...</xs:complexType>
        #                 or
        #                 <xs:.../>
        #             </xs:element>
        #         </xs:schema>
        #     </wsdl:types>
        # </wsdl:definitions>

        for types in wsdl('types', error=False) or []:
            # avoid issue if schema is not given in the main WSDL file
            schemas = types('schema', ns=self.xsd_uri, error=False)
            for schema in schemas or []:
                preprocess_schema(schema, imported_schemas, elements, self.xsd_uri,
                                  self.__soap_server, self.http, cache,
                                  force_download, self.wsdl_basedir,
                                  global_namespaces=global_namespaces)

        # 2nd phase: alias, postdefined elements, extend bases, convert lists
        postprocess_element(elements, [])

        for message in wsdl.message:
            for part in message('part', error=False) or []:
                element = {}
                element_name = part['element']
                if not element_name:
                    # some implementations (axis) uses type instead
                    element_name = part['type']
                type_ns = get_namespace_prefix(element_name)
                type_uri = part.get_namespace_uri(type_ns)
                part_name = part['name'] or None
                if type_uri == self.xsd_uri:
                    element_name = get_local_name(element_name)
                    fn = REVERSE_TYPE_MAP.get(element_name, None)
                    element = {part_name: fn}
                    # emulate a true Element (complexType) for rpc style
                    if (message['name'], part_name) not in messages:
                        od = Struct()
                        od.namespaces[None] = type_uri
                        messages[(message['name'], part_name)] = {message['name']: od}
                    else:
                        od = messages[(message['name'], part_name)].values()[0]
                    od.namespaces[part_name] = type_uri
                    od.references[part_name] = False
                    od.update(element)
                else:
                    element_name = get_local_name(element_name)
                    fn = elements.get(make_key(element_name, 'element', type_uri))
                    if not fn:
                        # some axis servers uses complexType for part messages (rpc)
                        fn = elements.get(make_key(element_name, 'complexType', type_uri))
                        od = Struct()
                        od[part_name] = fn
                        od.namespaces[None] = type_uri
                        od.namespaces[part_name] = type_uri
                        od.references[part_name] = False
                        element = {message['name']: od}
                    else:
                        element = {element_name: fn}
                    messages[(message['name'], part_name)] = element

        for port_type_node in wsdl.portType:
            port_type_name = port_type_node['name']
            port_type = port_types[port_type_name] = {}
            operations = port_type['operations'] = {}

            for operation_node in port_type_node.operation:
                op_name = operation_node['name']
                op = operations[op_name] = {}
                op['style'] = operation_node['style']
                op['parameter_order'] = (operation_node['parameterOrder'] or "").split(" ")
                op['documentation'] = unicode(operation_node('documentation', error=False)) or ''

                if operation_node('input', error=False):
                    op['input_msg'] = get_local_name(operation_node.input['message'])
                    ns = get_namespace_prefix(operation_node.input['message'])
                    op['namespace'] = operation_node.get_namespace_uri(ns)

                if operation_node('output', error=False):
                    op['output_msg'] = get_local_name(operation_node.output['message'])

                #Get all fault message types this operation may return
                fault_msgs = op['fault_msgs'] = {}
                faults = operation_node('fault', error=False)
                if faults is not None:
                    for fault in operation_node('fault', error=False):
                        fault_msgs[fault['name']] = get_local_name(fault['message'])

        for binding_node in wsdl.binding:
            port_type_name = get_local_name(binding_node['type'])
            if port_type_name not in port_types:
                # Invalid port type
                continue
            port_type = port_types[port_type_name]
            binding_name = binding_node['name']
            soap_binding = binding_node('binding', ns=list(soap_uris.values()), error=False)
            transport = soap_binding and soap_binding['transport'] or None
            style = soap_binding and soap_binding['style'] or None  # rpc

            binding = bindings[binding_name] = {
                'name': binding_name,
                'operations': copy.deepcopy(port_type['operations']),
                'port_type_name': port_type_name,
                'transport': transport,
                'style': style,
            }

            for operation_node in binding_node.operation:
                op_name = operation_node['name']
                op_op = operation_node('operation', ns=list(soap_uris.values()), error=False)
                action = op_op and op_op['soapAction']

                op = binding['operations'].setdefault(op_name, {})
                op['name'] = op_name
                op['style'] = op.get('style', style)
                if action is not None:
                    op['action'] = action

                # input and/or output can be not present!
                input = operation_node('input', error=False)
                body = input and input('body', ns=list(soap_uris.values()), error=False)
                parts_input_body = body and body['parts'] or None

                # parse optional header messages (some implementations use more than one!)
                parts_input_headers = []
                headers = input and input('header', ns=list(soap_uris.values()), error=False)
                for header in headers or []:
                    hdr = {'message': header['message'], 'part': header['part']}
                    parts_input_headers.append(hdr)

                if 'input_msg' in op:
                    headers = {}    # base header message structure
                    for input_header in parts_input_headers:
                        header_msg = get_local_name(input_header.get('message'))
                        header_part = get_local_name(input_header.get('part'))
                        # warning: some implementations use a separate message!
                        hdr = get_message(messages, header_msg or op['input_msg'], header_part)
                        if hdr:
                            headers.update(hdr)
                        else:
                            pass # not enough info to search the header message:
                    op['input'] = get_message(messages, op['input_msg'], parts_input_body, op['parameter_order'])
                    op['header'] = headers

                    try:
                        element = list(op['input'].values())[0]
                        ns_uri = element.namespaces[None]
                        qualified = element.qualified
                    except (AttributeError, KeyError) as e:
                        # TODO: fix if no parameters parsed or "variants"
                        ns_uri = op['namespace']
                        qualified = None
                    if ns_uri:
                        op['namespace'] = ns_uri
                        op['qualified'] = qualified

                    # Remove temporary property
                    del op['input_msg']

                else:
                    op['input'] = None
                    op['header'] = None

                output = operation_node('output', error=False)
                body = output and output('body', ns=list(soap_uris.values()), error=False)
                parts_output_body = body and body['parts'] or None
                if 'output_msg' in op:
                    op['output'] = get_message(messages, op['output_msg'], parts_output_body)
                    # Remove temporary property
                    del op['output_msg']
                else:
                    op['output'] = None

                if 'fault_msgs' in op:
                    faults = op['faults'] = {}
                    for msg in op['fault_msgs'].values():
                        msg_obj = get_message(messages, msg, parts_output_body)
                        tag_name = list(msg_obj)[0]
                        faults[tag_name] = msg_obj

                # useless? never used
                parts_output_headers = []
                headers = output and output('header', ns=list(soap_uris.values()), error=False)
                for header in headers or []:
                    hdr = {'message': header['message'], 'part': header['part']}
                    parts_output_headers.append(hdr)




        for service in wsdl("service", error=False) or []:
            service_name = service['name']
            if not service_name:
                continue  # empty service?

            serv = services.setdefault(service_name, {})
            ports = serv['ports'] = {}
            serv['documentation'] = service['documentation'] or ''
            for port in service.port:
                binding_name = get_local_name(port['binding'])

                if not binding_name in bindings:
                    continue    # unknown binding

                binding = ports[port['name']] = copy.deepcopy(bindings[binding_name])
                address = port('address', ns=list(soap_uris.values()), error=False)
                location = address and address['location'] or None
                soap_uri = address and soap_uris.get(address.get_prefix())
                soap_ver = soap_uri and self.soap_ns_uris.get(soap_uri)

                binding.update({
                    'location': location,
                    'service_name': service_name,
                    'soap_uri': soap_uri,
                    'soap_ver': soap_ver,
                })

        # create an default service if none is given in the wsdl:
        if not services:
            services[''] = {'ports': {'': None}}
   
        elements = list(e for e in elements.values() if type(e) is type) + sorted(e for e in elements.values() if not(type(e) is type))
        e = None
        self.elements = []
        for element in elements:
            if e!= element: self.elements.append(element)
            e = element

        return services

    def wsdl_parse(self, url, cache=False):
        """Parse Web Service Description v1.1"""

        log.debug('Parsing wsdl url: %s' % url)
        # Try to load a previously parsed wsdl:
        force_download = False
        if cache:
            # make md5 hash of the url for caching...
            filename_pkl = '%s.pkl' % hashlib.md5(url).hexdigest()
            if isinstance(cache, basestring):
                filename_pkl = os.path.join(cache, filename_pkl)
            if os.path.exists(filename_pkl):
                log.debug('Unpickle file %s' % (filename_pkl, ))
                f = open(filename_pkl, 'r')
                pkl = pickle.load(f)
                f.close()
                # sanity check:
                if pkl['version'][:-1] != __version__.split(' ')[0][:-1] or pkl['url'] != url:
                    warnings.warn('version or url mismatch! discarding cached wsdl', RuntimeWarning)
                    log.debug('Version: %s %s' % (pkl['version'], __version__))
                    log.debug('URL: %s %s' % (pkl['url'], url))
                    force_download = True
                else:
                    self.namespace = pkl['namespace']
                    self.documentation = pkl['documentation']
                    return pkl['services']

        # always return an unicode object:
        REVERSE_TYPE_MAP['string'] = str

        wsdl = self._url_to_xml_tree(url, cache, force_download)
        services = self._xml_tree_to_services(wsdl, cache, force_download)

        # dump the full service/port/operation map
        #log.debug(pprint.pformat(services))

        # Save parsed wsdl (cache)
        if cache:
            f = open(filename_pkl, "wb")
            pkl = {
                'version': __version__.split(' ')[0],
                'url': url,
                'namespace': self.namespace,
                'documentation': self.documentation,
                'services': services,
            }
            pickle.dump(pkl, f)
            f.close()

        return services

    def __setitem__(self, item, value):
        """Set SOAP Header value - this header will be sent for every request."""
        self.__headers[item] = value

    def close(self):
        """Finish the connection and remove temp files"""
        self.http.close()
        if self.cacert.startswith(tempfile.gettempdir()):
            log.debug('removing %s' % self.cacert)
            os.unlink(self.cacert)

    def __repr__(self):
        s = 'SOAP CLIENT'
        s += '\n ELEMENTS'
        for e in self.elements:
            if isinstance(e, type):
                e = e.__name__
            elif isinstance(e, Alias):
                e = e.xml_type
            elif isinstance(e, Struct) and e.key[1]=='element':
                e = repr(e)
            else:
                continue
            s += '\n  %s' % e
        for service in self.services:
            s += '\n SERVICE (%s)' % service
            ports = self.services[service]['ports']
            for port in ports:
                port = ports[port]
                if port['soap_ver'] == None: continue
                s += '\n   PORT (%s)' % port['name']
                s += '\n    Location: %s' % port['location']
                s += '\n    Soap ver: %s' % port['soap_ver']
                s += '\n    Soap URI: %s' % port['soap_uri']
                s += '\n    OPERATIONS'
                operations = port['operations']
                for operation in sorted(operations):
                    operation = self.get_operation(operation)
                    input = operation.get('input')
                    input = input and input.values() and list(input.values())[0]
                    input_str = ''
                    if isinstance(input, dict):
                        if 'parameters' not in input or input['parameters']!=None:
                            for k, v in input.items():
                                if isinstance(v, type):
                                    v = v.__name__
                                elif isinstance(v, Alias):
                                    v = v.xml_type
                                elif isinstance(v, Struct):
                                    v = v.key[0]
                                input_str += '%s: %s, ' % (k, v)
                    output = operation.get('output')
                    if output:
                        output = list(operation['output'].values())[0]
                    s += '\n     %s(%s)' % (
                        operation['name'],
                        input_str[:-2]
                        )
                    s += '\n      > %s' % output

        return s

def parse_proxy(proxy_str):
    """Parses proxy address user:pass@host:port into a dict suitable for httplib2"""
    proxy_dict = {}
    if proxy_str is None:
        return
    if '@' in proxy_str:
        user_pass, host_port = proxy_str.split('@')
    else:
        user_pass, host_port = '', proxy_str
    if ':' in host_port:
        host, port = host_port.split(':')
        proxy_dict['proxy_host'], proxy_dict['proxy_port'] = host, int(port)
    if ':' in user_pass:
        proxy_dict['proxy_user'], proxy_dict['proxy_pass'] = user_pass.split(':')
    return proxy_dict


if __name__ == '__main__':
    pass
