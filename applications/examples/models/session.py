from gluon.utils import web2py_uuid
cookie_key = cache.ram('cookie_key',lambda: web2py_uuid(),None)
session.connect(request,response,cookie_key=cookie_key)
