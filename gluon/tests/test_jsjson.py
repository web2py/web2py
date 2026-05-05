from gluon.html import SAFEJSON, jsjson, SafeString


def test_jsjson_escapes_script():
    obj = {"x": "</script><img src=x onerror=alert(1)>"}
    s = SAFEJSON(obj)
    assert isinstance(s, SafeString)
    xml = s.xml()
    # ensure raw '</' does not appear
    assert "</" not in xml
    # ensure we used the unicode-escaped form
    assert "\\u003c/" in xml
    assert jsjson(obj).xml() == xml
