#!/usr/bin/env python
# -*- coding: latin-1 -*-
# ******************************************************************************
# * Software: FPDF for python                                                  *
# * Version:  1.54c                                                            *
# * Date:     2010-09-10                                                       *
# * License:  LGPL v3.0                                                        *
# *                                                                            *
# * Original Author (PHP):  Olivier PLATHEY 2004-12-31                         *
# * Ported to Python 2.4 by Max (maxpat78@yahoo.it) on 2006-05                 *
# * Maintainer:  Mariano Reingart (reingart@gmail.com) et al since 2008 (est.) *
# * NOTE: 'I' and 'D' destinations are disabled, and simply print to STDOUT    *
# *****************************************************************************/

from datetime import datetime
import math
import os, sys, zlib, struct

try:
    # Check if PIL is available, necessary for JPEG support.
    import Image
except ImportError:
    Image = None

def substr(s, start, length=-1):
       if length < 0:
               length=len(s)-start
       return s[start:start+length]

def sprintf(fmt, *args): return fmt % args

# Global variables
FPDF_VERSION='1.54b'
FPDF_FONT_DIR=os.path.join(os.path.dirname(__file__),'font')
fpdf_charwidths = {}

class FPDF:
#Private properties
#~ page;               #current page number
#~ n;                  #current object number
#~ offsets;            #array of object offsets
#~ buffer;             #buffer holding in-memory PDF
#~ pages;              #array containing pages
#~ state;              #current document state
#~ compress;           #compression flag
#~ def_orientation;     #default orientation
#~ cur_orientation;     #current orientation
#~ orientation_changes; #array indicating orientation changes
#~ k;                  #scale factor (number of points in user unit)
#~ fw_pt,fh_pt;         #dimensions of page format in points
#~ fw,fh;             #dimensions of page format in user unit
#~ w_pt,h_pt;           #current dimensions of page in points
#~ w,h;               #current dimensions of page in user unit
#~ l_margin;            #left margin
#~ t_margin;            #top margin
#~ r_margin;            #right margin
#~ b_margin;            #page break margin
#~ c_margin;            #cell margin
#~ x,y;               #current position in user unit for cell positioning
#~ lasth;              #height of last cell printed
#~ line_width;          #line width in user unit
#~ core_fonts;          #array of standard font names
#~ fonts;              #array of used fonts
#~ font_files;          #array of font files
#~ diffs;              #array of encoding differences
#~ images;             #array of used images
#~ page_links;          #array of links in pages
#~ links;              #array of internal links
#~ font_family;         #current font family
#~ font_style;          #current font style
#~ underline;          #underlining flag
#~ current_font;        #current font info
#~ font_size_pt;         #current font size in points
#~ font_size;           #current font size in user unit
#~ draw_color;          #commands for drawing color
#~ fill_color;          #commands for filling color
#~ text_color;          #commands for text color
#~ color_flag;          #indicates whether fill and text colors are different
#~ ws;                 #word spacing
#~ auto_page_break;      #automatic page breaking
#~ page_break_trigger;   #threshold used to trigger page breaks
#~ in_footer;           #flag set when processing footer
#~ zoom_mode;           #zoom display mode
#~ layout_mode;         #layout display mode
#~ title;              #title
#~ subject;            #subject
#~ author;             #author
#~ keywords;           #keywords
#~ creator;            #creator
#~ alias_nb_pages;       #alias for total number of pages
#~ pdf_version;         #PDF version number

