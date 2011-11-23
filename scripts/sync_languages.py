#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO: Comment this code

import sys
import shutil
import os

from gluon.languages import findT

sys.path.insert(0, '.')

file = sys.argv[1]
apps = sys.argv[2:]

d = {}
for app in apps:
    path = 'applications/%s/' % app
    findT(path, file)
    langfile = open(os.path.join(path, 'languages', '%s.py' % file))
    try:
        data = eval(langfile.read())
    finally:
        langfile.close()
    d.update(data)

path = 'applications/%s/' % apps[-1]
file1 = os.path.join(path, 'languages', '%s.py' % file)

f = open(file1, 'w')
try:
    f.write('{\n')
    keys = d.keys()
    keys.sort()
    for key in keys:
        f.write('%s:%s,\n' % (repr(key), repr(str(d[key]))))
    f.write('}\n')
finally:
    f.close()

oapps = reversed(apps[:-1])
for app in oapps:
    path2 = 'applications/%s/' % app
    file2 = os.path.join(path2, 'languages', '%s.py' % file)
    shutil.copyfile(file1, file2)

