# -*- coding: utf-8 -*-
"""
Dummy simplejson module for backwards compatibility with applications that import simplejson from gluon.contrib

TODO: Remove this.
"""
from json import *

class JSONDecodeError(ValueError):
    pass