# ******************************************************************************
# *                                                                              *
# *                               Public methods                                 *
# *                                                                              *
# *******************************************************************************/
    def __init__(self, orientation='P',unit='mm',format='A4'):
        #Some checks
        self._dochecks()
        #Initialization of properties
        self.offsets={}
        self.page=0
        self.n=2
        self.buffer=''
        self.pages={}
        self.orientation_changes={}
        self.state=0
        self.fonts={}
        self.font_files={}
        self.diffs={}
        self.images={}
        self.page_links={}
        self.links={}
        self.in_footer=0
        self.lastw=0
        self.lasth=0
        self.font_family=''
        self.font_style=''
        self.font_size_pt=12
        self.underline=0
        self.draw_color='0 G'
        self.fill_color='0 g'
        self.text_color='0 g'
        self.color_flag=0
        self.ws=0
        self.angle=0
        #Standard fonts
        self.core_fonts={'courier':'Courier','courierB':'Courier-Bold','courierI':'Courier-Oblique','courierBI':'Courier-BoldOblique',
            'helvetica':'Helvetica','helveticaB':'Helvetica-Bold','helveticaI':'Helvetica-Oblique','helveticaBI':'Helvetica-BoldOblique',
            'times':'Times-Roman','timesB':'Times-Bold','timesI':'Times-Italic','timesBI':'Times-BoldItalic',
            'symbol':'Symbol','zapfdingbats':'ZapfDingbats'}
        #Scale factor
        if(unit=='pt'):
            self.k=1
        elif(unit=='mm'):
            self.k=72/25.4
        elif(unit=='cm'):
            self.k=72/2.54
        elif(unit=='in'):
            self.k=72
        else:
            self.error('Incorrect unit: '+unit)
        #Page format
        if(isinstance(format,basestring)):
            format=format.lower()
            if(format=='a3'):
                format=(841.89,1190.55)
            elif(format=='a4'):
                format=(595.28,841.89)
            elif(format=='a5'):
                format=(420.94,595.28)
            elif(format=='letter'):
                format=(612,792)
            elif(format=='legal'):
                format=(612,1008)
            else:
                self.error('Unknown page format: '+format)
            self.fw_pt=format[0]
            self.fh_pt=format[1]
        else:
            self.fw_pt=format[0]*self.k
            self.fh_pt=format[1]*self.k
        self.fw=self.fw_pt/self.k
        self.fh=self.fh_pt/self.k
        #Page orientation
        orientation=orientation.lower()
        if(orientation=='p' or orientation=='portrait'):
            self.def_orientation='P'
            self.w_pt=self.fw_pt
            self.h_pt=self.fh_pt
        elif(orientation=='l' or orientation=='landscape'):
            self.def_orientation='L'
            self.w_pt=self.fh_pt
            self.h_pt=self.fw_pt
        else:
            self.error('Incorrect orientation: '+orientation)
        self.cur_orientation=self.def_orientation
        self.w=self.w_pt/self.k
        self.h=self.h_pt/self.k
        #Page margins (1 cm)
        margin=28.35/self.k
        self.set_margins(margin,margin)
        #Interior cell margin (1 mm)
        self.c_margin=margin/10.0
        #line width (0.2 mm)
        self.line_width=.567/self.k
        #Automatic page break
        self.set_auto_page_break(1,2*margin)
        #Full width display mode
        self.set_display_mode('fullwidth')
        #Enable compression
        self.set_compression(1)
        #Set default PDF version number
        self.pdf_version='1.3'

    def set_margins(self, left,top,right=-1):
        "Set left, top and right margins"
        self.l_margin=left
        self.t_margin=top
        if(right==-1):
            right=left
        self.r_margin=right

    def set_left_margin(self, margin):
        "Set left margin"
        self.l_margin=margin
        if(self.page>0 and self.x<margin):
            self.x=margin

    def set_top_margin(self, margin):
        "Set top margin"
        self.t_margin=margin

    def set_right_margin(self, margin):
        "Set right margin"
        self.r_margin=margin

    def set_auto_page_break(self, auto,margin=0):
        "Set auto page break mode and triggering margin"
        self.auto_page_break=auto
        self.b_margin=margin
        self.page_break_trigger=self.h-margin

    def set_display_mode(self, zoom,layout='continuous'):
        "Set display mode in viewer"
        if(zoom=='fullpage' or zoom=='fullwidth' or zoom=='real' or zoom=='default' or not isinstance(zoom,basestring)):
            self.zoom_mode=zoom
        else:
            self.error('Incorrect zoom display mode: '+zoom)
        if(layout=='single' or layout=='continuous' or layout=='two' or layout=='default'):
            self.layout_mode=layout
        else:
            self.error('Incorrect layout display mode: '+layout)

    def set_compression(self, compress):
        "Set page compression"
        self.compress=compress

    def set_title(self, title):
        "Title of document"
        self.title=title

    def set_subject(self, subject):
        "Subject of document"
        self.subject=subject

    def set_author(self, author):
        "Author of document"
        self.author=author

    def set_keywords(self, keywords):
        "Keywords of document"
        self.keywords=keywords

    def set_creator(self, creator):
        "Creator of document"
        self.creator=creator

    def alias_nb_pages(self, alias='{nb}'):
        "Define an alias for total number of pages"
        self.str_alias_nb_pages=alias
        return alias

    def error(self, msg):
        "Fatal error"
        raise RuntimeError('FPDF error: '+msg)

    def open(self):
        "Begin document"
        self.state=1

    def close(self):
        "Terminate document"
        if(self.state==3):
            return
        if(self.page==0):
            self.add_page()
        #Page footer
        self.in_footer=1
        self.footer()
        self.in_footer=0
        #close page
        self._endpage()
        #close document
        self._enddoc()

    def add_page(self, orientation=''):
        "Start a new page"
        if(self.state==0):
            self.open()
        family=self.font_family
        if self.underline:
            style = self.font_style + 'U'
        else:
            style = self.font_style
        size=self.font_size_pt
        lw=self.line_width
        dc=self.draw_color
        fc=self.fill_color
        tc=self.text_color
        cf=self.color_flag
        if(self.page>0):
            #Page footer
            self.in_footer=1
            self.footer()
            self.in_footer=0
            #close page
            self._endpage()
        #Start new page
        self._beginpage(orientation)
        #Set line cap style to square
        self._out('2 J')
        #Set line width
        self.line_width=lw
        self._out(sprintf('%.2f w',lw*self.k))
        #Set font
        if(family):
            self.set_font(family,style,size)
        #Set colors
        self.draw_color=dc
        if(dc!='0 G'):
            self._out(dc)
        self.fill_color=fc
        if(fc!='0 g'):
            self._out(fc)
        self.text_color=tc
        self.color_flag=cf
        #Page header
        self.header()
        #Restore line width
        if(self.line_width!=lw):
            self.line_width=lw
            self._out(sprintf('%.2f w',lw*self.k))
        #Restore font
        if(family):
            self.set_font(family,style,size)
        #Restore colors
        if(self.draw_color!=dc):
            self.draw_color=dc
            self._out(dc)
        if(self.fill_color!=fc):
            self.fill_color=fc
            self._out(fc)
        self.text_color=tc
        self.color_flag=cf

    def header(self):
        "Header to be implemented in your own inherited class"
        pass

    def footer(self):
        "Footer to be implemented in your own inherited class"
        pass

    def page_no(self):
        "Get current page number"
        return self.page

    def set_draw_color(self, r,g=-1,b=-1):
        "Set color for all stroking operations"
        if((r==0 and g==0 and b==0) or g==-1):
            self.draw_color=sprintf('%.3f G',r/255.0)
        else:
            self.draw_color=sprintf('%.3f %.3f %.3f RG',r/255.0,g/255.0,b/255.0)
        if(self.page>0):
            self._out(self.draw_color)

    def set_fill_color(self,r,g=-1,b=-1):
        "Set color for all filling operations"
        if((r==0 and g==0 and b==0) or g==-1):
            self.fill_color=sprintf('%.3f g',r/255.0)
        else:
            self.fill_color=sprintf('%.3f %.3f %.3f rg',r/255.0,g/255.0,b/255.0)
        self.color_flag=(self.fill_color!=self.text_color)
        if(self.page>0):
            self._out(self.fill_color)

    def set_text_color(self, r,g=-1,b=-1):
        "Set color for text"
        if((r==0 and g==0 and b==0) or g==-1):
            self.text_color=sprintf('%.3f g',r/255.0)
        else:
            self.text_color=sprintf('%.3f %.3f %.3f rg',r/255.0,g/255.0,b/255.0)
        self.color_flag=(self.fill_color!=self.text_color)

    def get_string_width(self, s):
        "Get width of a string in the current font"
        cw=self.current_font['cw']
        w=0
        l=len(s)
        for i in xrange(0, l):
            w += cw.get(s[i],0)
        return w*self.font_size/1000.0

    def set_line_width(self, width):
        "Set line width"
        self.line_width=width
        if(self.page>0):
            self._out(sprintf('%.2f w',width*self.k))

    def line(self, x1,y1,x2,y2):
        "Draw a line"
        self._out(sprintf('%.2f %.2f m %.2f %.2f l S',x1*self.k,(self.h-y1)*self.k,x2*self.k,(self.h-y2)*self.k))

    def rect(self, x,y,w,h,style=''):
        "Draw a rectangle"
        if(style=='F'):
            op='f'
        elif(style=='FD' or style=='DF'):
            op='B'
        else:
            op='S'
        self._out(sprintf('%.2f %.2f %.2f %.2f re %s',x*self.k,(self.h-y)*self.k,w*self.k,-h*self.k,op))

    def add_font(self, family,style='',fname=''):
        "Add a TrueType or Type1 font"
        family=family.lower()
        if(fname==''):
            fname=family.replace(' ','')+style.lower()+'.font'
        fname=os.path.join(FPDF_FONT_DIR,fname)
        if(family=='arial'):
            family='helvetica'
        style=style.upper()
        if(style=='IB'):
            style='BI'
        fontkey=family+style
        if fontkey in self.fonts:
            self.error('Font already added: '+family+' '+style)
        execfile(fname, globals(), globals())
        if 'name' not in globals():
            self.error('Could not include font definition file')
        i=len(self.fonts)+1
        self.fonts[fontkey]={'i':i,'type':type,'name':name,'desc':desc,'up':up,'ut':ut,'cw':cw,'enc':enc,'file':filename}
        if(diff):
            #Search existing encodings
            d=0
            nb=len(self.diffs)
            for i in xrange(1,nb+1):
                if(self.diffs[i]==diff):
                    d=i
                    break
            if(d==0):
                d=nb+1
                self.diffs[d]=diff
            self.fonts[fontkey]['diff']=d
        if(filename):
            if(type=='TrueType'):
                self.font_files[filename]={'length1':originalsize}
            else:
                self.font_files[filename]={'length1':size1,'length2':size2}

    def set_font(self, family,style='',size=0):
        "Select a font; size given in points"
        family=family.lower()
        if(family==''):
            family=self.font_family
        if(family=='arial'):
            family='helvetica'
        elif(family=='symbol' or family=='zapfdingbats'):
            style=''
        style=style.upper()
        if('U' in style):
            self.underline=1
            style=style.replace('U','')
        else:
            self.underline=0
        if(style=='IB'):
            style='BI'
        if(size==0):
            size=self.font_size_pt
        #Test if font is already selected
        if(self.font_family==family and self.font_style==style and self.font_size_pt==size):
            return
        #Test if used for the first time
        fontkey=family+style
        if fontkey not in self.fonts:
            #Check if one of the standard fonts
            if fontkey in self.core_fonts:
                if fontkey not in fpdf_charwidths:
                    #Load metric file
                    name=os.path.join(FPDF_FONT_DIR,family)
                    if(family=='times' or family=='helvetica'):
                        name+=style.lower()
                    execfile(name+'.font')
                    if fontkey not in fpdf_charwidths:
                        self.error('Could not include font metric file for'+fontkey)
                i=len(self.fonts)+1
                self.fonts[fontkey]={'i':i,'type':'core','name':self.core_fonts[fontkey],'up':-100,'ut':50,'cw':fpdf_charwidths[fontkey]}
            else:
                self.error('Undefined font: '+family+' '+style)
        #Select it
        self.font_family=family
        self.font_style=style
        self.font_size_pt=size
        self.font_size=size/self.k
        self.current_font=self.fonts[fontkey]
        if(self.page>0):
            self._out(sprintf('BT /F%d %.2f Tf ET',self.current_font['i'],self.font_size_pt))

    def set_font_size(self, size):
        "Set font size in points"
        if(self.font_size_pt==size):
            return
        self.font_size_pt=size
        self.font_size=size/self.k
        if(self.page>0):
            self._out(sprintf('BT /F%d %.2f Tf ET',self.current_font['i'],self.font_size_pt))

    def add_link(self):
        "Create a new internal link"
        n=len(self.links)+1
        self.links[n]=(0,0)
        return n

    def set_link(self, link,y=0,page=-1):
        "Set destination of internal link"
        if(y==-1):
            y=self.y
        if(page==-1):
            page=self.page
        self.links[link]=[page,y]

    def link(self, x,y,w,h,link):
        "Put a link on the page"
        if not self.page in self.page_links:
            self.page_links[self.page] = []
        self.page_links[self.page] += [(x*self.k,self.h_pt-y*self.k,w*self.k,h*self.k,link),]

    def text(self, x,y,txt):
        "Output a string"
        s=sprintf('BT %.2f %.2f Td (%s) Tj ET',x*self.k,(self.h-y)*self.k,self._escape(txt))
        if(self.underline and txt!=''):
            s+=' '+self._dounderline(x,y,txt)
        if(self.color_flag):
            s='q '+self.text_color+' '+s+' Q'
        self._out(s)

    def rotate(self, angle, x=None, y=None):
        if x is None:
            x = self.x
        if y is None:
            y = self.y;
        if self.angle!=0:
            self._out('Q')
        self.angle = angle
        if angle!=0:
            angle *= math.pi/180;
            c = math.cos(angle);
            s = math.sin(angle);
            cx = x*self.k;
            cy = (self.h-y)*self.k
            s = sprintf('q %.5F %.5F %.5F %.5F %.2F %.2F cm 1 0 0 1 %.2F %.2F cm',c,s,-s,c,cx,cy,-cx,-cy)
            self._out(s)

    def accept_page_break(self):
        "Accept automatic page break or not"
        return self.auto_page_break

    def cell(self, w,h=0,txt='',border=0,ln=0,align='',fill=0,link=''):
        "Output a cell"
        k=self.k
        if(self.y+h>self.page_break_trigger and not self.in_footer and self.accept_page_break()):
            #Automatic page break
            x=self.x
            ws=self.ws
            if(ws>0):
                self.ws=0
                self._out('0 Tw')
            self.add_page(self.cur_orientation)
            self.x=x
            if(ws>0):
                self.ws=ws
                self._out(sprintf('%.3f Tw',ws*k))
        if(w==0):
            w=self.w-self.r_margin-self.x
        s=''
        if(fill==1 or border==1):
            if(fill==1):
                if border==1:
                    op='B'
                else:
                    op='f'
            else:
                op='S'
            s=sprintf('%.2f %.2f %.2f %.2f re %s ',self.x*k,(self.h-self.y)*k,w*k,-h*k,op)
        if(isinstance(border,basestring)):
            x=self.x
            y=self.y
            if('L' in border):
                s+=sprintf('%.2f %.2f m %.2f %.2f l S ',x*k,(self.h-y)*k,x*k,(self.h-(y+h))*k)
            if('T' in border):
                s+=sprintf('%.2f %.2f m %.2f %.2f l S ',x*k,(self.h-y)*k,(x+w)*k,(self.h-y)*k)
            if('R' in border):
                s+=sprintf('%.2f %.2f m %.2f %.2f l S ',(x+w)*k,(self.h-y)*k,(x+w)*k,(self.h-(y+h))*k)
            if('B' in border):
                s+=sprintf('%.2f %.2f m %.2f %.2f l S ',x*k,(self.h-(y+h))*k,(x+w)*k,(self.h-(y+h))*k)
        if(txt!=''):
            if(align=='R'):
                dx=w-self.c_margin-self.get_string_width(txt)
            elif(align=='C'):
                dx=(w-self.get_string_width(txt))/2.0
            else:
                dx=self.c_margin
            if(self.color_flag):
                s+='q '+self.text_color+' '
            txt2=txt.replace('\\','\\\\').replace(')','\\)').replace('(','\\(')
            s+=sprintf('BT %.2f %.2f Td (%s) Tj ET',(self.x+dx)*k,(self.h-(self.y+.5*h+.3*self.font_size))*k,txt2)
            if(self.underline):
                s+=' '+self._dounderline(self.x+dx,self.y+.5*h+.3*self.font_size,txt)
            if(self.color_flag):
                s+=' Q'
            if(link):
                self.link(self.x+dx,self.y+.5*h-.5*self.font_size,self.get_string_width(txt),self.font_size,link)
        if(s):
            self._out(s)
        self.lasth=h
        if(ln>0):
            #Go to next line
            self.y+=h
            if(ln==1):
                self.x=self.l_margin
        else:
            self.x+=w

    def multi_cell(self, w,h,txt,border=0,align='J',fill=0, split_only=False):
        "Output text with automatic or explicit line breaks"
        ret = [] # if split_only = True, returns splited text cells
        cw=self.current_font['cw']
        if(w==0):
            w=self.w-self.r_margin-self.x
        wmax=(w-2*self.c_margin)*1000.0/self.font_size
        s=txt.replace("\r",'')
        nb=len(s)
        if(nb>0 and s[nb-1]=="\n"):
            nb-=1
        b=0
        if(border):
            if(border==1):
                border='LTRB'
                b='LRT'
                b2='LR'
            else:
                b2=''
                if('L' in border):
                    b2+='L'
                if('R' in border):
                    b2+='R'
                if ('T' in border):
                    b=b2+'T'
                else:
                    b=b2
        sep=-1
        i=0
        j=0
        l=0
        ns=0
        nl=1
        while(i<nb):
            #Get next character
            c=s[i]
            if(c=="\n"):
                #Explicit line break
                if(self.ws>0):
                    self.ws=0
                    self._out('0 Tw')
                if not split_only:
                    self.cell(w,h,substr(s,j,i-j),b,2,align,fill)
                else:
                    ret.append(substr(s,j,i-j))
                i+=1
                sep=-1
                j=i
                l=0
                ns=0
                nl+=1
                if(border and nl==2):
                    b=b2
                continue
            if(c==' '):
                sep=i
                ls=l
                ns+=1
            l+=cw.get(c,0)
            if(l>wmax):
                #Automatic line break
                if(sep==-1):
                    if(i==j):
                        i+=1
                    if(self.ws>0):
                        self.ws=0
                        self._out('0 Tw')
                    if not split_only:
                        self.cell(w,h,substr(s,j,i-j),b,2,align,fill)
                    else:
                        ret.append(substr(s,j,i-j))
                else:
                    if(align=='J'):
                        if ns>1:
                            self.ws=(wmax-ls)/1000.0*self.font_size/(ns-1)
                        else:
                            self.ws=0
                        self._out(sprintf('%.3f Tw',self.ws*self.k))
                    if not split_only:
                        self.cell(w,h,substr(s,j,sep-j),b,2,align,fill)
                    else:
                        ret.append(substr(s,j,sep-j))
                    i=sep+1
                sep=-1
                j=i
                l=0
                ns=0
                nl+=1
                if(border and nl==2):
                    b=b2
            else:
                i+=1
        #Last chunk
        if(self.ws>0):
            self.ws=0
            self._out('0 Tw')
        if(border and 'B' in border):
            b+='B'
        if not split_only:
            self.cell(w,h,substr(s,j,i-j),b,2,align,fill)
        else:
            ret.append(substr(s,j,i-j))
        self.x=self.l_margin
        return ret

    def write(self, h,txt,link=''):
        "Output text in flowing mode"
        cw=self.current_font['cw']
        w=self.w-self.r_margin-self.x
        wmax=(w-2*self.c_margin)*1000.0/self.font_size
        s=txt.replace("\r",'')
        nb=len(s)
        sep=-1
        i=0
        j=0
        l=0
        nl=1
        while(i<nb):
            #Get next character
            c=s[i]
            if(c=="\n"):
                #Explicit line break
                self.cell(w,h,substr(s,j,i-j),0,2,'',0,link)
                i+=1
                sep=-1
                j=i
                l=0
                if(nl==1):
                    self.x=self.l_margin
                    w=self.w-self.r_margin-self.x
                    wmax=(w-2*self.c_margin)*1000.0/self.font_size
                nl+=1
                continue
            if(c==' '):
                sep=i
            l+=cw.get(c,0)
            if(l>wmax):
                #Automatic line break
                if(sep==-1):
                    if(self.x>self.l_margin):
                        #Move to next line
                        self.x=self.l_margin
                        self.y+=h
                        w=self.w-self.r_margin-self.x
                        wmax=(w-2*self.c_margin)*1000.0/self.font_size
                        i+=1
                        nl+=1
                        continue
                    if(i==j):
                        i+=1
                    self.cell(w,h,substr(s,j,i-j),0,2,'',0,link)
                else:
                    self.cell(w,h,substr(s,j,sep-j),0,2,'',0,link)
                    i=sep+1
                sep=-1
                j=i
                l=0
                if(nl==1):
                    self.x=self.l_margin
                    w=self.w-self.r_margin-self.x
                    wmax=(w-2*self.c_margin)*1000.0/self.font_size
                nl+=1
            else:
                i+=1
        #Last chunk
        if(i!=j):
            self.cell(l/1000.0*self.font_size,h,substr(s,j),0,0,'',0,link)

    def image(self, name,x,y,w=0,h=0,type='',link=''):
        "Put an image on the page"
        if not name in self.images:
            #First use of image, get info
            if(type==''):
                pos=name.rfind('.')
                if(not pos):
                    self.error('image file has no extension and no type was specified: '+name)
                type=substr(name,pos+1)
            type=type.lower()
            if(type=='jpg' or type=='jpeg'):
                info=self._parsejpg(name)
            elif(type=='png'):
                info=self._parsepng(name)
            else:
                #Allow for additional formats
                mtd='_parse'+type
                if not hasattr(self,mtd):
                    self.error('Unsupported image type: '+type)
                info=self.mtd(name)
            info['i']=len(self.images)+1
            self.images[name]=info
        else:
            info=self.images[name]
        #Automatic width and height calculation if needed
        if(w==0 and h==0):
            #Put image at 72 dpi
            w=info['w']/self.k
            h=info['h']/self.k
        if(w==0):
            w=h*info['w']/info['h']
        if(h==0):
            h=w*info['h']/info['w']
        self._out(sprintf('q %.2f 0 0 %.2f %.2f %.2f cm /I%d Do Q',w*self.k,h*self.k,x*self.k,(self.h-(y+h))*self.k,info['i']))
        if(link):
            self.link(x,y,w,h,link)

    def ln(self, h=''):
        "Line Feed; default value is last cell height"
        self.x=self.l_margin
        if(isinstance(h, basestring)):
            self.y+=self.lasth
        else:
            self.y+=h

    def get_x(self):
        "Get x position"
        return self.x

    def set_x(self, x):
        "Set x position"
        if(x>=0):
            self.x=x
        else:
            self.x=self.w+x

    def get_y(self):
        "Get y position"
        return self.y

    def set_y(self, y):
        "Set y position and reset x"
        self.x=self.l_margin
        if(y>=0):
            self.y=y
        else:
            self.y=self.h+y

    def set_xy(self, x,y):
        "Set x and y positions"
        self.set_y(y)
        self.set_x(x)

    def output(self, name='',dest=''):
        "Output PDF to some destination"
        #Finish document if necessary
        if(self.state<3):
            self.close()
        #Normalize parameters
 #       if(type(dest)==type(bool())):
 #           if dest:
 #               dest='D'
 #           else:
 #               dest='F'
        dest=dest.upper()
        if(dest==''):
            if(name==''):
                name='doc.pdf'
                dest='I'
            else:
                dest='F'
        if dest=='I':
            print self.buffer
        elif dest=='D':
            print self.buffer
        elif dest=='F':
            #Save to local file
            f=file(name,'wb')
            if(not f):
                self.error('Unable to create output file: '+name)
            f.write(self.buffer)
            f.close()
        elif dest=='S':
            #Return as a string
            return self.buffer
        else:
            self.error('Incorrect output destination: '+dest)
        return ''

