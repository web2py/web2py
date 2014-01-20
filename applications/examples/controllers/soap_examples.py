# coding: utf8

# SOAP webservices (server and client) example and basic test
# (using pysimplesoap contrib included in web2py)
# for more info see: https://code.google.com/p/pysimplesoap/wiki/Web2Py

from gluon.tools import Service
service = Service(globals())

# define the procedures to be exposed:

@service.soap('AddStrings', returns={'AddResult': str}, args={'a': str, 'b': str})
@service.soap('AddIntegers', returns={'AddResult': int}, args={'a': int, 'b': int})
def add(a, b):
    "Add two values"
    return a+b

@service.soap('SubIntegers', returns={'SubResult': int}, args={'a': int, 'b': int})
def sub(a, b):
    "Substract two values"
    return a-b

@service.soap('Division', returns={'divisionResult': float}, args={'a': float, 'b': float})
def division(a, b):
    "Divide two values "
    return a / b


# expose the soap methods

def call():
    return service()

# sample function to test the SOAP RPC

def test_soap_sub():
    from gluon.contrib.pysimplesoap.client import SoapClient, SoapFault
    # build the url to the WSDL (web service description)
    # like "http://localhost:8000/webservices/sample/call/soap?WSDL"
    url = URL(f="call/soap", vars={"WSDL": ""}, scheme=True)
    # create a SOAP client
    client = SoapClient(wsdl=url)
    # call the SOAP remote method
    try:
        ret = client.SubIntegers(a=3, b=2)
        result = ret['SubResult']
    except SoapFault, sf:
        result = sf
    response.view = "soap_examples/generic.html"
    return dict(xml_request=client.xml_request, 
                xml_response=client.xml_response,
                result=result)

