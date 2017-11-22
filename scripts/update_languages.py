#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Written by Vinyl Darkscratch, www.queengoob.org

# TODO: add comments

import os
import ast
import sys
import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from gluon.cfs import getcfs
from gluon.utf8 import Utf8
from gluon._compat import copyreg, PY2, maketrans, iterkeys, unicodeT, to_unicode, to_bytes, iteritems, to_native, pjoin
from gluon.languages import findT

# This script can be run with no arguments (which sets the application folder to the current working directory, and default language to English), one argument (which sets the default language), or two arguments (application folder path and default language).
# When run, it will update the default language, as well as strip all of the strings found in the non-default languages but not in the default language, and add the strings found in the default language to the non-default languages it is not, making sure translators don't do additional work that will never be used.

def read_dict_aux(filename):
	lang_text = open(filename, 'r').read().replace(b'\r\n', b'\n')
	try:
		return safe_eval(to_native(lang_text)) or {}
	except Exception:
		e = sys.exc_info()[1]
		status = 'Syntax error in %s (%s)' % (filename, e)
		return {'__corrupted__': status}

def read_dict(filename):
	return getcfs('lang:' + filename, filename, lambda: read_dict_aux(filename))

def safe_eval(text):
	if text.strip():
		try:
			return ast.literal_eval(text)
		except ImportError:
			return eval(text, {}, {})
	return None

def sort_function(x, y):
	return cmp(unicode(x, 'utf-8').lower(), unicode(y, 'utf-8').lower())

def write_file(file, contents):
	file.write('# -*- coding: utf-8 -*-\n{\n')
	for key in sorted(contents, sort_function):
		file.write('%s: %s,\n' % (repr(Utf8(key)),
								repr(Utf8(contents[key]))))
	file.write('}\n')
	file.close()

def update_languages(cwd, default_lang):
	defaultfp = os.path.join(cwd, "languages", '%s.py' %default_lang)
	findT(cwd, default_lang)
	default = read_dict(defaultfp)

	for lang in os.listdir(os.path.join(cwd, "languages")):
		if lang == default_lang+".py" or lang.startswith("plural-"): continue
		
		i18n = read_dict(os.path.join(cwd, "languages", lang))
		if i18n:
			new_dict = default
			for phrase in i18n:
				if phrase in default:
					new_dict[phrase] = i18n[phrase]
			write_file(open(os.path.join(cwd, "languages", lang), 'w'), new_dict)
			print lang

if __name__ == "__main__":
	cwd = os.getcwd()
	default_lang = 'en'

	if len(sys.argv) > 2:
		cwd = sys.argv[1]
		default_lang = sys.argv[2]
	elif len(sys.argv) > 1:
		default_lang = sys.argv[1]

	update_languages(cwd, default_lang)