# ******************************************************************************
# *                                                                              *
# *                              Protected methods                               *
# *                                                                              *
# *******************************************************************************/
    def _dochecks(self):
        #Check for locale-related bug
#        if(1.1==1):
#            self.error("Don\'t alter the locale before including class file");
        #Check for decimal separator
        if(sprintf('%.1f',1.0)!='1.0'):
            import locale
            locale.setlocale(locale.LC_NUMERIC,'C')

    def _getfontpath(self):
        return FPDF_FONT_DIR+'/'

    def _putpages(self):
        nb=self.page
        if hasattr(self,'str_alias_nb_pages'):
            #Replace number of pages
            for n in xrange(1,nb+1):
                self.pages[n]=self.pages[n].replace(self.str_alias_nb_pages,str(nb))
        if(self.def_orientation=='P'):
            w_pt=self.fw_pt
            h_pt=self.fh_pt
        else:
            w_pt=self.fh_pt
            h_pt=self.fw_pt
        if self.compress:
            filter='/Filter /FlateDecode '
        else:
            filter=''
        for n in xrange(1,nb+1):
            #Page
            self._newobj()
            self._out('<</Type /Page')
            self._out('/Parent 1 0 R')
            if n in self.orientation_changes:
                self._out(sprintf('/MediaBox [0 0 %.2f %.2f]',h_pt,w_pt))
            self._out('/Resources 2 0 R')
            if self.page_links and n in self.page_links:
                #Links
                annots='/Annots ['
                for pl in self.page_links[n]:
                    rect=sprintf('%.2f %.2f %.2f %.2f',pl[0],pl[1],pl[0]+pl[2],pl[1]-pl[3])
                    annots+='<</Type /Annot /Subtype /Link /Rect ['+rect+'] /Border [0 0 0] '
                    if(isinstance(pl[4],basestring)):
                        annots+='/A <</S /URI /URI '+self._textstring(pl[4])+'>>>>'
                    else:
                        l=self.links[pl[4]]
                        if l[0] in self.orientation_changes:
                            h=w_pt
                        else:
                            h=h_pt
                        annots+=sprintf('/Dest [%d 0 R /XYZ 0 %.2f null]>>',1+2*l[0],h-l[1]*self.k)
                self._out(annots+']')
            self._out('/Contents '+str(self.n+1)+' 0 R>>')
            self._out('endobj')
            #Page content
            if self.compress:
                p = zlib.compress(self.pages[n])
            else:
                p = self.pages[n]
            self._newobj()
            self._out('<<'+filter+'/Length '+str(len(p))+'>>')
            self._putstream(p)
            self._out('endobj')
        #Pages root
        self.offsets[1]=len(self.buffer)
        self._out('1 0 obj')
        self._out('<</Type /Pages')
        kids='/Kids ['
        for i in xrange(0,nb):
            kids+=str(3+2*i)+' 0 R '
        self._out(kids+']')
        self._out('/Count '+str(nb))
        self._out(sprintf('/MediaBox [0 0 %.2f %.2f]',w_pt,h_pt))
        self._out('>>')
        self._out('endobj')

    def _putfonts(self):
        nf=self.n
        for diff in self.diffs:
            #Encodings
            self._newobj()
            self._out('<</Type /Encoding /BaseEncoding /WinAnsiEncoding /Differences ['+self.diffs[diff]+']>>')
            self._out('endobj')
        for name,info in self.font_files.iteritems():
            #Font file embedding
            self._newobj()
            self.font_files[name]['n']=self.n
            font=''
            f=file(self._getfontpath()+name,'rb',1)
            if(not f):
                self.error('Font file not found')
            font=f.read()
            f.close()
            compressed=(substr(name,-2)=='.z')
            if(not compressed and 'length2' in info):
                header=(ord(font[0])==128)
                if(header):
                    #Strip first binary header
                    font=substr(font,6)
                if(header and ord(font[info['length1']])==128):
                    #Strip second binary header
                    font=substr(font,0,info['length1'])+substr(font,info['length1']+6)
            self._out('<</Length '+str(len(font)))
            if(compressed):
                self._out('/Filter /FlateDecode')
            self._out('/Length1 '+str(info['length1']))
            if('length2' in info):
                self._out('/Length2 '+str(info['length2'])+' /Length3 0')
            self._out('>>')
            self._putstream(font)
            self._out('endobj')
        for k,font in self.fonts.iteritems():
            #Font objects
            self.fonts[k]['n']=self.n+1
            type=font['type']
            name=font['name']
            if(type=='core'):
                #Standard font
                self._newobj()
                self._out('<</Type /Font')
                self._out('/BaseFont /'+name)
                self._out('/Subtype /Type1')
                if(name!='Symbol' and name!='ZapfDingbats'):
                    self._out('/Encoding /WinAnsiEncoding')
                self._out('>>')
                self._out('endobj')
            elif(type=='Type1' or type=='TrueType'):
                #Additional Type1 or TrueType font
                self._newobj()
                self._out('<</Type /Font')
                self._out('/BaseFont /'+name)
                self._out('/Subtype /'+type)
                self._out('/FirstChar 32 /LastChar 255')
                self._out('/Widths '+str(self.n+1)+' 0 R')
                self._out('/FontDescriptor '+str(self.n+2)+' 0 R')
                if(font['enc']):
                    if('diff' in font):
                        self._out('/Encoding '+str(nf+font['diff'])+' 0 R')
                    else:
                        self._out('/Encoding /WinAnsiEncoding')
                self._out('>>')
                self._out('endobj')
                #Widths
                self._newobj()
                cw=font['cw']
                s='['
                for i in xrange(32,256):
                    # Get doesn't rise exception; returns 0 instead of None if not set
                    s+=str(cw.get(chr(i)) or 0)+' '
                self._out(s+']')
                self._out('endobj')
                #Descriptor
                self._newobj()
                s='<</Type /FontDescriptor /FontName /'+name
                for k,v in font['desc'].iteritems():
                    s+=' /'+str(k)+' '+str(v)
                filename=font['file']
                if(filename):
                    s+=' /FontFile'
                    if type!='Type1':
                        s+='2'
                    s+=' '+str(self.font_files[filename]['n'])+' 0 R'
                self._out(s+'>>')
                self._out('endobj')
            else:
                #Allow for additional types
                mtd='_put'+type.lower()
                if(not method_exists(self,mtd)):
                    self.error('Unsupported font type: '+type)
                self.mtd(font)

    def _putimages(self):
        filter=''
        if self.compress:
            filter='/Filter /FlateDecode '
        for filename,info in self.images.iteritems():
            self._newobj()
            self.images[filename]['n']=self.n
            self._out('<</Type /XObject')
            self._out('/Subtype /Image')
            self._out('/Width '+str(info['w']))
            self._out('/Height '+str(info['h']))
            if(info['cs']=='Indexed'):
                self._out('/ColorSpace [/Indexed /DeviceRGB '+str(len(info['pal'])/3-1)+' '+str(self.n+1)+' 0 R]')
            else:
                self._out('/ColorSpace /'+info['cs'])
                if(info['cs']=='DeviceCMYK'):
                    self._out('/Decode [1 0 1 0 1 0 1 0]')
            self._out('/BitsPerComponent '+str(info['bpc']))
            if 'f' in info:
                self._out('/Filter /'+info['f'])
            if 'parms' in info:
                self._out(info['parms'])
            if('trns' in info and isinstance(info['trns'],list)):
                trns=''
                for i in xrange(0,len(info['trns'])):
                    trns+=str(info['trns'][i])+' '+str(info['trns'][i])+' '
                self._out('/Mask ['+trns+']')
            self._out('/Length '+str(len(info['data']))+'>>')
            self._putstream(info['data'])
            self.images[filename]['data'] = None
            self._out('endobj')
            #Palette
            if(info['cs']=='Indexed'):
                self._newobj()
                if self.compress:
                    pal=zlib.compress(info['pal'])
                else:
                    pal=info['pal']
                self._out('<<'+filter+'/Length '+str(len(pal))+'>>')
                self._putstream(pal)
                self._out('endobj')

    def _putxobjectdict(self):
        for image in self.images.values():
            self._out('/I'+str(image['i'])+' '+str(image['n'])+' 0 R')

    def _putresourcedict(self):
        self._out('/ProcSet [/PDF /Text /ImageB /ImageC /ImageI]')
        self._out('/Font <<')
        for font in self.fonts.values():
            self._out('/F'+str(font['i'])+' '+str(font['n'])+' 0 R')
        self._out('>>')
        self._out('/XObject <<')
        self._putxobjectdict()
        self._out('>>')

    def _putresources(self):
        self._putfonts()
        self._putimages()
        #Resource dictionary
        self.offsets[2]=len(self.buffer)
        self._out('2 0 obj')
        self._out('<<')
        self._putresourcedict()
        self._out('>>')
        self._out('endobj')

    def _putinfo(self):
        self._out('/Producer '+self._textstring('PyFPDF '+FPDF_VERSION+' http://pyfpdf.googlecode.com/'))
        if hasattr(self,'title'):
            self._out('/Title '+self._textstring(self.title))
        if hasattr(self,'subject'):
            self._out('/Subject '+self._textstring(self.subject))
        if hasattr(self,'author'):
            self._out('/Author '+self._textstring(self.author))
        if hasattr (self,'keywords'):
            self._out('/Keywords '+self._textstring(self.keywords))
        if hasattr(self,'creator'):
            self._out('/Creator '+self._textstring(self.creator))
        self._out('/CreationDate '+self._textstring('D:'+datetime.now().strftime('%Y%m%d%H%M%S')))

    def _putcatalog(self):
        self._out('/Type /Catalog')
        self._out('/Pages 1 0 R')
        if(self.zoom_mode=='fullpage'):
            self._out('/OpenAction [3 0 R /Fit]')
        elif(self.zoom_mode=='fullwidth'):
            self._out('/OpenAction [3 0 R /FitH null]')
        elif(self.zoom_mode=='real'):
            self._out('/OpenAction [3 0 R /XYZ null null 1]')
        elif(not isinstance(self.zoom_mode,basestring)):
            self._out('/OpenAction [3 0 R /XYZ null null '+(self.zoom_mode/100)+']')
        if(self.layout_mode=='single'):
            self._out('/PageLayout /SinglePage')
        elif(self.layout_mode=='continuous'):
            self._out('/PageLayout /OneColumn')
        elif(self.layout_mode=='two'):
            self._out('/PageLayout /TwoColumnLeft')

    def _putheader(self):
        self._out('%PDF-'+self.pdf_version)

    def _puttrailer(self):
        self._out('/Size '+str(self.n+1))
        self._out('/Root '+str(self.n)+' 0 R')
        self._out('/Info '+str(self.n-1)+' 0 R')

    def _enddoc(self):
        self._putheader()
        self._putpages()
        self._putresources()
        #Info
        self._newobj()
        self._out('<<')
        self._putinfo()
        self._out('>>')
        self._out('endobj')
        #Catalog
        self._newobj()
        self._out('<<')
        self._putcatalog()
        self._out('>>')
        self._out('endobj')
        #Cross-ref
        o=len(self.buffer)
        self._out('xref')
        self._out('0 '+(str(self.n+1)))
        self._out('0000000000 65535 f ')
        for i in xrange(1,self.n+1):
            self._out(sprintf('%010d 00000 n ',self.offsets[i]))
        #Trailer
        self._out('trailer')
        self._out('<<')
        self._puttrailer()
        self._out('>>')
        self._out('startxref')
        self._out(o)
        self._out('%%EOF')
        self.state=3

    def _beginpage(self, orientation):
        self.page+=1
        self.pages[self.page]=''
        self.state=2
        self.x=self.l_margin
        self.y=self.t_margin
        self.font_family=''
        #Page orientation
        if(not orientation):
            orientation=self.def_orientation
        else:
            orientation=orientation[0].upper()
            if(orientation!=self.def_orientation):
                self.orientation_changes[self.page]=1
        if(orientation!=self.cur_orientation):
            #Change orientation
            if(orientation=='P'):
                self.w_pt=self.fw_pt
                self.h_pt=self.fh_pt
                self.w=self.fw
                self.h=self.fh
            else:
                self.w_pt=self.fh_pt
                self.h_pt=self.fw_pt
                self.w=self.fh
                self.h=self.fw
            self.page_break_trigger=self.h-self.b_margin
            self.cur_orientation=orientation

    def _endpage(self):
        #End of page contents
        self.state=1

    def _newobj(self):
        #Begin a new object
        self.n+=1
        self.offsets[self.n]=len(self.buffer)
        self._out(str(self.n)+' 0 obj')

    def _dounderline(self, x,y,txt):
        #Underline text
        up=self.current_font['up']
        ut=self.current_font['ut']
        w=self.get_string_width(txt)+self.ws*txt.count(' ')
        return sprintf('%.2f %.2f %.2f %.2f re f',x*self.k,(self.h-(y-up/1000.0*self.font_size))*self.k,w*self.k,-ut/1000.0*self.font_size_pt)

    def _parsejpg(self, filename):
        # Extract info from a JPEG file
        if Image is None:
            self.error('PIL not installed')
        try:
            f = open(filename, 'rb')
            im = Image.open(f)
        except Exception, e:
            self.error('Missing or incorrect image file: %s. error: %s' % (filename, str(e)))
        else:
            a = im.size
        # We shouldn't get into here, as Jpeg is RGB=8bpp right(?), but, just in case...
        bpc=8
        if im.mode == 'RGB':
            colspace='DeviceRGB'
        elif im.mode == 'CMYK':
            colspace='DeviceCMYK'
        else:
            colspace='DeviceGray'

        # Read whole file from the start
        f.seek(0)
        data = f.read()
        f.close()
        return {'w':a[0],'h':a[1],'cs':colspace,'bpc':bpc,'f':'DCTDecode','data':data}

    def _parsepng(self, name):
        #Extract info from a PNG file
        if name.startswith("http://") or name.startswith("https://"):
            import urllib
            f = urllib.urlopen(name)
        else:
            f=open(name,'rb')
        if(not f):
            self.error("Can't open image file: "+name)
        #Check signature
        if(f.read(8)!='\x89'+'PNG'+'\r'+'\n'+'\x1a'+'\n'):
            self.error('Not a PNG file: '+name)
        #Read header chunk
        f.read(4)
        if(f.read(4)!='IHDR'):
            self.error('Incorrect PNG file: '+name)
        w=self._freadint(f)
        h=self._freadint(f)
        bpc=ord(f.read(1))
        if(bpc>8):
            self.error('16-bit depth not supported: '+name)
        ct=ord(f.read(1))
        if(ct==0):
            colspace='DeviceGray'
        elif(ct==2):
            colspace='DeviceRGB'
        elif(ct==3):
            colspace='Indexed'
        else:
            self.error('Alpha channel not supported: '+name)
        if(ord(f.read(1))!=0):
            self.error('Unknown compression method: '+name)
        if(ord(f.read(1))!=0):
            self.error('Unknown filter method: '+name)
        if(ord(f.read(1))!=0):
            self.error('Interlacing not supported: '+name)
        f.read(4)
        parms='/DecodeParms <</Predictor 15 /Colors '
        if ct==2:
            parms+='3'
        else:
            parms+='1'
        parms+=' /BitsPerComponent '+str(bpc)+' /Columns '+str(w)+'>>'
        #Scan chunks looking for palette, transparency and image data
        pal=''
        trns=''
        data=''
        n=1
        while n != None:
            n=self._freadint(f)
            type=f.read(4)
            if(type=='PLTE'):
                #Read palette
                pal=f.read(n)
                f.read(4)
            elif(type=='tRNS'):
                #Read transparency info
                t=f.read(n)
                if(ct==0):
                    trns=[ord(substr(t,1,1)),]
                elif(ct==2):
                    trns=[ord(substr(t,1,1)),ord(substr(t,3,1)),ord(substr(t,5,1))]
                else:
                    pos=t.find('\x00')
                    if(pos!=-1):
                        trns=[pos,]
                f.read(4)
            elif(type=='IDAT'):
                #Read image data block
                data+=f.read(n)
                f.read(4)
            elif(type=='IEND'):
                break
            else:
                f.read(n+4)
        if(colspace=='Indexed' and not pal):
            self.error('Missing palette in '+name)
        f.close()
        return {'w':w,'h':h,'cs':colspace,'bpc':bpc,'f':'FlateDecode','parms':parms,'pal':pal,'trns':trns,'data':data}

    def _freadint(self, f):
        #Read a 4-byte integer from file
        try:
            return struct.unpack('>HH',f.read(4))[1]
        except:
            return None

    def _textstring(self, s):
        #Format a text string
        return '('+self._escape(s)+')'

    def _escape(self, s):
        #Add \ before \, ( and )
        return s.replace('\\','\\\\').replace(')','\\)').replace('(','\\(')

    def _putstream(self, s):
        self._out('stream')
        self._out(s)
        self._out('endstream')

    def _out(self, s):
        #Add a line to the document
        if(self.state==2):
            self.pages[self.page]+=s+"\n"
        else:
            self.buffer+=str(s)+"\n"

    def interleaved2of5(self, txt, x, y, w=1.0, h=10.0):
        "Barcode I2of5 (numeric), adds a 0 if odd lenght"
        narrow = w / 3.0
        wide = w

        # wide/narrow codes for the digits
        bar_char={}
        bar_char['0'] = 'nnwwn'
        bar_char['1'] = 'wnnnw'
        bar_char['2'] = 'nwnnw'
        bar_char['3'] = 'wwnnn'
        bar_char['4'] = 'nnwnw'
        bar_char['5'] = 'wnwnn'
        bar_char['6'] = 'nwwnn'
        bar_char['7'] = 'nnnww'
        bar_char['8'] = 'wnnwn'
        bar_char['9'] = 'nwnwn'
        bar_char['A'] = 'nn'
        bar_char['Z'] = 'wn'

        self.set_fill_color(0)
        code = txt
        # add leading zero if code-length is odd
        if len(code) % 2 != 0:
            code = '0' + code

        # add start and stop codes
        code = 'AA' + code.lower() + 'ZA'

        for i in xrange(0, len(code), 2):
            # choose next pair of digits
            char_bar = code[i];
            char_space = code[i+1];
            # check whether it is a valid digit
            if not char_bar in bar_char.keys():
                raise RuntimeError ('Caractér "%s" inválido para el código de barras I25: ' % char_bar)
            if not char_space in bar_char.keys():
                raise RuntimeError ('Caractér "%s" inválido para el código de barras I25: ' % char_space)

            # create a wide/narrow-sequence (first digit=bars, second digit=spaces)
            seq = ''
            for s in xrange(0, len(bar_char[char_bar])):
                seq += bar_char[char_bar][s] + bar_char[char_space][s]

            for bar in xrange(0, len(seq)):
                # set line_width depending on value
                if seq[bar] == 'n':
                    line_width = narrow
                else:
                    line_width = wide

                # draw every second value, because the second digit of the pair is represented by the spaces
                if bar % 2 == 0:
                    self.rect(x, y, line_width, h, 'F')

                x += line_width


    def code39(self, txt, x, y, w=1.5, h=5.0):
        "Barcode 3of9"
        wide = w
        narrow = w /3.0
        gap = narrow

        bar_char={}
        bar_char['0'] = 'nnnwwnwnn'
        bar_char['1'] = 'wnnwnnnnw'
        bar_char['2'] = 'nnwwnnnnw'
        bar_char['3'] = 'wnwwnnnnn'
        bar_char['4'] = 'nnnwwnnnw'
        bar_char['5'] = 'wnnwwnnnn'
        bar_char['6'] = 'nnwwwnnnn'
        bar_char['7'] = 'nnnwnnwnw'
        bar_char['8'] = 'wnnwnnwnn'
        bar_char['9'] = 'nnwwnnwnn'
        bar_char['A'] = 'wnnnnwnnw'
        bar_char['B'] = 'nnwnnwnnw'
        bar_char['C'] = 'wnwnnwnnn'
        bar_char['D'] = 'nnnnwwnnw'
        bar_char['E'] = 'wnnnwwnnn'
        bar_char['F'] = 'nnwnwwnnn'
        bar_char['G'] = 'nnnnnwwnw'
        bar_char['H'] = 'wnnnnwwnn'
        bar_char['I'] = 'nnwnnwwnn'
        bar_char['J'] = 'nnnnwwwnn'
        bar_char['K'] = 'wnnnnnnww'
        bar_char['L'] = 'nnwnnnnww'
        bar_char['M'] = 'wnwnnnnwn'
        bar_char['N'] = 'nnnnwnnww'
        bar_char['O'] = 'wnnnwnnwn'
        bar_char['P'] = 'nnwnwnnwn'
        bar_char['Q'] = 'nnnnnnwww'
        bar_char['R'] = 'wnnnnnwwn'
        bar_char['S'] = 'nnwnnnwwn'
        bar_char['T'] = 'nnnnwnwwn'
        bar_char['U'] = 'wwnnnnnnw'
        bar_char['V'] = 'nwwnnnnnw'
        bar_char['W'] = 'wwwnnnnnn'
        bar_char['X'] = 'nwnnwnnnw'
        bar_char['Y'] = 'wwnnwnnnn'
        bar_char['Z'] = 'nwwnwnnnn'
        bar_char['-'] = 'nwnnnnwnw'
        bar_char['.'] = 'wwnnnnwnn'
        bar_char[' '] = 'nwwnnnwnn'
        bar_char['*'] = 'nwnnwnwnn'
        bar_char['$'] = 'nwnwnwnnn'
        bar_char['/'] = 'nwnwnnnwn'
        bar_char['+'] = 'nwnnnwnwn'
        bar_char['%'] = 'nnnwnwnwn'

        self.set_fill_color(0)
        code = txt

        code = code.upper()
        for i in xrange (0, len(code), 2):
            char_bar = code[i];

            if not char_bar in bar_char.keys():
                raise RuntimeError ('Caracter "%s" inválido para el código de barras' % char_bar)

            seq= ''
            for s in xrange(0, len(bar_char[char_bar])):
                seq += bar_char[char_bar][s]

            for bar in xrange(0, len(seq)):
                if seq[bar] == 'n':
                    line_width = narrow
                else:
                    line_width = wide

                if bar % 2 == 0:
                    self.rect(x,y,line_width,h,'F')
                x += line_width
        x += gap

