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
from thread import allocate_lock
from html import XML, xmlescape

__all__ = ['translator', 'findT', 'update_all_languages']

is_gae = settings.global_settings.web2py_runtime_gae

# pattern to find T(blah blah blah) expressions

PY_STRING_LITERAL_RE = r'(?<=[^\w]T\()(?P<name>'\
     + r"[uU]?[rR]?(?:'''(?:[^']|'{1,2}(?!'))*''')|"\
     + r"(?:'(?:[^'\\]|\\.)*')|" + r'(?:"""(?:[^"]|"{1,2}(?!"))*""")|'\
     + r'(?:"(?:[^"\\]|\\.)*"))'

regex_translate = re.compile(PY_STRING_LITERAL_RE, re.DOTALL)
regex_param=re.compile(r'(?P<b>(?<!\\)(?:\\\\)*){(?P<s>.+?(?<!\\)(?:\\\\)*)}')

# patter for a valid accept_language

regex_language = \
    re.compile('^([a-zA-Z]{2})(\-[a-zA-Z]{2})?(\-[a-zA-Z]+)?$')
regex_langfile = re.compile('^[a-zA-Z]{2}(-[a-zA-Z]{2})?\.py$')
regex_langinfo = re.compile("^[^'\"]*['\"]([^'\"]*)['\"]\s*:\s*['\"]([^'\"]*)['\"].*$")

# cache of translated messages:
# of structure:
# { 'languages/xx.py':
#     ( {"def-message": "xx-message",
#        ...
#        "def-message": "xx-message"}, lock_object )
#  'languages/yy.py': ( {dict}, lock_object )
#  ...
# }
tcache={}

def get_from_cache(cache, val, fun):
    lock=cache[1]
    lock.acquire()
    try:
        result=cache[0].get(val);
    finally:
        lock.release()
    if result:
        return result
    lock.acquire()
    try:
        result=cache[0].setdefault(val, fun())
    finally:
        lock.release()
    return result

def clear_cache(cache):
    cache[1].acquire()
    try:
        cache[0].clear();
    finally:
        cache[1].release()


def lang_sampling(lang_tuple, langlist):
    """ search lang_tuple in langlist
    Args:
        lang_tuple (tuple of strings): ('aa'[[,'-bb'],'-cc'])
        langlist   (list of strings): [available languages]
    Returns:
        language from langlist or None
    """
    # step 1:
    # compare "aa-bb-cc" | "aa-bb" | "aa" from lang_tuple
    # with strings from langlist. Return appropriate string
    # from langlist:
    tries = range(len(lang_tuple),0,-1)
    for i in tries:
        language="".join(lang_tuple[:i])
        if language in langlist:
            return language
    # step 2 (if not found in step 1):
    # compare "aa-bb-cc" | "aa-bb" | "aa" from lang_tuple
    # with left part of a string from langlist. Return
    # appropriate string from langlist
    for i in tries:
        lang="".join(lang_tuple[:i])
        for language in langlist:
            if language.startswith(lang):
                return language
    return None


def read_dict_aux(filename):
    fp = portalocker.LockedFile(filename, 'r')
    lang_text = fp.read().replace('\r\n', '\n')
    fp.close()
    # clear cache of translated messages:
    clear_cache(tcache.setdefault(filename, ({}, allocate_lock())))
    clear_cache(tcache.setdefault('@'+filename, ({}, allocate_lock())))
    if not lang_text.strip():
        return {}
    try:
        return eval(lang_text)
    except:
        logging.error('Syntax error in %s' % filename)
        return {'__corrupted__':True}

def read_dict(filename):
    """ return dictionary with translation messages
    """
    return getcfs('lang:'+filename, filename,
                lambda:read_dict_aux(filename))


def get_lang_info(lang, langdir):
    """retrieve lang information from *langdir*/*lang*.py file.
       Read few strings from lang.py file until keys !langname!,
       !langcode! or keys greater then '!*' were found

    args:
        lang (str): lang-code or 'default'
        langdir (str): path to 'languages' directory in web2py app dir

    returns:
        tuple(langcode, langname, langfile_mtime)
        e.g.: ('en', 'English', 1338549043.0)
    """
    filename = os.path.join(langdir, lang+'.py')
    langcode=''
    langname=''
    f = portalocker.LockedFile(filename, 'r')
    try:
        while not (langcode and langname):
            line = f.readline()
            if not line:
               break
            match=regex_langinfo.match(line)
            if match:
                if match.group(1) == '!langname!':
                    langname=match.group(2)
                elif match.group(1) == '!langcode!':
                    langcode=match.group(2)
                elif match.group(1)[0] > '!':
                    break
    finally:
        f.close()
    if not langcode:
        langcode = lang if lang != 'default' else 'en'
    return langcode, langname or langcode, os.stat(filename).st_mtime

