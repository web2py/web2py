#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

if getattr(sys, 'frozen', None):
    path = os.getcwd() # Seems necessary for py2exe
else:
    path = os.path.dirname(os.path.abspath(__file__))
    os.chdir(path)

sys.path = [path]+[p for p in sys.path if not p==path]

# import gluon.import_all ##### This should be uncommented for py2exe.py
import gluon.widget

# Start Web2py and Web2py cron service!
if __name__ == '__main__':
    try:
        from multiprocessing import freeze_support
        freeze_support()
    except:
        sys.stderr.write('Sorry, -K only supported for python 2.6-2.7\n')
    gluon.widget.start(cron=True)




