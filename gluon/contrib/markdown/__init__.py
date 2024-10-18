from gluon._compat import to_unicode
from gluon.html import XML

from .markdown2 import *


def WIKI(text, encoding="utf8", safe_mode="escape", html4tags=False, **attributes):
    if not text:
        test = ""
    if "extras" in attributes:
        extras = attributes["extras"]
        del attributes["extras"]
    else:
        extras = None
    text = to_unicode(text, encoding, "replace")

    return XML(
        markdown(text, extras=extras, safe_mode=safe_mode, html4tags=html4tags).encode(
            encoding, "xmlcharrefreplace"
        ),
        **attributes
    )
