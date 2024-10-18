from .Constants import PY2
from .Elements import *
from .PropertySets import *
from .Renderer import *
from .Styles import *

if PY2:
    from cStringIO import StringIO as BytesIO
else:
    from io import BytesIO


def dumps(doc):
    s = BytesIO()
    r = Renderer()
    r.Write(doc, s)
    return s.getvalue()
