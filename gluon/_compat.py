from pydal._compat import *

if PY2:
    from gluon.contrib import ipaddress
else:
    import ipaddress
