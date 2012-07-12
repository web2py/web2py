#!/usr/bin/env python
# created by Massimo Di Pierro
# improved by Vladyslav Kozlovskyy
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

__all__ = ['render', 'markmin2html', 'markmin_escape']

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
- less than 200 lines of functional code
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

------------------------------------------------------------------------------
**SOURCE**                                    | **OUTPUT**
``# title``                                   | **title**
``## section``                                | **section**
``### subsection``                            | **subsection**
``**bold**``                                  | **bold**
``''italic''``                                | ''italic''
``~~strikeout~~``                             | ~~strikeout~~
``!`!`verbatim`!`!``                          | ``verbatim``
``\`\`color with **bold**\`\`:red``           | ``color with **bold**``:red
``\`\`many colors\`\`:color[blue:#ffff00]``   | ``many colors``:color[blue:#ffff00]
``http://google.com``                         | http://google.com
``[[**click** me #myanchor]]``                | [[**click** me #myanchor]]
``[[click me [extra info] #myanchor popup]]`` | [[click me [extra info] #myanchor popup]]
-------------------------------------------------------------------------------

### More on links

The format is always ``[[title link]]`` or ``[[title [extra] link]]``. Notice you can nest bold, italic, strikeout and code inside the link ``title``.

### Anchors [[myanchor]]

You can place an anchor anywhere in the text using the syntax ``[[name]]`` where ''name'' is the name of the anchor.
You can then link the anchor with [[link #myanchor]], i.e. ``[[link #myanchor]]`` or [[link with an extra info [extra info] #myanchor]], i.e.
``[[link with an extra info [extra info] #myanchor]]``.

### Images

[[alt-string for the image [the image title] http://www.web2py.com/examples/static/web2py_logo.png right 200px]]
This paragraph has an image aligned to the right with a width of 200px. Its is placed using the code

``[[alt-string for the image [the image title] http://www.web2py.com/examples/static/web2py_logo.png right 200px]]``.

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

**NOTE:** You can escape markmin constructions (\\'\\',\`\`,\*\*,\~\~,\[,\{,\]\},\$,\@) with '\\\\' character:
 so \\\\`\\\\` can replace !`!`! escape string

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
[[message link video]]
[[message link audio]]

[[message [title] link video]]
[[message [title] link audio]]
``
where ``message`` will be shown in brousers without HTML5 video/audio tags support.

### Latex and other extensions

Formulas can be embedded into HTML with ''\$\$``formula``\$\$''.
You can use Google charts to render the formula:

``
LATEX = '<img src="http://chart.apis.google.com/chart?cht=tx&chl=%s" />'
markmin2html(text,{'latex':lambda code: LATEX % code.replace('"','\\\\"')})
``

### Code with syntax highlighting

This requires a syntax highlighting tool, such as the web2py CODE helper.

``
extra={'code_cpp':lambda text: CODE(text,language='cpp').xml(),
       'code_java':lambda text: CODE(text,language='java').xml(),
       'code_python':lambda text: CODE(text,language='python').xml(),
       'code_html':lambda text: CODE(text,language='html').xml()}
``
or simple:
``
extra={'code':lambda text,lang='': CODE(text,language=lang).xml()}
``
``
markmin2html(text,extra=extra)
``

Code can now be marked up as in this example:
``
!`!`
<html><body>example</body></html>
!`!`:code_html
``
OR
``
!`!`
<html><body>example</body></html>
!`!`:code[html]
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
html_colors=['aqua', 'black', 'blue', 'fuchsia', 'gray', 'green',
             'lime', 'maroon', 'navy', 'olive', 'purple', 'red',
             'silver', 'teal', 'white', 'yellow']

META = 'META'
LINK = 'LINK'
DISABLED_META = META[::-1]
LATEX = '<img src="http://chart.apis.google.com/chart?cht=tx&chl=%s" />'
regex_URL=re.compile(r'(?P<b>(?<!\\)(?:\\\\)*)@\{(?P<f>\w+)/(?P<args>.+?)\}')
regex_env=re.compile(r'(?P<b>(?<!\\)(?:\\\\)*)@\{(?P<a>\w+?)\}')
regex_expand_meta = re.compile('('+META+'|'+DISABLED_META+')')
regex_newlines = re.compile(r'(\n\r)|(\r\n)')
regex_dd=re.compile(r'\$\$(?P<latex>.*?)\$\$')
regex_code = re.compile('('+META+'|'+DISABLED_META+r')|((?P<b>(?<!\\)(?:\\\\)*)``(?P<t>.*?(?<!\\)(?:\\\\)*)``(?:(?<!\\):(?P<c>\w+)(?:(?<!\\)\[(?P<p>\S+?)(?<!\\)\])?)?)',re.S)
regex_maps = [
    (re.compile(r'[ \t\r]+\n'),'\n'),
    (re.compile(r'[ \t\r]+\n'),'\n'),
    (re.compile(r'(?P<b1>(?<!\\)(?:\\\\)*)\*\*(?P<t>[^\s*]+( +[^\s*]+)*)(?P<b2>(?<!\\)(?:\\\\)*)\*\*'),'\g<b1><strong>\g<t>\g<b2></strong>'),
    (re.compile(r'(?P<b1>(?<!\\)(?:\\\\)*)~~(?P<t>[^\s*]+( +[^\s*]+)*)(?P<b2>(?<!\\)(?:\\\\)*)~~'),'\g<b1><del>\g<t>\g<b2></del>'),
    (re.compile(r"(?P<b1>(?<!\\)(?:\\\\)*)''(?P<t>[^\s']+(?: +[^\s']+)*)(?P<b2>(?<!\\)(?:\\\\)*)''"),'\g<b1><em>\g<t>\g<b2></em>'),
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
regex_qr = re.compile(r'(?<!["\w>/=])qr:(?P<k>\w+://[\w\d\-+?&%/:.]+)',re.M)
regex_embed = re.compile(r'(?<!["\w>/=])embed:(?P<k>\w+://[\w\d\-+_=?%&/:.]+)', re.M)
regex_iframe = re.compile(r'(?<!["\w>/=])iframe:(?P<k>\w+://[\w\d\-+=?%&/:.]+)', re.M)
regex_auto_image = re.compile(r'(?<!["\w>/=])(?P<k>\w+://[\w\d\-+_=%&/:.]+\.(jpeg|JPEG|jpg|JPG|gif|GIF|png|PNG)(\?[\w\d/\-+_=%&:.]+)?)',re.M)
regex_auto_video = re.compile(r'(?<!["\w>/=])(?P<k>\w+://[\w\d\-+_=%&/:.]+\.(mp4|MP4|mpeg|MPEG|mov|MOV)(\?[\w\d/\-+_=%&:.]+)?)',re.M)
regex_auto_audio = re.compile(r'(?<!["\w>/=])(?P<k>\w+://[\w\d\-+_=%&/:.]+\.(mp3|MP3|wav|WAV)(\?[\w\d/\-+_=%&:.]+)?)',re.M)
regex_auto = re.compile(r'(?<!["\w>/=])(?P<k>\w+://[\w\d\-+_=?%&/:.]+)',re.M)

regex_link=re.compile(r'('+LINK+r')|(?P<b>(?<!\\)(?:\\\\)*)\[\[(?P<s>.*?)(?<!\\)\]\]')
regex_link_level2=re.compile(r'^(?P<t>\S.*?)?(?:\s+(?<!\\)\[(?P<a>.+?(?<!\\)(?:\\\\)*)\])?(?:\s+(?P<k>\S+))?(?:\s+(?P<p>popup))?\s*$')
regex_media_level2=re.compile(r'^(?P<t>\S.*?)?(?:\s+(?<!\\)\[(?P<a>.+?(?<!\\)(?:\\\\)*)\])?(?:\s+(?P<k>\S+))?\s+(?P<p>img|IMG|left|right|center|video|audio)(?:\s+(?P<w>\d+px))?\s*$')

regex_backslash = re.compile(r"(\\+)(['`:*~\\[\]{}@\$])")
regex_markmin_escape = re.compile(r"(\\*)(['`:*~\\[\]{}@\$])")

