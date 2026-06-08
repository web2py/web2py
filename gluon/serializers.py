"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""

import datetime
import decimal
import json as json_parser
import re

import gluon.contrib.rss2 as rss2
from gluon.html import TAG, XmlComponent, xmlescape
from gluon.languages import lazyT
from gluon.storage import Storage

have_yaml = True
try:
    import yaml as yamlib
except ImportError:
    have_yaml = False


def cast_keys(o, cast=str, encoding="utf-8"):
    """
    Builds a new object with <cast> type keys.
    Use this function if you are in Python < 2.6.5
    This avoids syntax errors when unpacking dictionary arguments.

    Args:
        o: is the object input
        cast:  (defaults to str) is an object type or function
            which supports conversion such as:

                converted = cast(o)

        encoding: (defaults to utf-8) is the encoding for unicode
            keys. This is not used for custom cast functions

    """

    if isinstance(o, (dict, Storage)):
        if isinstance(o, dict):
            newobj = dict()
        else:
            newobj = Storage()
        for k, v in o.items():
            key = k.decode("utf8") if isinstance(k, bytes) else str(k)
            newobj[key] = cast_keys(v)
    elif isinstance(o, (tuple, set, list)):
        newobj = []
        for item in o:
            newobj.append(cast_keys(item))
        if isinstance(o, tuple):
            newobj = tuple(newobj)
        elif isinstance(o, set):
            newobj = set(newobj)
    else:
        # no string cast (unknown object)
        newobj = o
    return newobj


def loads_json(o, unicode_keys=True, **kwargs):
    # deserialize a json string
    result = json_parser.loads(o, **kwargs)
    if not unicode_keys:
        # filter non-str keys in dictionary objects
        result = cast_keys(result, encoding=kwargs.get("encoding", "utf-8"))
    return result


def custom_json(o):
    if hasattr(o, "custom_json") and callable(o.custom_json):
        return o.custom_json()
    if isinstance(o, (datetime.date, datetime.datetime, datetime.time)):
        return o.isoformat()[:19].replace("T", " ")
    elif isinstance(o, int):
        return int(o)
    elif isinstance(o, decimal.Decimal):
        return float(o)
    elif isinstance(o, (bytes, bytearray)):
        return str(o) if hasattr(str, "decode") else str(o, encoding="utf-8")
    elif isinstance(o, lazyT):
        return str(o)
    elif isinstance(o, XmlComponent):
        return o.xml()
    elif isinstance(o, set):
        return list(o)
    elif hasattr(o, "as_list") and callable(o.as_list):
        return o.as_list()
    elif hasattr(o, "as_dict") and callable(o.as_dict):
        return o.as_dict()
    else:
        raise TypeError(repr(o) + " is not JSON serializable")


# a valid XML element name (a Name per XML 1.0, restricted here to a
# conservative ASCII-plus-unicode-word subset). A key carrying '<', '>', '"' or
# whitespace would otherwise let (possibly attacker-controlled) data break out
# of the element and inject arbitrary XML/markup.
_XML_NAME_RE = re.compile(r"^[A-Za-z_:][\w.\-:]*$", re.UNICODE)


def xml_safe_key(key):
    """Validate that a dict key is usable as an XML element name.

    ``xml_rec`` turns dict keys into tag names (``TAG[key]``) and ``TAG`` emits
    the name verbatim, so an invalid key would produce malformed and, with
    attacker-controlled keys, injectable XML. Rather than silently rewriting the
    key -- which would corrupt the serialised data and could collapse distinct
    keys onto the same tag -- reject any key that is not a valid XML name so the
    serialiser fails closed.
    """
    name = key if isinstance(key, str) else str(key)
    if name == "":
        # empty key is the "no wrapper element" sentinel used by xml_rec
        return ""
    if not _XML_NAME_RE.match(name):
        raise ValueError("invalid XML element name: %r" % (key,))
    return name


def xml_rec(value, key, quote=True):
    if hasattr(value, "custom_xml") and callable(value.custom_xml):
        return value.custom_xml()
    elif isinstance(value, (dict, Storage)):
        return TAG[xml_safe_key(key)](
            *[TAG[xml_safe_key(k)](xml_rec(v, "", quote)) for k, v in value.items()]
        )
    elif isinstance(value, list):
        return TAG[xml_safe_key(key)](
            *[TAG.item(xml_rec(item, "", quote)) for item in value]
        )
    elif hasattr(value, "as_list") and callable(value.as_list):
        return str(xml_rec(value.as_list(), "", quote))
    elif hasattr(value, "as_dict") and callable(value.as_dict):
        return str(xml_rec(value.as_dict(), "", quote))
    else:
        return xmlescape(value, quote)


def xml(value, encoding="UTF-8", key="document", quote=True):
    return ('<?xml version="1.0" encoding="%s"?>' % encoding) + str(
        xml_rec(value, key, quote)
    )


