#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Useful regexes
---------------
"""

import re

# pattern to find defined tables

regex_tables = re.compile(
    """^[\w]+\.define_table\(\s*[\'\"](?P<name>\w+)[\'\"]""",
    flags=re.M)

# patterns to find includes and extends in views

regex_include = re.compile(
    '(?P<all>\{\{\s*include\s+[\'"](?P<name>[^\'"]*)[\'"]\s*\}\})')

regex_extend = re.compile(
    '^\s*(?P<all>\{\{\s*extend\s+[\'"](?P<name>[^\'"]+)[\'"]\s*\}\})', re.MULTILINE)
