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

"Pythonic simple SOAP Client implementation"

__author__ = "Mariano Reingart (reingart@gmail.com)"
__copyright__ = "Copyright (C) 2008 Mariano Reingart"
__license__ = "LGPL 3.0"
__version__ = "1.02c"

import urllib
try:
    import httplib2
    Http = httplib2.Http
except ImportError:
    import urllib2
    class Http(): # wrapper to use when httplib2 not available
        def request(self, url, method, body, headers):
            f = urllib2.urlopen(urllib2.Request(url, body, headers))
            return f.info(), f.read()


from simplexml import SimpleXMLElement, TYPE_MAP, OrderedDict

class SoapFault(RuntimeError):
    def __init__(self,faultcode,faultstring):
        self.faultcode = faultcode
        self.faultstring = faultstring

# soap protocol specification & namespace
soap_namespaces = dict(
    soap11="http://schemas.xmlsoap.org/soap/envelope/",
    soap="http://schemas.xmlsoap.org/soap/envelope/",
    soapenv="http://schemas.xmlsoap.org/soap/envelope/",
    soap12="http://www.w3.org/2003/05/soap-env",
)

class SoapClient(object):
    "Simple SOAP Client (s�mil PHP)"
    def __init__(self, location = None, action = None, namespace = None,
                 cert = None, trace = False, exceptions = True, proxy = None, ns=False,
                 soap_ns=None, wsdl = None, cache = False):
        self.certssl = cert
        self.keyssl = None
        self.location = location        # server location (url)
        self.action = action            # SOAP base action
        self.namespace = namespace      # message
        self.trace = trace              # show debug messages
        self.exceptions = exceptions    # lanzar execpiones? (Soap Faults)
        self.xml_request = self.xml_response = ''
        if not soap_ns and not ns:
            self.__soap_ns = 'soap' # 1.1
        elif not soap_ns and ns:
            self.__soap_ns = 'soapenv' # 1.2
        else:
            self.__soap_ns = soap_ns

        # parse wsdl url
        self.services = wsdl and self.wsdl(wsdl, debug=trace, cache=cache)
        self.service_port = None                 # service port for late binding

        if not proxy:
            self.http = Http()
        else:
            import socks
            ##httplib2.debuglevel=4
            self.http = httplib2.Http(proxy_info = httplib2.ProxyInfo(
                proxy_type=socks.PROXY_TYPE_HTTP, **proxy))
        #if self.certssl: # esto funciona para validar al server?
        #    self.http.add_certificate(self.keyssl, self.keyssl, self.certssl)
        self.__ns = ns # namespace prefix or False to not use it
        if not ns:
            self.__xml = """<?xml version="1.0" encoding="UTF-8"?>
<%(soap_ns)s:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:%(soap_ns)s="%(soap_uri)s">
<%(soap_ns)s:Body>
    <%(method)s xmlns="%(namespace)s">
    </%(method)s>
</%(soap_ns)s:Body>
</%(soap_ns)s:Envelope>"""
        else:
            self.__xml = """<?xml version="1.0" encoding="UTF-8"?>
<%(soap_ns)s:Envelope xmlns:%(soap_ns)s="%(soap_uri)s" xmlns:%(ns)s="%(namespace)s">
<%(soap_ns)s:Header/>
<%(soap_ns)s:Body>
    <%(ns)s:%(method)s>
    </%(ns)s:%(method)s>
</%(soap_ns)s:Body>
</%(soap_ns)s:Envelope>"""

    def __getattr__(self, attr):
        "Return a pseudo-method that can be called"
        if not self.services: # not using WSDL?
            return lambda self=self, *args, **kwargs: self.call(attr,*args,**kwargs)
        else: # using WSDL:
            return lambda self=self, *args, **kwargs: self.wsdl_call(attr,*args,**kwargs)

    def call(self, method, *args, **kwargs):
        "Prepare xml request and make SOAP call, returning a SimpleXMLElement"
        #TODO: method != input_message
        # Basic SOAP request:
        xml = self.__xml % dict(method=method, namespace=self.namespace, ns=self.__ns,
                                soap_ns=self.__soap_ns, soap_uri=soap_namespaces[self.__soap_ns])
        request = SimpleXMLElement(xml,namespace=self.__ns and self.namespace, prefix=self.__ns)
        # serialize parameters
        if kwargs:
            parameters = kwargs.items()
        else:
            parameters = args
        if parameters and isinstance(parameters[0], SimpleXMLElement):
            # merge xmlelement parameter ("raw" - already marshalled)
            for param in parameters[0].children():
                getattr(request,method).import_node(param)
        else:
            # marshall parameters:
            for k,v in parameters: # dict: tag=valor
                getattr(request,method).marshall(k,v)
        self.xml_request = request.as_xml()
        self.xml_response = self.send(method, self.xml_request)
        response = SimpleXMLElement(self.xml_response, namespace=self.namespace)
        if self.exceptions and response("Fault", ns=soap_namespaces.values(), error=False):
            raise SoapFault(unicode(response.faultcode), unicode(response.faultstring))
        return response

    def send(self, method, xml):
        "Send SOAP request using HTTP"
        if self.location == 'test': return
        location = "%s" % self.location #?op=%s" % (self.location, method)
        if self.services:
            soap_action = self.action
        else:
            soap_action = self.action+method
        headers={
                'Content-type': 'text/xml; charset="UTF-8"',
                'Content-length': str(len(xml)),
                "SOAPAction": "\"%s\"" % (soap_action)
                }
        if self.trace:
            print "-"*80
            print "POST %s" % location
            print '\n'.join(["%s: %s" % (k,v) for k,v in headers.items()])
            print u"\n%s" % xml.decode("utf8","ignore")
        response, content = self.http.request(
            location,"POST", body=xml, headers=headers )
        self.response = response
        self.content = content
        if self.trace:
            print
            print '\n'.join(["%s: %s" % (k,v) for k,v in response.items()])
            print content#.decode("utf8","ignore")
            print "="*80
        return content

    def get_operation(self, method):
        # try to find operation in wsdl file
        soap_ver = self.__soap_ns == 'soap12' and 'soap12' or 'soap11'
        if not self.service_port:
            for service_name, service in self.services.items():
                for port_name, port in [port for port in service['ports'].items()]:
                    if port['soap_ver'] == soap_ver:
                        self.service_port = service_name, port_name
                        break
                else:
                    raise RuntimeError("Cannot determine service in WSDL: "
                                       "SOAP version: %s" % soap_ver)
        else:
            port = self.services[self.service_port[0]]['ports'][self.service_port[1]]
        self.location = port['location']
        operation = port['operations'].get(unicode(method))
        if not operation:
            raise RuntimeError("Operation %s not found in WSDL: "
                               "Service/Port Type: %s" %
                               (method, self.service_port))
        return operation

    def wsdl_call(self, method, *args, **kwargs):
        "Pre and post process SOAP call, input and output parameters using WSDL"
        soap_uri = soap_namespaces[self.__soap_ns]
        operation = self.get_operation(method)
        # get i/o type declarations:
        input = operation['input']
        output = operation['output']
        if 'action' in operation:
            self.action = operation['action']
        # sort parameters (same order as xsd:sequence)
        def sort_dict(od, d):
            if isinstance(od, dict):
                ret = OrderedDict()
                for k in od.keys():
                    v = d.get(k)
                    if v:
                        if isinstance(v, dict):
                            v = sort_dict(od[k], v)
                        elif isinstance(v, list):
                            v = [sort_dict(od[k][0], v1)
                                    for v1 in v]
                        ret[str(k)] = v
                return ret
            else:
                return d
        if input and kwargs:
            params = sort_dict(input.values()[0], kwargs).items()
            method = input.keys()[0]
        #elif not input:
            #TODO: no message! (see wsmtxca.dummy)
        else:
            params = kwargs and kwargs.items()
        # call remote procedure
        response = self.call(method, *params)
        # parse results:
        resp = response('Body',ns=soap_uri).children().unmarshall(output)
        return resp and resp.values()[0] # pass Response tag children

    def help(self, method):
        "Return operation documentation and invocation/returned value example"
        operation = self.get_operation(method)
        input = operation['input'].values()
        input = input and input[0]
        output = operation['output'].values()[0]
        return u"%s(%s)\n -> %s:\n\n%s" % (
            method,
            input and ", ".join("%s=%s" % (k,repr(v)) for k,v
                                 in input.items()) or "",
            output and output or "",
            operation.get("documentation",""),
            )

    def wsdl(self, url, debug=False, cache=False):
        "Parse Web Service Description v1.1"
        soap_ns = {
            "http://schemas.xmlsoap.org/wsdl/soap/": 'soap11',
            "http://schemas.xmlsoap.org/wsdl/soap12/": 'soap12',
            }
        wsdl_uri="http://schemas.xmlsoap.org/wsdl/"
        xsd_uri="http://www.w3.org/2001/XMLSchema"
        xsi_uri="http://www.w3.org/2001/XMLSchema-instance"

        get_local_name = lambda s: str((':' in s) and s.split(':')[1] or s)

        REVERSE_TYPE_MAP = dict([(v,k) for k,v in TYPE_MAP.items()])

        def fetch(url):
            "Fetch a document from a URL, save it locally if cache enabled"
            import os, hashlib
            # make md5 hash of the url for caching...
            filename = "%s.xml" % hashlib.md5(url).hexdigest()
            if isinstance(cache, basestring):
                filename = os.path.join(cache, filename)
            if cache and os.path.exists(filename):
                if debug: print "Reading file %s" % (filename, )
                f = open(filename, "r")
                xml = f.read()
                f.close()
            else:
                if debug: print "Fetching url %s" % (url, )
                f = urllib.urlopen(url)
                xml = f.read()
                if cache:
                    if debug: print "Writing file %s" % (filename, )
                    f = open(filename, "w")
                    f.write(xml)
                    f.close()
            return xml

        # Open uri and read xml:
        xml = fetch(url)
        # Parse WSDL XML:
        wsdl = SimpleXMLElement(xml, namespace=wsdl_uri)

        # detect soap prefix and uri (xmlns attributes of <definitions>)
        xsd_ns = None
        soap_uris = {}
        for k, v in wsdl[:]:
            if v in soap_ns and k.startswith("xmlns:"):
                soap_uris[get_local_name(k)] = v
            if v== xsd_uri and k.startswith("xmlns:"):
                xsd_ns = get_local_name(k)

        # Extract useful data:
        self.namespace = wsdl['targetNamespace']
        self.documentation = unicode(wsdl('documentation', error=False) or '')

        services = {}
        bindings = {}           # binding_name: binding
        operations = {}         # operation_name: operation
        port_type_bindings = {} # port_type_name: binding
        messages = {}           # message: element
        elements = {}           # element: type def

        for service in wsdl.service:
            service_name=service['name']
            if not service_name:
                continue # empty service?
            if debug: print "Processing service", service_name
            serv = services.setdefault(service_name, {'ports': {}})
            serv['documentation']=service['documentation'] or ''
            for port in service.port:
                binding_name = get_local_name(port['binding'])
                address = port('address', ns=soap_uris.values(), error=False)
                location = address and address['location'] or None
                soap_uri = address and soap_uris.get(address.get_prefix())
                soap_ver = soap_uri and soap_ns.get(soap_uri)
                bindings[binding_name] = {'service_name': service_name,
                    'location': location,
                    'soap_uri': soap_uri, 'soap_ver': soap_ver,
                    }
                serv['ports'][port['name']] = bindings[binding_name]

        for binding in wsdl.binding:
            binding_name = binding['name']
            if debug: print "Processing binding", service_name
            soap_binding = binding('binding', ns=soap_uris.values(), error=False)
            transport = soap_binding and soap_binding['transport'] or None
            port_type_name = get_local_name(binding['type'])
            bindings[binding_name].update({
                'port_type_name': port_type_name,
                'transport': transport, 'operations': {},
                })
            port_type_bindings[port_type_name] = bindings[binding_name]
            for operation in binding.operation:
                op_name = operation['name']
                op = operation('operation',ns=soap_uris.values(), error=False)
                action = op and op['soapAction']
                d = operations.setdefault(op_name, {})
                bindings[binding_name]['operations'][op_name] = d
                d.update({'name': op_name})
                #if action: #TODO: separe operation_binding from operation
                if action:
                    d["action"] = action

        #TODO: cleanup element/schema/types parsing:
        def process_element(element_name, node):
            "Parse and define simple element types"
            if debug: print "Processing element", element_name
            for tag in node:
                if tag.get_local_name() in ("annotation", "documentation"):
                    continue
                elif tag.get_local_name() in ('element', 'restriction'):
                    if debug: print element_name,"has not children!",tag
                    children = tag # element "alias"?
                    alias = True
                elif tag.children():
                    children = tag.children()
                    alias = False
                else:
                    if debug: print element_name,"has not children!",tag
                    continue #TODO: abstract?
                d = OrderedDict()
                for e in children:
                    t = e['type']
                    if not t:
                        t = e['base'] # complexContent (extension)!
                    if not t:
                        t = 'anyType' # no type given!
                    t = t.split(":")
                    if len(t)>1:
                        ns, type_name = t
                    else:
                        ns, type_name = None, t[0]
                    if element_name == type_name:
                        continue # prevent infinite recursion
                    uri = ns and e.get_namespace_uri(ns) or xsd_uri
                    if uri==xsd_uri:
                        # look for the type, None == any
                        fn = REVERSE_TYPE_MAP.get(unicode(type_name), None)
                    else:
                        # complex type, postprocess later
                        fn = elements.setdefault(unicode(type_name), OrderedDict())
                    if e['name'] is not None and not alias:
                        e_name = unicode(e['name'])
                        d[e_name] = fn
                    else:
                        if debug: print "complexConent/simpleType/element", element_name, "=", type_name
                        d[None] = fn
                    if e['maxOccurs']=="unbounded":
                        # it's an array... TODO: compound arrays?
                        d.array = True
                    if e is not None and e.get_local_name() == 'extension' and e.children():
                        # extend base element:
                        process_element(element_name, e.children())
                elements.setdefault(element_name, OrderedDict()).update(d)

        # check axis2 namespace at schema types attributes
        self.namespace = dict(wsdl.types("schema", ns=xsd_uri)[:]).get('targetNamespace', self.namespace)

        imported_schemas = {}

        def preprocess_schema(schema):
            "Find schema elements and complex types"
            for element in schema.children():
                if element.get_local_name() in ('import', ):
                    schema_namespace = element['namespace']
                    schema_location = element['schemaLocation']
                    if schema_location is None:
                        if debug: print "Schema location not provided for %s!" % (schema_namespace, )
                        continue
                    if schema_location in imported_schemas:
                        if debug: print "Schema %s already imported!" % (schema_location, )
                        continue
                    imported_schemas[schema_location] = schema_namespace
                    if debug: print "Importing schema %s from %s" % (schema_namespace, schema_location)
                    # Open uri and read xml:
                    xml = fetch(schema_location)
                    # Parse imported XML schema (recursively):
                    imported_schema = SimpleXMLElement(xml, namespace=xsd_uri)
                    preprocess_schema(imported_schema)

                if element.get_local_name() in ('element', 'complexType', "simpleType"):
                    element_name = unicode(element['name'])
                    if debug: print "Parsing Element %s: %s" % (element.get_local_name(),element_name)
                    if element.get_local_name() == 'complexType':
                        children = element.children()
                    elif element.get_local_name() == 'simpleType':
                        children = element("restriction", ns=xsd_uri)
                    elif element.get_local_name() == 'element' and element['type']:
                        children = element
                    else:
                        children = element.children()
                        if children:
                            children = children.children()
                        elif element.get_local_name() == 'element':
                            children = element
                    if children:
                        process_element(element_name, children)

        def postprocess_element(elements):
            "Fix unresolved references (elements referenced before its definition, thanks .net)"
            for k,v in elements.items():
                if isinstance(v, OrderedDict):
                    if v.array:
                        elements[k] = [v] # convert arrays to python lists
                    if v!=elements: #TODO: fix recursive elements
                        postprocess_element(v)
                    if None in v and v[None]: # extension base?
                        if isinstance(v[None], dict):
                            for i, kk in enumerate(v[None]):
                                # extend base -keep orginal order-
                                elements[k].insert(kk, v[None][kk], i)
                            del v[None]
                        else:  # "alias", just replace
                            if debug: print "Replacing ", k , " = ", v[None]
                            elements[k] = v[None]
                            #break
                if isinstance(v, list):
                    for n in v: # recurse list
                        postprocess_element(n)


        # process current wsdl schema:
        for schema in wsdl.types("schema", ns=xsd_uri):
            preprocess_schema(schema)

        postprocess_element(elements)

        for message in wsdl.message:
            if debug: print "Processing message", message['name']
            part = message('part', error=False)
            element = {}
            if part:
                element_name = part['element']
                if not element_name:
                    element_name = part['type'] # some uses type instead
                element_name = get_local_name(element_name)
                element = {element_name: elements.get(element_name)}
            messages[message['name']] = element

        for port_type in wsdl.portType:
            port_type_name = port_type['name']
            if debug: print "Processing port type", port_type_name
            binding = port_type_bindings[port_type_name]

            for operation in port_type.operation:
                op_name = operation['name']
                op = operations[op_name]
                op['documentation'] = unicode(operation('documentation', error=False) or '')
                if binding['soap_ver']:
                    #TODO: separe operation_binding from operation (non SOAP?)
                    input = get_local_name(operation.input['message'])
                    output = get_local_name(operation.output['message'])
                    op['input'] = messages[input]
                    op['output'] = messages[output]

        if debug:
            import pprint
            pprint.pprint(services)

        return services

