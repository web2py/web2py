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


def _pdf_same_origin(request):
    """
    Return this application's own origin, e.g. "http://localhost:8000".

    Built from the server's own configuration rather than from
    request.env.http_host: the Host header is supplied by the client, so
    deriving the authority from it lets a caller aim the server's image
    fetches at any host it likes (SSRF).
    """
    env = request.env
    scheme = request.is_https and "https" or "http"
    host = env.server_name or "127.0.0.1"
    if ":" in host and not host.startswith("["):  # bare IPv6 literal
        host = "[%s]" % host
    port = str(env.server_port or "")
    if port and port != (request.is_https and "443" or "80"):
        return "%s://%s:%s" % (scheme, host, port)
    return "%s://%s" % (scheme, host)


def _resolve_pdf_image_path(path, request):
    """
    Map an <img src> from the rendered page onto something FPDF can load.

    * "/<app>/static/..." becomes a local file: no network access at all.
    * An absolute http(s) URL is passed through. The page named a host
      explicitly, so the server fetches it -- an application that renders
      untrusted HTML has to restrict <img src> before converting to PDF.
    * Any other rooted path is fetched from this application's own origin,
      which is built from the server configuration and then verified, so a
      crafted path cannot smuggle in a different authority (for instance
      "@evil.example/x.jpg", where "@" turns the origin into userinfo).
    * Anything else -- a relative path, or a scheme such as file: or data:
      -- is refused rather than guessed at.
    """
    static_prefix = "/%s/static/" % request.application
    if path.startswith(static_prefix):
        relative_static_path = path[len(static_prefix):]
        try:
            return safe_path_join(request.folder, "static", relative_static_path)
        except ValueError:
            raise HTTP(403, "invalid static path")
    scheme = urlsplit(path).scheme.lower()
    if scheme in ("http", "https"):
        return path
    if scheme or not path.startswith("/"):
        raise HTTP(403, "invalid image source")
    origin = _pdf_same_origin(request)
    url = origin + path
    if urlsplit(url).netloc != urlsplit(origin).netloc:
        raise HTTP(403, "invalid image path")
    return url


class _SameHostRedirect(HTTPRedirectHandler):
    """
    Follow a redirect only while it stays on the host that was asked for.

    Deciding which host to contact is the whole of the check above, and a
    redirect hands that decision to whoever answers first: a same-origin
    image would otherwise be bounced onto an address only the server can
    reach. Redirects within one host (http to https, a moved path) are
    ordinary and stay allowed.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).netloc.lower() != urlsplit(req.full_url).netloc.lower():
            raise HTTPError(
                req.full_url,
                code,
                "PDF image cross-host redirect refused",
                headers,
                fp,
            )
        return HTTPRedirectHandler.redirect_request(
            self, req, fp, code, msg, headers, newurl
        )


_pdf_image_opener = build_opener(_SameHostRedirect)


class _PdfFPDF(FPDF, HTMLMixin):
    """FPDF whose image fetches cannot be redirected onto another host."""

    def load_resource(self, reason, filename):
        if reason == "image" and filename.startswith(("http://", "https://")):
            return BytesIO(_pdf_image_opener.open(filename).read())
        return FPDF.load_resource(self, reason, filename)


def pyfpdf_from_html(html):
    """Render html to PDF with the bundled FPDF; returns PDF bytes."""
    request = current.request

    def image_map(path):
        return _resolve_pdf_image_path(path, request)

    pdf = _PdfFPDF()
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


def pdf_from_html(html):
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
        pdf = pyfpdf_from_html(html)
    raise HTTP(200, pdf, **{"Content-Type": "application/pdf"})