#End of class

# Fonts:

fpdf_charwidths['courier']={}

for i in xrange(0,256):
    fpdf_charwidths['courier'][chr(i)]=600
    fpdf_charwidths['courierB']=fpdf_charwidths['courier']
    fpdf_charwidths['courierI']=fpdf_charwidths['courier']
    fpdf_charwidths['courierBI']=fpdf_charwidths['courier']

fpdf_charwidths['helvetica']={
    '\x00':278,'\x01':278,'\x02':278,'\x03':278,'\x04':278,'\x05':278,'\x06':278,'\x07':278,'\x08':278,'\t':278,'\n':278,'\x0b':278,'\x0c':278,'\r':278,'\x0e':278,'\x0f':278,'\x10':278,'\x11':278,'\x12':278,'\x13':278,'\x14':278,'\x15':278,
    '\x16':278,'\x17':278,'\x18':278,'\x19':278,'\x1a':278,'\x1b':278,'\x1c':278,'\x1d':278,'\x1e':278,'\x1f':278,' ':278,'!':278,'"':355,'#':556,'$':556,'%':889,'&':667,'\'':191,'(':333,')':333,'*':389,'+':584,
    ',':278,'-':333,'.':278,'/':278,'0':556,'1':556,'2':556,'3':556,'4':556,'5':556,'6':556,'7':556,'8':556,'9':556,':':278,';':278,'<':584,'=':584,'>':584,'?':556,'@':1015,'A':667,
    'B':667,'C':722,'D':722,'E':667,'F':611,'G':778,'H':722,'I':278,'J':500,'K':667,'L':556,'M':833,'N':722,'O':778,'P':667,'Q':778,'R':722,'S':667,'T':611,'U':722,'V':667,'W':944,
    'X':667,'Y':667,'Z':611,'[':278,'\\':278,']':278,'^':469,'_':556,'`':333,'a':556,'b':556,'c':500,'d':556,'e':556,'f':278,'g':556,'h':556,'i':222,'j':222,'k':500,'l':222,'m':833,
    'n':556,'o':556,'p':556,'q':556,'r':333,'s':500,'t':278,'u':556,'v':500,'w':722,'x':500,'y':500,'z':500,'{':334,'|':260,'}':334,'~':584,'\x7f':350,'\x80':556,'\x81':350,'\x82':222,'\x83':556,
    '\x84':333,'\x85':1000,'\x86':556,'\x87':556,'\x88':333,'\x89':1000,'\x8a':667,'\x8b':333,'\x8c':1000,'\x8d':350,'\x8e':611,'\x8f':350,'\x90':350,'\x91':222,'\x92':222,'\x93':333,'\x94':333,'\x95':350,'\x96':556,'\x97':1000,'\x98':333,'\x99':1000,
    '\x9a':500,'\x9b':333,'\x9c':944,'\x9d':350,'\x9e':500,'\x9f':667,'\xa0':278,'\xa1':333,'\xa2':556,'\xa3':556,'\xa4':556,'\xa5':556,'\xa6':260,'\xa7':556,'\xa8':333,'\xa9':737,'\xaa':370,'\xab':556,'\xac':584,'\xad':333,'\xae':737,'\xaf':333,
    '\xb0':400,'\xb1':584,'\xb2':333,'\xb3':333,'\xb4':333,'\xb5':556,'\xb6':537,'\xb7':278,'\xb8':333,'\xb9':333,'\xba':365,'\xbb':556,'\xbc':834,'\xbd':834,'\xbe':834,'\xbf':611,'\xc0':667,'\xc1':667,'\xc2':667,'\xc3':667,'\xc4':667,'\xc5':667,
    '\xc6':1000,'\xc7':722,'\xc8':667,'\xc9':667,'\xca':667,'\xcb':667,'\xcc':278,'\xcd':278,'\xce':278,'\xcf':278,'\xd0':722,'\xd1':722,'\xd2':778,'\xd3':778,'\xd4':778,'\xd5':778,'\xd6':778,'\xd7':584,'\xd8':778,'\xd9':722,'\xda':722,'\xdb':722,
    '\xdc':722,'\xdd':667,'\xde':667,'\xdf':611,'\xe0':556,'\xe1':556,'\xe2':556,'\xe3':556,'\xe4':556,'\xe5':556,'\xe6':889,'\xe7':500,'\xe8':556,'\xe9':556,'\xea':556,'\xeb':556,'\xec':278,'\xed':278,'\xee':278,'\xef':278,'\xf0':556,'\xf1':556,
    '\xf2':556,'\xf3':556,'\xf4':556,'\xf5':556,'\xf6':556,'\xf7':584,'\xf8':611,'\xf9':556,'\xfa':556,'\xfb':556,'\xfc':556,'\xfd':500,'\xfe':556,'\xff':500}

