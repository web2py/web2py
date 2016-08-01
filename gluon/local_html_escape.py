import sys

PY2 = sys.version_info[0] == 2

def local_html_escape(data, quote=False):
    """
    Works with bytes.
    Replace special characters "&", "<" and ">" to HTML-safe sequences.
    If the optional flag quote is true (the default), the quotation mark
    characters, both double quote (") and single quote (') characters are also
    translated.
    """
    if PY2:
        import cgi 
        s = cgi.escape(data, quote)
        return s.replace("'", "&#x27;") if quote else s
    else:
        import html
        if isinstance(s, str):
            return html.escape(s, quote=quote)
        s = s.replace(b"&", b"&amp;") # Must be done first!
        s = s.replace(b"<", b"&lt;")
        s = s.replace(b">", b"&gt;")
        if quote:
            s = s.replace(b'"', b"&quot;")
            s = s.replace(b'\'', b"&#x27;")
        return s
