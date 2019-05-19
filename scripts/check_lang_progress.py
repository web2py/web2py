#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Written by Vinyl Darkscratch, www.queengoob.org

import sys
import os

# TODO: add comments

# This script can be run with no arguments (which sets the language folder to the current working directory, and default language to English), one argument (which sets the default language), or two arguments (language folder path and default language).
# When run, this script will compare the original language's strings to their assigned values and determine if they match, just like web2py's interface.  While some phrases may be the exact same between both languages, this should provide a good idea of how far along translations are.

def check_lang_progress(cwd, default_lang):
	for x in os.listdir(cwd):
		if x == default_lang or x.startswith("plural-"): continue
		
		data = eval(open(os.path.join(cwd, x)).read())

		total = 0
		translated = 0

		for key in data:
			total += 1
			if key.replace('@markmin\x01', '') != data[key]: translated += 1

		print "Translations for %s (%s): %d/%d Translated (%d Untranslated)" %(data['!langname!'], data['!langcode!'], translated, total, total-translated)

if __name__ == "__main__":
	cwd = os.getcwd()
	default_lang = 'en'

	if len(sys.argv) > 2:
		cwd = sys.argv[1]
		default_lang = sys.argv[2]
	elif len(sys.argv) > 1:
		default_lang = sys.argv[1]

	check_lang_progress(cwd, default_lang)