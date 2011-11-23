#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""

import os
import sys
import wsgiref.handlers

path = os.path.dirname(os.path.abspath(__file__))
os.chdir(path)
sys.path = [path]+[p for p in sys.path if not p==path]

import gluon.main

wsgiref.handlers.CGIHandler().run(gluon.main.wsgibase)

