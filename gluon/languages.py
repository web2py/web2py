#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""

import os
import re
import cgi
import portalocker
import logging
import marshal
import copy_reg
from fileutils import listdir
import settings
from cfs import getcfs

__all__ = ['translator', 'findT', 'update_all_languages']

is_gae = settings.global_settings.web2py_runtime_gae

# pattern to find T(blah blah blah) expressions

PY_STRING_LITERAL_RE = r'(?<=[^\w]T\()(?P<name>'\
     + r"[uU]?[rR]?(?:'''(?:[^']|'{1,2}(?!'))*''')|"\
     + r"(?:'(?:[^'\\]|\\.)*')|" + r'(?:"""(?:[^"]|"{1,2}(?!"))*""")|'\
     + r'(?:"(?:[^"\\]|\\.)*"))'

regex_translate = re.compile(PY_STRING_LITERAL_RE, re.DOTALL)

# patter for a valid accept_language

regex_language = \
    re.compile('^[a-zA-Z]{2}(\-[a-zA-Z]{2})?(\-[a-zA-Z]+)?$')


def read_dict_aux(filename):
    fp = portalocker.LockedFile(filename, 'r')
    lang_text = fp.read().replace('\r\n', '\n')
    fp.close()
    if not lang_text.strip():
        return {}
    try:
        return eval(lang_text)
    except:
        logging.error('Syntax error in %s' % filename)
        return {}

def read_dict(filename):    
    return getcfs('language:%s'%filename,filename,
                  lambda filename=filename:read_dict_aux(filename))

def utf8_repr(s):
    r''' # note that we use raw strings to avoid having to use double back slashes below

    utf8_repr() works same as repr() when processing ascii string
    >>> utf8_repr('abc') == utf8_repr("abc") == repr('abc') == repr("abc") == "'abc'"
    True
    >>> utf8_repr('a"b"c') == repr('a"b"c') == '\'a"b"c\''
    True
    >>> utf8_repr("a'b'c") == repr("a'b'c") == '"a\'b\'c"'
    True
    >>> utf8_repr('a\'b"c') == repr('a\'b"c') == utf8_repr("a'b\"c") == repr("a'b\"c") == '\'a\\\'b"c\''
    True
    >>> utf8_repr('a\r\nb') == repr('a\r\nb') == "'a\\r\\nb'" # Test for \r, \n
    True

    Unlike repr(), utf8_repr() remains utf8 content when processing utf8 string
    >>> utf8_repr('中文字') == utf8_repr("中文字") == "'中文字'" != repr('中文字')
    True
    >>> utf8_repr('中"文"字') == "'中\"文\"字'" != repr('中"文"字')
    True
    >>> utf8_repr("中'文'字") == '"中\'文\'字"' != repr("中'文'字")
    True
    >>> utf8_repr('中\'文"字') == utf8_repr("中'文\"字") == '\'中\\\'文"字\'' != repr('中\'文"字') == repr("中'文\"字")
    True
    >>> utf8_repr('中\r\n文') == "'中\\r\\n文'" != repr('中\r\n文') # Test for \r, \n
    True
    '''
    if (s.find("'") >= 0) and (s.find('"') < 0): # only single quote exists
        s = ''.join(['"', s, '"']) # s = ''.join(['"', s.replace('"','\\"'), '"'])
    else:
        s = ''.join(["'", s.replace("'","\\'"), "'"])
    return s.replace("\n","\\n").replace("\r","\\r")


def write_dict(filename, contents):
    try:
        fp = portalocker.LockedFile(filename, 'w')
    except (IOError, OSError):
        if not is_gae:
            logging.warning('Unable to write to file %s' % filename)
        return
    fp.write('# coding: utf8\n{\n')
    for key in sorted(contents):
        fp.write('%s: %s,\n' % (utf8_repr(key), utf8_repr(contents[key])))
    fp.write('}\n')
    fp.close()


class lazyT(object):

    """
    never to be called explicitly, returned by translator.__call__
    """

    m = None
    s = None
    T = None

    def __init__(
        self,
        message,
        symbols = {},
        T = None,
        ):
        self.m = message
        self.s = symbols
        self.T = T

    def __repr__(self):
        return "<lazyT %s>" % (repr(str(self.m)), )

    def __str__(self):
        return self.T.translate(self.m, self.s)

    def __eq__(self, other):
        return self.T.translate(self.m, self.s) == other

    def __ne__(self, other):
        return self.T.translate(self.m, self.s) != other

    def __add__(self, other):
        return '%s%s' % (self, other)

    def __radd__(self, other):
        return '%s%s' % (other, self)

    def __cmp__(self,other):
        return cmp(str(self),str(other))

    def __hash__(self):
        return hash(str(self))

    def __getattr__(self, name):
        return getattr(str(self),name)

    def __getitem__(self, i):
        return str(self)[i]

    def __getslice__(self, i, j):
        return str(self)[i:j]

    def __iter__(self):
        for c in str(self): yield c

    def __len__(self):
        return len(str(self))

    def xml(self):
        return cgi.escape(str(self))

    def encode(self, *a, **b):
        return str(self).encode(*a, **b)

    def decode(self, *a, **b):
        return str(self).decode(*a, **b)

    def read(self):
        return str(self)

    def __mod__(self, symbols):
        return self.T.translate(self.m, symbols)


