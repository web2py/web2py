#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Plural subsystem is created by Vladyslav Kozlovskyy (Ukraine)
                               <dbdevelop@gmail.com>
"""

from os import path as ospath, stat as ostat, sep as osep
import re
from utf8 import Utf8
from cgi import escape
import portalocker
import logging
import marshal
import numbers
import copy_reg
from fileutils import abspath, listdir
import settings
from cfs import getcfs, cfs
from thread import allocate_lock
from html import XML, xmlescape
from contrib.markmin.markmin2html import render, markmin_escape
from string import maketrans

__all__ = ['translator', 'findT', 'update_all_languages']

# used as a default filter i translator.M()
markmin = lambda s: render( regex_param.sub(
                       lambda m: '{' + markmin_escape(m.group('s')) + '}',
                          s ), sep='br', auto=False )

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
regex_langinfo = re.compile("^[^'\"]*['\"]([^'\"]*)['\"]\s*:\s*['\"]([^'\"]*)['\"].*$")
regex_backslash = re.compile(r"\\([\\{}%])")
regex_plural = re.compile('%({.+?})')
regex_plural_dict = re.compile('^{(?P<w>[^()[\]][^()[\]]*?)\((?P<n>[^()\[\]]+)\)}$')  # %%{word(varname or number)}
regex_plural_tuple = re.compile('^{(?P<w>[^[\]()]+)(?:\[(?P<i>\d+)\])?}$') # %%{word[index]} or %%{word}
regex_plural_q = re.compile('^asdf$') # %%{?word?cnt}, %%{??cnt} or %%{?cnt}
regex_plural_rules = re.compile('^plural_rules-[a-zA-Z]{2}(-[a-zA-Z]{2})?\.py$')

upper_fun = lambda s: unicode(s,'utf-8').upper().encode('utf-8')
title_fun = lambda s: unicode(s,'utf-8').title().encode('utf-8')
cap_fun   = lambda s: unicode(s,'utf-8').capitalize().encode('utf-8')

# DEFAULT PLURAL-FORMS RULES:
default_nplurals = 1 # language doesn't use plural forms
default_get_plural_id = lambda n: 0 # only one singular/plural form is used
default_construct_plural_form = lambda word, plural_id: word # word is unchangeable

ttab_in  = maketrans("\\%{}", '\x1c\x1d\x1e\x1f')
ttab_out = maketrans('\x1c\x1d\x1e\x1f', "\\%{}")

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
    lock=cache[1]
    lock.acquire()
    try:
        cache[0].clear();
    finally:
        lock.release()


def lang_sampling(lang_tuple, langlist):
    """ search *lang_tuple* in *langlist*

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
    # clear cache of processed messages:
    clear_cache(tcache.setdefault(filename, ({}, allocate_lock())))
    if not lang_text.strip():
        return {}
    try:
        return eval(lang_text)
    except Exception as e:
        status='Syntax error in %s (%s)' % (filename, e)
        logging.error(status)
        return {'__corrupted__':status}


def read_dict(filename):
    """ return dictionary with translation messages
    """
    return getcfs('lang:'+filename, filename,
                lambda: read_dict_aux(filename))


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
    filename = ospath.join(langdir, lang+'.py')
    langcode=langname=''
    f = portalocker.LockedFile(filename, 'r')
    try:
        while not (langcode and langname):
            line = f.readline()
            if not line:
               break
            match=regex_langinfo.match(line)
            if match:
                k = match.group(1)
                if k == '!langname!':
                    langname = match.group(2)
                elif k == '!langcode!':
                    langcode = match.group(2)
                elif k[0:1] > '!':
                    break
    finally:
        f.close()
    if not langcode:
        langcode = lang if lang != 'default' else 'en'
    return langcode, langname or langcode, ostat(filename).st_mtime

def read_possible_languages_aux(langdir):
    langs = {}
    # scan languages directory for langfiles:
    for langfile in [f for f in
                      listdir(langdir, regex_langfile) +
                      listdir(langdir, '^default\.py$')
                      if osep not in f]:
        lang=langfile[:-3]
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
    lang_path = ospath.join(path, 'languages')
    return getcfs('langs:'+lang_path, lang_path,
                   lambda: read_possible_languages_aux(lang_path))


