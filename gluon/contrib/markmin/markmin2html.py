#!/usr/bin/env python 
# created my Massimo Di Pierro
# license MIT/BSD/GPL
import re
import cgi

"""
TODO: next version should use MathJax

<script type="text/javascript" src="http://cdn.mathjax.org/mathjax/latest/MathJax.js">
MathJax.Hub.Config({
 extensions: ["tex2jax.js","TeX/AMSmath.js","TeX/AMSsymbols.js"],
 jax: ["input/TeX", "output/HTML-CSS"],
 tex2jax: {
     inlineMath: [ ['$','$'], ["\\(","\\)"] ],
     displayMath: [ ['$$','$$'], ["\\[","\\]"] ],
 },
 "HTML-CSS": { availableFonts: ["TeX"] }
});
</script>
"""

__all__ = ['render', 'markmin2html']

__doc__ = """
# Markmin markup language

## About

This is a new markup language that we call markmin designed to produce high quality scientific papers and books and also put them online. We provide serializers for html, latex and pdf. It is implemented in the ``markmin2html`` function in the ``markmin2html.py``.

Example of usage:

``
m = "Hello **world** [[link http://web2py.com]]"
from markmin2html import markmin2html
print markmin2html(m)
from markmin2latex import markmin2latex
print markmin2latex(m)
from markmin2pdf import markmin2pdf # requires pdflatex
print markmin2pdf(m)
``

## Why?

We wanted a markup language with the following requirements:
- less than 100 lines of functional code
- easy to read
- secure
- support table, ul, ol, code
- support html5 video and audio elements (html serialization only)
- can align images and resize them
- can specify class for tables and code elements
- can add anchors
- does not use _ for markup (since it creates odd behavior)
- automatically links urls
- fast
- easy to extend
- supports latex and pdf including references
- allows to describe the markup in the markup (this document is generated from markmin syntax)

(results depend on text but in average for text ~100K markmin is 30% faster than markdown, for text ~10K it is 10x faster)

The [[web2py book http://www.lulu.com/product/paperback/web2py-%283rd-edition%29/12822827]] published by lulu, for example, was entirely generated with markmin2pdf from the online [[web2py wiki http://www.web2py.com/book]]

## Download

- http://web2py.googlecode.com/hg/gluon/contrib/markmin/markmin2html.py
- http://web2py.googlecode.com/hg/gluon/contrib/markmin/markmin2latex.py
- http://web2py.googlecode.com/hg/gluon/contrib/markmin/markmin2pdf.py

markmin2html.py and markmin2latex.py are single files and have no web2py dependence. Their license is BSD.

## Examples

### Bold, italic, code and links

--------------------------------------------------
**SOURCE**                 | **OUTPUT**
``# title``                | **title**
``## section``             | **section**
``### subsection``         | **subsection**
``**bold**``               | **bold**
``''italic''``             | ''italic''
``!`!`verbatim`!`!``       | ``verbatim``
``http://google.com``      | http://google.com
``[[click me #myanchor]]`` | [[click me #myanchor]]
---------------------------------------------------

### More on links

The format is always ``[[title link]]``. Notice you can nest bold, italic and code inside the link title.

### Anchors [[myanchor]]

You can place an anchor anywhere in the text using the syntax ``[[name]]`` where ''name'' is the name of the anchor.
You can then link the anchor with [[link #myanchor]], i.e. ``[[link #myanchor]]``.

### Images

[[some image http://www.web2py.com/examples/static/web2py_logo.png right 200px]]
This paragraph has an image aligned to the right with a width of 200px. Its is placed using the code

``[[some image http://www.web2py.com/examples/static/web2py_logo.png right 200px]]``.

### Unordered Lists

``
- Dog
- Cat
- Mouse
``

is rendered as
- Dog
- Cat
- Mouse

Two new lines between items break the list in two lists.

### Ordered Lists

``
+ Dog
+ Cat
+ Mouse
``

is rendered as
+ Dog
+ Cat
+ Mouse


### Tables

Something like this
``
---------
**A** | **B** | **C**
0 | 0 | X
0 | X | 0
X | 0 | 0
-----:abc
``
is a table and is rendered as
---------
**A** | **B** | **C**
0 | 0 | X
0 | X | 0
X | 0 | 0
-----:abc
Four or more dashes delimit the table and | separates the columns.
The ``:abc`` at the end sets the class for the table and it is optional.

### Blockquote

A table with a single cell is rendered as a blockquote:

-----
Hello world
-----

### Code, ``<code>``, escaping and extra stuff

``
def test():
    return "this is Python code"
``:python

Optionally a ` inside a ``!`!`...`!`!`` block can be inserted escaped with !`!.
The ``:python`` after the markup is also optional. If present, by default, it is used to set the class of the <code> block.
The behavior can be overridden by passing an argument ``extra`` to the ``render`` function. For example:

``
markmin2html("!`!!`!aaa!`!!`!:custom",
             extra=dict(custom=lambda text: 'x'+text+'x'))
``:python

generates

``'xaaax'``:python

(the ``!`!`...`!`!:custom`` block is rendered by the ``custom=lambda`` function passed to ``render``).


### Html5 support

Markmin also supports the <video> and <audio> html5 tags using the notation:
``
[[title link video]]
[[title link audio]]
``

### Latex and other extensions

Formulas can be embedded into HTML with ``$````$``formula``$````$``.
You can use Google charts to render the formula:

``
LATEX = '<img src="http://chart.apis.google.com/chart?cht=tx&chl=%s" />'
markmin2html(text,{'latex':lambda code: LATEX % code.replace('"','\"')})
``

### Code with syntax highlighting

This requires a syntax highlighting tool, such as the web2py CODE helper.

``
extra={'code_cpp':lambda text: CODE(text,language='cpp').xml(),
       'code_java':lambda text: CODE(text,language='java').xml(),
       'code_python':lambda text: CODE(text,language='python').xml(),
       'code_html':lambda text: CODE(text,language='html').xml()}
markmin2html(text,extra=extra)
``

Code can now be marked up as in this example:

``
!`!`
<html><body>example</body></html>
!`!`:code_html
``

### Citations and References

Citations are treated as internal links in html and proper citations in latex if there is a final section called "References". Items like

``
- [[key]] value
``

in the References will be translated into Latex

``
\\bibitem{key} value
``

Here is an example of usage:

``
As shown in Ref.!`!`mdipierro`!`!:cite

## References
- [[mdipierro]] web2py Manual, 3rd Edition, lulu.com
``

### Caveats
``<ul/>``, ``<ol/>``, ``<code/>``, ``<table/>``, ``<blockquote/>``, ``<h1/>``, ..., ``<h6/>`` do not have ``<p>...</p>`` around them.

"""

