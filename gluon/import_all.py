#!/usr/bin/env python

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

This file is not strictly required by web2py. It is used for three purposes:

1) check that all required modules are installed properly
2) provide py2exe and py2app a list of modules to be packaged in the binary
3) (optional) preload modules in memory to speed up http responses

"""

import builtins
import os
import sys

import array
import atexit
import base64
import binascii
import bisect
import bz2
import calendar
import cmath
import cmd
import code
import codecs
import codeop
import collections
import colorsys
import contextlib
import collections
import pickle
import io
import csv
import ctypes
import datetime
import decimal
import difflib
import dis
import doctest
import email
import email.charset
import email.encoders
import email.errors
import email.generator
import email.header
import email.iterators
import email.message
import email.mime
import email.mime.audio
import email.mime.base
import email.mime.image
import email.mime.message
import email.mime.multipart
import email.mime.nonmultipart
import email.mime.text
import email.parser
import email.utils
import encodings.idna
import errno
import filecmp
import fileinput
import fnmatch
import ftplib
import functools
import gc
import getopt
import getpass
import gettext
import glob
import gzip
import hashlib
import heapq
import hmac
import imaplib
import inspect
import itertools
import keyword
import linecache
import locale
import logging
import mailbox
import marshal
import math
import mimetypes
import mmap
import modulefinder
import netrc
import operator
import optparse
import os
import pdb
import pickle
import pickletools
import pkgutil
import platform
import poplib
import pprint
import py_compile
import pyclbr
import pydoc
import queue
import quopri
import random
import re
import rlcompleter
import runpy
import sched
import select
import shelve
import shlex
import shutil
import signal
import site
import smtplib
import socket
import sqlite3
import stat
import string
import stringprep
import struct
import subprocess
import tabnanny
import tarfile
import tempfile
import textwrap
import threading
import time
import timeit
import token
import tokenize
import trace
import traceback
import types
import unicodedata
import unittest
import urllib
import uuid
import warnings
import wave
import weakref
import webbrowser
import wsgiref
import wsgiref.handlers
import wsgiref.headers
import wsgiref.simple_server
import wsgiref.util
import wsgiref.validate
import xml.dom
import xml.dom.minidom
import xml.dom.pulldom
import xml.etree.ElementTree
import xml.parsers.expat
import xml.sax
import xml.sax.handler
import xml.sax.saxutils
import xml.sax.xmlreader
import zipfile
import zipimport
import zlib
import argparse
import json
import multiprocessing
import hashlib
import uuid

try:
    import tkinter
except Exception:
    ...
