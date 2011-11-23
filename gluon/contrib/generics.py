# fix response

import re
import os
import cPickle
import gluon.serializers
from gluon import current
from gluon.html import markmin_serializer, TAG, HTML, BODY, UL, XML
from gluon.contenttype import contenttype
from gluon.contrib.pyfpdf import FPDF, HTMLMixin
from gluon.sanitizer import sanitize
from gluon.contrib.markmin.markmin2latex import markmin2latex
from gluon.contrib.markmin.markmin2pdf import markmin2pdf

def wrapper(f):
    def g(data):
        try:
            output = f(data)
        except (TypeError, ValueError):
            raise HTTP(405, '%s serialization error' % extension.upper())
        except ImportError:
            raise HTTP(405, '%s not available' % extension.upper())
        except:
            raise HTTP(405, '%s error' % extension.upper())
        return XML(ouput)
    return g

def latex_from_html(html):
    markmin=TAG(html).element('body').flatten(markmin_serializer)
    return XML(markmin2latex(markmin))

def pdflatex_from_html(html):
    if os.system('which pdflatex > /dev/null')==0:
        markmin=TAG(html).element('body').flatten(markmin_serializer)
        out,warning,errors=markmin2pdf(markmin)
        if errors:
            current.response.headers['Content-Type']='text/html'
            raise HTTP(405,HTML(BODY(H1('errors'),
                                     LU(*errors),
                                     H1('warnings'),
                                     LU(*warnings))).xml())
        else:
            return XML(out)

def pyfpdf_from_html(html):
    request = current.request
    def image_map(path):
        if path.startswith('/%s/static/' % request.application):
            return os.path.join(request.folder,path.split('/',2)[2])
        return 'http%s://%s%s' % (request.is_https and 's' or '',request.env.http_host, path)
    class MyFPDF(FPDF, HTMLMixin): pass
    pdf=MyFPDF()
    pdf.add_page()
    html = sanitize(html, escape=False)  #### should have better list of allowed tags
    pdf.write_html(html,image_map=image_map)
    return XML(pdf.output(dest='S'))

def pdf_from_html(html):
    # try use latex and pdflatex
    if os.system('which pdflatex > /dev/null')==0:
        return pdflatex_from_html(html)
    else:
        return pyfpdf_from_html(html)


