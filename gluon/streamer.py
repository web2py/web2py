#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""

import os
import stat
import time
import re
import errno
import rewrite
from http import HTTP
from contenttype import contenttype


regex_start_range = re.compile('\d+(?=\-)')
regex_stop_range = re.compile('(?<=\-)\d+')

DEFAULT_CHUNK_SIZE = 64*1024

def streamer(stream, chunk_size = DEFAULT_CHUNK_SIZE, bytes = None):
    offset = 0
    while bytes is None or offset < bytes:
        if not bytes is None and bytes - offset < chunk_size:
            chunk_size = bytes - offset
        data = stream.read(chunk_size)
        length = len(data)
        if not length:
            break
        else:
            yield data
        if length < chunk_size:
            break
        offset += length
    stream.close()

def stream_file_or_304_or_206(
    static_file,
    chunk_size = DEFAULT_CHUNK_SIZE,
    request = None,
    headers = {},
    error_message = None,
    ):
    if error_message is None:
        error_message = rewrite.thread.routes.error_message % 'invalid request'
    try:
        fp = open(static_file)
    except IOError, e:
        if e[0] == errno.EISDIR:
            raise HTTP(403, error_message, web2py_error='file is a directory')
        elif e[0] == errno.EACCES:
            raise HTTP(403, error_message, web2py_error='inaccessible file')
        else:
            raise HTTP(404, error_message, web2py_error='invalid file')
    else:
        fp.close()
    stat_file = os.stat(static_file)
    fsize = stat_file[stat.ST_SIZE]
    mtime = time.strftime('%a, %d %b %Y %H:%M:%S GMT',
                          time.gmtime(stat_file[stat.ST_MTIME]))
    headers.setdefault('Content-Type', contenttype(static_file))
    headers.setdefault('Last-Modified', mtime)
    headers.setdefault('Pragma', 'cache')
    headers.setdefault('Cache-Control', 'private')

    if request and request.env.http_if_modified_since == mtime:
        raise HTTP(304, **{'Content-Type': headers['Content-Type']})

    elif request and request.env.http_range:
        start_items = regex_start_range.findall(request.env.http_range)
        if not start_items:
            start_items = [0]
        stop_items = regex_stop_range.findall(request.env.http_range)
        if not stop_items or int(stop_items[0]) > fsize - 1:
            stop_items = [fsize - 1]
        part = (int(start_items[0]), int(stop_items[0]), fsize)
        bytes = part[1] - part[0] + 1
        try:
            stream = open(static_file, 'rb')
        except IOError, e:
            if e[0] in (errno.EISDIR, errno.EACCES):
                raise HTTP(403)
            else:
                raise HTTP(404)
        stream.seek(part[0])
        headers['Content-Range'] = 'bytes %i-%i/%i' % part
        headers['Content-Length'] = '%i' % bytes
        status = 206
    else:
        try:
            stream = open(static_file, 'rb')
        except IOError, e:
            if e[0] in (errno.EISDIR, errno.EACCES):
                raise HTTP(403)
            else:
                raise HTTP(404)
        headers['Content-Length'] = fsize
        bytes = None
        status = 200
    if request and request.env.web2py_use_wsgi_file_wrapper:
        wrapped = request.env.wsgi_file_wrapper(stream, chunk_size)
    else:
        wrapped = streamer(stream, chunk_size=chunk_size, bytes=bytes)
    raise HTTP(status, wrapped, **headers)