def parse_proxy(proxy_str):
    "Parses proxy address user:pass@host:port into a dict suitable for httplib2"
    proxy_dict = {}
    if proxy_str is None:
        return
    if "@" in proxy_str:
        user_pass, host_port = proxy_str.split("@")
    else:
        user_pass, host_port = "", proxy_str
    if ":" in host_port:
        host, port = host_port.split(":")
        proxy_dict['proxy_host'], proxy_dict['proxy_port'] = host, int(port)
    if ":" in user_pass:
        proxy_dict['proxy_user'], proxy_dict['proxy_pass'] = user_pass.split(":")
    return proxy_dict


if __name__=="__main__":
    import sys

    if '--web2py' in sys.argv:
        # test local sample webservice exposed by web2py
        from client import SoapClient
        if not '--wsdl' in sys.argv:
            client = SoapClient(
                location = "http://127.0.0.1:8000/webservices/sample/call/soap",
                action = 'http://127.0.0.1:8000/webservices/sample/call/soap', # SOAPAction
                namespace = "http://127.0.0.1:8000/webservices/sample/call/soap",
                soap_ns='soap', trace = True, ns = False, exceptions=True)
        else:
            client = SoapClient(wsdl="http://127.0.0.1:8000/webservices/sample/call/soap?WSDL",trace=True)
        response = client.Dummy()
        print 'dummy', response
        response = client.Echo(value='hola')
        print 'echo', repr(response)
        response = client.AddIntegers(a=1,b=2)
        if not '--wsdl' in sys.argv:
            result = response.AddResult # manully convert returned type
            print int(result)
        else:
            result = response['AddResult']
            print result, type(result), "auto-unmarshalled"

    if '--raw' in sys.argv:
        # raw (unmarshalled parameter) local sample webservice exposed by web2py
        from client import SoapClient
        client = SoapClient(
            location = "http://127.0.0.1:8000/webservices/sample/call/soap",
            action = 'http://127.0.0.1:8000/webservices/sample/call/soap', # SOAPAction
            namespace = "http://127.0.0.1:8000/webservices/sample/call/soap",
            soap_ns='soap', trace = True, ns = False)
        params = SimpleXMLElement("""<?xml version="1.0" encoding="UTF-8"?><AddIntegers><a>3</a><b>2</b></AddIntegers>""") # manully convert returned type
        response = client.call('AddIntegers',params)
        result = response.AddResult
        print int(result) # manully convert returned type

    if '--ctg' in sys.argv:
        # test AFIP Agriculture webservice
        client = SoapClient(
            location = "https://fwshomo.afip.gov.ar/wsctg/services/CTGService",
            action = 'http://impl.service.wsctg.afip.gov.ar/CTGService/', # SOAPAction
            namespace = "http://impl.service.wsctg.afip.gov.ar/CTGService/",
            trace = True,
            ns = True)
        response = client.dummy()
        result = response.dummyResponse
        print str(result.appserver)
        print str(result.dbserver)
        print str(result.authserver)

    if '--wsfe' in sys.argv:
        # Demo & Test (AFIP Electronic Invoice):
        ta_file = open("TA.xml")
        try:
            ta_string = ta_file.read()   # read access ticket (wsaa.py)
        finally:
            ta_file.close()
        ta = SimpleXMLElement(ta_string)
        token = str(ta.credentials.token)
        sign = str(ta.credentials.sign)
        cuit = long(20267565393)
        id = 1234
        cbte =199
        client = SoapClient(
            location = "https://wswhomo.afip.gov.ar/wsfe/service.asmx",
            action = 'http://ar.gov.afip.dif.facturaelectronica/', # SOAPAction
            namespace = "http://ar.gov.afip.dif.facturaelectronica/",
            trace = True)
        results = client.FERecuperaQTYRequest(
            argAuth= {"Token": token, "Sign": sign, "cuit":long(cuit)}
        )
        if int(results.FERecuperaQTYRequestResult.RError.percode) != 0:
            print "Percode: %s" % results.FERecuperaQTYRequestResult.RError.percode
            print "MSGerror: %s" % results.FERecuperaQTYRequestResult.RError.perrmsg
        else:
            print int(results.FERecuperaQTYRequestResult.qty.value)

    if '--feriados' in sys.argv:
        # Demo & Test: Argentina Holidays (Ministerio del Interior):
        # this webservice seems disabled
        from datetime import datetime, timedelta
        client = SoapClient(
            location = "http://webservices.mininterior.gov.ar/Feriados/Service.svc",
            action = 'http://tempuri.org/IMyService/', # SOAPAction
            namespace = "http://tempuri.org/FeriadoDS.xsd",
            trace = True)
        dt1 = datetime.today() - timedelta(days=60)
        dt2 = datetime.today() + timedelta(days=60)
        feriadosXML = client.FeriadosEntreFechasas_xml(dt1=dt1.isoformat(), dt2=dt2.isoformat());
        print feriadosXML

    if '--wsdl-parse' in sys.argv:
        client = SoapClient()
        # Test PySimpleSOAP WSDL
        client.wsdl("file:C:/test.wsdl", debug=True)
        # Test Java Axis WSDL:
        client.wsdl('https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl',debug=True)
        # Test .NET 2.0 WSDL:
        client.wsdl('https://wswhomo.afip.gov.ar/wsfe/service.asmx?WSDL',debug=True)
        client.wsdl('https://wswhomo.afip.gov.ar/wsfex/service.asmx?WSDL',debug=True)
        client.wsdl('https://testdia.afip.gov.ar/Dia/Ws/wDigDepFiel/wDigDepFiel.asmx?WSDL',debug=True)
        # Test JBoss WSDL:
        client.wsdl('https://fwshomo.afip.gov.ar/wsctg/services/CTGService?wsdl',debug=True)
        client.wsdl('https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl',debug=True)

    if '--wsdl-client' in sys.argv:
        client = SoapClient(wsdl='https://wswhomo.afip.gov.ar/wsfex/service.asmx?WSDL',trace=True)
        results = client.FEXDummy()
        print results['FEXDummyResult']['AppServer']
        print results['FEXDummyResult']['DbServer']
        print results['FEXDummyResult']['AuthServer']
        ta_file = open("TA.xml")
        try:
            ta_string = ta_file.read()   # read access ticket (wsaa.py)
        finally:
            ta_file.close()
        ta = SimpleXMLElement(ta_string)
        token = str(ta.credentials.token)
        sign = str(ta.credentials.sign)
        response = client.FEXGetCMP(
            Auth={"Token": token, "Sign": sign, "Cuit": 20267565393},
            Cmp={"Tipo_cbte": 19, "Punto_vta": 1, "Cbte_nro": 1})
        result = response['FEXGetCMPResult']
        if False: print result
        if 'FEXErr' in result:
            print "FEXError:", result['FEXErr']['ErrCode'], result['FEXErr']['ErrCode']
        cbt = result['FEXResultGet']
        print cbt['Cae']
        FEX_event = result['FEXEvents']
        print FEX_event['EventCode'], FEX_event['EventMsg']

    if '--wsdl-ctg' in sys.argv:
        client = SoapClient(wsdl='https://fwshomo.afip.gov.ar/wsctg/services/CTGService?wsdl',
                            trace=True, ns = "ctg")
        results = client.dummy()
        print results
        print results['DummyResponse']['appserver']
        print results['DummyResponse']['dbserver']
        print results['DummyResponse']['authserver']
        ta_file = open("TA.xml")
        try:
            ta_string = ta_file.read()   # read access ticket (wsaa.py)
        finally:
            ta_file.close()
        ta = SimpleXMLElement(ta_string)
        token = str(ta.credentials.token)
        sign = str(ta.credentials.sign)
        print client.help("obtenerProvincias")
        response = client.obtenerProvincias(auth={"token":token, "sign":sign, "cuitRepresentado":20267565393})
        print "response=",response
        for ret in response:
            print ret['return']['codigoProvincia'], ret['return']['descripcionProvincia'].encode("latin1")
        prueba = dict(numeroCartaDePorte=512345678, codigoEspecie=23,
                cuitRemitenteComercial=20267565393, cuitDestino=20267565393, cuitDestinatario=20267565393,
                codigoLocalidadOrigen=3058, codigoLocalidadDestino=3059,
                codigoCosecha='0910', pesoNetoCarga=1000, cantHoras=1,
                patenteVehiculo='CZO985', cuitTransportista=20267565393,
                numeroCTG="43816783", transaccion='10000001681', observaciones='',
            )

        response = client.solicitarCTG(
            auth={"token": token, "sign": sign, "cuitRepresentado": 20267565393},
            solicitarCTGRequest= prueba)

        print response['return']['numeroCTG']

    ##print parse_proxy(None)
    ##print parse_proxy("host:1234")
    ##print parse_proxy("user:pass@host:1234")
    ##sys.exit(0)

