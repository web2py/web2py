"""
gluon.sanitizer — XSS defense exposed by web2py.

Delegates to yatl.sanitizer but installs a hardening patch on
yatl.sanitizer.XssCleaner.handle_starttag before re-exporting
sanitize().

Background
----------
yatl's XssCleaner emits values of url-bearing attributes (href, src,
background) without escaping:

    bt += ' %s="%s"' % (attribute, attrs[attribute])

HTMLParser decodes character references (including ``&quot;`` -> ``"``)
inside attribute values, so an attacker can supply

    <a href="https://example.com/&quot; onclick=&quot;alert(1)">x</a>

and have the resulting ``"`` close the href attribute on the way out,
injecting an event-handler attribute (XSS). Every other attribute
already goes through xml.sax.saxutils.quoteattr; this module makes the
url-bearing branch do the same.

The patch is applied at the XssCleaner.handle_starttag class method, so
every existing call site — gluon.sanitizer.sanitize, gluon.html.XML
(sanitize=True), yatl.helpers.XML(sanitize=True) — picks it up after
this module has been imported. gluon.html imports this module to make
that ordering explicit.
"""
from xml.sax.saxutils import quoteattr

from yatl.sanitizer import XssCleaner, sanitize, xmlescape

__all__ = ["sanitize"]


def _safe_handle_starttag(self, tag, attrs):
    if tag not in self.permitted_tags:
        self.in_disallowed.append(True)
        if not self.strip_disallowed:
            self.result += xmlescape("<%s>" % tag)
        return
    self.in_disallowed.append(False)
    bt = "<" + tag
    if tag in self.allowed_attributes:
        attrs = dict(attrs)
        self.allowed_attributes_here = [
            x
            for x in self.allowed_attributes[tag]
            if x in attrs and len(attrs[x]) > 0
        ]
        for attribute in self.allowed_attributes_here:
            if attribute in ("href", "src", "background"):
                if self.url_is_acceptable(attrs[attribute]):
                    bt += " %s=%s" % (attribute, quoteattr(attrs[attribute]))
            else:
                bt += " %s=%s" % (
                    xmlescape(attribute),
                    quoteattr(attrs[attribute]),
                )
    # deal with <a> without href and <img> without src
    if bt == "<a" or bt == "<img":
        return
    if tag in self.requires_no_close:
        bt += "/"
    bt += ">"
    self.result += bt
    if tag not in self.requires_no_close:
        self.open_tags.insert(0, tag)


def _yatl_is_vulnerable():
    """Return True if yatl's XssCleaner has the href attribute-breakout bug.

    Tests with the known exploit payload so the patch is skipped automatically
    once yatl fixes the bug upstream.
    """
    probe = XssCleaner(
        permitted_tags=["a"],
        allowed_attributes={"a": ["href"]},
    )
    result = probe.strip(
        '<a href="http://x.com/&quot; onclick=&quot;alert(1)">x</a>'
    )
    return "onclick" in result


if _yatl_is_vulnerable():
    XssCleaner.handle_starttag = _safe_handle_starttag