META = 'META'
LATEX = '<img src="http://chart.apis.google.com/chart?cht=tx&chl=%s" />'
regex_newlines = re.compile(r'(\n\r)|(\r\n)')
regex_dd=re.compile(r'\$\$(?P<latex>.*?)\$\$')
regex_code = re.compile(r'('+META+r')|(``(?P<t>.*?)``(:(?P<c>\w+))?)',re.S)
regex_maps = [
    (re.compile(r'[ \t\r]+\n'),'\n'),
    (re.compile(r'[ \t\r]+\n'),'\n'),
    (re.compile(r'\*\*(?P<t>[^\s*]+( +[^\s*]+)*)\*\*'),'<strong>\g<t></strong>'),
    (re.compile("''(?P<t>[^\s']+( +[^\s']+)*)''"),'<em>\g<t></em>'),
    (re.compile(r'^#{6} (?P<t>[^\n]+)',re.M),'\n\n<<h6>\g<t></h6>\n'),
    (re.compile(r'^#{5} (?P<t>[^\n]+)',re.M),'\n\n<<h5>\g<t></h5>\n'),
    (re.compile(r'^#{4} (?P<t>[^\n]+)',re.M),'\n\n<<h4>\g<t></h4>\n'),
    (re.compile(r'^#{3} (?P<t>[^\n]+)',re.M),'\n\n<<h3>\g<t></h3>\n'),
    (re.compile(r'^#{2} (?P<t>[^\n]+)',re.M),'\n\n<<h2>\g<t></h2>\n'),
    (re.compile(r'^#{1} (?P<t>[^\n]+)',re.M),'\n\n<<h1>\g<t></h1>\n'),
    (re.compile(r'^\- +(?P<t>.*)',re.M),'<<ul><li>\g<t></li></ul>'),
    (re.compile(r'^\+ +(?P<t>.*)',re.M),'<<ol><li>\g<t></li></ol>'),
    (re.compile(r'</ol>\n<<ol>'),''),
    (re.compile(r'</ul>\n<<ul>'),''),
    (re.compile(r'<<'),'\n\n<<'),
    (re.compile(r'\n\s+\n'),'\n\n')]
