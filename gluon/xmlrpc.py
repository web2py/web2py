#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""

from gluon._compat import PY2

if PY2:
    from SimpleXMLRPCServer import SimpleXMLRPCDispatcher
else:
    from xmlrpc.server import SimpleXMLRPCDispatcher

def handler(request, response, methods):
    response.session_id = None  # no sessions for xmlrpc
    dispatcher = SimpleXMLRPCDispatcher(allow_none=True, encoding=None)
    for method in methods:
        dispatcher.register_function(method)
    dispatcher.register_introspection_functions()
    response.headers['Content-Type'] = 'text/xml'
    dispatch = getattr(dispatcher, '_dispatch', None)
    return dispatcher._marshaled_dispatch(request.body.read(), dispatch)