def read_possible_languages_aux(langdir, item=None):
    if not item: item = {}
    langs = {}
    # scan languages directory for langfiles:
    for langfile in (listdir(langdir, regex_langfile) +
                            listdir(langdir, '^default\.py$')):
        lang=langfile[:-3]
        if (lang in item and item[lang][2] ==
                   os.stat(os.path.join(langdir, langfile)).st_mtime):
            # if langfile's mtime wasn't changed - use previous value:
            langs[lang]=item[lang]
        else:
            # otherwise, reread langfile:
            langs[lang]=get_lang_info(lang, langdir)
    if 'default' not in langs:
        # if default.py is not found, add default value:
        langs['default'] = ('en', 'English', 0)
    deflang=langs['default']
    if deflang[0] not in langs:
        # create language from default.py:
        langs[deflang[0]] = (deflang[0], deflang[1], 0)
    return langs

def read_possible_languages(path):
    lang_path = os.path.join(path, 'languages')
    return getcfs('langs:'+path.rstrip(os.path.sep), lang_path,
                   lambda: read_possible_languages_aux(lang_path))

def utf8_repr(s):
    r""" 
    
    # note that we use raw strings to avoid having to use double back slashes below

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
    """
    if (s.find("'") >= 0) and (s.find('"') < 0): # only single quote exists
        s = ''.join(['"', s, '"']) # s = ''.join(['"', s.replace('"','\\"'), '"'])
    else:
        s = ''.join(["'", s.replace("'","\\'"), "'"])
    return s.replace("\n","\\n").replace("\r","\\r")


def write_dict(filename, contents):
    if contents.get('__corrupted__',False):
        return
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
    m = s = T = None

    def __init__(self, message, symbols = {}, T = None, filter=None):
        self.m, self.s, self.T, self.f = message, symbols, T, filter

    def __repr__(self):
        return "<lazyT %s>" % (repr(str(self.m)), )

    def __str__(self):
        return self.T.translate(self.m, self.s, self.f)

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
        return self.T.translate(self.m, symbols, filter=self.f)


