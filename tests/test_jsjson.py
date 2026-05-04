import json

from gluon.html import jsjson, SafeString


def test_jsjson_escapes_script():
    obj = {"x": "</script><img src=x onerror=alert(1)>"}
    s = jsjson(obj)
    assert isinstance(s, SafeString)
    xml = s.xml()
    # ensure raw '</' does not appear
    assert "</" not in xml
    # ensure we used the unicode-escaped form
    assert "\\u003c/" in xml