def markmin_escape(text):
   """ insert \\ before markmin control characters: '`:*~[]{}@$ """
   return regex_markmin_escape.sub(lambda m: '\\'+m.group(0).replace('\\','\\\\'), text)

def remove_backslashes(text):
   return  regex_backslash.sub(lambda m: m.group(0)[m.group(0).find('\\')+1:].replace('\\\\','\\') , text)

def render(text,extra={},allowed={},sep='p',URL=None,environment=None,latex='google',auto=True):
    """
    Arguments:
    - text is the text to be processed
    - extra is a dict like extra=dict(custom=lambda value: value) that process custom code
      as in " ``this is custom code``:custom "
    - allowed is a dictionary of list of allowed classes like
      allowed = dict(code=('python','cpp','java'))
    - sep can be 'p' to separate text in <p>...</p>
      or can be 'br' to separate text using <br />
    - auto is a True/False value (default is True) -
      enables auto links processing for iframe,embed,qr,url,image,video,audio

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
    '<p><img src="http://example.com" alt="this is an image" style="float:left" /></p>'

    >>> render('[[this is an image http://example.com left 200px]]')
    '<p><img src="http://example.com" alt="this is an image" style="float:left" width="200px" /></p>'

    >>> render("[[Your browser doesn't support <video> HTML5 tag http://example.com video]]")
    '<p><video controls="controls"><source src="http://example.com" />Your browser doesn\\'t support &lt;video&gt; HTML5 tag</video></p>'

    >>> render("[[Your browser doesn't support <audio> HTML5 tag http://example.com audio]]")
    '<p><audio controls="controls"><source src="http://example.com" />Your browser doesn\\'t support &lt;audio&gt; HTML5 tag</audio></p>'

    >>> render('[[this is a **link** http://example.com]]')
    '<p><a href="http://example.com">this is a <strong>link</strong></a></p>'

    >>> render("``aaa``:custom", extra=dict(custom=lambda text: 'x'+text+'x'))
    'xaaax'

    >>> print render(r"$$\int_a^b sin(x)dx$$")
    <img src="http://chart.apis.google.com/chart?cht=tx&chl=\\int_a^b sin(x)dx" />

    >>> markmin2html(r"use backslash: \[\[[[mess\[[ag\]]e link]]\]]")
    '<p>use backslash: [[<a href="link">mess[[ag]]e</a>]]</p>'

    >>> markmin2html("backslash instead of exclamation sign: \``probe``")
    '<p>backslash instead of exclamation sign: ``probe``</p>'

    >>> render(r"simple image: [[\[[this is an image\]] http://example.com IMG]]!!!")
    '<p>simple image: <img src="http://example.com" alt="[[this is an image]]" />!!!</p>'

    >>> render(r"simple link no anchor with popup: [[ http://example.com popup]]")
    '<p>simple link no anchor with popup: <a href="http://example.com" target="_blank">http://example.com</a></p>'

    >>> render("auto-url: http://example.com")
    '<p>auto-url: <a href="http://example.com">http://example.com</a></p>'

    >>> render("auto-image: (http://example.com/image.jpeg)")
    '<p>auto-image: (<img src="http://example.com/image.jpeg" controls />)</p>'

    >>> render("title1: [[test message [simple \[test\] title] http://example.com ]] test")
    '<p>title1: <a href="http://example.com" title="simple [test] title">test message</a> test</p>'

    >>> render("title2: \[\[[[test message [simple title] http://example.com popup]]\]]")
    '<p>title2: [[<a href="http://example.com" title="simple title" target="_blank">test message</a>]]</p>'

    >>> render("title3: [[ [link w/o anchor but with title] http://www.example.com ]]")
    '<p>title3: <a href="http://www.example.com" title="link w/o anchor but with title">http://www.example.com</a></p>'

    >>> render("title4: [[ [simple title] http://www.example.com popup]]")
    '<p>title4: <a href="http://www.example.com" title="simple title" target="_blank">http://www.example.com</a></p>'

    >>> render("title5: [[test message [simple title] http://example.com IMG]]")
    '<p>title5: <img src="http://example.com" alt="test message" title="simple title" /></p>'

    >>> render("title6: [[[test message w/o title] http://example.com IMG]]")
    '<p>title6: <img src="http://example.com" alt="[test message w/o title]" /></p>'

    >>> render("title7: [[[this is not a title] [this is a title] http://example.com IMG]]")
    '<p>title7: <img src="http://example.com" alt="[this is not a title]" title="this is a title" /></p>'

    >>> render("title8: [[test message [title] http://example.com center]]")
    '<p>title8: <p style="text-align:center"><img src="http://example.com" alt="test message" title="title" /></p></p>'

    >>> render("title9: [[test message [title] http://example.com left]]")
    '<p>title9: <img src="http://example.com" alt="test message" title="title" style="float:left" /></p>'

    >>> render("title10: [[test message [title] http://example.com right 100px]]")
    '<p>title10: <img src="http://example.com" alt="test message" title="title" style="float:right" width="100px" /></p>'

    >>> render("title11: [[test message [title] http://example.com center 200px]]")
    '<p>title11: <p style="text-align:center"><img src="http://example.com" alt="test message" title="title" width="200px" /></p></p>'

    >>> render(r"\\[[probe]]")
    '<p>[[probe]]</p>'

    >>> render(r"\\\\[[probe]]")
    '<p>\\\\<span id="probe"></span></p>'

    >>> render(r"\\\\\\[[probe]]")
    '<p>\\\\[[probe]]</p>'

    >>> render(r"\\\\\\\\[[probe]]")
    '<p>\\\\\\\\<span id="probe"></span></p>'

    >>> render(r"\\\\\\\\\[[probe]]")
    '<p>\\\\\\\\[[probe]]</p>'

    >>> render(r"\\\\\\\\\\\[[probe]]")
    '<p>\\\\\\\\\\\\<span id="probe"></span></p>'

    >>> render("``[[ [\\[[probe\]\\]] URL\\[x\\]]]``:red[dummy_params]")
    '<span style="color: red"><a href="URL[x]" title="[[probe]]">URL[x]</a></span>'

    >>> render("the \\**text**")
    '<p>the **text**</p>'

    >>> render("the \\``text``")
    '<p>the ``text``</p>'

    >>> render("the \\\\''text''")
    "<p>the ''text''</p>"

    >>> render("the [[link [**with** ``<b>title</b>``:red] http://www.example.com]]")
    '<p>the <a href="http://www.example.com" title="**with** ``&lt;b&gt;title&lt;/b&gt;``:red">link</a></p>'

    >>> render("the [[link \\[**without** ``<b>title</b>``:red\\] http://www.example.com]]")
    '<p>the <a href="http://www.example.com">link [<strong>without</strong> <span style="color: red">&lt;b&gt;title&lt;/b&gt;</span>]</a></p>'

    >>> render("aaa-META-``code``:text-LINK-[[link http://www.example.com]]-LINK-[[image http://www.picture.com img]]-end")
    '<p>aaa-META-<code class="text">code</code>-LINK-<a href="http://www.example.com">link</a>-LINK-<img src="http://www.picture.com" alt="image" />-end</p>'

    >>> render("[[<a>test</a> [<a>test2</a>] <a>text3</a>]]")
    '<p><a href="&lt;a&gt;text3&lt;/a&gt;" title="&lt;a&gt;test2&lt;/a&gt;">&lt;a&gt;test&lt;/a&gt;</a></p>'

    >>> render("[[<a>test</a> [<a>test2</a>] <a>text3</a> IMG]]")
    '<p><img src="&lt;a&gt;text3&lt;/a&gt;" alt="&lt;a&gt;test&lt;/a&gt;" title="&lt;a&gt;test2&lt;/a&gt;" /></p>'

    >>> render("**bold** ''italic'' ~~strikeout~~")
    '<p><strong>bold</strong> <em>italic</em> <del>strikeout</del></p>'

    >>> render("this is ``a red on yellow text``:c[#FF0000:#FFFF00]")
    '<p>this is <span style="color: #FF0000;background-color: #FFFF00;">a red on yellow text</span></p>'

    >>> render("this is ``a text with yellow background``:c[:yellow]")
    '<p>this is <span style="background-color: yellow;">a text with yellow background</span></p>'

    >>> render("this is ``a colored text (RoyalBlue)``:color[rgb(65,105,225)]")
    '<p>this is <span style="color: rgb(65,105,225);">a colored text (RoyalBlue)</span></p>'

    >>> render("this is ``a green text``:color[green:]")
    '<p>this is <span style="color: green;">a green text</span></p>'

    >>> render("**@{probe}**", environment=dict(probe="this is a test"))
    '<p><strong>this is a test</strong></p>'
    """
    text = str(text or '')
    if environment:
        def u2(match, environment=environment):
            b,a = match.group('b','a')
            return b + str(environment.get(a, match.group(0)))
        text = regex_env.sub(u2,text)
    if URL is not None:
        # this is experimental @{controller/index/args}
        # turns into a digitally signed URL
        def u1(match,URL=URL):
            b,f,args = match.group('b','f','args')
            return b + URL(f,args=args.split('/'),scheme=True,host=True)
        text = regex_URL.sub(u1,text)

    if latex == 'google':
        text = regex_dd.sub('``\g<latex>``:latex ', text)
    text = regex_newlines.sub('\n',text)

    #############################################################
    # replace all blocks marked with ``...``:class with META
    # store them into segments they will be treated as code
    #############################################################
    segments = []
    def mark_code(m):
        if m.group() in ( META, DISABLED_META ):
            segments.append((None, None, None, m.group(0)))
            return m.group()
        else:
            c = m.group('c') or ''
            p = m.group('p') or ''
            b = m.group('b') or ''
            if 'code' in allowed and not c in allowed['code']: c = ''
            code = m.group('t').replace('!`!','`')
            segments.append((code, c, p, m.group(0)))
        return b + META
    text = regex_code.sub(mark_code, text)

    #############################################################
    # replace all blocks marked with [[...]] with LINK
    # store them into links|medias they will be treated as link
    #############################################################
    links = []
    def mark_link(m):
        if m.group() == LINK:
            links.append(None)
            b = ''
        else:
            s = m.group('s') or ''
            b = m.group('b') or ''
            links.append(s)
        return b + LINK
    text = regex_link.sub(mark_link, text)

    #############################################################
    # normalize spaces
    #############################################################
    text = '\n'.join(t.strip() for t in text.split('\n'))
    text = cgi.escape(text)

    if auto:
        text = regex_iframe.sub('<iframe src="\g<k>" frameborder="0" allowfullscreen></iframe>',text)
        text = regex_embed.sub('<a href="\g<k>" class="embed">\g<k></a>',text)
        text = regex_qr.sub('<img width="80px" src="http://qrcode.kaywa.com/img.php?s=8&amp;d=\g<k>" alt="qr code" />',text)
        text = regex_auto_image.sub('<img src="\g<k>" controls />', text)
        text = regex_auto_video.sub('<video src="\g<k>" controls></video>', text)
        text = regex_auto_audio.sub('<audio src="\g<k>" controls></audio>', text)
        text = regex_auto.sub('<a href="\g<k>">\g<k></a>', text)

    #############################################################
    # do h1,h2,h3,h4,h5,h6,b,i,ol,ul
    #############################################################
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
    # deal with images, videos, audios and links
    #############################################################
    def sub_media(m):
        d=m.groupdict()
        if not d['k']:
            return m.group(0)
        d['k'] = cgi.escape(d['k'])
        d['t'] = d['t'] or ''
        d['width'] = ' width="%s"'%d['w'] if d['w'] else ''
        d['title'] = ' title="%s"'%cgi.escape(d['a']).replace(META, DISABLED_META) if d['a'] else ''
        d['style'] = d['p_begin'] = d['p_end'] = ''
        if d['p'] == 'center':
            d['p_begin'] = '<p style="text-align:center">'
            d['p_end'] = '</p>'
        elif d['p'] in ('left','right'):
            d['style'] = ' style="float:%s"'%d['p']
        if d['p'] in ('video','audio'):
            d['t']=render(d['t'],{},{},'',URL,environment,latex,auto)
            return '<%(p)s controls="controls"%(title)s%(width)s><source src="%(k)s" />%(t)s</%(p)s>'%d
        d['alt'] = ' alt="%s"'%cgi.escape(d['t']).replace(META, DISABLED_META) if d['t'] else ''
        return '%(p_begin)s<img src="%(k)s"%(alt)s%(title)s%(style)s%(width)s />%(p_end)s'%d

    def sub_link(m):
        d=m.groupdict()
        if not d['k'] and not d['t']:
            return m.group(0)
        d['t'] = d['t'] or ''
        d['a'] = cgi.escape(d['a']) if d['a'] else ''
        if d['k']:
            d['k'] = cgi.escape(d['k'])
            d['title'] = ' title="%s"' % d['a'].replace(META, DISABLED_META) if d['a'] else ''
            d['target'] = ' target="_blank"' if d['p'] == 'popup' else ''
            d['t'] = render(d['t'],{},{},'',URL,environment,latex,auto) if d['t'] else d['k']
            return '<a href="%(k)s"%(title)s%(target)s>%(t)s</a>'%d
        d['t'] = cgi.escape(d['t'])
        return '<span id="%(t)s">%(a)s</span>'%d

    parts = text.split(LINK)
    text = parts[0]
    for i,s in enumerate(links):
        if s==None:
            html = LINK
        else:
            html = regex_media_level2.sub(sub_media, s)
            if html == s:
                html = regex_link_level2.sub(sub_link, html)
            if html == s:
                # return unprocessed string as a signal of an error
                html = '[[%s]]'%s
        text = text+html+parts[i+1]

    #############################################################
    # process all code text
    #############################################################
    def expand_meta(m):
        code,b,p,s = segments.pop(0)
        if code==None or m.group() == DISABLED_META:
           return cgi.escape(s)
        if b in extra:
            if code[:1]=='\n': code=code[1:]
            if code[-1:]=='\n': code=code[:-1]
            if p:
                return extra[b](code,p)
            else:
                return extra[b](code)
        elif b=='cite':
            return '['+','.join('<a href="#%s" class="%s">%s</a>' \
                  % (d,b,d) \
                  for d in cgi.escape(code).split(','))+']'
        elif b=='latex':
            return LATEX % code.replace('"','\"').replace('\n',' ')
        elif b in html_colors:
            return '<span style="color: %s">%s</span>' \
                  % (b, render(code,{},{},'',URL,environment,latex,auto))
        elif b in ('c', 'color') and p:
             c=p.split(':')
             fg='color: %s;' % c[0] if c[0] else ''
             bg='background-color: %s;' % c[1] if len(c)>1 and c[1] else ''
             return '<span style="%s%s">%s</span>' \
                   % (fg, bg, render(code,{},{},'',URL,environment,latex,auto))
        elif code[:1]=='\n' and code[-1:]=='\n':
            return '<pre><code class="%s">%s</code></pre>' % (b,cgi.escape(code[1:-1]))
        return '<code class="%s">%s</code>' % (b,cgi.escape(code[ (code[:1]=='\n')
                                                                : [None,-1][code[-1:]=='\n']]))
    text = regex_expand_meta.sub(expand_meta, text)
    text = remove_backslashes(text)
    return text

def markmin2html(text, extra={}, allowed={}, sep='p', auto=True):
    return render(text, extra, allowed, sep, auto=auto)

if __name__ == '__main__':
    import sys
    import doctest
    if sys.argv[1:2] == ['-h']:
        print '<html><body>'+markmin2html(__doc__)+'</body></html>'
    elif len(sys.argv) > 1:
        fargv = open(sys.argv[1],'r')
        try:
            print '<html><body>'+markmin2html(fargv.read())+'</body></html>'
        finally:
            fargv.close()
    else:
        doctest.testmod()

