# -*- coding: iso-8859-1 -*-

"PDF Template Helper for FPDF.py"

from __future__ import with_statement

__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2010 Mariano Reingart"
__license__ = "LGPL 3.0"

import sys,os,csv
from .fpdf import FPDF
from .py3k import PY3K, basestring, unicode

def rgb(col):
    return (col // 65536), (col // 256 % 256), (col% 256)

class Template:
    def __init__(self, infile=None, elements=None, format='A4', orientation='portrait',
                 title='', author='', subject='', creator='', keywords=''):
        if elements:
            self.load_elements(elements)
        self.handlers = {'T': self.text, 'L': self.line, 'I': self.image, 
                         'B': self.rect, 'BC': self.barcode, 'W': self.write, }
        self.texts = {}
        pdf = self.pdf = FPDF(format=format,orientation=orientation, unit="mm")
        pdf.set_title(title)
        pdf.set_author(author)
        pdf.set_creator(creator)
        pdf.set_subject(subject)
        pdf.set_keywords(keywords)

    def load_elements(self, elements):
        "Initialize the internal element structures"
        self.pg_no = 0
        self.elements = elements
        self.keys = [v['name'].lower() for v in self.elements]
    
    def parse_csv(self, infile, delimiter=",", decimal_sep="."):
        "Parse template format csv file and create elements dict"
        keys = ('name','type','x1','y1','x2','y2','font','size',
            'bold','italic','underline','foreground','background',
            'align','text','priority', 'multiline')
        self.elements = []
        self.pg_no = 0
        if not PY3K:
            f = open(infile, 'rb')
        else:
            f = open(infile)
        with f:
            for row in csv.reader(f, delimiter=delimiter):
                kargs = {}
                for i,v in enumerate(row):
                    if not v.startswith("'") and decimal_sep!=".": 
                        v = v.replace(decimal_sep,".")
                    else:
                        v = v
                    if v=='':
                        v = None
                    else:
                        v = eval(v.strip())
                    kargs[keys[i]] = v
                self.elements.append(kargs)
        self.keys = [v['name'].lower() for v in self.elements]

    def add_page(self):
        self.pg_no += 1
        self.texts[self.pg_no] = {}
        
    def __setitem__(self, name, value):
        if name.lower() in self.keys:
            if not PY3K and isinstance(value, unicode):
                value = value.encode("latin1","ignore")
            elif value is None:
                value = ""
            else:
                value = str(value)
            self.texts[self.pg_no][name.lower()] = value

    # setitem shortcut (may be further extended)
    set = __setitem__

    def has_key(self, name):
        return name.lower() in self.keys
        
    def __getitem__(self, name):
        if name in self.keys:
            key = name.lower()
            if key in self.texts:
                # text for this page:
                return self.texts[self.pg_no][key]
            else:
                # find first element for default text:
                elements = [element for element in self.elements
                    if element['name'].lower() == key]
                if elements:
                    return elements[0]['text']

    def split_multicell(self, text, element_name):
        "Divide (\n) a string using a given element width"
        pdf = self.pdf
        element = [element for element in self.elements
            if element['name'].lower() == element_name.lower()][0]
        style = ""
        if element['bold']: style += "B"
        if element['italic']: style += "I"
        if element['underline']: style += "U"
        pdf.set_font(element['font'],style,element['size'])
        align = {'L':'L','R':'R','I':'L','D':'R','C':'C','':''}.get(element['align']) # D/I in spanish
        if isinstance(text, unicode) and not PY3K:
            text = text.encode("latin1","ignore")
        else:
            text = str(text)
        return pdf.multi_cell(w=element['x2']-element['x1'],
                             h=element['y2']-element['y1'],
                             txt=text,align=align,split_only=True)
        
    def render(self, outfile, dest="F"):
        pdf = self.pdf
        for pg in range(1, self.pg_no+1):
            pdf.add_page()
            pdf.set_font('Arial','B',16)
            pdf.set_auto_page_break(False,margin=0)

            for element in sorted(self.elements,key=lambda x: x['priority']):
                #print "dib",element['type'], element['name'], element['x1'], element['y1'], element['x2'], element['y2']
                element = element.copy()
                element['text'] = self.texts[pg].get(element['name'].lower(), element['text'])
                if 'rotate' in element:
                    pdf.rotate(element['rotate'], element['x1'], element['y1'])
                self.handlers[element['type'].upper()](pdf, **element)
                if 'rotate' in element:
                    pdf.rotate(0)
        
        if dest:
            return pdf.output(outfile, dest)
        
    def text(self, pdf, x1=0, y1=0, x2=0, y2=0, text='', font="arial", size=10, 
             bold=False, italic=False, underline=False, align="", 
             foreground=0, backgroud=65535, multiline=None,
             *args, **kwargs):
        if text:
            if pdf.text_color!=rgb(foreground):
                pdf.set_text_color(*rgb(foreground))
            if pdf.fill_color!=rgb(backgroud):
                pdf.set_fill_color(*rgb(backgroud))

            font = font.strip().lower()
            if font == 'arial black':
                font = 'arial'
            style = ""
            for tag in 'B', 'I', 'U':
                if (text.startswith("<%s>" % tag) and text.endswith("</%s>" %tag)):
                    text = text[3:-4]
                    style += tag
            if bold: style += "B"
            if italic: style += "I"
            if underline: style += "U"
            align = {'L':'L','R':'R','I':'L','D':'R','C':'C','':''}.get(align) # D/I in spanish
            pdf.set_font(font,style,size)
            ##m_k = 72 / 2.54
            ##h = (size/m_k)
            pdf.set_xy(x1,y1)
            if multiline is None:
                # multiline==None: write without wrapping/trimming (default)
                pdf.cell(w=x2-x1,h=y2-y1,txt=text,border=0,ln=0,align=align)
            elif multiline:
                # multiline==True: automatic word - warp
                pdf.multi_cell(w=x2-x1,h=y2-y1,txt=text,border=0,align=align)
            else:
                # multiline==False: trim to fit exactly the space defined
                text = pdf.multi_cell(w=x2-x1, h=y2-y1,
                             txt=text, align=align, split_only=True)[0]
                print("trimming: *%s*" % text)
                pdf.cell(w=x2-x1,h=y2-y1,txt=text,border=0,ln=0,align=align)

            #pdf.Text(x=x1,y=y1,txt=text)

    def line(self, pdf, x1=0, y1=0, x2=0, y2=0, size=0, foreground=0, *args, **kwargs):
        if pdf.draw_color!=rgb(foreground):
            #print "SetDrawColor", hex(foreground)
            pdf.set_draw_color(*rgb(foreground))
        #print "SetLineWidth", size
        pdf.set_line_width(size)
        pdf.line(x1, y1, x2, y2)

    def rect(self, pdf, x1=0, y1=0, x2=0, y2=0, size=0, foreground=0, backgroud=65535, *args, **kwargs):
        if pdf.draw_color!=rgb(foreground):
            pdf.set_draw_color(*rgb(foreground))
        if pdf.fill_color!=rgb(backgroud):
            pdf.set_fill_color(*rgb(backgroud))
        pdf.set_line_width(size)
        pdf.rect(x1, y1, x2-x1, y2-y1)

    def image(self, pdf, x1=0, y1=0, x2=0, y2=0, text='', *args,**kwargs):
        if text:
            pdf.image(text,x1,y1,w=x2-x1,h=y2-y1,type='',link='')

    def barcode(self, pdf, x1=0, y1=0, x2=0, y2=0, text='', font="arial", size=1,
             foreground=0, *args, **kwargs):
        if pdf.draw_color!=rgb(foreground):
            pdf.set_draw_color(*rgb(foreground))
        font = font.lower().strip()
        if font == 'interleaved 2of5 nt':
            pdf.interleaved2of5(text,x1,y1,w=size,h=y2-y1)

    # Added by Derek Schwalenberg Schwalenberg1013@gmail.com to allow (url) links in templates (using write method) 2014-02-22
    def write(self, pdf, x1=0, y1=0, x2=0, y2=0, text='', font="arial", size=1,
              bold=False, italic=False, underline=False, align="", link='http://example.com',
             foreground=0, *args, **kwargs):
        if pdf.text_color!=rgb(foreground):
            pdf.set_text_color(*rgb(foreground))
        font = font.strip().lower()
        if font == 'arial black':
            font = 'arial'
        style = ""
        for tag in 'B', 'I', 'U':
            if (text.startswith("<%s>" % tag) and text.endswith("</%s>" %tag)):
                text = text[3:-4]
                style += tag
        if bold: style += "B"
        if italic: style += "I"
        if underline: style += "U"
        align = {'L':'L','R':'R','I':'L','D':'R','C':'C','':''}.get(align) # D/I in spanish
        pdf.set_font(font,style,size)
        ##m_k = 72 / 2.54
        ##h = (size/m_k)
        pdf.set_xy(x1,y1)
        pdf.write(5,text,link)