class translator(object):

    """
    this class is instantiated by gluon.compileapp.build_environment
    as the T object

        T.force(None) # turns off translation
        T.force('fr, it') # forces web2py to translate using fr.py or it.py

        T(\"Hello World\") # translates \"Hello World\" using the selected file

    notice 1: there is no need to force since, by default, T uses
    http_accept_language to determine a translation file.

    notice 2: en and en-en are considered different languages!

    notice 3: if language xx-yy is not found force() probes other similar
    languages using such algorithm: xx-yy.py -> xx.py -> xx-yy*.py -> xx*.py
    """

    def __init__(self, request):
        global tcache
        self.request = request
        self.folder = request.folder
        default = os.path.join(self.folder,'languages','default.py')
        if os.path.exists(default):
            self.default_language_file = default
            self.default_t = read_dict(default)
        else: # languages/default.py is not found
            self.default_language_file = os.path.join(self.folder,'languages','')
            self.default_t = {}
        self.cache = tcache.setdefault(self.default_language_file, ({}, allocate_lock()))
        self.current_languages = [self.get_possible_languages_info('default')[0]]
        self.accepted_language = None # filed in self.force()
        self.language_file = None # filed in self.force()
        self.http_accept_language = request.env.http_accept_language
        self.requested_languages = self.force(self.http_accept_language)
        self.lazy = True
        self.otherTs = {}

    def get_possible_languages_info(self, lang=None):
        """
        returns info for selected language or dictionary with all
            possible languages info from APP/languages/*.py
        args:
            *lang* (str): language
        returns:
            if *lang* is defined:
               return tuple(langcode, langname, langfile_mtime) or None

            if *lang* is NOT defined:
               returns dictionary with all possible languages:
            { langcode(from filename): ( langcode(from !langcode! key),
                                         langname(from !langname! key),
                                         langfile_mtime ) }
        """
        if lang:
            return read_possible_languages(self.folder).get(lang)
        return read_possible_languages(self.folder)

    def get_possible_languages(self):
        """ get list of all possible languages for current applications """
        return sorted( set(lang for lang in
                           read_possible_languages(self.folder).iterkeys()
                           if lang != 'default')
                     | set(self.current_languages))

    def set_current_languages(self, *languages):
        """
        set current AKA "default" languages
        setting one of this languages makes force() function
        turn translation off to use default language
        """
        if len(languages) == 1 and isinstance(languages[0], (tuple, list)):
            languages = languages[0]
        self.current_languages = languages
        self.force(self.http_accept_language)

    def force(self, *languages):
        """

        select language(s) for translation

        if a list of languages is passed as a parameter,
        first language from this list that matches the ones
        from the possible_languages dictionary will be
        selected
        
        default language will be selected if none
        of them matches possible_languages.
        """
        global tcache
        if not languages or languages[0] is None:
            languages = []
        if len(languages) == 1 and isinstance(languages[0], (str, unicode)):
            languages = languages[0]

        if languages:
            if isinstance(languages, (str, unicode)):
                parts = languages.split(';')
                languages = []
                for al in parts:
                    languages.extend(al.split(','))

            possible_languages = self.get_possible_languages()
            for language in languages:
                match_language = regex_language.match(language.strip().lower())
                if match_language:
                    match_language = tuple(part
                                           for part in match_language.groups()
                                           if part)
                    language = lang_sampling(match_language,
                                             self.current_languages)
                    if language:
                        self.accepted_language = language
                        break
                    language = lang_sampling(match_language, possible_languages)
                    if language:
                        self.language_file = os.path.join(self.folder,
                                                           'languages',
                                                           language + '.py')
                        if os.path.exists(self.language_file):
                            self.t = read_dict(self.language_file)
                            self.accepted_language = language
                            self.cache = tcache.setdefault(
                                self.language_file, ({},allocate_lock()))
                            return languages
        self.language_file = self.default_language_file
        self.cache = tcache[self.language_file]
        self.t = self.default_t
        return languages

    def __call__(self, message, symbols={}, language=None, lazy=None, filter=None):
        """
        get cached translated plain text message with inserted parameters(symbols)
        if lazy==True lazyT object is returned
        """
        lazy = lazy or self.lazy
        if not language and lazy:
            return lazyT(message, symbols, self, filter=filter)
        elif not language:
            return self.translate(message, symbols, filter=filter)
        elif language in self.otherTs:
            otherT = self.otherTs[language]
        else:
            otherT = self.otherTs[language] = translator(self.request)
            otherT.force(language)
        return otherT(message, symbols, lazy=lazy, filter=filter)


    def get_t(self, message, filter=None, startwith_templ='##'):
        """
        user ## to add a comment into a translation string
        the comment can be useful do discriminate different possible
        translations for the same string (for example different locations)

        T(' hello world ') -> ' hello world '
        T(' hello world ## token') -> ' hello world '
        T('hello ## world## token') -> 'hello ## world'

        the ## notation is ignored in multiline strings and strings that
        start with ##. this is to allow markmin syntax to be translated
        """
        mt = self.t.get(message, None)
        if mt is None:
            if not message.startswith(startwith_templ) and not '\n' in message:
                tokens = message.rsplit('##', 1)
            else:
                # this allows markmin syntax in translations
                tokens = [message]
            self.t[message] = mt = self.default_t.get(message, tokens[0])
            if (self.language_file != self.default_language_file and not is_gae):
                write_dict(self.language_file, self.t)
        if filter:
            mt = filter(mt)
        return mt

    def params_substitution(self, message, symbols):
        """
        substitute parameters from symbols into message using %.
        also parse %%{} placeholders for plural-forms processing.
        returns: string with parameters
        """
        return message % symbols

    def translate(self, message, symbols, filter=None):
        """
        get cached translated message with inserted parameters(symbols)
        """
        message = get_from_cache(self.cache, (message, filter), 
                                 lambda: self.get_t(message,filter))
        if symbols or symbols == 0 or symbols == "":
            return self.params_substitution(message, symbols)        
        return message

def findT(path, language='en'):
    """
    must be run by the admin app
    """
    filename = os.path.join(path, 'languages', language +'.py')
    sentences = read_dict(filename)
    mp = os.path.join(path, 'models')
    cp = os.path.join(path, 'controllers')
    vp = os.path.join(path, 'views')
    mop = os.path.join(path, 'modules')
    for file in listdir(mp, '^.+\.py$', 0) + listdir(cp, '^.+\.py$', 0)\
         + listdir(vp, '^.+\.html$', 0) + listdir(mop, '^.+\.py$', 0):
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
    if not '!langcode!' in sentences:
        sentences['!langcode!'] = (
            'en' if language in ('default', 'en') else language)
    if not '!langname!' in sentences:
        sentences['!langname!'] = (
            'English' if language in ('default', 'en') else sentences['!langcode!'])
    write_dict(filename, sentences)

### important to allow safe session.flash=T(....)
def lazyT_unpickle(data):
    return marshal.loads(data)
def lazyT_pickle(data):
    return lazyT_unpickle, (marshal.dumps(str(data)),)
copy_reg.pickle(lazyT, lazyT_pickle, lazyT_unpickle)


def update_all_languages(application_path):
    path = os.path.join(application_path, 'languages/')
    for language in listdir(path, regex_langfile):
        findT(application_path, language[:-3])


if __name__ == '__main__':
    import doctest
    doctest.testmod()