fpdf_charwidths['helveticaB']={
    '\x00':278,'\x01':278,'\x02':278,'\x03':278,'\x04':278,'\x05':278,'\x06':278,'\x07':278,'\x08':278,'\t':278,'\n':278,'\x0b':278,'\x0c':278,'\r':278,'\x0e':278,'\x0f':278,'\x10':278,'\x11':278,'\x12':278,'\x13':278,'\x14':278,'\x15':278,
    '\x16':278,'\x17':278,'\x18':278,'\x19':278,'\x1a':278,'\x1b':278,'\x1c':278,'\x1d':278,'\x1e':278,'\x1f':278,' ':278,'!':333,'"':474,'#':556,'$':556,'%':889,'&':722,'\'':238,'(':333,')':333,'*':389,'+':584,
    ',':278,'-':333,'.':278,'/':278,'0':556,'1':556,'2':556,'3':556,'4':556,'5':556,'6':556,'7':556,'8':556,'9':556,':':333,';':333,'<':584,'=':584,'>':584,'?':611,'@':975,'A':722,
    'B':722,'C':722,'D':722,'E':667,'F':611,'G':778,'H':722,'I':278,'J':556,'K':722,'L':611,'M':833,'N':722,'O':778,'P':667,'Q':778,'R':722,'S':667,'T':611,'U':722,'V':667,'W':944,
    'X':667,'Y':667,'Z':611,'[':333,'\\':278,']':333,'^':584,'_':556,'`':333,'a':556,'b':611,'c':556,'d':611,'e':556,'f':333,'g':611,'h':611,'i':278,'j':278,'k':556,'l':278,'m':889,
    'n':611,'o':611,'p':611,'q':611,'r':389,'s':556,'t':333,'u':611,'v':556,'w':778,'x':556,'y':556,'z':500,'{':389,'|':280,'}':389,'~':584,'\x7f':350,'\x80':556,'\x81':350,'\x82':278,'\x83':556,
    '\x84':500,'\x85':1000,'\x86':556,'\x87':556,'\x88':333,'\x89':1000,'\x8a':667,'\x8b':333,'\x8c':1000,'\x8d':350,'\x8e':611,'\x8f':350,'\x90':350,'\x91':278,'\x92':278,'\x93':500,'\x94':500,'\x95':350,'\x96':556,'\x97':1000,'\x98':333,'\x99':1000,
    '\x9a':556,'\x9b':333,'\x9c':944,'\x9d':350,'\x9e':500,'\x9f':667,'\xa0':278,'\xa1':333,'\xa2':556,'\xa3':556,'\xa4':556,'\xa5':556,'\xa6':280,'\xa7':556,'\xa8':333,'\xa9':737,'\xaa':370,'\xab':556,'\xac':584,'\xad':333,'\xae':737,'\xaf':333,
    '\xb0':400,'\xb1':584,'\xb2':333,'\xb3':333,'\xb4':333,'\xb5':611,'\xb6':556,'\xb7':278,'\xb8':333,'\xb9':333,'\xba':365,'\xbb':556,'\xbc':834,'\xbd':834,'\xbe':834,'\xbf':611,'\xc0':722,'\xc1':722,'\xc2':722,'\xc3':722,'\xc4':722,'\xc5':722,
    '\xc6':1000,'\xc7':722,'\xc8':667,'\xc9':667,'\xca':667,'\xcb':667,'\xcc':278,'\xcd':278,'\xce':278,'\xcf':278,'\xd0':722,'\xd1':722,'\xd2':778,'\xd3':778,'\xd4':778,'\xd5':778,'\xd6':778,'\xd7':584,'\xd8':778,'\xd9':722,'\xda':722,'\xdb':722,
    '\xdc':722,'\xdd':667,'\xde':667,'\xdf':611,'\xe0':556,'\xe1':556,'\xe2':556,'\xe3':556,'\xe4':556,'\xe5':556,'\xe6':889,'\xe7':556,'\xe8':556,'\xe9':556,'\xea':556,'\xeb':556,'\xec':278,'\xed':278,'\xee':278,'\xef':278,'\xf0':611,'\xf1':611,
    '\xf2':611,'\xf3':611,'\xf4':611,'\xf5':611,'\xf6':611,'\xf7':584,'\xf8':611,'\xf9':611,'\xfa':611,'\xfb':611,'\xfc':611,'\xfd':556,'\xfe':611,'\xff':556
}

