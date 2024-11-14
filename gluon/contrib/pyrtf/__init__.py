from io import BytesIO

from .Constants import PY2
from .Elements import *
from .PropertySets import *
from .Renderer import *
from .Styles import *


def dumps(doc):
    s = BytesIO()
    r = Renderer()
    r.Write(doc, s)
    return s.getvalue()