regex_table = re.compile(r'^\-{4,}\n(?P<t>.*?)\n\-{4,}(:(?P<c>\w+))?\n',re.M|re.S)
regex_anchor = re.compile(r'\[\[(?P<t>\S+)\]\]')
regex_image_center_width = re.compile(r'\[\[(?P<t>[^\]]*?) +(?P<k>\S+) +center +(?P<w>\d+px)\]\]')
regex_image_width = re.compile(r'\[\[(?P<t>[^\]]*?) +(?P<k>\S+) +(?P<p>left|right) +(?P<w>\d+px)\]\]')
regex_image_center = re.compile(r'\[\[(?P<t>[^\]]*?) +(?P<k>\S+) +center\]\]')
regex_image = re.compile(r'\[\[(?P<t>[^\]]*?) +(?P<k>\S+) +(?P<p>left|right|center)\]\]')
regex_video = re.compile(r'\[\[(?P<t>[^\]]*?) +(?P<k>\S+) +video\]\]')
regex_audio = re.compile(r'\[\[(?P<t>[^\]]*?) +(?P<k>\S+) +audio\]\]')
regex_link = re.compile(r'\[\[(?P<t>[^\]]*?) +(?P<k>\S+)\]\]')
regex_link_popup = re.compile(r'\[\[(?P<t>[^\]]*?) +(?P<k>\S+) popup\]\]')
regex_link_no_anchor = re.compile(r'\[\[ +(?P<k>\S+)\]\]')
regex_qr = re.compile(r'(?<!["\w>/=])qr:(?P<k>\w+://[\w.\-+?&%/:]+)',re.M)
regex_embed = re.compile(r'(?<!["\w>/=])embed:(?P<k>\w+://[\w.\-+?&%/:]+)', re.M)
regex_iframe = re.compile(r'(?<!["\w>/=])iframe:(?P<k>\w+://[\w.\-+?&%/:]+)', re.M)
regex_auto_image = re.compile(r'(?<!["\w>/=])(?P<k>\w+://\S+\.(jpeg|jpg|gif|png)(\?\S+)?)',re.M)
regex_auto_video = re.compile(r'(?<!["\w>/=])(?P<k>\w+://\S+\.(mp4|mpeg|mov)(\?\S+)?)',re.M)
regex_auto_audio = re.compile(r'(?<!["\w>/=])(?P<k>\w+://\S+\.(mp3|wav)(\?\S+)?)',re.M)
regex_auto = re.compile(r'(?<!["\w>/=])(?P<k>\w+://\S+)',re.M)

