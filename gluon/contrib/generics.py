# fix response

import os
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener

from gluon import HTTP, current
from gluon.contrib.fpdf import FPDF, HTMLMixin
from gluon.contrib.markmin.markmin2latex import markmin2latex
from gluon.contrib.markmin.markmin2pdf import markmin2pdf
from gluon.html import BODY, H1, HTML, TAG, UL, XML, markmin_serializer
from gluon.sanitizer import sanitize
from gluon.utils import safe_path_join


def wrapper(f):
    def g(data):
        try:
            output = f(data)
            return XML(output)
        except (TypeError, ValueError) as e:
            raise HTTP(405, "%s serialization error" % e)
        except ImportError as e:
            raise HTTP(405, "%s not available" % e)
        except Exception as e:
            raise HTTP(405, "%s error" % e)

    return g


def latex_from_html(html):
    markmin = TAG(html).element("body").flatten(markmin_serializer)
    return markmin2latex(markmin)


def pdflatex_from_html(html):
    if os.system("which pdflatex > /dev/null") == 0:
        markmin = TAG(html).element("body").flatten(markmin_serializer)
        out, warnings, errors = markmin2pdf(markmin)
        if errors:
            current.response.headers["Content-Type"] = "text/html"
            raise HTTP(
                405,
                HTML(
                    BODY(H1("errors"), UL(*errors), H1("warnings"), UL(*warnings))
                ).xml(),
            )
        else:
            return out


def _canonical_origin(origin):
    """
    Parse an origin such as "https://Example.com:8443/" and rebuild it as
    "scheme://host[:port]", or return None when it is not a plain http(s)
    origin. Credentials, paths, queries and fragments are not allowed: a
    trusted origin names a host to connect to and nothing else.
    """
    try:
        parts = urlsplit(origin)
        port = parts.port
    except (TypeError, ValueError, AttributeError):
        return None
    scheme = (parts.scheme or "").lower()
    host = parts.hostname
    if scheme not in ("http", "https") or not host:
        return None
    if parts.username is not None or parts.password is not None:
        return None
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        return None
    if ":" in host:  # IPv6 literal
        host = "[%s]" % host
    if port is None or port == {"http": 80, "https": 443}[scheme]:
        return "%s://%s" % (scheme, host)
    return "%s://%s:%d" % (scheme, host, port)


def _trusted_pdf_image_origins(origins):
    """
    Normalize the application-supplied list of origins that PDF images may be
    fetched from. Raises HTTP(500) on a malformed entry: that is a
    configuration mistake, and failing loudly beats silently fetching from
    somewhere unexpected.
    """
    if not origins:
        return []
    if isinstance(origins, str):
        origins = [origins]
    trusted = []
    for origin in origins:
        canonical = _canonical_origin(origin)
        if canonical is None:
            raise HTTP(500, "invalid PDF image origin %r" % (origin,))
        trusted.append(canonical)
    return trusted


def _resolve_pdf_image_path(path, request, trusted_origins=None):
    """
    Map an <img src> from the rendered page onto something FPDF can load.

    * "/<app>/static/..." becomes a local file: no network access at all.
    * Everything else would be fetched by the server, so it is refused
      unless the application named the origins it trusts
      (``trusted_origins``). Nothing about the request is used to choose
      the host: HTTP_HOST is supplied by the client, and several WSGI
      servers (gunicorn, Apache with UseCanonicalName Off, ...) derive
      SERVER_NAME / SERVER_PORT from it too.
    * With trusted origins, a rooted path is fetched from the first one,
      and an absolute http(s) URL is fetched only if its origin is listed.
    * Anything else -- a relative path, or a scheme such as file: or data:
      -- is refused.
    """
    static_prefix = "/%s/static/" % request.application
    if path.startswith(static_prefix):
        relative_static_path = path[len(static_prefix):]
        try:
            return safe_path_join(request.folder, "static", relative_static_path)
        except ValueError:
            raise HTTP(403, "invalid static path")
    trusted = _trusted_pdf_image_origins(trusted_origins)
    if not trusted:
        raise HTTP(403, "PDF image source requires a trusted image origin")
    try:
        parts = urlsplit(path)
    except ValueError:
        raise HTTP(403, "invalid image source")
    scheme = parts.scheme.lower()
    if scheme in ("http", "https"):
        origin = _canonical_origin("%s://%s" % (scheme, parts.netloc))
        if origin not in trusted:
            raise HTTP(403, "PDF image origin not trusted")
        return path
    # A value that does not begin with a single "/" would attach to the host
    # and move the fetch to another server, e.g. "@internal:8080/x" ->
    # "http://host@internal:8080/x".
    if scheme or not path.startswith("/") or path.startswith("//"):
        raise HTTP(403, "invalid image source")
    url = trusted[0] + path
    if _canonical_origin("%s://%s" % urlsplit(url)[:2]) != trusted[0]:
        raise HTTP(403, "invalid image path")
    return url