class translator(object):

    """
    this class is instantiated by gluon.compileapp.build_environment
    as the T object

    ::

        T.force(None) # turns off translation
        T.force('fr, it') # forces web2py to translate using fr.py or it.py

        T(\"Hello World\") # translates \"Hello World\" using the selected file

    notice 1: there is no need to force since, by default, T uses
    accept_language to determine a translation file.

    notice 2: en and en-en are considered different languages!
    """

    def __init__(self, request):
        self.request = request
        self.folder = request.folder
        self.current_languages = ['en']
        self.accepted_language = None
        self.language_file = None
        self.http_accept_language = request.env.http_accept_language
        self.requested_languages = self.force(self.http_accept_language)
        self.lazy = True
        self.otherTs = {}

    def get_possible_languages(self):
        possible_languages = [lang for lang in self.current_languages]
        file_ending = re.compile("\.py$")
        for langfile in os.listdir(os.path.join(self.folder,'languages')):
            if file_ending.search(langfile):
                possible_languages.append(file_ending.sub('',langfile))
        return possible_languages

    def set_current_languages(self, *languages):
        if len(languages) == 1 and isinstance(languages[0], (tuple, list)):
            languages = languages[0]
        self.current_languages = languages
        self.force(self.http_accept_language)

    def force(self, *languages):
        if not languages or languages[0] is None:
            languages = []
        if len(languages) == 1 and isinstance(languages[0], (str, unicode)):
            languages = languages[0]
        if languages:
            if isinstance(languages, (str, unicode)):
                accept_languages = languages.split(';')
                languages = []
                [languages.extend(al.split(',')) for al in accept_languages]
                languages = [item.strip().lower() for item in languages \
                                 if regex_language.match(item.strip())]

            for language in languages:
                if language in self.current_languages:
                    self.accepted_language = language
                    break
                filename = os.path.join(self.folder, 'languages/', language + '.py')
                if os.path.exists(filename):
                    self.accepted_language = language
                    self.language_file = filename
                    self.t = read_dict(filename)
                    return languages
        self.language_file = None
        self.t = {}  # ## no language by default
        return languages

    def __call__(self, message, symbols={}, language=None, lazy=None):
        if lazy is None:
            lazy = self.lazy
        if not language:
            if lazy:
                return lazyT(message, symbols, self)
            else:
                return self.translate(message, symbols)
        else:
            try:
                otherT = self.otherTs[language]
            except KeyError:
                otherT = self.otherTs[language] = translator(self.request)
                otherT.force(language)
            return otherT(message, symbols, lazy=lazy)

    def translate(self, message, symbols):
        """
        user ## to add a comment into a translation string
        the comment can be useful do discriminate different possible
        translations for the same string (for example different locations)

        T(' hello world ') -> ' hello world '
        T(' hello world ## token') -> 'hello world'
        T('hello ## world ## token') -> 'hello ## world'

        the ## notation is ignored in multiline strings and strings that
        start with ##. this is to allow markmin syntax to be translated
        """
        #for some reason languages.py gets executed before gaehandler.py
        # is able to set web2py_runtime_gae, so re-check here
        is_gae = settings.global_settings.web2py_runtime_gae
        if not message.startswith('#') and not '\n' in message:
            tokens = message.rsplit('##', 1)
        else:
            # this allows markmin syntax in translations
            tokens = [message]
        if len(tokens) == 2:
            tokens[0] = tokens[0].strip()
            message = tokens[0] + '##' + tokens[1].strip()
        mt = self.t.get(message, None)
        if mt is None:
            self.t[message] = mt = tokens[0]
            if self.language_file and not is_gae:
                write_dict(self.language_file, self.t)
        if symbols or symbols == 0:
            return mt % symbols
        return mt


def findT(path, language='en-us'):
    """
    must be run by the admin app
    """
    filename = os.path.join(path, 'languages', '%s.py' % language)
    sentences = read_dict(filename)
    mp = os.path.join(path, 'models')
    cp = os.path.join(path, 'controllers')
    vp = os.path.join(path, 'views')
    for file in listdir(mp, '.+\.py', 0) + listdir(cp, '.+\.py', 0)\
         + listdir(vp, '.+\.html', 0):
        fp = portalocker.LockedFile(file, 'r')
        data = fp.read()
        fp.close()
        items = regex_translate.findall(data)
        for item in items:
            try:
                message = eval(item)
                if not message.startswith('#') and not '\n' in message:
                    tokens = message.rsplit('##', 1)
                else:
                    # this allows markmin syntax in translations
                    tokens = [message]
                if len(tokens) == 2:
                    message = tokens[0].strip() + '##' + tokens[1].strip()
                if message and not message in sentences:
                    sentences[message] = message
            except:
                pass
    write_dict(filename, sentences)

### important to allow safe session.flash=T(....)
def lazyT_unpickle(data):
    return marshal.loads(data)
def lazyT_pickle(data):
    return lazyT_unpickle, (marshal.dumps(str(data)),)
copy_reg.pickle(lazyT, lazyT_pickle, lazyT_unpickle)

def update_all_languages(application_path):
    path = os.path.join(application_path, 'languages/')
    for language in listdir(path, '^\w+(\-\w+)?\.py$'):
        findT(application_path, language[:-3])


if __name__ == '__main__':
    import doctest
    doctest.testmod()





