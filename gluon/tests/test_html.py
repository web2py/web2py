#!/bin/python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.html
"""

import unittest
from fix_path import fix_sys_path

fix_sys_path(__file__)

from html import *
from html import verifyURL
from html import truncate_string
from storage import Storage
from html import XML_pickle, XML_unpickle
from html import TAG_pickler, TAG_unpickler


class TestBareHelpers(unittest.TestCase):

    # xmlescape() = covered by other tests

    # TODO: def test_call_as_list(self):

    def test_truncate_string(self):
        # Ascii text
        self.assertEqual(truncate_string('Lorem ipsum dolor sit amet, consectetur adipiscing elit, '
                                         'sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.',
                                         length=30), 'Lorem ipsum dolor sit amet,...')
        self.assertEqual(truncate_string('Short text shorter than the length parameter.', length=100),
                         'Short text shorter than the length parameter.')
        # French text
        self.assertEqual(truncate_string('Un texte en français avec des accents et des caractères bizarre.', length=30),
                         'Un texte en français avec d...')

    def test_StaticURL(self):
        # test response.static_version coupled with response.static_version_urls
        self.assertEqual(URL('a', 'c', 'f'), '/a/c/f')
        self.assertEqual(URL('a', 'static', 'design.css'), '/a/static/design.css')
        response = Storage()
        response.static_version = '1.2.3'
        from globals import current
        current.response = response
        self.assertEqual(URL('a', 'static', 'design.css'), '/a/static/design.css')
        response.static_version_urls = True
        self.assertEqual(URL('a', 'static', 'design.css'), '/a/static/_1.2.3/design.css')

    def test_URL(self):
        self.assertEqual(URL('a', 'c', 'f', args='1'), '/a/c/f/1')
        self.assertEqual(URL('a', 'c', 'f', args=('1', '2')), '/a/c/f/1/2')
        self.assertEqual(URL('a', 'c', 'f', args=['1', '2']), '/a/c/f/1/2')
        self.assertEqual(URL('a', 'c', '/f'), '/a/c/f')
        self.assertEqual(URL('a', 'c', 'f.json'), '/a/c/f.json')
        self.assertRaises(SyntaxError, URL, *['a'])

        request = Storage()
        request.application = 'a'
        request.controller = 'c'
        request.function = 'f'
        request.env = {}

        from globals import current  # Can't be moved with other import
        current.request = request

        must_return = '/a/c/f'
        self.assertEqual(URL(), must_return)
        self.assertEqual(URL('f'), must_return)
        self.assertEqual(URL('c', 'f'), must_return)
        self.assertEqual(URL('a', 'c', 'f'), must_return)
        self.assertEqual(URL('a', 'c', 'f', extension='json'), '/a/c/f.json')

        def weird():
            pass
        self.assertEqual(URL('a', 'c', weird), '/a/c/weird')
        self.assertRaises(SyntaxError, URL, *['a', 'c', 1])
        # test signature
        rtn = URL(a='a', c='c', f='f', args=['x', 'y', 'z'],
                  vars={'p': (1, 3), 'q': 2}, anchor='1', hmac_key='key')
        self.assertEqual(rtn, '/a/c/f/x/y/z?p=1&p=3&q=2&_signature=a32530f0d0caa80964bb92aad2bedf8a4486a31f#1')
        # test _signature exclusion
        rtn = URL(a='a', c='c', f='f', args=['x', 'y', 'z'],
                  vars={'p': (1, 3), 'q': 2, '_signature': 'abc'},
                  anchor='1', hmac_key='key')
        self.assertEqual(rtn, '/a/c/f/x/y/z?p=1&p=3&q=2&_signature=a32530f0d0caa80964bb92aad2bedf8a4486a31f#1')
        # emulate user_signature
        current.session = Storage(auth=Storage(hmac_key='key'))
        self.assertEqual(URL(user_signature=True), '/a/c/f?_signature=c4aed53c08cff08f369dbf8b5ba51889430cf2c2')
        # hash_vars combination
        rtn = URL('a', 'c', 'f', args=['x', 'y', 'z'], vars={'p': (1, 3), 'q': 2}, hmac_key='key')
        self.assertEqual(rtn, '/a/c/f/x/y/z?p=1&p=3&q=2&_signature=a32530f0d0caa80964bb92aad2bedf8a4486a31f')
        rtn = URL('a', 'c', 'f', args=['x', 'y', 'z'], vars={'p': (1, 3), 'q': 2}, hmac_key='key', hash_vars=True)
        self.assertEqual(rtn, '/a/c/f/x/y/z?p=1&p=3&q=2&_signature=a32530f0d0caa80964bb92aad2bedf8a4486a31f')
        rtn = URL('a', 'c', 'f', args=['x', 'y', 'z'], vars={'p': (1, 3), 'q': 2}, hmac_key='key', hash_vars=False)
        self.assertEqual(rtn, '/a/c/f/x/y/z?p=1&p=3&q=2&_signature=0b5a0702039992aad23c82794b8496e5dcd59a5b')
        rtn = URL('a', 'c', 'f', args=['x', 'y', 'z'], vars={'p': (1, 3), 'q': 2}, hmac_key='key', hash_vars=['p'])
        self.assertEqual(rtn, '/a/c/f/x/y/z?p=1&p=3&q=2&_signature=5d01b982fd72b39674b012e0288071034e156d7a')
        rtn = URL('a', 'c', 'f', args=['x', 'y', 'z'], vars={'p': (1, 3), 'q': 2}, hmac_key='key', hash_vars='p')
        self.assertEqual(rtn, '/a/c/f/x/y/z?p=1&p=3&q=2&_signature=5d01b982fd72b39674b012e0288071034e156d7a')
        # test url_encode
        rtn = URL('a', 'c', 'f', args=['x', 'y', 'z'], vars={'maï': (1, 3), 'lié': 2}, url_encode=False)
        self.assertEqual(rtn, '/a/c/f/x/y/z?li\xc3\xa9=2&ma\xc3\xaf=1&ma\xc3\xaf=3')
        rtn = URL('a', 'c', 'f', args=['x', 'y', 'z'], vars={'maï': (1, 3), 'lié': 2}, url_encode=True)
        self.assertEqual(rtn, '/a/c/f/x/y/z?li%C3%A9=2&ma%C3%AF=1&ma%C3%AF=3')
        # test CRLF detection
        self.assertRaises(SyntaxError, URL, *['a\n', 'c', 'f'])
        self.assertRaises(SyntaxError, URL, *['a\r', 'c', 'f'])

    def test_verifyURL(self):
        r = Storage()
        r.application = 'a'
        r.controller = 'c'
        r.function = 'f'
        r.extension = 'html'
        r.env = {}
        r.get_vars = Storage()
        # missing signature as request.get_vars returns False
        rtn = verifyURL(r, 'key')
        self.assertEqual(rtn, False)
        # reverse tests from previous testcase with hash_vars combinations
        r.args = ['x', 'y', 'z']
        r.get_vars = Storage(p=(1, 3), q=2)
        # add signature
        r.get_vars['_signature'] = 'a32530f0d0caa80964bb92aad2bedf8a4486a31f'
        rtn = verifyURL(r, 'key')
        self.assertEqual(rtn, True)
        r.get_vars['_signature'] = 'a32530f0d0caa80964bb92aad2bedf8a4486a31f'
        rtn = verifyURL(r, 'key', hash_vars=True)
        self.assertEqual(rtn, True)
        r.get_vars['_signature'] = '0b5a0702039992aad23c82794b8496e5dcd59a5b'
        rtn = verifyURL(r, 'key', hash_vars=False)
        self.assertEqual(rtn, True)
        r.get_vars['_signature'] = '5d01b982fd72b39674b012e0288071034e156d7a'
        rtn = verifyURL(r, 'key', hash_vars=['p'])
        self.assertEqual(rtn, True)
        r.get_vars['_signature'] = '5d01b982fd72b39674b012e0288071034e156d7a'
        rtn = verifyURL(r, 'key', hash_vars='p')
        self.assertEqual(rtn, True)
        # without session, user_signature returns always False
        rtn = verifyURL(r, user_signature=True)
        self.assertEqual(rtn, False)
        # same goes if you don't use an hmac_key
        rtn = verifyURL(r)
        self.assertEqual(rtn, False)
        # emulate user signature
        from globals import current
        current.session = Storage(auth=Storage(hmac_key='key'))
        r.get_vars['_signature'] = 'a32530f0d0caa80964bb92aad2bedf8a4486a31f'
        rtn = verifyURL(r, user_signature=True)
        self.assertEqual(rtn, True)

    # TODO: def test_XmlComponent(self):

    def test_XML(self):
        # sanitization process
        self.assertEqual(XML('<h1>Hello<a data-hello="world">World</a></h1>').xml(),
                         '<h1>Hello<a data-hello="world">World</a></h1>')
        # with sanitize, data-attributes are not permitted
        self.assertEqual(XML('<h1>Hello<a data-hello="world">World</a></h1>', sanitize=True).xml(),
                         '<h1>HelloWorld</h1>')
        # stringify by default
        self.assertEqual(XML(1.3), '1.3')
        self.assertEqual(XML(u'<div>è</div>').xml(), '<div>\xc3\xa8</div>')
        # you can calc len on the class, that equals the xml() and the str()
        self.assertEqual(len(XML('1.3')), len('1.3'))
        self.assertEqual(len(XML('1.3').xml()), len('1.3'))
        self.assertEqual(len(str(XML('1.3'))), len('1.3'))
        # you can concatenate them to strings (check for __add__ and __radd__ methods)
        self.assertEqual(XML('a') + 'b', 'ab')
        self.assertEqual(XML('a') + XML('b'), 'ab')
        self.assertEqual('a' + XML('b'), 'ab')
        # you can compare them
        self.assertEqual(XML('a') == XML('a'), True)
        # beware that the comparison is made on the XML repr
        self.assertEqual(XML('<h1>Hello<a data-hello="world">World</a></h1>', sanitize=True),
                         XML('<h1>HelloWorld</h1>'))
        # bug check for the sanitizer for closing no-close tags
        self.assertEqual(XML('<p>Test</p><br/><p>Test</p><br/>', sanitize=True),
                         XML('<p>Test</p><br /><p>Test</p><br />'))
        # basic flatten test
        self.assertEqual(XML('<p>Test</p>').flatten(), '<p>Test</p>')
        self.assertEqual(XML('<p>Test</p>').flatten(render=lambda text, tag, attr: text), '<p>Test</p>')

    def test_XML_pickle_unpickle(self):
        # weird test
        self.assertEqual(XML_unpickle(XML_pickle('data to be pickle')[1][0]), 'data to be pickle')

    def test_DIV(self):
        # Empty DIV()
        self.assertEqual(DIV().xml(), '<div></div>')
        self.assertEqual(DIV('<>', _a='1', _b='2').xml(),
                         '<div a="1" b="2">&lt;&gt;</div>')
        # attributes can be updated like in a dict
        div = DIV('<>', _a='1')
        div['_b'] = '2'
        self.assertEqual(div.xml(),
                         '<div a="1" b="2">&lt;&gt;</div>')
        # also with a mapping
        div.update(_b=2, _c=3)
        self.assertEqual(div.xml(),
                         '<div a="1" b="2" c="3">&lt;&gt;</div>')
        # length of the DIV is the number of components
        self.assertEqual(len(DIV('a', 'bc')), 2)
        # also if empty, DIV is True in a boolean evaluation
        self.assertTrue(True if DIV() else False)
        # parent and siblings
        a = DIV(SPAN('a'), DIV('b'))
        s = a.element('span')
        d = s.parent
        d['_class'] = 'abc'
        self.assertEqual(a.xml(), '<div class="abc"><span>a</span><div>b</div></div>')
        self.assertEqual([el.xml() for el in s.siblings()], ['<div>b</div>'])
        self.assertEqual(s.sibling().xml(), '<div>b</div>')
        # siblings with wrong args
        self.assertEqual(s.siblings('a'), [])
        # siblings with good args
        self.assertEqual(s.siblings('div')[0].xml(), '<div>b</div>')
        # Check for siblings with wrong kargs and value
        self.assertEqual(s.siblings(a='d'), [])
        # Check for siblings with good kargs and value
        # Can't figure this one out what is a right value here??
        # Commented for now...
        # self.assertEqual(s.siblings(div='<div>b</div>'), ???)
        # No other sibling should return None
        self.assertEqual(DIV(P('First element')).element('p').sibling(), None)
        # --------------------------------------------------------------------------------------------------------------
        # This use unicode to hit xmlescape() line :
        #     """
        #     elif isinstance(data, unicode):
        #         data = data.encode('utf8', 'xmlcharrefreplace')
        #     """
        self.assertEqual(DIV(u'Texte en français avec des caractères accentués...').xml(),
                         '<div>Texte en fran\xc3\xa7ais avec des caract\xc3\xa8res accentu\xc3\xa9s...</div>')
        # --------------------------------------------------------------------------------------------------------------
        self.assertEqual(DIV('Test with an ID', _id='id-of-the-element').xml(),
                         '<div id="id-of-the-element">Test with an ID</div>')
        self.assertEqual(DIV().element('p'), None)

        # Corner case for raise coverage of one line
        # I think such assert fail cause of python 2.6
        # Work under python 2.7
        # with self.assertRaises(SyntaxError) as cm:
        #     DIV(BR('<>')).xml()
        # self.assertEqual(cm.exception[0], '<br/> tags cannot have components')

        # test .get('attrib')
        self.assertEqual(DIV('<p>Test</p>', _class="class_test").get('_class'), 'class_test')

    def test_CAT(self):
        # Empty CAT()
        self.assertEqual(CAT().xml(), '')
        # CAT('')
        self.assertEqual(CAT('').xml(), '')
        # CAT(' ')
        self.assertEqual(CAT(' ').xml(), ' ')

    def test_TAG_pickler_unpickler(self):
        # weird test
        self.assertEqual(TAG_unpickler(TAG_pickler(TAG.div('data to be pickle'))[1][0]).xml(),
                         '<div>data to be pickle</div>')

    def test_TAG(self):
        self.assertEqual(TAG.first(TAG.second('test'), _key=3).xml(),
                         '<first key="3"><second>test</second></first>')
        # ending in underscore "triggers" <input /> style
        self.assertEqual(TAG.first_(TAG.second('test'), _key=3).xml(),
                         '<first key="3" />')
        # unicode test for TAG
        self.assertEqual(TAG.div(u'Texte en français avec des caractères accentués...').xml(),
                         '<div>Texte en fran\xc3\xa7ais avec des caract\xc3\xa8res accentu\xc3\xa9s...</div>')

    def test_HTML(self):
        self.assertEqual(HTML('<>', _a='1', _b='2').xml(),
                         '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">\n<html a="1" b="2" lang="en">&lt;&gt;</html>')
        self.assertEqual(HTML('<>', _a='1', _b='2', doctype='strict').xml(),
                         '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">\n<html a="1" b="2" lang="en">&lt;&gt;</html>')
        self.assertEqual(HTML('<>', _a='1', _b='2', doctype='transitional').xml(),
                         '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">\n<html a="1" b="2" lang="en">&lt;&gt;</html>')
        self.assertEqual(HTML('<>', _a='1', _b='2', doctype='frameset').xml(),
                         '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">\n<html a="1" b="2" lang="en">&lt;&gt;</html>')
        self.assertEqual(HTML('<>', _a='1', _b='2', doctype='html5').xml(),
                         '<!DOCTYPE HTML>\n<html a="1" b="2" lang="en">&lt;&gt;</html>')
        self.assertEqual(HTML('<>', _a='1', _b='2', doctype='').xml(),
                         '<html a="1" b="2" lang="en">&lt;&gt;</html>')
        self.assertEqual(HTML('<>', _a='1', _b='2', doctype='CustomDocType').xml(),
                         'CustomDocType\n<html a="1" b="2" lang="en">&lt;&gt;</html>')

    def test_XHTML(self):
        # Empty XHTML test
        self.assertEqual(XHTML().xml(),
                         '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n<html lang="en" xml:lang="en" xmlns="http://www.w3.org/1999/xhtml"></html>')
        # Not Empty XHTML test
        self.assertEqual(XHTML('<>', _a='1', _b='2').xml(),
                         '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n<html a="1" b="2" lang="en" xml:lang="en" xmlns="http://www.w3.org/1999/xhtml">&lt;&gt;</html>')
        self.assertEqual(XHTML('<>', _a='1', _b='2', doctype='').xml(),
                         '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n<html a="1" b="2" lang="en" xml:lang="en" xmlns="http://www.w3.org/1999/xhtml">&lt;&gt;</html>')
        self.assertEqual(XHTML('<>', _a='1', _b='2', doctype='strict').xml(),
                         '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n<html a="1" b="2" lang="en" xml:lang="en" xmlns="http://www.w3.org/1999/xhtml">&lt;&gt;</html>')
        self.assertEqual(XHTML('<>', _a='1', _b='2', doctype='transitional').xml(),
                         '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n<html a="1" b="2" lang="en" xml:lang="en" xmlns="http://www.w3.org/1999/xhtml">&lt;&gt;</html>')
        self.assertEqual(XHTML('<>', _a='1', _b='2', doctype='frameset').xml(),
                         '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">\n<html a="1" b="2" lang="en" xml:lang="en" xmlns="http://www.w3.org/1999/xhtml">&lt;&gt;</html>')
        self.assertEqual(XHTML('<>', _a='1', _b='2', doctype='xmlns').xml(),
                         'xmlns\n<html a="1" b="2" lang="en" xml:lang="en" xmlns="http://www.w3.org/1999/xhtml">&lt;&gt;</html>')
        self.assertEqual(XHTML('<>', _a='1', _b='2', _xmlns='xmlns').xml(),
                         '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n<html a="1" b="2" lang="en" xml:lang="en" xmlns="http://www.w3.org/1999/xhtml">&lt;&gt;</html>')

    def test_HEAD(self):
        self.assertEqual(HEAD('<>', _a='1', _b='2').xml(),
                         '<head a="1" b="2">&lt;&gt;</head>')

    def test_TITLE(self):
        self.assertEqual(TITLE('<>', _a='1', _b='2').xml(),
                         '<title a="1" b="2">&lt;&gt;</title>')

    def test_META(self):
        self.assertEqual(META(_a='1', _b='2').xml(),
                         '<meta a="1" b="2" />')

    def test_LINK(self):
        self.assertEqual(LINK(_a='1', _b='2').xml(),
                         '<link a="1" b="2" />')

    def test_SCRIPT(self):
        self.assertEqual(SCRIPT('<>', _a='1', _b='2').xml(),
                         '''<script a="1" b="2"><!--
<>
//--></script>''')
        self.assertEqual(SCRIPT('<>').xml(),
                         '''<script><!--
<>
//--></script>''')
        self.assertEqual(SCRIPT().xml(), '<script></script>')

    def test_STYLE(self):
        self.assertEqual(STYLE('<>', _a='1', _b='2').xml(),
                         '<style a="1" b="2"><!--/*--><![CDATA[/*><!--*/\n<>\n/*]]>*/--></style>')
        # Try to hit : return DIV.xml(self)
        self.assertEqual(STYLE().xml(), '<style></style>')

    def test_IMG(self):
        self.assertEqual(IMG(_a='1', _b='2').xml(),
                         '<img a="1" b="2" />')

    def test_SPAN(self):
        self.assertEqual(SPAN('<>', _a='1', _b='2').xml(),
                         '<span a="1" b="2">&lt;&gt;</span>')

    def test_BODY(self):
        self.assertEqual(BODY('<>', _a='1', _b='2').xml(),
                         '<body a="1" b="2">&lt;&gt;</body>')

    def test_H1(self):
        self.assertEqual(H1('<>', _a='1', _b='2').xml(),
                         '<h1 a="1" b="2">&lt;&gt;</h1>')

    def test_H2(self):
        self.assertEqual(H2('<>', _a='1', _b='2').xml(),
                         '<h2 a="1" b="2">&lt;&gt;</h2>')

    def test_H3(self):
        self.assertEqual(H3('<>', _a='1', _b='2').xml(),
                         '<h3 a="1" b="2">&lt;&gt;</h3>')

    def test_H4(self):
        self.assertEqual(H4('<>', _a='1', _b='2').xml(),
                         '<h4 a="1" b="2">&lt;&gt;</h4>')

    def test_H5(self):
        self.assertEqual(H5('<>', _a='1', _b='2').xml(),
                         '<h5 a="1" b="2">&lt;&gt;</h5>')

    def test_H6(self):
        self.assertEqual(H6('<>', _a='1', _b='2').xml(),
                         '<h6 a="1" b="2">&lt;&gt;</h6>')

    def test_P(self):
        self.assertEqual(P('<>', _a='1', _b='2').xml(),
                         '<p a="1" b="2">&lt;&gt;</p>')
        # test cr2br
        self.assertEqual(P('a\nb').xml(), '<p>a\nb</p>')
        self.assertEqual(P('a\nb', cr2br=True).xml(), '<p>a<br />b</p>')

    def test_STRONG(self):
        self.assertEqual(STRONG('<>', _a='1', _b='2').xml(),
                         '<strong a="1" b="2">&lt;&gt;</strong>')

    def test_B(self):
        self.assertEqual(B('<>', _a='1', _b='2').xml(),
                         '<b a="1" b="2">&lt;&gt;</b>')

    def test_BR(self):
        # empty BR()
        self.assertEqual(BR().xml(), '<br />')
        self.assertEqual(BR(_a='1', _b='2').xml(), '<br a="1" b="2" />')

    def test_HR(self):
        self.assertEqual(HR(_a='1', _b='2').xml(), '<hr a="1" b="2" />')

    def test_A(self):
        self.assertEqual(A('<>', _a='1', _b='2').xml(),
                         '<a a="1" b="2">&lt;&gt;</a>')
        self.assertEqual(A('a', cid='b').xml(),
                         '<a data-w2p_disable_with="default" data-w2p_method="GET" data-w2p_target="b">a</a>')
        self.assertEqual(A('a', callback='b', _id='c').xml(),
                         '<a data-w2p_disable_with="default" data-w2p_method="POST" href="b" id="c">a</a>')
        # Callback with no id trigger web2py_uuid() call
        from html import web2pyHTMLParser
        a = A('a', callback='b').xml()
        for tag in web2pyHTMLParser(a).tree.elements('a'):
            uuid_generated = tag.attributes['_id']
        self.assertEqual(a,
                         '<a data-w2p_disable_with="default" data-w2p_method="POST" href="b" id="{id}">a</a>'.format(id=uuid_generated))
        self.assertEqual(A('a', delete='tr').xml(),
                         '<a data-w2p_disable_with="default" data-w2p_remove="tr">a</a>')
        self.assertEqual(A('a', _id='b', target='<self>').xml(),
                         '<a data-w2p_disable_with="default" data-w2p_target="b" id="b">a</a>')
        self.assertEqual(A('a', component='b').xml(),
                         '<a data-w2p_disable_with="default" data-w2p_method="GET" href="b">a</a>')
        self.assertEqual(A('a', _id='b', callback='c', noconfirm=True).xml(),
                         '<a data-w2p_disable_with="default" data-w2p_method="POST" href="c" id="b">a</a>')
        self.assertEqual(A('a', cid='b').xml(),
                         '<a data-w2p_disable_with="default" data-w2p_method="GET" data-w2p_target="b">a</a>')
        self.assertEqual(A('a', cid='b', _disable_with='processing...').xml(),
                         '<a data-w2p_disable_with="processing..." data-w2p_method="GET" data-w2p_target="b">a</a>')
        self.assertEqual(A('a', callback='b', delete='tr', noconfirm=True, _id='c').xml(),
                         '<a data-w2p_disable_with="default" data-w2p_method="POST" data-w2p_remove="tr" href="b" id="c">a</a>')
        self.assertEqual(A('a', callback='b', delete='tr', confirm='Are you sure?', _id='c').xml(),
                         '<a data-w2p_confirm="Are you sure?" data-w2p_disable_with="default" data-w2p_method="POST" data-w2p_remove="tr" href="b" id="c">a</a>')

    def test_BUTTON(self):
        self.assertEqual(BUTTON('test', _type='button').xml(),
                         '<button type="button">test</button>')

    def test_EM(self):
        self.assertEqual(EM('<>', _a='1', _b='2').xml(),
                         '<em a="1" b="2">&lt;&gt;</em>')

    def test_EMBED(self):
        self.assertEqual(EMBED(_a='1', _b='2').xml(),
                         '<embed a="1" b="2" />')

    def test_TT(self):
        self.assertEqual(TT('<>', _a='1', _b='2').xml(),
                         '<tt a="1" b="2">&lt;&gt;</tt>')

    def test_PRE(self):
        self.assertEqual(PRE('<>', _a='1', _b='2').xml(),
                         '<pre a="1" b="2">&lt;&gt;</pre>')

    def test_CENTER(self):
        self.assertEqual(CENTER('<>', _a='1', _b='2').xml(),
                         '<center a="1" b="2">&lt;&gt;</center>')

    def test_CODE(self):
        self.assertEqual(CODE("print 'hello world'",
                              language='python',
                              link=None,
                              counter=1,
                              styles={},
                              highlight_line=None).xml(),
                         '<table><tr style="vertical-align:top;"><td style="min-width:40px; text-align: right;"><pre style="\n        font-size: 11px;\n        font-family: Bitstream Vera Sans Mono,monospace;\n        background-color: transparent;\n        margin: 0;\n        padding: 5px;\n        border: none;\n        color: #A0A0A0;\n">1.</pre></td><td><pre style="\n        font-size: 11px;\n        font-family: Bitstream Vera Sans Mono,monospace;\n        background-color: transparent;\n        margin: 0;\n        padding: 5px;\n        border: none;\n        overflow: auto;\n        white-space: pre !important;\n"><span style="color:#185369; font-weight: bold">print </span><span style="color: #FF9966">\'hello world\'</span></pre></td></tr></table>')

    def test_LABEL(self):
        self.assertEqual(LABEL('<>', _a='1', _b='2').xml(),
                         '<label a="1" b="2">&lt;&gt;</label>')

    def test_LI(self):
        self.assertEqual(LI('<>', _a='1', _b='2').xml(),
                         '<li a="1" b="2">&lt;&gt;</li>')

    def test_UL(self):
        self.assertEqual(UL('<>', _a='1', _b='2').xml(),
                         '<ul a="1" b="2"><li>&lt;&gt;</li></ul>')

    def test_OL(self):
        self.assertEqual(OL('<>', _a='1', _b='2').xml(),
                         '<ol a="1" b="2"><li>&lt;&gt;</li></ol>')

    def test_TD(self):
        self.assertEqual(TD('<>', _a='1', _b='2').xml(),
                         '<td a="1" b="2">&lt;&gt;</td>')

    def test_TH(self):
        self.assertEqual(TH('<>', _a='1', _b='2').xml(),
                         '<th a="1" b="2">&lt;&gt;</th>')

    def test_TR(self):
        self.assertEqual(TR('<>', _a='1', _b='2').xml(),
                         '<tr a="1" b="2"><td>&lt;&gt;</td></tr>')

    def test_THEAD(self):
        self.assertEqual(THEAD('<>', _a='1', _b='2').xml(),
                         '<thead a="1" b="2"><tr><th>&lt;&gt;</th></tr></thead>')
        # self.assertEqual(THEAD(TRHEAD('<>'), _a='1', _b='2').xml(),
        #                  '<thead a="1" b="2"><tr><th>&lt;&gt;</th></tr></thead>')
        self.assertEqual(THEAD(TR('<>'), _a='1', _b='2').xml(),
                         '<thead a="1" b="2"><tr><td>&lt;&gt;</td></tr></thead>')

    def test_TBODY(self):
        self.assertEqual(TBODY('<>', _a='1', _b='2').xml(),
                         '<tbody a="1" b="2"><tr><td>&lt;&gt;</td></tr></tbody>')

    def test_TFOOT(self):
        self.assertEqual(TFOOT('<>', _a='1', _b='2').xml(),
                         '<tfoot a="1" b="2"><tr><td>&lt;&gt;</td></tr></tfoot>')

    def test_COL(self):
        # Empty COL test
        self.assertEqual(COL().xml(), '<col />')
        # Not Empty COL test
        self.assertEqual(COL(_span='2').xml(), '<col span="2" />')
        # Commented for now not so sure how to make it pass properly was passing locally
        # I think this test is interesting and add value
        # This fail relate to python 2.6 limitation I think
        # Failing COL test
        # with self.assertRaises(SyntaxError) as cm:
        #     COL('<>').xml()
        # self.assertEqual(cm.exception[0], '<col/> tags cannot have components')
        # For now
        self.assertRaises(SyntaxError, COL, '<>')

    def test_COLGROUP(self):
        # Empty COLGROUP test
        self.assertEqual(COLGROUP().xml(), '<colgroup></colgroup>')
        # Not Empty COLGROUP test
        self.assertEqual(COLGROUP('<>', _a='1', _b='2').xml(), '<colgroup a="1" b="2">&lt;&gt;</colgroup>')

    def test_TABLE(self):
        self.assertEqual(TABLE('<>', _a='1', _b='2').xml(),
                         '<table a="1" b="2"><tr><td>&lt;&gt;</td></tr>' +
                         '</table>')

    def test_I(self):
        self.assertEqual(I('<>', _a='1', _b='2').xml(),
                         '<i a="1" b="2">&lt;&gt;</i>')

    def test_IFRAME(self):
        self.assertEqual(IFRAME('<>', _a='1', _b='2').xml(),
                         '<iframe a="1" b="2">&lt;&gt;</iframe>')

    def test_INPUT(self):
        self.assertEqual(INPUT(_a='1', _b='2').xml(), '<input a="1" b="2" type="text" />')
        # list value
        self.assertEqual(INPUT(_value=[1, 2, 3]).xml(), '<input type="text" value="[1, 2, 3]" />')

    def test_TEXTAREA(self):
        self.assertEqual(TEXTAREA('<>', _a='1', _b='2').xml(),
                         '<textarea a="1" b="2" cols="40" rows="10">&lt;&gt;' +
                         '</textarea>')
        # override _rows and _cols
        self.assertEqual(TEXTAREA('<>', _a='1', _b='2', _rows=5, _cols=20).xml(),
                         '<textarea a="1" b="2" cols="20" rows="5">&lt;&gt;' +
                         '</textarea>')
        self.assertEqual(TEXTAREA('<>', value='bla bla bla...', _rows=10, _cols=40).xml(),
                         '<textarea cols="40" rows="10">bla bla bla...</textarea>')

    def test_OPTION(self):
        self.assertEqual(OPTION('<>', _a='1', _b='2').xml(),
                         '<option a="1" b="2" value="&lt;&gt;">&lt;&gt;' +
                         '</option>')

    def test_OBJECT(self):
        self.assertEqual(OBJECT('<>', _a='1', _b='2').xml(),
                         '<object a="1" b="2">&lt;&gt;</object>')

    def test_OPTGROUP(self):
        # Empty OPTGROUP test
        self.assertEqual(OPTGROUP().xml(),
                         '<optgroup></optgroup>')
        # Not Empty OPTGROUP test
        self.assertEqual(OPTGROUP('<>', _a='1', _b='2').xml(),
                         '<optgroup a="1" b="2"><option value="&lt;&gt;">&lt;&gt;</option></optgroup>')
        # With an OPTION
        self.assertEqual(OPTGROUP(OPTION('Option 1', _value='1'), _label='Group 1').xml(),
                         '<optgroup label="Group 1"><option value="1">Option 1</option></optgroup>')

    def test_SELECT(self):
        self.assertEqual(SELECT('<>', _a='1', _b='2').xml(),
                         '<select a="1" b="2">' +
                         '<option value="&lt;&gt;">&lt;&gt;</option></select>')
        self.assertEqual(SELECT(OPTION('option 1', _value='1'),
                                OPTION('option 2', _value='2')).xml(),
                         '<select><option value="1">option 1</option><option value="2">option 2</option></select>')
        self.assertEqual(SELECT(OPTION('option 1', _value='1', _selected='selected'),
                                OPTION('option 2', _value='2'),
                                _multiple='multiple').xml(),
                         '<select multiple="multiple"><option selected="selected" value="1">option 1</option><option value="2">option 2</option></select>')
        # More then one select with mutilple
        self.assertEqual(SELECT(OPTION('option 1', _value='1', _selected='selected'),
                                OPTION('option 2', _value='2', _selected='selected'),
                                _multiple='multiple').xml(),
                         '<select multiple="multiple"><option selected="selected" value="1">option 1</option><option selected="selected" value="2">option 2</option></select>'
                         )
        # OPTGROUP
        self.assertEqual(SELECT(OPTGROUP(OPTION('option 1', _value='1'),
                                         OPTION('option 2', _value='2'),
                                         _label='Group 1',)).xml(),
                         '<select><optgroup label="Group 1"><option value="1">option 1</option><option value="2">option 2</option></optgroup></select>')
        # List
        self.assertEqual(SELECT([1, 2, 3, 4, 5]).xml(),
                         '<select><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5</option></select>')
        # Tuple
        self.assertEqual(SELECT((1, 2, 3, 4, 5)).xml(),
                         '<select><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5</option></select>')
        # String value
        self.assertEqual(SELECT('Option 1', 'Option 2').xml(),
                         '<select><option value="Option 1">Option 1</option><option value="Option 2">Option 2</option></select>')
        # list as a value
        self.assertEqual(SELECT(OPTION('option 1', _value=[1, 2, 3]),
                                OPTION('option 2', _value=[4, 5, 6], _selected='selected'),
                                _multiple='multiple').xml(),
                         '<select multiple="multiple"><option value="[1, 2, 3]">option 1</option><option selected="selected" value="[4, 5, 6]">option 2</option></select>')

    def test_FIELDSET(self):
        self.assertEqual(FIELDSET('<>', _a='1', _b='2').xml(),
                         '<fieldset a="1" b="2">&lt;&gt;</fieldset>')

    def test_LEGEND(self):
        self.assertEqual(LEGEND('<>', _a='1', _b='2').xml(),
                         '<legend a="1" b="2">&lt;&gt;</legend>')

    def test_FORM(self):
        self.assertEqual(FORM('<>', _a='1', _b='2').xml(),
                         '<form a="1" action="#" b="2" enctype="multipart/form-data" method="post">&lt;&gt;</form>')
        # These 2 crash AppVeyor and Travis with: "ImportError: No YAML serializer available"
        # self.assertEqual(FORM('<>', _a='1', _b='2').as_yaml(),
        #                  "accepted: null\nattributes: {_a: '1', _action: '#', _b: '2', _enctype: multipart/form-data, _method: post}\ncomponents: [<>]\nerrors: {}\nlatest: {}\nparent: null\nvars: {}\n")
        # self.assertEqual(FORM('<>', _a='1', _b='2').as_xml(),
        #                  '<?xml version="1.0" encoding="UTF-8"?><document><errors></errors><vars></vars><parent>None</parent><attributes><_enctype>multipart/form-data</_enctype><_action>#</_action><_b>2</_b><_a>1</_a><_method>post</_method></attributes><components><item>&amp;lt;&amp;gt;</item></components><accepted>None</accepted><latest></latest></document>')

    def test_BEAUTIFY(self):
        self.assertEqual(BEAUTIFY(['a', 'b', {'hello': 'world'}]).xml(),
                         '<div><table><tr><td><div>a</div></td></tr><tr><td><div>b</div></td></tr><tr><td><div><table><tr><td style="font-weight:bold;vertical-align:top;">hello</td><td style="vertical-align:top;">:</td><td><div>world</div></td></tr></table></div></td></tr></table></div>')
        # unicode
        self.assertEqual(BEAUTIFY([P(u'àéèûôç'), 'a', 'b', {'hello': 'world'}]).xml(),
                         '<div><table><tr><td><div><p>\xc3\xa0\xc3\xa9\xc3\xa8\xc3\xbb\xc3\xb4\xc3\xa7</p></div></td></tr><tr><td><div>a</div></td></tr><tr><td><div>b</div></td></tr><tr><td><div><table><tr><td style="font-weight:bold;vertical-align:top;">hello</td><td style="vertical-align:top;">:</td><td><div>world</div></td></tr></table></div></td></tr></table></div>')

    def test_MENU(self):
        self.assertEqual(MENU([('Home', False, '/welcome/default/index', [])]).xml(),
                         '<ul class="web2py-menu web2py-menu-vertical"><li class="web2py-menu-first"><a href="/welcome/default/index">Home</a></li></ul>')
        # Multiples entries menu
        self.assertEqual(MENU([('Home', False, '/welcome/default/index', []),
                               ('Item 1', False, '/welcome/default/func_one', []),
                               ('Item 2', False, '/welcome/default/func_two', []),
                               ('Item 3', False, '/welcome/default/func_three', []),
                               ('Item 4', False, '/welcome/default/func_four', [])]).xml(),
                         '<ul class="web2py-menu web2py-menu-vertical"><li class="web2py-menu-first"><a href="/welcome/default/index">Home</a></li><li><a href="/welcome/default/func_one">Item 1</a></li><li><a href="/welcome/default/func_two">Item 2</a></li><li><a href="/welcome/default/func_three">Item 3</a></li><li class="web2py-menu-last"><a href="/welcome/default/func_four">Item 4</a></li></ul>'
                         )
        # mobile=True
        self.assertEqual(MENU([('Home', False, '/welcome/default/index', [])], mobile=True).xml(),
                         '<select class="web2py-menu web2py-menu-vertical" onchange="window.location=this.value"><option value="/welcome/default/index">Home</option></select>')
        # Multiples entries menu for mobile
        self.assertEqual(MENU([('Home', False, '/welcome/default/index', []),
                               ('Item 1', False, '/welcome/default/func_one', []),
                               ('Item 2', False, '/welcome/default/func_two', []),
                               ('Item 3', False, '/welcome/default/func_three', []),
                               ('Item 4', False, '/welcome/default/func_four', [])], mobile=True).xml(),
                         '<select class="web2py-menu web2py-menu-vertical" onchange="window.location=this.value"><option value="/welcome/default/index">Home</option><option value="/welcome/default/func_one">Item 1</option><option value="/welcome/default/func_two">Item 2</option><option value="/welcome/default/func_three">Item 3</option><option value="/welcome/default/func_four">Item 4</option></select>')

    # TODO: def test_embed64(self):

    # TODO: def test_web2pyHTMLParser(self):

    # TODO: def test_markdown_serializer(self):

    # TODO: def test_markmin_serializer(self):

    def test_MARKMIN(self):
        # This test pass with python 2.7 but expected to fail under 2.6
        # with self.assertRaises(TypeError) as cm:
        #     MARKMIN().xml()
        # self.assertEqual(cm.exception[0], '__init__() takes at least 2 arguments (1 given)')
        # For now
        self.assertRaises(TypeError, MARKMIN)
        self.assertEqual(MARKMIN('').xml(), '')
        self.assertEqual(MARKMIN('<>').xml(),
                         '<p>&lt;&gt;</p>')
        self.assertEqual(MARKMIN("``hello_world = 'Hello World!'``:python").xml(),
                         '<code class="python">hello_world = \'Hello World!\'</code>')
        self.assertEqual(MARKMIN('<>').flatten(), '<>')

    def test_ASSIGNJS(self):
        # empty assignation
        self.assertEqual(ASSIGNJS().xml(), '')
        # text assignation
        self.assertEqual(ASSIGNJS(var1='1', var2='2').xml(), 'var var1 = "1";\nvar var2 = "2";\n')
        # int assignation
        self.assertEqual(ASSIGNJS(var1=1, var2=2).xml(), 'var var1 = 1;\nvar var2 = 2;\n')


class TestData(unittest.TestCase):

    def test_Adata(self):
        self.assertEqual(A('<>', data=dict(abc='<def?asd>', cde='standard'), _a='1', _b='2').xml(),
                         '<a a="1" b="2" data-abc="&lt;def?asd&gt;" data-cde="standard">&lt;&gt;</a>')


if __name__ == '__main__':
    unittest.main()