class JSONEncoderForHTML(json_parser.JSONEncoder):
    """An encoder that produces JSON safe to embed in HTML.
    To embed JSON content in, say, a script tag on a web page, the
    characters &, < and > should be escaped. They cannot be escaped
    with the usual entities (e.g. &amp;) because they are not expanded
    within <script> tags.
    This class also escapes the line separator and paragraph separator
    characters U+2028 and U+2029, irrespective of the ensure_ascii setting,
    as these characters are not valid in JavaScript strings (see
    http://timelessrepo.com/json-isnt-a-javascript-subset).
    """

    def encode(self, o):
        # Override JSONEncoder.encode because it has hacks for
        # performance that make things more complicated.
        chunks = self.iterencode(o, True)
        if self.ensure_ascii:
            return "".join(chunks)
        else:
            return "".join(chunks)

    def iterencode(self, o, _one_shot=False):
        chunks = super(JSONEncoderForHTML, self).iterencode(o, _one_shot)
        for chunk in chunks:
            chunk = chunk.replace("&", "\\u0026")
            chunk = chunk.replace("<", "\\u003c")
            chunk = chunk.replace(">", "\\u003e")

            if not self.ensure_ascii:
                chunk = chunk.replace("\u2028", "\\u2028")
                chunk = chunk.replace("\u2029", "\\u2029")

            yield chunk


def json(
    value, default=custom_json, indent=None, sort_keys=False, cls=JSONEncoderForHTML
):
    return json_parser.dumps(
        value, default=default, cls=cls, sort_keys=sort_keys, indent=indent
    )


def csv(value):
    return ""


# control characters (other than CR/TAB/LF) are not allowed anywhere in an
# iCalendar stream; CR/LF are handled separately by the escapers below
_ICS_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def ics_escape_text(value):
    """Escape a value for use as an iCalendar TEXT property value.

    Follows RFC 5545 section 3.3.11: backslash, semicolon and comma are
    backslash-escaped and every CR/LF newline becomes a literal ``\\n``.
    Without this, attacker-controlled values (event titles, ids, ...) can
    embed a newline and close the current property/component, injecting
    arbitrary iCalendar content (CRLF / property / component injection).
    """
    text = value if isinstance(value, str) else str(value)
    text = text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    # normalise every newline convention to the escaped TEXT newline
    text = text.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")
    # drop any remaining control characters that could break the stream
    return _ICS_CONTROL_RE.sub("", text)


def ics_escape_uri(value):
    """Sanitise a value used as an iCalendar URI property value.

    URIs are not TEXT and must not be backslash-escaped, but they also may
    not contain CR/LF or other control characters; strip them so the value
    cannot break out of the property and inject new iCalendar content.
    """
    text = value if isinstance(value, str) else str(value)
    text = text.replace("\r", "").replace("\n", "")
    return _ICS_CONTROL_RE.sub("", text)


def ics(events, title=None, link=None, timeshift=0, calname=True, **ignored):
    title = title or "(unknown)"
    if link and not callable(link):
        link = lambda item, prefix=link: prefix.replace("[id]", str(item["id"]))
    s = "BEGIN:VCALENDAR"
    s += "\nVERSION:2.0"
    if not calname is False:
        s += "\nX-WR-CALNAME:%s" % ics_escape_text(calname or title)
    s += "\nSUMMARY:%s" % ics_escape_text(title)
    s += "\nPRODID:Generated by web2py"
    s += "\nCALSCALE:GREGORIAN"
    s += "\nMETHOD:PUBLISH"
    for item in events:
        s += "\nBEGIN:VEVENT"
        s += "\nUID:%s" % ics_escape_text(item["id"])
        if link:
            s += "\nURL:%s" % ics_escape_uri(link(item))
        shift = datetime.timedelta(seconds=3600 * timeshift)
        start = item["start_datetime"] + shift
        stop = item["stop_datetime"] + shift
        s += "\nDTSTART:%s" % start.strftime("%Y%m%dT%H%M%S")
        s += "\nDTEND:%s" % stop.strftime("%Y%m%dT%H%M%S")
        s += "\nSUMMARY:%s" % ics_escape_text(item["title"])
        s += "\nEND:VEVENT"
    s += "\nEND:VCALENDAR"
    return s


def rss(feed):
    if not "entries" in feed and "items" in feed:
        feed["entries"] = feed["items"]

    now = datetime.datetime.now()
    rss = rss2.RSS2(
        title=feed.get("title", ""),
        link=feed.get("link", ""),
        description=feed.get("description", ""),
        lastBuildDate=feed.get("created_on", now),
        items=[
            rss2.RSSItem(
                title=entry.get("title", "(notitle)"),
                link=entry.get("link", ""),
                description=entry.get("description", ""),
                pubDate=entry.get("created_on", now),
            )
            for entry in feed.get("entries", [])
        ],
    )
    return rss.to_xml(encoding="utf8")


def yaml(data):
    if have_yaml:
        return yamlib.dump(data)
    else:
        raise ImportError("No YAML serializer available")


def loads_yaml(data):
    if have_yaml:
        return yamlib.safe_load(data)
    else:
        raise ImportError("No YAML serializer available")