class _TrustedOriginRedirect(HTTPRedirectHandler):
    """
    Follow a redirect only when it leads to a trusted origin.

    Choosing which host to contact is the whole of the check above, and a
    redirect hands that choice to whoever answers first: an image on a
    trusted host would otherwise be bounced onto an address only the server
    can reach.
    """

    def __init__(self, trusted_origins):
        self.trusted_origins = trusted_origins

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            parts = urlsplit(newurl)
            origin = _canonical_origin("%s://%s" % (parts.scheme, parts.netloc))
        except ValueError:
            origin = None
        if origin is None or origin not in self.trusted_origins:
            raise HTTPError(
                req.full_url,
                code,
                "PDF image redirect to untrusted origin refused",
                headers,
                fp,
            )
        return HTTPRedirectHandler.redirect_request(
            self, req, fp, code, msg, headers, newurl
        )


class _PdfFPDF(FPDF, HTMLMixin):
    """FPDF whose image fetches cannot be redirected off the trusted origins."""

    def __init__(self, *args, **kwargs):
        self.trusted_image_origins = kwargs.pop("trusted_image_origins", [])
        FPDF.__init__(self, *args, **kwargs)

    def load_resource(self, reason, filename):
        if reason == "image" and filename.startswith(("http://", "https://")):
            opener = build_opener(_TrustedOriginRedirect(self.trusted_image_origins))
            return BytesIO(opener.open(filename).read())
        return FPDF.load_resource(self, reason, filename)


def pyfpdf_from_html(html, trusted_image_origins=None):
    """
    Render html to PDF with the bundled FPDF; returns PDF bytes.

    Images under /<app>/static/ are read from disk. Any other image is
    fetched over the network, and only from ``trusted_image_origins``
    (a string or list such as ["https://myapp.example.com"]); when it is
    not given, ``response.pdf_image_origins`` is used, so a controller can
    enable it for the stock generic.pdf view. Without either, such images
    are refused.
    """
    request = current.request
    if trusted_image_origins is None:
        response = getattr(current, "response", None)
        trusted_image_origins = getattr(response, "pdf_image_origins", None)
    trusted = _trusted_pdf_image_origins(trusted_image_origins)

    def image_map(path):
        return _resolve_pdf_image_path(path, request, trusted)

    pdf = _PdfFPDF(trusted_image_origins=trusted)
    pdf.add_page()
    # pyfpdf needs some attributes to render the table correctly:
    html = sanitize(
        html,
        allowed_attributes={
            "a": ["href", "title"],
            "img": ["src", "alt"],
            "blockquote": ["type"],
            "td": ["align", "bgcolor", "colspan", "height", "width"],
            "tr": ["bgcolor", "height", "width"],
            "table": ["border", "bgcolor", "height", "width"],
        },
        escape=False,
    )
    pdf.write_html(html, image_map=image_map)
    return pdf.output(dest="S")


def pdf_from_html(html, trusted_image_origins=None):
    """
    Serve html as a PDF. Raises HTTP(200) carrying the PDF bytes.

    A PDF is binary and a view renders into a text buffer, so the bytes
    cannot be returned through the template; raising the response is the
    same thing Auth does for file downloads, and it keeps the shipped
    "=pdf_from_html(html)" generic.pdf views working unchanged.
    """
    # try use latex and pdflatex
    if os.system("which pdflatex > /dev/null") == 0:
        pdf = pdflatex_from_html(html)
    else:
        pdf = pyfpdf_from_html(html, trusted_image_origins)
    raise HTTP(200, pdf, **{"Content-Type": "application/pdf"})
