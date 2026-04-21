# fix response

import os

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


def _resolve_pdf_image_path(path, request):
    static_prefix = "/%s/static/" % request.application
    if path.startswith(static_prefix):
        relative_static_path = path[len(static_prefix):]
        try:
            return safe_path_join(request.folder, "static", relative_static_path)
        except ValueError:
            raise HTTP(403, "invalid static path")
    return "http%s://%s%s" % (
        request.is_https and "s" or "",
        request.env.http_host,
        path,
    )


def pyfpdf_from_html(html):
    request = current.request

    def image_map(path):
        return _resolve_pdf_image_path(path, request)

    class MyFPDF(FPDF, HTMLMixin):
        pass

    pdf = MyFPDF()
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
    return XML(pdf.output(dest="S"))


def pdf_from_html(html):
    # try use latex and pdflatex
    if os.system("which pdflatex > /dev/null") == 0:
        return pdflatex_from_html(html)
    else:
        return pyfpdf_from_html(html)