def read_plural_rules_aux(filename):
    """retrieve plural rules from rules/*plural_rules-lang*.py file.

    args:
        filename (str): plural_rules filename

    returns:
        tuple(nplurals, get_plural_id, construct_plural_form)
        e.g.: (3, <function>, <function>)
    """
    f = portalocker.LockedFile(filename, 'r')
    plural_py=f.read().replace('\r\n','\n')
    f.close()
    try:
        exec(plural_py)
        nplurals=locals().get('nplurals', default_nplurals)
        get_plural_id=locals().get('get_plural_id', default_get_plural_id)
        construct_plural_form=locals().get('construct_plural_form',
                               default_construct_plural_form)
        status='ok'
    except Exception as e:
        nplurals=default_nplurals
        get_plural_id=default_get_plural_id
        construct_plural_form=default_construct_plural_form
        status='Syntax error in %s (%s)' % (filename, e)
        logging.error(status)
    return (nplurals, get_plural_id, construct_plural_form, status)

def read_plural_rules(lang):
    filename = abspath('gluon','contrib','rules', 'plural_rules-%s.py' % lang)
    return getcfs('plural_rules-'+lang, filename,
               lambda: read_plural_rules_aux(filename))

pcache={}
def read_possible_plurals():
    """ create list of all possible plural rules files
        result is cached to increase speed
    """
    global pcache
    pdir = abspath('gluon','contrib','rules')
    plurals = {}
    # scan rules directory for plural_rules-*.py files:
    for pname in [f for f in listdir(pdir, regex_plural_rules)
                  if osep not in f]:

        lang=pname[13:-3]
        fname=ospath.join(pdir, pname)
        mtime=ostat(fname).st_mtime
        if lang in pcache and pcache[lang][2] == mtime:
            # if plural_file's mtime wasn't changed - use previous value:
            plurals[lang]=pcache[lang]
        else:
            # otherwise, reread plural_rules-file:
            if 'plural_rules-'+lang in cfs:
               n,f1,f2,status=read_plural_rules(lang)
            else:
               n,f1,f2,status=read_plural_rules_aux(fname)
            plurals[lang]=(n, pname, mtime, status)
    pcache=plurals
    return pcache

def get_plural_rules(languages):
    """get plural-forms rules for language *lang*
       if rules not found - default rules will be return and lang=='unknown'

    args:
        lang (str): the languages, for one of which the plural-forms is return

    returns:
        tuples(lang, plural_rules-filename, nplurals,
                        get_plural_id(), construct_plural_form(), status)
    """
    if isinstance(languages, str):
       languages = [languages]

    all_plurals=read_possible_plurals()
    for lang in languages:
        match_language = regex_language.match(lang.strip().lower())
        if match_language:
            match_language = tuple(part
                                   for part in match_language.groups()
                                   if part)
            lang = lang_sampling(match_language, all_plurals.keys())
            if lang:
               ( nplurals,
                  get_plural_id,
                  construct_plural_form,
                  status
               ) = read_plural_rules(lang)
               return (lang, all_plurals[lang][1], nplurals,
                                                   get_plural_id,
                                                   construct_plural_form,
                                                   status)
    return ('unknown', None, default_nplurals,
                             default_get_plural_id,
                             default_construct_plural_form,
                             'ok')