fpdf_charwidths['helveticaBI']={
    '\x00':278,'\x01':278,'\x02':278,'\x03':278,'\x04':278,'\x05':278,'\x06':278,'\x07':278,'\x08':278,'\t':278,'\n':278,'\x0b':278,'\x0c':278,'\r':278,'\x0e':278,'\x0f':278,'\x10':278,'\x11':278,'\x12':278,'\x13':278,'\x14':278,'\x15':278,
    '\x16':278,'\x17':278,'\x18':278,'\x19':278,'\x1a':278,'\x1b':278,'\x1c':278,'\x1d':278,'\x1e':278,'\x1f':278,' ':278,'!':333,'"':474,'#':556,'$':556,'%':889,'&':722,'\'':238,'(':333,')':333,'*':389,'+':584,
    ',':278,'-':333,'.':278,'/':278,'0':556,'1':556,'2':556,'3':556,'4':556,'5':556,'6':556,'7':556,'8':556,'9':556,':':333,';':333,'<':584,'=':584,'>':584,'?':611,'@':975,'A':722,
    'B':722,'C':722,'D':722,'E':667,'F':611,'G':778,'H':722,'I':278,'J':556,'K':722,'L':611,'M':833,'N':722,'O':778,'P':667,'Q':778,'R':722,'S':667,'T':611,'U':722,'V':667,'W':944,
    'X':667,'Y':667,'Z':611,'[':333,'\\':278,']':333,'^':584,'_':556,'`':333,'a':556,'b':611,'c':556,'d':611,'e':556,'f':333,'g':611,'h':611,'i':278,'j':278,'k':556,'l':278,'m':889,
    'n':611,'o':611,'p':611,'q':611,'r':389,'s':556,'t':333,'u':611,'v':556,'w':778,'x':556,'y':556,'z':500,'{':389,'|':280,'}':389,'~':584,'\x7f':350,'\x80':556,'\x81':350,'\x82':278,'\x83':556,
    '\x84':500,'\x85':1000,'\x86':556,'\x87':556,'\x88':333,'\x89':1000,'\x8a':667,'\x8b':333,'\x8c':1000,'\x8d':350,'\x8e':611,'\x8f':350,'\x90':350,'\x91':278,'\x92':278,'\x93':500,'\x94':500,'\x95':350,'\x96':556,'\x97':1000,'\x98':333,'\x99':1000,
    '\x9a':556,'\x9b':333,'\x9c':944,'\x9d':350,'\x9e':500,'\x9f':667,'\xa0':278,'\xa1':333,'\xa2':556,'\xa3':556,'\xa4':556,'\xa5':556,'\xa6':280,'\xa7':556,'\xa8':333,'\xa9':737,'\xaa':370,'\xab':556,'\xac':584,'\xad':333,'\xae':737,'\xaf':333,
    '\xb0':400,'\xb1':584,'\xb2':333,'\xb3':333,'\xb4':333,'\xb5':611,'\xb6':556,'\xb7':278,'\xb8':333,'\xb9':333,'\xba':365,'\xbb':556,'\xbc':834,'\xbd':834,'\xbe':834,'\xbf':611,'\xc0':722,'\xc1':722,'\xc2':722,'\xc3':722,'\xc4':722,'\xc5':722,
    '\xc6':1000,'\xc7':722,'\xc8':667,'\xc9':667,'\xca':667,'\xcb':667,'\xcc':278,'\xcd':278,'\xce':278,'\xcf':278,'\xd0':722,'\xd1':722,'\xd2':778,'\xd3':778,'\xd4':778,'\xd5':778,'\xd6':778,'\xd7':584,'\xd8':778,'\xd9':722,'\xda':722,'\xdb':722,
    '\xdc':722,'\xdd':667,'\xde':667,'\xdf':611,'\xe0':556,'\xe1':556,'\xe2':556,'\xe3':556,'\xe4':556,'\xe5':556,'\xe6':889,'\xe7':556,'\xe8':556,'\xe9':556,'\xea':556,'\xeb':556,'\xec':278,'\xed':278,'\xee':278,'\xef':278,'\xf0':611,'\xf1':611,
    '\xf2':611,'\xf3':611,'\xf4':611,'\xf5':611,'\xf6':611,'\xf7':584,'\xf8':611,'\xf9':611,'\xfa':611,'\xfb':611,'\xfc':611,'\xfd':556,'\xfe':611,'\xff':556}

fpdf_charwidths['helveticaI']={
    '\x00':278,'\x01':278,'\x02':278,'\x03':278,'\x04':278,'\x05':278,'\x06':278,'\x07':278,'\x08':278,'\t':278,'\n':278,'\x0b':278,'\x0c':278,'\r':278,'\x0e':278,'\x0f':278,'\x10':278,'\x11':278,'\x12':278,'\x13':278,'\x14':278,'\x15':278,
    '\x16':278,'\x17':278,'\x18':278,'\x19':278,'\x1a':278,'\x1b':278,'\x1c':278,'\x1d':278,'\x1e':278,'\x1f':278,' ':278,'!':278,'"':355,'#':556,'$':556,'%':889,'&':667,'\'':191,'(':333,')':333,'*':389,'+':584,
    ',':278,'-':333,'.':278,'/':278,'0':556,'1':556,'2':556,'3':556,'4':556,'5':556,'6':556,'7':556,'8':556,'9':556,':':278,';':278,'<':584,'=':584,'>':584,'?':556,'@':1015,'A':667,
    'B':667,'C':722,'D':722,'E':667,'F':611,'G':778,'H':722,'I':278,'J':500,'K':667,'L':556,'M':833,'N':722,'O':778,'P':667,'Q':778,'R':722,'S':667,'T':611,'U':722,'V':667,'W':944,
    'X':667,'Y':667,'Z':611,'[':278,'\\':278,']':278,'^':469,'_':556,'`':333,'a':556,'b':556,'c':500,'d':556,'e':556,'f':278,'g':556,'h':556,'i':222,'j':222,'k':500,'l':222,'m':833,
    'n':556,'o':556,'p':556,'q':556,'r':333,'s':500,'t':278,'u':556,'v':500,'w':722,'x':500,'y':500,'z':500,'{':334,'|':260,'}':334,'~':584,'\x7f':350,'\x80':556,'\x81':350,'\x82':222,'\x83':556,
    '\x84':333,'\x85':1000,'\x86':556,'\x87':556,'\x88':333,'\x89':1000,'\x8a':667,'\x8b':333,'\x8c':1000,'\x8d':350,'\x8e':611,'\x8f':350,'\x90':350,'\x91':222,'\x92':222,'\x93':333,'\x94':333,'\x95':350,'\x96':556,'\x97':1000,'\x98':333,'\x99':1000,
    '\x9a':500,'\x9b':333,'\x9c':944,'\x9d':350,'\x9e':500,'\x9f':667,'\xa0':278,'\xa1':333,'\xa2':556,'\xa3':556,'\xa4':556,'\xa5':556,'\xa6':260,'\xa7':556,'\xa8':333,'\xa9':737,'\xaa':370,'\xab':556,'\xac':584,'\xad':333,'\xae':737,'\xaf':333,
    '\xb0':400,'\xb1':584,'\xb2':333,'\xb3':333,'\xb4':333,'\xb5':556,'\xb6':537,'\xb7':278,'\xb8':333,'\xb9':333,'\xba':365,'\xbb':556,'\xbc':834,'\xbd':834,'\xbe':834,'\xbf':611,'\xc0':667,'\xc1':667,'\xc2':667,'\xc3':667,'\xc4':667,'\xc5':667,
    '\xc6':1000,'\xc7':722,'\xc8':667,'\xc9':667,'\xca':667,'\xcb':667,'\xcc':278,'\xcd':278,'\xce':278,'\xcf':278,'\xd0':722,'\xd1':722,'\xd2':778,'\xd3':778,'\xd4':778,'\xd5':778,'\xd6':778,'\xd7':584,'\xd8':778,'\xd9':722,'\xda':722,'\xdb':722,
    '\xdc':722,'\xdd':667,'\xde':667,'\xdf':611,'\xe0':556,'\xe1':556,'\xe2':556,'\xe3':556,'\xe4':556,'\xe5':556,'\xe6':889,'\xe7':500,'\xe8':556,'\xe9':556,'\xea':556,'\xeb':556,'\xec':278,'\xed':278,'\xee':278,'\xef':278,'\xf0':556,'\xf1':556,
    '\xf2':556,'\xf3':556,'\xf4':556,'\xf5':556,'\xf6':556,'\xf7':584,'\xf8':611,'\xf9':556,'\xfa':556,'\xfb':556,'\xfc':556,'\xfd':500,'\xfe':556,'\xff':500}

fpdf_charwidths['symbol']={
    '\x00':250,'\x01':250,'\x02':250,'\x03':250,'\x04':250,'\x05':250,'\x06':250,'\x07':250,'\x08':250,'\t':250,'\n':250,'\x0b':250,'\x0c':250,'\r':250,'\x0e':250,'\x0f':250,'\x10':250,'\x11':250,'\x12':250,'\x13':250,'\x14':250,'\x15':250,
    '\x16':250,'\x17':250,'\x18':250,'\x19':250,'\x1a':250,'\x1b':250,'\x1c':250,'\x1d':250,'\x1e':250,'\x1f':250,' ':250,'!':333,'"':713,'#':500,'$':549,'%':833,'&':778,'\'':439,'(':333,')':333,'*':500,'+':549,
    ',':250,'-':549,'.':250,'/':278,'0':500,'1':500,'2':500,'3':500,'4':500,'5':500,'6':500,'7':500,'8':500,'9':500,':':278,';':278,'<':549,'=':549,'>':549,'?':444,'@':549,'A':722,
    'B':667,'C':722,'D':612,'E':611,'F':763,'G':603,'H':722,'I':333,'J':631,'K':722,'L':686,'M':889,'N':722,'O':722,'P':768,'Q':741,'R':556,'S':592,'T':611,'U':690,'V':439,'W':768,
    'X':645,'Y':795,'Z':611,'[':333,'\\':863,']':333,'^':658,'_':500,'`':500,'a':631,'b':549,'c':549,'d':494,'e':439,'f':521,'g':411,'h':603,'i':329,'j':603,'k':549,'l':549,'m':576,
    'n':521,'o':549,'p':549,'q':521,'r':549,'s':603,'t':439,'u':576,'v':713,'w':686,'x':493,'y':686,'z':494,'{':480,'|':200,'}':480,'~':549,'\x7f':0,'\x80':0,'\x81':0,'\x82':0,'\x83':0,
    '\x84':0,'\x85':0,'\x86':0,'\x87':0,'\x88':0,'\x89':0,'\x8a':0,'\x8b':0,'\x8c':0,'\x8d':0,'\x8e':0,'\x8f':0,'\x90':0,'\x91':0,'\x92':0,'\x93':0,'\x94':0,'\x95':0,'\x96':0,'\x97':0,'\x98':0,'\x99':0,
    '\x9a':0,'\x9b':0,'\x9c':0,'\x9d':0,'\x9e':0,'\x9f':0,'\xa0':750,'\xa1':620,'\xa2':247,'\xa3':549,'\xa4':167,'\xa5':713,'\xa6':500,'\xa7':753,'\xa8':753,'\xa9':753,'\xaa':753,'\xab':1042,'\xac':987,'\xad':603,'\xae':987,'\xaf':603,
    '\xb0':400,'\xb1':549,'\xb2':411,'\xb3':549,'\xb4':549,'\xb5':713,'\xb6':494,'\xb7':460,'\xb8':549,'\xb9':549,'\xba':549,'\xbb':549,'\xbc':1000,'\xbd':603,'\xbe':1000,'\xbf':658,'\xc0':823,'\xc1':686,'\xc2':795,'\xc3':987,'\xc4':768,'\xc5':768,
    '\xc6':823,'\xc7':768,'\xc8':768,'\xc9':713,'\xca':713,'\xcb':713,'\xcc':713,'\xcd':713,'\xce':713,'\xcf':713,'\xd0':768,'\xd1':713,'\xd2':790,'\xd3':790,'\xd4':890,'\xd5':823,'\xd6':549,'\xd7':250,'\xd8':713,'\xd9':603,'\xda':603,'\xdb':1042,
    '\xdc':987,'\xdd':603,'\xde':987,'\xdf':603,'\xe0':494,'\xe1':329,'\xe2':790,'\xe3':790,'\xe4':786,'\xe5':713,'\xe6':384,'\xe7':384,'\xe8':384,'\xe9':384,'\xea':384,'\xeb':384,'\xec':494,'\xed':494,'\xee':494,'\xef':494,'\xf0':0,'\xf1':329,
    '\xf2':274,'\xf3':686,'\xf4':686,'\xf5':686,'\xf6':384,'\xf7':384,'\xf8':384,'\xf9':384,'\xfa':384,'\xfb':384,'\xfc':494,'\xfd':494,'\xfe':494,'\xff':0}