def render(text,extra={},allowed={},sep='p',URL=None,environment=None,latex='google'):
    """
    Arguments:
    - text is the text to be processed
    - extra is a dict like extra=dict(custom=lambda value: value) that process custom code
      as in " ``this is custom code``:custom "
    - allowed is a dictionary of list of allowed classes like
      allowed = dict(code=('python','cpp','java'))
    - sep can be 'p' to separate text in <p>...</p>
      or can be 'br' to separate text using <br />


    >>> render('this is\\n# a section\\nparagraph')
    '<p>this is</p><h1>a section</h1><p>paragraph</p>'
    >>> render('this is\\n## a subsection\\nparagraph')
    '<p>this is</p><h2>a subsection</h2><p>paragraph</p>'
    >>> render('this is\\n### a subsubsection\\nparagraph')
    '<p>this is</p><h3>a subsubsection</h3><p>paragraph</p>'
    >>> render('**hello world**')
    '<p><strong>hello world</strong></p>'
    >>> render('``hello world``')
    '<code class="">hello world</code>'
    >>> render('``hello world``:python')
    '<code class="python">hello world</code>'
    >>> render('``\\nhello\\nworld\\n``:python')
    '<pre><code class="python">hello\\nworld</code></pre>'
    >>> render("''hello world''")
    '<p><em>hello world</em></p>'
    >>> render('** hello** **world**')
    '<p>** hello** <strong>world</strong></p>'

    >>> render('- this\\n- is\\n- a list\\n\\nand this\\n- is\\n- another')
    '<ul><li>this</li><li>is</li><li>a list</li></ul><p>and this</p><ul><li>is</li><li>another</li></ul>'

    >>> render('+ this\\n+ is\\n+ a list\\n\\nand this\\n+ is\\n+ another')
    '<ol><li>this</li><li>is</li><li>a list</li></ol><p>and this</p><ol><li>is</li><li>another</li></ol>'

    >>> render("----\\na | b\\nc | d\\n----\\n")
    '<table class=""><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></table>'

    >>> render("----\\nhello world\\n----\\n")
    '<blockquote class="">hello world</blockquote>'

    >>> render('[[this is a link http://example.com]]')
    '<p><a href="http://example.com">this is a link</a></p>'

    >>> render('[[this is an image http://example.com left]]')
    '<p><img src="http://example.com" alt="this is an image" align="left" /></p>'
    >>> render('[[this is an image http://example.com left 200px]]')
    '<p><img src="http://example.com" alt="this is an image" align="left" width="200px" /></p>'

    >>> render('[[this is an image http://example.com video]]')
    '<p><video controls="controls"><source src="http://example.com" /></video></p>'
    >>> render('[[this is an image http://example.com audio]]')
    '<p><audio controls="controls"><source src="http://example.com" /></audio></p>'

    >>> render('[[this is a **link** http://example.com]]')
    '<p><a href="http://example.com">this is a <strong>link</strong></a></p>'

    >>> render("``aaa``:custom",extra=dict(custom=lambda text: 'x'+text+'x'))
    'xaaax'
    
    >>> print render(r"$$\int_a^b sin(x)dx$$")
    <img src="http://chart.apis.google.com/chart?cht=tx&chl=\\int_a^b sin(x)dx" />
    """
    text = str(text or '')
    if environment:
        def u2(match,environment=environment):
            a = match.group('a')
            return str(environment[a])
        text = re.compile(r'@\{(?P<a>\w+?)\}').sub(u2,text)
    if not URL is None:
        # this is experimental @{controller/index/args}
        # turns into a digitally signed URL
        def u1(match,URL=URL):
            f,args = match.group('f'), match.group('args')
            return URL(f,args=args.split('/'),scheme=True,host=True)
        text = re.compile(
            '@\{(?P<f>\w+)/(?P<args>.+?)\}'
            ).sub(u1,text)
                          
    #############################################################
    # replace all blocks marked with ``...``:class with META
    # store them into segments they will be treated as code
    #############################################################
    segments, i = [], 0
    if latex == 'google':
        text = regex_dd.sub('``\g<latex>``:latex ',text)
    text = regex_newlines.sub('\n',text)
    while True:
        item = regex_code.search(text,i)
        if not item: break
        if item.group()==META:
            segments.append((None,None))
            text = text[:item.start()]+META+text[item.end():]
        else:
            c = item.group('c') or ''
            if 'code' in allowed and not c in allowed['code']: c = ''
            code = item.group('t').replace('!`!','`')
            segments.append((code,c))
            text = text[:item.start()]+META+text[item.end():]
        i=item.start()+3

    #############################################################
    # do h1,h2,h3,h4,h5,h6,b,i,ol,ul and normalize spaces
    #############################################################
    text = '\n'.join(t.strip() for t in text.split('\n'))
    text = cgi.escape(text)
    for regex, sub in regex_maps:
        text = regex.sub(sub,text)

    #############################################################
    # process tables and blockquotes
    #############################################################
    while True:
        item = regex_table.search(text)
        if not item: break
        c = item.group('c') or ''
        if 'table' in allowed and not c in allowed['table']: c = ''
        content = item.group('t')
        if ' | ' in content:
            rows = content.replace('\n','</td></tr><tr><td>').replace(' | ','</td><td>')
            text = text[:item.start()] + '<<table class="%s"><tr><td>'%c + rows + '</td></tr></table>\n' + text[item.end():]
        else:
            text = text[:item.start()] + '<<blockquote class="%s">'%c + content + '</blockquote>\n' + text[item.end():]

    #############################################################
    # deal with images, videos, audios and links
    #############################################################

    text = regex_anchor.sub('<span id="\g<t>"><span>', text)
    text = regex_image_center_width.sub('<p align="center"><img src="\g<k>" alt="\g<t>" width="\g<w>" /></p>', text)
    text = regex_image_width.sub('<img src="\g<k>" alt="\g<t>" align="\g<p>" width="\g<w>" />', text)
    text = regex_image_center.sub('<p align="center"><img src="\g<k>" alt="\g<t>" /></p>', text)
    text = regex_image.sub('<img src="\g<k>" alt="\g<t>" align="\g<p>" />', text)
    text = regex_video.sub('<video controls="controls"><source src="\g<k>" /></video>', text)
    text = regex_audio.sub('<audio controls="controls"><source src="\g<k>" /></audio>', text)
    text = regex_link_popup.sub('<a href="\g<k>" target="_blank">\g<t></a>', text)
    text = regex_link_no_anchor.sub('<a href="\g<k>">\g<k></a>', text)
    text = regex_link.sub('<a href="\g<k>">\g<t></a>', text)
    text = regex_qr.sub('<img width="80px" src="http://qrcode.kaywa.com/img.php?s=8&amp;d=\g<k>" alt="qr code" />',text)
    text = regex_iframe.sub('<iframe src="\g<k>" frameborder="0" allowfullscreen></iframe>',text)
    text = regex_embed.sub('<a href="\g<k>" class="embed">\g<k></a>',text)
    text = regex_auto_image.sub('<img src="\g<k>" controls />', text)
    text = regex_auto_video.sub('<video src="\g<k>" controls></video>', text)
    text = regex_auto_audio.sub('<audio src="\g<k>" controls></audio>', text)
    text = regex_auto.sub('<a href="\g<k>">\g<k></a>', text)

    #############################################################
    # deal with paragraphs (trick <<ul, <<ol, <<table, <<h1, etc)
    # the << indicates that there should NOT be a new paragraph
    # META indicates a code block therefore no new paragraph
    #############################################################
    items = [item.strip() for item in text.split('\n\n')]
    if sep=='p':
        text = ''.join(
            (p[:2]!='<<' and p!=META and '<p>%s</p>'%p or '%s'%p) \
                for p in items if p.strip())
    elif sep=='br':
        text = '<br />'.join(items)

    #############################################################
    # finally get rid of <<
    #############################################################
    text=text.replace('<<','<')

    #############################################################
    # process all code text
    #############################################################
    parts = text.split(META)
    text = parts[0]
    for i,(code,b) in enumerate(segments):
        if code==None:
            html = META
        else:
            if b in extra:
                if code[:1]=='\n': code=code[1:]
                if code[-1:]=='\n': code=code[:-1]
                html = extra[b](code)
            elif b=='cite':
                html = '['+','.join('<a href="#%s" class="%s">%s</a>' \
                      % (d,b,d) \
                      for d in cgi.escape(code).split(','))+']'
            elif b=='latex':
                html = LATEX % code.replace('"','\"').replace('\n',' ')
            elif code[:1]=='\n' or code[-1:]=='\n':
                if code[:1]=='\n': code=code[1:]
                if code[-1:]=='\n': code=code[:-1]
                html = '<pre><code class="%s">%s</code></pre>' % (b,cgi.escape(code))
            else:
                if code[:1]=='\n': code=code[1:]
                if code[-1:]=='\n': code=code[:-1]
                html = '<code class="%s">%s</code>' % (b,cgi.escape(code))
        text = text+html+parts[i+1]
    return text


def markmin2html(text,extra={},allowed={},sep='p'):
    return render(text,extra,allowed,sep)

if __name__ == '__main__':
    import sys
    import doctest
    if sys.argv[1:2]==['-h']:
        print '<html><body>'+markmin2html(__doc__)+'</body></html>'
    elif len(sys.argv)>1:
        fargv = open(sys.argv[1],'r')
        try:
            print '<html><body>'+markmin2html(fargv.read())+'</body></html>'
        finally:
            fargv.close()
    else:
        doctest.testmod()

