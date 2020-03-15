from .PropertySets import  *
from .Elements import  *
from .Styles import  *
from .Renderer import  *
from .Constants import PY2

if PY2:
    from cStringIO import StringIO as BytesIO
else:
    from io import BytesIO

def dumps(doc):
    s = BytesIO()
    r = Renderer()
    r.Write(doc, s)
    return s.getvalue()