fpdf_charwidths['times']={
    '\x00':250,'\x01':250,'\x02':250,'\x03':250,'\x04':250,'\x05':250,'\x06':250,'\x07':250,'\x08':250,'\t':250,'\n':250,'\x0b':250,'\x0c':250,'\r':250,'\x0e':250,'\x0f':250,'\x10':250,'\x11':250,'\x12':250,'\x13':250,'\x14':250,'\x15':250,
    '\x16':250,'\x17':250,'\x18':250,'\x19':250,'\x1a':250,'\x1b':250,'\x1c':250,'\x1d':250,'\x1e':250,'\x1f':250,' ':250,'!':333,'"':408,'#':500,'$':500,'%':833,'&':778,'\'':180,'(':333,')':333,'*':500,'+':564,
    ',':250,'-':333,'.':250,'/':278,'0':500,'1':500,'2':500,'3':500,'4':500,'5':500,'6':500,'7':500,'8':500,'9':500,':':278,';':278,'<':564,'=':564,'>':564,'?':444,'@':921,'A':722,
    'B':667,'C':667,'D':722,'E':611,'F':556,'G':722,'H':722,'I':333,'J':389,'K':722,'L':611,'M':889,'N':722,'O':722,'P':556,'Q':722,'R':667,'S':556,'T':611,'U':722,'V':722,'W':944,
    'X':722,'Y':722,'Z':611,'[':333,'\\':278,']':333,'^':469,'_':500,'`':333,'a':444,'b':500,'c':444,'d':500,'e':444,'f':333,'g':500,'h':500,'i':278,'j':278,'k':500,'l':278,'m':778,
    'n':500,'o':500,'p':500,'q':500,'r':333,'s':389,'t':278,'u':500,'v':500,'w':722,'x':500,'y':500,'z':444,'{':480,'|':200,'}':480,'~':541,'\x7f':350,'\x80':500,'\x81':350,'\x82':333,'\x83':500,
    '\x84':444,'\x85':1000,'\x86':500,'\x87':500,'\x88':333,'\x89':1000,'\x8a':556,'\x8b':333,'\x8c':889,'\x8d':350,'\x8e':611,'\x8f':350,'\x90':350,'\x91':333,'\x92':333,'\x93':444,'\x94':444,'\x95':350,'\x96':500,'\x97':1000,'\x98':333,'\x99':980,
    '\x9a':389,'\x9b':333,'\x9c':722,'\x9d':350,'\x9e':444,'\x9f':722,'\xa0':250,'\xa1':333,'\xa2':500,'\xa3':500,'\xa4':500,'\xa5':500,'\xa6':200,'\xa7':500,'\xa8':333,'\xa9':760,'\xaa':276,'\xab':500,'\xac':564,'\xad':333,'\xae':760,'\xaf':333,
    '\xb0':400,'\xb1':564,'\xb2':300,'\xb3':300,'\xb4':333,'\xb5':500,'\xb6':453,'\xb7':250,'\xb8':333,'\xb9':300,'\xba':310,'\xbb':500,'\xbc':750,'\xbd':750,'\xbe':750,'\xbf':444,'\xc0':722,'\xc1':722,'\xc2':722,'\xc3':722,'\xc4':722,'\xc5':722,
    '\xc6':889,'\xc7':667,'\xc8':611,'\xc9':611,'\xca':611,'\xcb':611,'\xcc':333,'\xcd':333,'\xce':333,'\xcf':333,'\xd0':722,'\xd1':722,'\xd2':722,'\xd3':722,'\xd4':722,'\xd5':722,'\xd6':722,'\xd7':564,'\xd8':722,'\xd9':722,'\xda':722,'\xdb':722,
    '\xdc':722,'\xdd':722,'\xde':556,'\xdf':500,'\xe0':444,'\xe1':444,'\xe2':444,'\xe3':444,'\xe4':444,'\xe5':444,'\xe6':667,'\xe7':444,'\xe8':444,'\xe9':444,'\xea':444,'\xeb':444,'\xec':278,'\xed':278,'\xee':278,'\xef':278,'\xf0':500,'\xf1':500,
    '\xf2':500,'\xf3':500,'\xf4':500,'\xf5':500,'\xf6':500,'\xf7':564,'\xf8':500,'\xf9':500,'\xfa':500,'\xfb':500,'\xfc':500,'\xfd':500,'\xfe':500,'\xff':500}

fpdf_charwidths['timesB']={
    '\x00':250,'\x01':250,'\x02':250,'\x03':250,'\x04':250,'\x05':250,'\x06':250,'\x07':250,'\x08':250,'\t':250,'\n':250,'\x0b':250,'\x0c':250,'\r':250,'\x0e':250,'\x0f':250,'\x10':250,'\x11':250,'\x12':250,'\x13':250,'\x14':250,'\x15':250,
    '\x16':250,'\x17':250,'\x18':250,'\x19':250,'\x1a':250,'\x1b':250,'\x1c':250,'\x1d':250,'\x1e':250,'\x1f':250,' ':250,'!':333,'"':555,'#':500,'$':500,'%':1000,'&':833,'\'':278,'(':333,')':333,'*':500,'+':570,
    ',':250,'-':333,'.':250,'/':278,'0':500,'1':500,'2':500,'3':500,'4':500,'5':500,'6':500,'7':500,'8':500,'9':500,':':333,';':333,'<':570,'=':570,'>':570,'?':500,'@':930,'A':722,
    'B':667,'C':722,'D':722,'E':667,'F':611,'G':778,'H':778,'I':389,'J':500,'K':778,'L':667,'M':944,'N':722,'O':778,'P':611,'Q':778,'R':722,'S':556,'T':667,'U':722,'V':722,'W':1000,
    'X':722,'Y':722,'Z':667,'[':333,'\\':278,']':333,'^':581,'_':500,'`':333,'a':500,'b':556,'c':444,'d':556,'e':444,'f':333,'g':500,'h':556,'i':278,'j':333,'k':556,'l':278,'m':833,
    'n':556,'o':500,'p':556,'q':556,'r':444,'s':389,'t':333,'u':556,'v':500,'w':722,'x':500,'y':500,'z':444,'{':394,'|':220,'}':394,'~':520,'\x7f':350,'\x80':500,'\x81':350,'\x82':333,'\x83':500,
    '\x84':500,'\x85':1000,'\x86':500,'\x87':500,'\x88':333,'\x89':1000,'\x8a':556,'\x8b':333,'\x8c':1000,'\x8d':350,'\x8e':667,'\x8f':350,'\x90':350,'\x91':333,'\x92':333,'\x93':500,'\x94':500,'\x95':350,'\x96':500,'\x97':1000,'\x98':333,'\x99':1000,
    '\x9a':389,'\x9b':333,'\x9c':722,'\x9d':350,'\x9e':444,'\x9f':722,'\xa0':250,'\xa1':333,'\xa2':500,'\xa3':500,'\xa4':500,'\xa5':500,'\xa6':220,'\xa7':500,'\xa8':333,'\xa9':747,'\xaa':300,'\xab':500,'\xac':570,'\xad':333,'\xae':747,'\xaf':333,
    '\xb0':400,'\xb1':570,'\xb2':300,'\xb3':300,'\xb4':333,'\xb5':556,'\xb6':540,'\xb7':250,'\xb8':333,'\xb9':300,'\xba':330,'\xbb':500,'\xbc':750,'\xbd':750,'\xbe':750,'\xbf':500,'\xc0':722,'\xc1':722,'\xc2':722,'\xc3':722,'\xc4':722,'\xc5':722,
    '\xc6':1000,'\xc7':722,'\xc8':667,'\xc9':667,'\xca':667,'\xcb':667,'\xcc':389,'\xcd':389,'\xce':389,'\xcf':389,'\xd0':722,'\xd1':722,'\xd2':778,'\xd3':778,'\xd4':778,'\xd5':778,'\xd6':778,'\xd7':570,'\xd8':778,'\xd9':722,'\xda':722,'\xdb':722,
    '\xdc':722,'\xdd':722,'\xde':611,'\xdf':556,'\xe0':500,'\xe1':500,'\xe2':500,'\xe3':500,'\xe4':500,'\xe5':500,'\xe6':722,'\xe7':444,'\xe8':444,'\xe9':444,'\xea':444,'\xeb':444,'\xec':278,'\xed':278,'\xee':278,'\xef':278,'\xf0':500,'\xf1':556,
    '\xf2':500,'\xf3':500,'\xf4':500,'\xf5':500,'\xf6':500,'\xf7':570,'\xf8':500,'\xf9':556,'\xfa':556,'\xfb':556,'\xfc':556,'\xfd':500,'\xfe':556,'\xff':500}