def read_plural_dict_aux(filename):
    fp = portalocker.LockedFile(filename, 'r')
    lang_text = fp.read().replace('\r\n', '\n')
    fp.close()
    if not lang_text.strip():
        return {}
    try:
        return eval(lang_text)
    except Exception as e:
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
    m = s = T = f = t = M = None

    def __init__(
        self,
        message,
        symbols = {},
        T = None,
        filter = None,
        ftag = None,
        M = False
        ):
        self.M = M
        if isinstance(message, lazyT):
            self.m = message.m
            self.s = symbols or message.s
            self.T = T or message.T
            self.f = filter or message.f
            self.t = ftag or message.t
        else:
            self.m = message
            self.s = symbols
            self.T = T
            self.f = filter
            self.t = ftag

    def __repr__(self):
        return "<lazyT %s>" % (repr(str(self.m)), )

    def __str__(self):
        return str(self.T.apply_filter(self.m, self.s, self.f, self.t) if self.M else
                   self.T.translate(self.m, self.s))

    def __eq__(self, other):
        return (self.T.apply_filter(self.m, self.s, self.f, self.t) if self.M else
                   self.T.translate(self.m, self.s)) == other

    def __ne__(self, other):
        return (self.T.apply_filter(self.m, self.s, self.f, self.t) if self.M else
                   self.T.translate(self.m, self.s)) != other

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
        return str(self) if self.M else escape(str(self))

    def encode(self, *a, **b):
        return str(self).encode(*a, **b)

    def decode(self, *a, **b):
        return str(self).decode(*a, **b)

    def read(self):
        return str(self)

    def __mod__(self, symbols):
        return (self.T.apply_filter(self.m, self.s, self.f, self.t) if self.M else
                self.T.translate(self.m, self.s))


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

    notice 2: en and en-en are considered different languages!

    notice 3: if language xx-yy is not found force() probes other similar
    languages using such algorithm: xx-yy.py -> xx.py -> xx-yy*.py -> xx*.py
    """

    def __init__(self, request):
        global tcache
        self.request = request
        self.folder = request.folder
        dfile = ospath.join(self.folder,'languages','default.py')
        if ospath.exists(dfile):
            self.default_language_file = dfile
            self.default_t = read_dict(dfile)
        else: # languages/default.py is not found
            self.default_language_file = ospath.join(self.folder, 'languages','')
            self.default_t = {}
        self.cache = tcache.setdefault(self.default_language_file, ({}, allocate_lock()))
        self.current_languages = [self.get_possible_languages_info('default')[0]]
        self.http_accept_language = request.env.http_accept_language
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
        self.requested_languages = self.force(self.http_accept_language)
        self.lazy = True
        self.otherTs = {}
        self.filter = markmin
        self.ftag = 'markmin'

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

    def set_plural(self, languages):
        """ initialize plural forms subsystem
            invoked from self.force()
        """
        ( self.plural_language,
          self.plural_rules_file,
          self.nplurals,
          self.get_plural_id,
          self.construct_plural_form,
          self.plural_status
        ) = get_plural_rules(languages)

        if self.plural_language == 'unknown':
            self.plural_file = None
            self.plural_dict = {}
        else:
            self.plural_file = ospath.join(self.folder,
                                           'languages',
                                           'plural-%s.py' % self.plural_language)
            if ospath.exists(self.plural_file):
                self.plural_dict = read_plural_dict(self.plural_file)
            else:
                self.plural_dict = {}

    def plural(self, word, n):
        """ get plural form of word for number *n*
            NOTE: *word" MUST be defined in current language
                  (T.accepted_language)

            invoked from T()/M() in %%{} tag
        args:
            word (str): word in singular
            n (numeric): number plural form created for

        returns:
            (str): word in appropriate singular/plural form
        """
        nplurals = self.nplurals
        if word:
            id = self.get_plural_id(abs(int(n)))
            if id > 0:
                forms = self.plural_dict.get(word, [])
                if forms:
                    try:
                        form = forms[id-1]
                    except:
                        form = None
                    if form: return form
                form = self.construct_plural_form(word, id)
                if len(forms) < nplurals-1:
                    forms.extend('' for i in xrange(nplurals-len(forms)-1))
                forms[id-1] = form
                self.plural_dict[word] = forms
                if (self.plural_file and
                       not settings.global_settings.web2py_runtime_gae):
                    write_plural_dict(self.plural_file, self.plural_dict)
                return form
        return word

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
        language = ''

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
            for lang in languages:
                match_language = regex_language.match(lang.strip().lower())
                if match_language:
                    match_language = tuple(part
                                           for part in match_language.groups()
                                           if part)
                    language = lang_sampling(match_language,
                                             self.current_languages)
                    if language:
                        break
                    language = lang_sampling(match_language, possible_languages)
                    if language:
                        self.language_file = ospath.join(self.folder,
                                                         'languages',
                                                         language + '.py')
                        if ospath.exists(self.language_file):
                            self.t = read_dict(self.language_file)
                            self.cache = tcache.setdefault(self.language_file,
                                                           ({},allocate_lock()))
                            self.set_plural(language)
                            self.accepted_language = language
                            return languages
        self.accepted_language = language or self.current_languages[0]
        self.language_file = self.default_language_file
        self.cache = tcache[self.language_file]
        self.t = self.default_t
        self.set_plural(language or self.current_languages)
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
        message = get_from_cache(self.cache, prefix+message,
                                 lambda: get_tr(message, prefix, filter))
        if symbols or symbols == 0 or symbols == "":
            if isinstance(symbols, dict):
                symbols.update( (key, xmlescape(value).translate(ttab_in))
                                for key, value in symbols.iteritems()
                                 if not isinstance(value, numbers.Number) )
            else:
                if not isinstance(symbols, tuple):
                    symbols = (symbols,)
                symbols = tuple(value if isinstance(value, numbers.Number)
                                    else xmlescape(value).translate(ttab_in)
                                     for value in symbols)
            message = self.params_substitution(message, symbols)
        return XML(message.translate(ttab_out))

    def M(self, message, symbols={}, language=None, lazy=None, filter=None, ftag=None):
        """ get cached translated markmin-message with inserted parametes

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
        if mt is not None:
            return mt
        if not message.startswith('##') and not '\n' in message:
            tokens = message.rsplit('##', 1)
        else:
            # this allows markmin syntax in translations
            tokens = [message]
        self.t[key] = mt = self.default_t.get(key, tokens[0])
        if (self.language_file != self.default_language_file and
             not settings.global_settings.web2py_runtime_gae):
            write_dict(self.language_file, self.t)
        return  regex_backslash.sub(lambda m: m.group(1).translate(ttab_in), mt)

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
                word = w[c=='\\':]
                if c not in '!?':
                    return self.plural(word, symbols[int(i or 0)])
                elif c == '?':
                    part2 = w[max(1,w.find('?',1)+1):]
                    if i is None:
                        # ?[word]?number or ?number
                        num = part2
                    else:
                        # ?[word]?word2[number], ?word2[number] or ?word2[number]
                        num = symbols[int(i or 0)]
                    return w[1:abs(w.find('?',1))] if int(num) == 1 else part2
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
                """
                w,n = m.group('w','n')
                c = w[0]
                word = w[c=='\\':]
                n = int(n) if n.isdigit() else symbols[n]
                if c not in '!?':
                    return self.plural(word, n)
                elif c == '?':
                    # ?[word]?word2(var or num), ?word2(var or num) or ?word2(var or num)
                    return w[1:abs(w.find('?',1))] if int(n) == 1 else w[max(1,w.find('?',1)+1):]
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
        message = get_from_cache(self.cache, message, lambda: self.get_t(message))
        if symbols or symbols == 0 or symbols == "":
            if isinstance(symbols, dict):
                symbols.update( (key, str(value).translate(ttab_in))
                                for key, value in symbols.iteritems()
                                 if not isinstance(value, numbers.Number) )
            else:
                if not isinstance(symbols, tuple):
                    symbols = (symbols,)
                symbols = tuple(value if isinstance(value, numbers.Number)
                                    else str(value).translate(ttab_in)
                                     for value in symbols)

            message = self.params_substitution(message, symbols)
        return message.translate(ttab_out)

def findT(path, language='en'):
    """
    must be run by the admin app
    """
    filename = ospath.join(path, 'languages', language + '.py')
    sentences = read_dict(filename)
    mp = ospath.join(path, 'models')
    cp = ospath.join(path, 'controllers')
    vp = ospath.join(path, 'views')
    mop = ospath.join(path, 'modules')
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
    path = ospath.join(application_path, 'languages/')
    for language in listdir(path, regex_langfile):
        findT(application_path, language[:-3])


if __name__ == '__main__':
    import doctest
    doctest.testmod()

