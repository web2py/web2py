#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Plural subsystem is created by Vladyslav Kozlovskyy (Ukraine)
                               <dbdevelop@gmail.com>
"""

import os
import re
import pkgutil
from utf8 import Utf8
from cgi import escape
import portalocker
import logging
import marshal
import copy_reg
from fileutils import listdir
import settings
from cfs import getcfs
from thread import allocate_lock
from html import XML, xmlescape
from contrib.markmin.markmin2html import render, markmin_escape
from string import maketrans

__all__ = ['translator', 'findT', 'update_all_languages']

ospath = os.path
ostat = os.stat
osep = os.sep
pjoin = os.path.join
pdirname = os.path.dirname
isdir = os.path.isdir
is_gae = settings.global_settings.web2py_runtime_gae

DEFAULT_LANGUAGE = 'en'

# DEFAULT PLURAL-FORMS RULES:
# language doesn't use plural forms
DEFAULT_NPLURALS = 1
# only one singular/plural form is used
DEFAULT_GET_PLURAL_ID = lambda n: 0
# word is unchangeable
DEFAULT_CONSTRUCTOR_PLURAL_FORM = lambda word, plural_id: word

def safe_eval(text):
    if text.strip():
        try:
            import ast
            return ast.literal_eval(text)
        except ImportError:
            return eval(text,{},{})
    return None

# used as default filter in translator.M()
def markmin_aux(m):
    return '{%s}' % markmin_escape(m.group('s'))
def markmin(s):
    return render(regex_param.sub(markmin_aux,s),
                  sep='br', autolinks=None, id_prefix='')

NUMBERS = (int,long,float)

# pattern to find T(blah blah blah) expressions
PY_STRING_LITERAL_RE = r'(?<=[^\w]T\()(?P<name>'\
     + r"[uU]?[rR]?(?:'''(?:[^']|'{1,2}(?!'))*''')|"\
     + r"(?:'(?:[^'\\]|\\.)*')|" + r'(?:"""(?:[^"]|"{1,2}(?!"))*""")|'\
     + r'(?:"(?:[^"\\]|\\.)*"))'

regex_translate = re.compile(PY_STRING_LITERAL_RE, re.DOTALL)
regex_param=re.compile(r'{(?P<s>.+?)}')

# pattern for a valid accept_language

regex_language = \
    re.compile('^([a-zA-Z]{2})(\-[a-zA-Z]{2})?(\-[a-zA-Z]+)?$')
regex_langfile = re.compile('^[a-zA-Z]{2}(-[a-zA-Z]{2})?\.py$')
regex_backslash = re.compile(r"\\([\\{}%])")
regex_plural = re.compile('%({.+?})')
regex_plural_dict = re.compile('^{(?P<w>[^()[\]][^()[\]]*?)\((?P<n>[^()\[\]]+)\)}$')  # %%{word(varname or number)}
regex_plural_tuple = re.compile('^{(?P<w>[^[\]()]+)(?:\[(?P<i>\d+)\])?}$') # %%{word[index]} or %%{word}

# UTF8 helper functions
def upper_fun(s):
    return unicode(s,'utf-8').upper().encode('utf-8')
def title_fun(s):
    return unicode(s,'utf-8').title().encode('utf-8')
def cap_fun(s):
    return lambda s: unicode(s,'utf-8').capitalize().encode('utf-8')
ttab_in  = maketrans("\\%{}", '\x1c\x1d\x1e\x1f')
ttab_out = maketrans('\x1c\x1d\x1e\x1f', "\\%{}")

# cache of translated messages:
# global_language_cache:
# { 'languages/xx.py':
#     ( {"def-message": "xx-message",
#        ...
#        "def-message": "xx-message"}, lock_object )
#  'languages/yy.py': ( {dict}, lock_object )
#  ...
# }

global_language_cache={}

def get_from_cache(cache, val, fun):
    lang_dict, lock = cache
    lock.acquire()
    try:
        result = lang_dict.get(val);
    finally:
        lock.release()
    if result:
        return result
    lock.acquire()
    try:
        result = lang_dict.setdefault(val, fun())
    finally:
        lock.release()
    return result

def clear_cache(filename):
    cache = global_language_cache.setdefault(
        filename, ({}, allocate_lock()))
    lang_dict, lock = cache
    lock.acquire()
    try:
        lang_dict.clear();
    finally:
        lock.release()

def lang_sampling(lang_tuple, langlist):
    """
    search *lang_tuple* in *langlist*

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
    lang_text = portalocker.read_locked(filename).replace('\r\n', '\n')
    clear_cache(filename)
    try:
        return safe_eval(lang_text) or {}
    except Exception, e:
        status = 'Syntax error in %s (%s)' % (filename, e)
        logging.error(status)
        return {'__corrupted__':status}

def read_dict(filename):
    """
    return dictionary with translation messages
    """
    return getcfs('lang:'+filename, filename,
                lambda: read_dict_aux(filename))


def get_lang_info(lang, langdir):
    """
    retrieve lang information from *langdir*/*lang*.py file.
    Read few strings from lang.py file until keys !langname!,
    !langcode! or keys greater then '!*' were found

    args:
        lang (str): lang-code or 'default'
        langdir (str): path to 'languages' directory in web2py app dir

    returns:
        tuple(langcode, langname, langfile_mtime)
        e.g.: ('en', 'English', 1338549043.0)
    """
    filename = ospath.join(langdir, lang+'.py')
    d = read_dict(filename)    
    langcode = d.get('!langcode!',DEFAULT_LANGUAGE)
    langname = d.get('!langname!',langcode)
    return (langcode, langname or langcode, ostat(filename).st_mtime)

def read_possible_languages(appdir):
    langs = {}
    # scan languages directory for langfiles:
    langdir = ospath.join(appdir,'languages')
    for filename in os.listdir(langdir):
        if regex_langfile.match(filename) or filename=='default.py':
            lang = filename[:-3]
            langs[lang] = get_lang_info(lang, langdir)
    if not 'en' in langs:
        # if default.py is not found, add default value:
        langs['en'] = ('en', 'English', 0)
    return langs

def read_possible_plurals():
    """
    create list of all possible plural rules files
    result is cached to increase speed
    """
    try:
        import gluon.contrib.plural_rules as package
        plurals = {}
        for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
            if len(modname)==2:
                module = __import__(package.__name__+'.'+modname)
                lang = modname
                pname = modname+'.py'
                nplurals = getattr(module,'nplurals', DEFAULT_NPLURALS)
                get_plural_id = getattr(
                    module,'get_plural_id', 
                    DEFAULT_GET_PLURAL_ID)
                construct_plural_form = getattr(
                    module,'construct_plural_form',
                    DEFAULT_CONSTRUCTOR_PLURAL_FORM)
                plurals[lang] = (lang, nplurals, get_plural_id,
                                 construct_plural_form, pname)
    except ImportError:
        logging.warn('Unable to import plural rules')
    plurals['default'] = ('default',
                          DEFAULT_NPLURALS,
                          DEFAULT_GET_PLURAL_ID,
                          DEFAULT_CONSTRUCTOR_PLURAL_FORM,
                          None)
    return plurals

PLURAL_RULES = read_possible_plurals()

def read_plural_dict_aux(filename):
    lang_text = portalocker.read_locked(filename).replace('\r\n', '\n')
    try:
        return eval(lang_text) or {}
    except Exception, e:
        status='Syntax error in %s (%s)' % (filename, e)
        logging.error(status)
        return {'__corrupted__':status}

def read_plural_dict(filename):
    return getcfs('plurals:'+filename, filename,
                      lambda: read_plural_dict_aux(filename))

def write_plural_dict(filename, contents):
    if '__corrupted__' in contents:
        return
    try:
        fp = portalocker.LockedFile(filename, 'w')
        fp.write('#!/usr/bin/env python\n{\n# "singular form (0)": ["first plural form (1)", "second plural form (2)", ...],\n')
        # coding: utf8\n{\n')
        for key in sorted(contents,lambda x,y: cmp(unicode(x,'utf-8').lower(), unicode(y,'utf-8').lower())):
            forms = '['+','.join([repr(Utf8(form)) for form in contents[key]])+']'
            fp.write('%s: %s,\n' % (repr(Utf8(key)), forms))
        fp.write('}\n')
    except (IOError, OSError):
        if not is_gae:
            logging.warning('Unable to write to file %s' % filename)
        return
    finally:
        fp.close()


def write_dict(filename, contents):
    if '__corrupted__' in contents:
        return
    try:
        fp = portalocker.LockedFile(filename, 'w')
    except (IOError, OSError):
        if not settings.global_settings.web2py_runtime_gae:
            logging.warning('Unable to write to file %s' % filename)
        return
    fp.write('# coding: utf8\n{\n')
    for key in sorted(contents,lambda x,y: cmp(unicode(x,'utf-8').lower(), unicode(y,'utf-8').lower())):
        fp.write('%s: %s,\n' % (repr(Utf8(key)), repr(Utf8(contents[key]))))
    fp.write('}\n')
    fp.close()



class lazyT(object):
    """
    never to be called explicitly, returned by
    translator.__call__() or translator.M()
    """
    m = s = T = f = t = None
    M = is_copy = False

    def __init__(
        self,
        message,
        symbols = {},
        T = None,
        filter = None,
        ftag = None,
        M = False
        ):
        if isinstance(message, lazyT):
            self.m = message.m
            self.s = message.s
            self.T = message.T
            self.f = message.f
            self.t = message.t
            self.M = message.M
            self.is_copy = True
        else:
            self.m = message
            self.s = symbols
            self.T = T
            self.f = filter
            self.t = ftag
            self.M = M
            self.is_copy = False

    def __repr__(self):
        return "<lazyT %s>" % (repr(Utf8(self.m)), )

    def __str__(self):
        return str(self.T.apply_filter(self.m, self.s, self.f, self.t) if self.M else
                   self.T.translate(self.m, self.s))

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return str(self) != str(other)

    def __add__(self, other):
        return '%s%s' % (self, other)

    def __radd__(self, other):
        return '%s%s' % (other, self)

    def __mul__(self, other):
        return str(self) * other

    def __cmp__(self,other):
        return cmp(str(self), str(other))

    def __hash__(self):
        return hash(str(self))

    def __getattr__(self, name):
        return getattr(str(self), name)

    def __getitem__(self, i):
        return str(self)[i]

    def __getslice__(self, i, j):
        return str(self)[i:j]

    def __iter__(self):
        for c in str(self): yield c

    def __len__(self):
        return len(str(self))

    def xml(self):
        return str(self) if self.M else escape(str(self))

    def encode(self, *a, **b):
        return str(self).encode(*a, **b)

    def decode(self, *a, **b):
        return str(self).decode(*a, **b)

    def read(self):
        return str(self)

    def __mod__(self, symbols):
        if self.is_copy: return lazyT(self)
        return lazyT(self.m, symbols, self.T, self.f, self.t, self.M)

class translator(object):
    """
    this class is instantiated by gluon.compileapp.build_environment
    as the T object
    ::
        T.force(None) # turns off translation
        T.force('fr, it') # forces web2py to translate using fr.py or it.py

        T(\"Hello World\") # translates \"Hello World\" using the selected file

    notice 1: there is no need to force since, by default, T uses
    http_accept_language to determine a translation file.
    notice 2: 
       en and en-en are considered different languages!
    notice 3: 
       if language xx-yy is not found force() probes other similar
    languages using such algorithm: 
        xx-yy.py -> xx.py -> xx-yy*.py -> xx*.py
    """

    def __init__(self, request):
        self.request = request
        self.folder = request.folder
        self.langpath = ospath.join(self.folder,'languages')
        self.filenames = set(os.listdir(self.langpath))
        self.http_accept_language = request.env.http_accept_language
        # self.cache                        # filled in self.force()
        # self.accepted_language = None     # filled in self.force()
        # self.language_file = None         # filled in self.force()
        # self.plural_language = None       # filled in self.force()
        # self.nplurals = None              # filled in self.force()
        # self.get_plural_id = None         # filled in self.force()
        # self.construct_plural_form = None # filled in self.force()
        # self.plural_rules_file = None     # filled in self.force()
        # self.plural_file = None           # filled in self.force()
        # self.plural_dict = None           # filled in self.force()
        # self.plural_status = None         # filled in self.force()
        self.requested_languages = \
            self.force(self.http_accept_language)
        self.lazy = True
        self.otherTs = {}
        self.filter = markmin
        self.ftag = 'markmin'

    def get_possible_languages(self):
        return [lang[:-3] for lang in self.filenames \
                    if regex_langfile.match(lang)]

    def set_current_languages(self, *languages):
        """
        set current AKA "default" languages
        setting one of this languages makes force() function
        turn translation off to use default language
        """
        if len(languages) == 1 and isinstance(
            languages[0], (tuple, list)):
            languages = languages[0]
        self.current_languages = languages
        self.force(self.http_accept_language)

    def set_plural(self, language):
        """
        initialize plural forms subsystem
        invoked from self.force()
        """
        lang = language[:2] 
        (self.plural_language,
         self.nplurals,
         self.get_plural_id,
         self.construct_plural_form,
         self.plural_filename
         ) = PLURAL_RULES.get(language,PLURAL_RULES['default'])
        for lang in (language, language[:5], language[:2]):
            filename = 'plural-%s.py' % lang
            if filename in self.filenames:
                self.plural_file = ospath.join(self.langpath,filename)
                self.plural_dict = read_plural_dict(self.plural_file)
                break
        else:
            self.plural_file = None
            self.plural_dict = {}
 
    def plural(self, word, n):
        """
        get plural form of word for number *n*
            NOTE: *word* MUST be defined in current language
                  (T.accepted_language)

            invoked from T()/M() in %%{} tag
        args:
            word (str): word in singular
            n (numeric): number plural form created for

        returns:
            (str): word in appropriate singular/plural form
        """
        nplurals = self.nplurals
        if int(n)==1:
            return word
        elif word:
            id = self.get_plural_id(abs(int(n)))
            # id = 0 first plural form
            # id = 1 second plural form
            # etc.
            forms = self.plural_dict.get(word, [])
            if len(forms)>=id:
                # have this plural form
                return forms[id-1]
            else:
                # guessing this plural form
                forms += ['']*(nplurals-len(forms)-1)
                form = self.construct_plural_form(word, id)
                forms[id-1] = form
                self.plural_dict[word] = forms
                if self.plural_file and not is_gae:
                    write_plural_dict(self.plural_file,
                                      self.plural_dict)
                return form

    def get_possible_languages_info(self, lang=None):
        """
        return info for selected language or dictionary with all
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
        info = read_possible_languages(self.folder)
        if lang: info = info.get(lang)
        return info

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
        language = ''
        if isinstance(languages,str):
            languages = regex_language.findall(languages.lower())
        elif not languages or languages[0] is None:
            languages = []
        for lang in languages:
            if lang+'.py' in self.filenames:
                language = lang
                langfile = language+'.py'
                break
            elif len(lang)>5 and lang[:5]+'.py' in self.filenames:
                language = lang[:5]
                langfile = language+'.py'
                break
            elif len(lang)>2 and lang[:2]+'.py' in self.filenames:
                language = lang[:2]
                langfile = language+'.py'
                break
        else:
            if 'default.py' in self.filenames:
                language = DEFAULT_LANGUAGE
                langfile = 'default.py'
            else:
                language = DEFAULT_LANGUAGE
                langfile = None
        self.accepted_language = language
        if langfile:
            self.language_file = ospath.join(self.langpath,langfile)
            self.t = read_dict(self.language_file)
        else:
            self.language_file = None
            self.t = {}
        self.cache = global_language_cache.setdefault(
            self.language_file,({},allocate_lock()))
        self.set_plural(language)
        return languages

    def __call__(self, message, symbols={}, language=None, lazy=None):
        """
        get cached translated plain text message with inserted parameters(symbols)
        if lazy==True lazyT object is returned
        """
        if lazy is None:
            lazy = self.lazy
        if not language:
            if lazy :
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

    def apply_filter(self, message, symbols={}, filter=None, ftag=None):
        def get_tr(message, prefix, filter):
            s = self.get_t(message, prefix)
            return filter(s) if filter else self.filter(s)
        if filter:
            prefix = '@'+(ftag or 'userdef')+'\x01'
        else:
            prefix = '@'+self.ftag+'\x01'
        message = get_from_cache(
            self.cache, prefix+message,
            lambda: get_tr(message, prefix, filter))
        if symbols or symbols == 0 or symbols == "":
            if isinstance(symbols, dict):
                symbols.update(
                    (key, xmlescape(value).translate(ttab_in))
                    for key, value in symbols.iteritems()
                    if not isinstance(value, NUMBERS) )
            else:
                if not isinstance(symbols, tuple):
                    symbols = (symbols,)
                symbols = tuple(
                    value if isinstance(value, NUMBERS)
                    else xmlescape(value).translate(ttab_in)
                    for value in symbols)
            message = self.params_substitution(message, symbols)
        return XML(message.translate(ttab_out))

    def M(self, message, symbols={}, language=None, 
          lazy=None, filter=None, ftag=None):
        """
        get cached translated markmin-message with inserted parametes
        if lazy==True lazyT object is returned
        """
        if lazy is None:
            lazy = self.lazy
        if not language:
            if lazy:
                return lazyT(message, symbols, self, filter, ftag,  True)
            else:
                return self.apply_filter(message, symbols, filter, ftag)
        else:
            try:
                otherT = self.otherTs[language]
            except KeyError:
                otherT = self.otherTs[language] = translator(self.request)
                otherT.force(language)
            return otherT.M(message, symbols, lazy=lazy)

    def get_t(self, message, prefix=''):
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
        key = prefix+message
        mt = self.t.get(key, None)
        if mt is None:
            # we did not find a translation
            if message.find('##')>0 and not '\n' in message:
                # remove comments
                message = message.rsplit('##', 1)[0]
            # guess translation same as original
            self.t[key] = mt = message
            # update language file for later translation
            if self.language_file and not is_gae:
                write_dict(self.language_file, self.t)
            # fix backslash escaping
            mt = regex_backslash.sub(
                lambda m: m.group(1).translate(ttab_in), mt)
        return mt

    def params_substitution(self, message, symbols):
        """
        substitute parameters from symbols into message using %.
        also parse %%{} placeholders for plural-forms processing.
        returns: string with parameters
        NOTE: *symbols* MUST BE OR tuple OR dict of parameters!
        """
        def sub_plural(m):
            """string in %{} is transformed by this rules:
               If string starts with  \\, ! or ? such transformations
               take place:

               "!string of words" -> "String of word" (Capitalize)
               "!!string of words" -> "String Of Word" (Title)
               "!!!string of words" -> "STRING OF WORD" (Upper)
               "\\!string of words" -> "!string of word"
                             (remove \\ and disable transformations)
               "?word?number" -> "word" (return word, if number == 1)
               "?number" or "??number" -> "" (remove number,
                                              if number == 1)
               "?word?number" -> "number" (if number != 1)
            """
            def sub_tuple(m):
                """ word[number], !word[number], !!word[number], !!!word[number]
                    word, !word, !!word, !!!word, ?word?number, ??number, ?number
                    ?word?word[number], ?word?[number], ??word[number]
                """
                w,i = m.group('w','i')
                c = w[0]
                if c not in '!?':
                    return self.plural(w, symbols[int(i or 0)])
                elif c == '?':
                    (p1, sep, p2) = w[1:].partition("?")
                    part1 = p1 if sep else ""
                    (part2, sep, part3) = (p2 if sep else p1).partition("?")
                    if not sep: part3 = part2
                    if i is None:
                       # ?[word]?number[?number] or ?number
                       if not part2: return m.group(0)
                       num = int(part2)
                    else:
                       # ?[word]?word2[?word3][number]
                       num = int(symbols[int(i or 0)])
                    return part1 if num==1 else part3 if num==0 else part2
                elif w.startswith('!!!'):
                    word = w[3:]
                    fun = upper_fun
                elif w.startswith('!!'):
                    word = w[2:]
                    fun = title_fun
                else:
                    word = w[1:]
                    fun = cap_fun
                if i is not None:
                   return fun(self.plural(word, symbols[int(i)]))
                return fun(word)

            def sub_dict(m):
                """ word(var), !word(var), !!word(var), !!!word(var)
                    word(num), !word(num), !!word(num), !!!word(num)
                    ?word2(var), ?word1?word2(var), ?word1?word2?word0(var)
                    ?word2(num), ?word1?word2(num), ?word1?word2?word0(num)
                """
                w,n = m.group('w','n')
                c = w[0]
                n = int(n) if n.isdigit() else symbols[n]
                if c not in '!?':
                    return self.plural(w, n)
                elif c == '?':
                    # ?[word1]?word2[?word0](var or num), ?[word1]?word2(var or num) or ?word2(var or num)
                    (p1, sep, p2) = w[1:].partition("?")
                    part1 = p1 if sep else ""
                    (part2, sep, part3) = (p2 if sep else p1).partition("?")
                    if not sep: part3 = part2
                    num = int(n)
                    return part1 if num==1 else part3 if num==0 else part2
                elif w.startswith('!!!'):
                    word = w[3:]
                    fun = upper_fun
                elif w.startswith('!!'):
                    word = w[2:]
                    fun = title_fun
                else:
                    word = w[1:]
                    fun = cap_fun
                return fun(self.plural(word, n))

            s = m.group(1)
            part = regex_plural_tuple.sub(sub_tuple, s)
            if part == s:
                part = regex_plural_dict.sub(sub_dict, s)
                if part == s:
                    return m.group(0)
            return part
        message = message % symbols
        message = regex_plural.sub(sub_plural, message )
        return message

    def translate(self, message, symbols):
        """
        get cached translated message with inserted parameters(symbols)
        """
        message = get_from_cache(self.cache, message, 
                                 lambda: self.get_t(message))
        if symbols or symbols == 0 or symbols == "":
            if isinstance(symbols, dict):
                symbols.update(
                    (key, str(value).translate(ttab_in))
                    for key, value in symbols.iteritems()
                    if not isinstance(value, NUMBERS) )
            else:
                if not isinstance(symbols, tuple):
                    symbols = (symbols,)
                symbols = tuple(
                    value if isinstance(value, NUMBERS)
                    else str(value).translate(ttab_in)
                    for value in symbols)
            message = self.params_substitution(message, symbols)
        return message.translate(ttab_out)

def findT(path, language='en'):
    """
    must be run by the admin app
    """
    lang_file = ospath.join(path, 'languages', language + '.py')
    sentences = read_dict(lang_file)
    mp = ospath.join(path, 'models')
    cp = ospath.join(path, 'controllers')
    vp = ospath.join(path, 'views')
    mop = ospath.join(path, 'modules')
    for filename in \
            listdir(mp, '^.+\.py$', 0)+listdir(cp, '^.+\.py$', 0)\
            +listdir(vp, '^.+\.html$', 0)+listdir(mop, '^.+\.py$', 0):
        data = portalocker.read_locked(filename)
        items = regex_translate.findall(data)
        for item in items:
            try:
                message = safe_eval(item)
            except:
                continue # silently ignore inproperly formatted strings
            if not message.startswith('#') and not '\n' in message:
                tokens = message.rsplit('##', 1)
            else:
                # this allows markmin syntax in translations
                tokens = [message]
            if len(tokens) == 2:
                message = tokens[0].strip()+'##'+tokens[1].strip()
            if message and not message in sentences:
                sentences[message] = message
    if not '!langcode!' in sentences:
        sentences['!langcode!'] = (
            'en' if language in ('default', 'en') else language)
    if not '!langname!' in sentences:
        sentences['!langname!'] = (
            'English' if language in ('default', 'en')
            else sentences['!langcode!'])
    write_dict(lang_file, sentences)

### important to allow safe session.flash=T(....)
def lazyT_unpickle(data):
    return marshal.loads(data)
def lazyT_pickle(data):
    return lazyT_unpickle, (marshal.dumps(str(data)),)
copy_reg.pickle(lazyT, lazyT_pickle, lazyT_unpickle)


def update_all_languages(application_path):
    path = ospath.join(application_path, 'languages/')
    for language in listdir(path, regex_langfile):
        findT(application_path, language[:-3])


if __name__ == '__main__':
    import doctest
    doctest.testmod()