fpdf_charwidths['timesBI']={
    '\x00':250,'\x01':250,'\x02':250,'\x03':250,'\x04':250,'\x05':250,'\x06':250,'\x07':250,'\x08':250,'\t':250,'\n':250,'\x0b':250,'\x0c':250,'\r':250,'\x0e':250,'\x0f':250,'\x10':250,'\x11':250,'\x12':250,'\x13':250,'\x14':250,'\x15':250,
    '\x16':250,'\x17':250,'\x18':250,'\x19':250,'\x1a':250,'\x1b':250,'\x1c':250,'\x1d':250,'\x1e':250,'\x1f':250,' ':250,'!':389,'"':555,'#':500,'$':500,'%':833,'&':778,'\'':278,'(':333,')':333,'*':500,'+':570,
    ',':250,'-':333,'.':250,'/':278,'0':500,'1':500,'2':500,'3':500,'4':500,'5':500,'6':500,'7':500,'8':500,'9':500,':':333,';':333,'<':570,'=':570,'>':570,'?':500,'@':832,'A':667,
    'B':667,'C':667,'D':722,'E':667,'F':667,'G':722,'H':778,'I':389,'J':500,'K':667,'L':611,'M':889,'N':722,'O':722,'P':611,'Q':722,'R':667,'S':556,'T':611,'U':722,'V':667,'W':889,
    'X':667,'Y':611,'Z':611,'[':333,'\\':278,']':333,'^':570,'_':500,'`':333,'a':500,'b':500,'c':444,'d':500,'e':444,'f':333,'g':500,'h':556,'i':278,'j':278,'k':500,'l':278,'m':778,
    'n':556,'o':500,'p':500,'q':500,'r':389,'s':389,'t':278,'u':556,'v':444,'w':667,'x':500,'y':444,'z':389,'{':348,'|':220,'}':348,'~':570,'\x7f':350,'\x80':500,'\x81':350,'\x82':333,'\x83':500,
    '\x84':500,'\x85':1000,'\x86':500,'\x87':500,'\x88':333,'\x89':1000,'\x8a':556,'\x8b':333,'\x8c':944,'\x8d':350,'\x8e':611,'\x8f':350,'\x90':350,'\x91':333,'\x92':333,'\x93':500,'\x94':500,'\x95':350,'\x96':500,'\x97':1000,'\x98':333,'\x99':1000,
    '\x9a':389,'\x9b':333,'\x9c':722,'\x9d':350,'\x9e':389,'\x9f':611,'\xa0':250,'\xa1':389,'\xa2':500,'\xa3':500,'\xa4':500,'\xa5':500,'\xa6':220,'\xa7':500,'\xa8':333,'\xa9':747,'\xaa':266,'\xab':500,'\xac':606,'\xad':333,'\xae':747,'\xaf':333,
    '\xb0':400,'\xb1':570,'\xb2':300,'\xb3':300,'\xb4':333,'\xb5':576,'\xb6':500,'\xb7':250,'\xb8':333,'\xb9':300,'\xba':300,'\xbb':500,'\xbc':750,'\xbd':750,'\xbe':750,'\xbf':500,'\xc0':667,'\xc1':667,'\xc2':667,'\xc3':667,'\xc4':667,'\xc5':667,
    '\xc6':944,'\xc7':667,'\xc8':667,'\xc9':667,'\xca':667,'\xcb':667,'\xcc':389,'\xcd':389,'\xce':389,'\xcf':389,'\xd0':722,'\xd1':722,'\xd2':722,'\xd3':722,'\xd4':722,'\xd5':722,'\xd6':722,'\xd7':570,'\xd8':722,'\xd9':722,'\xda':722,'\xdb':722,
    '\xdc':722,'\xdd':611,'\xde':611,'\xdf':500,'\xe0':500,'\xe1':500,'\xe2':500,'\xe3':500,'\xe4':500,'\xe5':500,'\xe6':722,'\xe7':444,'\xe8':444,'\xe9':444,'\xea':444,'\xeb':444,'\xec':278,'\xed':278,'\xee':278,'\xef':278,'\xf0':500,'\xf1':556,
    '\xf2':500,'\xf3':500,'\xf4':500,'\xf5':500,'\xf6':500,'\xf7':570,'\xf8':500,'\xf9':556,'\xfa':556,'\xfb':556,'\xfc':556,'\xfd':444,'\xfe':500,'\xff':444}

fpdf_charwidths['timesI']={
    '\x00':250,'\x01':250,'\x02':250,'\x03':250,'\x04':250,'\x05':250,'\x06':250,'\x07':250,'\x08':250,'\t':250,'\n':250,'\x0b':250,'\x0c':250,'\r':250,'\x0e':250,'\x0f':250,'\x10':250,'\x11':250,'\x12':250,'\x13':250,'\x14':250,'\x15':250,
    '\x16':250,'\x17':250,'\x18':250,'\x19':250,'\x1a':250,'\x1b':250,'\x1c':250,'\x1d':250,'\x1e':250,'\x1f':250,' ':250,'!':333,'"':420,'#':500,'$':500,'%':833,'&':778,'\'':214,'(':333,')':333,'*':500,'+':675,
    ',':250,'-':333,'.':250,'/':278,'0':500,'1':500,'2':500,'3':500,'4':500,'5':500,'6':500,'7':500,'8':500,'9':500,':':333,';':333,'<':675,'=':675,'>':675,'?':500,'@':920,'A':611,
    'B':611,'C':667,'D':722,'E':611,'F':611,'G':722,'H':722,'I':333,'J':444,'K':667,'L':556,'M':833,'N':667,'O':722,'P':611,'Q':722,'R':611,'S':500,'T':556,'U':722,'V':611,'W':833,
    'X':611,'Y':556,'Z':556,'[':389,'\\':278,']':389,'^':422,'_':500,'`':333,'a':500,'b':500,'c':444,'d':500,'e':444,'f':278,'g':500,'h':500,'i':278,'j':278,'k':444,'l':278,'m':722,
    'n':500,'o':500,'p':500,'q':500,'r':389,'s':389,'t':278,'u':500,'v':444,'w':667,'x':444,'y':444,'z':389,'{':400,'|':275,'}':400,'~':541,'\x7f':350,'\x80':500,'\x81':350,'\x82':333,'\x83':500,
    '\x84':556,'\x85':889,'\x86':500,'\x87':500,'\x88':333,'\x89':1000,'\x8a':500,'\x8b':333,'\x8c':944,'\x8d':350,'\x8e':556,'\x8f':350,'\x90':350,'\x91':333,'\x92':333,'\x93':556,'\x94':556,'\x95':350,'\x96':500,'\x97':889,'\x98':333,'\x99':980,
    '\x9a':389,'\x9b':333,'\x9c':667,'\x9d':350,'\x9e':389,'\x9f':556,'\xa0':250,'\xa1':389,'\xa2':500,'\xa3':500,'\xa4':500,'\xa5':500,'\xa6':275,'\xa7':500,'\xa8':333,'\xa9':760,'\xaa':276,'\xab':500,'\xac':675,'\xad':333,'\xae':760,'\xaf':333,
    '\xb0':400,'\xb1':675,'\xb2':300,'\xb3':300,'\xb4':333,'\xb5':500,'\xb6':523,'\xb7':250,'\xb8':333,'\xb9':300,'\xba':310,'\xbb':500,'\xbc':750,'\xbd':750,'\xbe':750,'\xbf':500,'\xc0':611,'\xc1':611,'\xc2':611,'\xc3':611,'\xc4':611,'\xc5':611,
    '\xc6':889,'\xc7':667,'\xc8':611,'\xc9':611,'\xca':611,'\xcb':611,'\xcc':333,'\xcd':333,'\xce':333,'\xcf':333,'\xd0':722,'\xd1':667,'\xd2':722,'\xd3':722,'\xd4':722,'\xd5':722,'\xd6':722,'\xd7':675,'\xd8':722,'\xd9':722,'\xda':722,'\xdb':722,
    '\xdc':722,'\xdd':556,'\xde':611,'\xdf':500,'\xe0':500,'\xe1':500,'\xe2':500,'\xe3':500,'\xe4':500,'\xe5':500,'\xe6':667,'\xe7':444,'\xe8':444,'\xe9':444,'\xea':444,'\xeb':444,'\xec':278,'\xed':278,'\xee':278,'\xef':278,'\xf0':500,'\xf1':500,
    '\xf2':500,'\xf3':500,'\xf4':500,'\xf5':500,'\xf6':500,'\xf7':675,'\xf8':500,'\xf9':500,'\xfa':500,'\xfb':500,'\xfc':500,'\xfd':444,'\xfe':500,'\xff':444}

fpdf_charwidths['zapfdingbats']={
    '\x00':0,'\x01':0,'\x02':0,'\x03':0,'\x04':0,'\x05':0,'\x06':0,'\x07':0,'\x08':0,'\t':0,'\n':0,'\x0b':0,'\x0c':0,'\r':0,'\x0e':0,'\x0f':0,'\x10':0,'\x11':0,'\x12':0,'\x13':0,'\x14':0,'\x15':0,
    '\x16':0,'\x17':0,'\x18':0,'\x19':0,'\x1a':0,'\x1b':0,'\x1c':0,'\x1d':0,'\x1e':0,'\x1f':0,' ':278,'!':974,'"':961,'#':974,'$':980,'%':719,'&':789,'\'':790,'(':791,')':690,'*':960,'+':939,
    ',':549,'-':855,'.':911,'/':933,'0':911,'1':945,'2':974,'3':755,'4':846,'5':762,'6':761,'7':571,'8':677,'9':763,':':760,';':759,'<':754,'=':494,'>':552,'?':537,'@':577,'A':692,
    'B':786,'C':788,'D':788,'E':790,'F':793,'G':794,'H':816,'I':823,'J':789,'K':841,'L':823,'M':833,'N':816,'O':831,'P':923,'Q':744,'R':723,'S':749,'T':790,'U':792,'V':695,'W':776,
    'X':768,'Y':792,'Z':759,'[':707,'\\':708,']':682,'^':701,'_':826,'`':815,'a':789,'b':789,'c':707,'d':687,'e':696,'f':689,'g':786,'h':787,'i':713,'j':791,'k':785,'l':791,'m':873,
    'n':761,'o':762,'p':762,'q':759,'r':759,'s':892,'t':892,'u':788,'v':784,'w':438,'x':138,'y':277,'z':415,'{':392,'|':392,'}':668,'~':668,'\x7f':0,'\x80':390,'\x81':390,'\x82':317,'\x83':317,
    '\x84':276,'\x85':276,'\x86':509,'\x87':509,'\x88':410,'\x89':410,'\x8a':234,'\x8b':234,'\x8c':334,'\x8d':334,'\x8e':0,'\x8f':0,'\x90':0,'\x91':0,'\x92':0,'\x93':0,'\x94':0,'\x95':0,'\x96':0,'\x97':0,'\x98':0,'\x99':0,
    '\x9a':0,'\x9b':0,'\x9c':0,'\x9d':0,'\x9e':0,'\x9f':0,'\xa0':0,'\xa1':732,'\xa2':544,'\xa3':544,'\xa4':910,'\xa5':667,'\xa6':760,'\xa7':760,'\xa8':776,'\xa9':595,'\xaa':694,'\xab':626,'\xac':788,'\xad':788,'\xae':788,'\xaf':788,
    '\xb0':788,'\xb1':788,'\xb2':788,'\xb3':788,'\xb4':788,'\xb5':788,'\xb6':788,'\xb7':788,'\xb8':788,'\xb9':788,'\xba':788,'\xbb':788,'\xbc':788,'\xbd':788,'\xbe':788,'\xbf':788,'\xc0':788,'\xc1':788,'\xc2':788,'\xc3':788,'\xc4':788,'\xc5':788,
    '\xc6':788,'\xc7':788,'\xc8':788,'\xc9':788,'\xca':788,'\xcb':788,'\xcc':788,'\xcd':788,'\xce':788,'\xcf':788,'\xd0':788,'\xd1':788,'\xd2':788,'\xd3':788,'\xd4':894,'\xd5':838,'\xd6':1016,'\xd7':458,'\xd8':748,'\xd9':924,'\xda':748,'\xdb':918,
    '\xdc':927,'\xdd':928,'\xde':928,'\xdf':834,'\xe0':873,'\xe1':828,'\xe2':924,'\xe3':924,'\xe4':917,'\xe5':930,'\xe6':931,'\xe7':463,'\xe8':883,'\xe9':836,'\xea':836,'\xeb':867,'\xec':867,'\xed':696,'\xee':696,'\xef':874,'\xf0':0,'\xf1':874,
    '\xf2':760,'\xf3':946,'\xf4':771,'\xf5':865,'\xf6':771,'\xf7':888,'\xf8':967,'\xf9':888,'\xfa':831,'\xfb':873,'\xfc':927,'\xfd':970,'\xfe':918,'\xff':0}



