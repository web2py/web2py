#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
docstring
"""

__author__ = "Gu Yingbo (tensiongyb@gmail.com)"

import os
import re
import sys
import time
import base64
import asyncore
import asynchat
import rfc822
import socket
import thread
import signal
import collections
from traceback import format_exc
from urllib import unquote, splitquery
from urlparse import urlparse
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

RN = '\r\n'
RNRN = '\r\n\r\n'
QUOTED_SLASH = re.compile("(?i)%2F")

COMMA_SEPARATED_HEADERS = ['ACCEPT', 'ACCEPT-CHARSET', 'ACCEPT-ENCODING',
    'ACCEPT-LANGUAGE', 'ACCEPT-RANGES', 'ALLOW', 'CACHE-CONTROL',
    'CONNECTION', 'CONTENT-ENCODING', 'CONTENT-LANGUAGE', 'EXPECT',
    'IF-MATCH', 'IF-NONE-MATCH', 'PRAGMA', 'PROXY-AUTHENTICATE', 'TE',
    'TRAILER', 'TRANSFER-ENCODING', 'UPGRADE', 'VARY', 'VIA', 'WARNING',
    'WWW-AUTHENTICATE']

class FIFO(list):
    def is_empty(self):
        return len(self)==0
    def push(self,data):
        self.append(data)
    def first(self):
        return self[0] if len(self) else None

class RequestHandler(asynchat.async_chat):

    def __init__(self, sock, server):
        asynchat.async_chat.__init__(self, sock)
        self.server = server
        self.reset()

    def reset(self):
        self.ac_in_buffer = ''
        self.ac_out_buffer = ''
        self.producer_fifo.clear() # = collections.deque()
        self.set_terminator(RNRN)
        self.process = "reading headers"
        self.started_response = False
        self.status = ""
        self.outheaders = []
        self.sent_headers = False
        self.close_connection = False
        self.chunked_write = False
    
        self.rfile = StringIO.StringIO()

        self.environ = {
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "wsgi.errors": sys.stderr,
            }

    def collect_incoming_data(self, data):
        """Buffer the data"""
        if self.process == "reading chunked":
            self.line_buffer += data
        else:
            self.rfile.write(data)

    def found_terminator(self):
        if self.process == "reading headers":
            self.rfile.write(RNRN)
            self.rfile.seek(0)
            try:
                self.parse_request()
            except:
                self.simple_response("500 Internal Server Error", format_exc())
                return

            if not self.read_chunked:
                if self.environ["REQUEST_METHOD"].upper() == "POST":
                    cl = int(self.environ["CONTENT_LENGTH"])
                    self.rfile = StringIO.StringIO()
                    self.environ["wsgi.input"] = self.rfile
                    self.process = "dealing post"
                    self.set_terminator(cl)
                else:
                    return self.wsgi_response()
            else:
                self.rfile = StringIO.StringIO()
                self.environ["wsgi.input"] = self.rfile
                self.process = "reading chunked"
                self.set_terminator(RN)
                self.line_buffer = ""
                self.cl = 0
        elif self.process == "dealing post":
            self.rfile.seek(0)
            return self.wsgi_response()
        elif self.process == "reading chunked":
            line = self.line_buffer.split(";", 1)
            chunk_size = int(line.pop(0), 16)
            if chunk_size <= 0:
                self.process = "reading tail headers"
                self.set_terminator(RNRN)
            else:
                self.cl += chunk_size
                self.process = "get chunked"
                self.set_terminator(self.cl+2) # browsers sometimes over-send
        elif self.process == "get chunked":
            crlf = self.rfile.getvalue()[-2:]
            if not crlf != RN:
                self.simple_response("400 Bad Request",
                        "Bad chunked transfer coding "
                        "(expected '\\r\\n', got %r)" % crlf)
                return
            else:
                self.process = "reading chunked"
                self.set_terminator(RN)
                self.rfile.seek(-2, 2)
                self.rfile.truncate()
        elif self.process == "reading tail headers":
            self.read_headers()
            self.rfile.seek(0)
            self.environ["CONTENT_LENGTH"] = str(self.cl) or ""
            return self.wsgi_response()

    def reset_when_done(self):
        self.producer_fifo.append('\0')

    def refill_buffer (self):
        while 1:
            if len(self.producer_fifo):
                p = self.producer_fifo.first()
                # a 'None' in the producer fifo is a sentinel,
                # telling us to close the channel.
                if p == 0:
                    if not self.ac_out_buffer:
                        self.producer_fifo.pop()
                        self.reset()
                    return
                elif p is None:
                    if not self.ac_out_buffer:
                        self.producer_fifo.pop()
                        self.close()
                    return
                elif isinstance(p, str):
                    self.producer_fifo.pop()
                    self.ac_out_buffer = self.ac_out_buffer + p 
                    return
                data = p.more()
                if data:
                    self.ac_out_buffer = self.ac_out_buffer + data
                    return
                else:
                    self.producer_fifo.pop()
            else:
                return

    def wsgi_response(self):
        try:
            self.respond()
        except:
            self.simple_response("500 Internal Server Error", format_exc())
        else:
            if self.close_connection or ( not self.server.keep_going ):
                self.close_when_done()
            else:
                self.reset_when_done()

    def readable(self):
        return self.server.keep_going and not self.writable() and \
            asynchat.async_chat.readable(self) 

    def handle_expt(self):
        asynchat.async_chat.handle_expt(self)
        self.close()

    def handle_error(self):
        asynchat.async_chat.handle_error(self)
        self.close()

    def parse_request(self):
        """
        Parse the next HTTP request start-line and message-headers.
        HTTP/1.1 connections are persistent by default. If a client
        requests a page, then idles (leaves the connection open),
        then rfile.readline() will raise socket.error("timed out").
        Note that it does this based on the value given to settimeout(),
        and doesn't need the client to request or acknowledge the close
        (although your TCP stack might suffer for it: cf Apache's history
        with FIN_WAIT_2).
        """
        request_line = self.rfile.readline()
        if not request_line:
            # Force self.ready = False so the connection will close.
            self.ready = False
            return
        
        if request_line == RN:
            # RFC 2616 sec 4.1: "...if the server is reading the protocol
            # stream at the beginning of a message and receives a CRLF
            # first, it should ignore the CRLF."
            # But only ignore one leading line! else we enable a DoS.
            request_line = self.rfile.readline()
            if not request_line:
                self.ready = False
                return
        
        server = self.server
        environ = self.environ
        environ["SERVER_SOFTWARE"] = "%s WSGI Server" % server.version
        
        method, path, req_protocol = request_line.strip().split(" ", 2)
        environ["REQUEST_METHOD"] = method
        
        # path may be an abs_path (including "http://host.domain.tld");
        scheme, location, path, params, qs, frag = urlparse(path)
        
        if frag:
            self.simple_response("400 Bad Request",
                                 "Illegal #fragment in Request-URI.")
            return
        
        if scheme:
            environ["wsgi.url_scheme"] = scheme
        if params:
            path = path + ";" + params
        
        # Unquote the path+params (e.g. "/this%20path" -> "this path").
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5.1.2
        #
        # But note that "...a URI must be separated into its components
        # before the escaped characters within those components can be
        # safely decoded." http://www.ietf.org/rfc/rfc2396.txt, sec 2.4.2
        atoms = [unquote(x) for x in QUOTED_SLASH.split(path)]
        path = "%2F".join(atoms)
        
        environ["SCRIPT_NAME"] = ""
        environ["PATH_INFO"] = path
        ##if path == "*":
        ##    # This means, of course, that the last wsgi_app (shortest path)
        ##    # will always handle a URI of "*".
        ##    environ["SCRIPT_NAME"] = ""
        ##    environ["PATH_INFO"] = "*"
        ##    self.wsgi_app = server.mount_points[-1][1]
        ##else:
        ##    for mount_point, wsgi_app in server.mount_points:
        ##        # The mount_points list should be sorted by length, descending.
        ##        if path.startswith(mount_point + "/") or path == mount_point:
        ##            environ["SCRIPT_NAME"] = mount_point
        ##            environ["PATH_INFO"] = path[len(mount_point):]
        ##            self.wsgi_app = wsgi_app
        ##            break
        ##    else:
        ##        self.simple_response("404 Not Found")
        ##        return
        
        # Note that, like wsgiref and most other WSGI servers,
        # we unquote the path but not the query string.
        environ["QUERY_STRING"] = qs
        
        # Compare request and server HTTP protocol versions, in case our
        # server does not support the requested protocol. Limit our output
        # to min(req, server). We want the following output:
        #     request    server     actual written   supported response
        #     protocol   protocol  response protocol    feature set
        # a     1.0        1.0           1.0                1.0
        # b     1.0        1.1           1.1                1.0
        # c     1.1        1.0           1.0                1.0
        # d     1.1        1.1           1.1                1.1
        # Notice that, in (b), the response will be "HTTP/1.1" even though
        # the client only understands 1.0. RFC 2616 10.5.6 says we should
        # only return 505 if the _major_ version is different.
        rp = int(req_protocol[5]), int(req_protocol[7])
        sp = int(server.protocol[5]), int(server.protocol[7])
        if sp[0] != rp[0]:
            self.simple_response("505 HTTP Version Not Supported")
            return
        # Bah. "SERVER_PROTOCOL" is actually the REQUEST protocol.
        environ["SERVER_PROTOCOL"] = req_protocol
        # set a non-standard environ entry so the WSGI app can know what
        # the *real* server protocol is (and what features to support).
        # See http://www.faqs.org/rfcs/rfc2145.html.
        environ["ACTUAL_SERVER_PROTOCOL"] = server.protocol
        self.response_protocol = "HTTP/%s.%s" % min(rp, sp)
        
        # If the Request-URI was an absoluteURI, use its location atom.
        if location:
            environ["SERVER_NAME"] = location
        
        # then all the http headers
        try:
            self.read_headers()
        except ValueError, ex:
            self.simple_response("400 Bad Request", repr(ex.args))
            return
        
        creds = environ.get("HTTP_AUTHORIZATION", "").split(" ", 1)
        environ["AUTH_TYPE"] = creds[0]
        if creds[0].lower() == 'basic':
            user, pw = base64.decodestring(creds[1]).split(":", 1)
            environ["REMOTE_USER"] = user
        
        # Persistent connection support
        if self.response_protocol == "HTTP/1.1":
            if environ.get("HTTP_CONNECTION", "") == "close":
                self.close_connection = True
        else:
            # HTTP/1.0
            if environ.get("HTTP_CONNECTION", "") != "Keep-Alive":
                self.close_connection = True
        
        # Transfer-Encoding support
        te = None
        if self.response_protocol == "HTTP/1.1":
            te = environ.get("HTTP_TRANSFER_ENCODING")
            if te:
                te = [x.strip().lower() for x in te.split(",") if x.strip()]
        
        read_chunked = False
        
        if te:
            for enc in te:
                if enc == "chunked":
                    read_chunked = True
                else:
                    # Note that, even if we see "chunked", we must reject
                    # if there is an extension we don't recognize.
                    self.simple_response("501 Unimplemented")
                    self.close_connection = True
                    return
        
        self.read_chunked = read_chunked
        return

        if read_chunked:
            if not self.decode_chunked():
                return
        
        # From PEP 333:
        # "Servers and gateways that implement HTTP 1.1 must provide
        # transparent support for HTTP 1.1's "expect/continue" mechanism.
        # This may be done in any of several ways:
        #   1. Respond to requests containing an Expect: 100-continue request
        #      with an immediate "100 Continue" response, and proceed normally.
        #   2. Proceed with the request normally, but provide the application
        #      with a wsgi.input stream that will send the "100 Continue"
        #      response if/when the application first attempts to read from
        #      the input stream. The read request must then remain blocked
        #      until the client responds.
        #   3. Wait until the client decides that the server does not support
        #      expect/continue, and sends the request body on its own.
        #      (This is suboptimal, and is not recommended.)
        #
        # We used to do 3, but are now doing 1. Maybe we'll do 2 someday,
        # but it seems like it would be a big slowdown for such a rare case.
        if environ.get("HTTP_EXPECT", "") == "100-continue":
            self.simple_response(100)
        
        self.ready = True

    def new_header(self,k,v):
        if k:
            environ = self.environ
            envname = 'HTTP_'+k
            if k in COMMA_SEPARATED_HEADERS:
                existing = environ.get(envname)
                if existing:
                    v = ", ".join((existing, v))
            environ[envname] = v
        
    def read_headers(self):
        """Read header lines from the incoming stream."""
        k = v = None
        while True:
            line = self.rfile.readline()
            if not line or '\0' in line:
                # No more data--illegal end of headers
                raise ValueError("Illegal headers")            
            elif line == RN:
                # Normal end of headers
                self.new_header(k,v)
                break            
            elif line[0] in ' \t':
                v += line.strip()
            else:
                self.new_header(k,v)
                k, v = line.split(":", 1)
                k, v = k.strip().upper(), v.strip()

        environ = self.environ            
        ct = environ.pop("HTTP_CONTENT_TYPE", None)
        if ct:
            environ["CONTENT_TYPE"] = ct
        cl = environ.pop("HTTP_CONTENT_LENGTH", None)
        if cl:
            environ["CONTENT_LENGTH"] = cl
    
    def decode_chunked(self):
        """Decode the 'chunked' transfer coding."""
        cl = 0
        data = StringIO.StringIO()
        while True:
            line = self.rfile.readline().strip().split(";", 1)
            chunk_size = int(line.pop(0), 16)
            if chunk_size <= 0:
                break
##            if line: chunk_extension = line[0]
            cl += chunk_size
            data.write(self.rfile.read(chunk_size))
            crlf = self.rfile.read(2)
            if crlf != RN:
                self.simple_response("400 Bad Request",
                                     "Bad chunked transfer coding "
                                     "(expected '\\r\\n', got %r)" % crlf)
                return
        
        # Grab any trailer headers
        self.read_headers()
        
        data.seek(0)
        self.environ["wsgi.input"] = data
        self.environ["CONTENT_LENGTH"] = str(cl) or ""
        return True
    
    def respond(self):
        """
        Call the appropriate WSGI app and write its iterable output.
        """
        response = self.server.wsgi_app(self.environ, self.start_response)
        try:
            for chunk in response:
                # "The start_response callable must not actually transmit
                # the response headers. Instead, it must store them for the
                # server or gateway to transmit only after the first
                # iteration of the application return value that yields
                # a NON-EMPTY string, or upon the application's first
                # invocation of the write() callable." (PEP 333)
                if chunk:
                    print 'sending',chunk
                    self.write(chunk)
                    print 'sent!'
        finally:
            if hasattr(response, "close"):
                response.close()

        if not self.sent_headers:
            self.send_headers()
        if self.chunked_write:
            self.push("0\r\n")
    
    def simple_response(self, status, msg=""):
        """Write a simple response back to the client."""
        status = str(status)
        buf = ["%s %s\r\n" % (self.server.protocol, status),
               "Content-Length: %s\r\n" % len(msg)]
        
        if status[:3] == "413" and self.response_protocol == 'HTTP/1.1':
            # Request Entity Too Large
            self.close_connection = True
            buf.append("Connection: close\r\n")
        
        buf.append(RN)
        if msg:
            buf.append(msg)
        self.push(''.join(buf))
    
        if self.close_connection or ( not self.server.keep_going ):
            self.close_when_done()
        else:
            self.reset_when_done()

    def start_response(self, status, headers, exc_info = None):
        """WSGI callable to begin the HTTP response."""
        if self.started_response:
            if not exc_info:
                raise AssertionError("WSGI start_response called a second "
                                     "time with no exc_info.")
            else:
                try:
                    raise exc_info[0], exc_info[1], exc_info[2]
                finally:
                    exc_info = None
        self.started_response = True
        self.status = status
        self.outheaders.extend(headers)
        return self.write
    
    def write(self, chunk):
        """
        WSGI callable to write unbuffered data to the client.
        
        This method is also used internally by start_response (to write
        data from the iterable returned by the WSGI application).
        """
        if not self.started_response:
            raise AssertionError("WSGI write called before start_response.")
                
        if not self.sent_headers:
            self.send_headers()

        if self.chunked_write and chunk:
            buf = [hex(len(chunk))[2:], RN, chunk, RN]
            self.push(''.join(buf))
        else:
            self.push(chunk)
    
    def send_headers(self):
        """
        Assert, process, and send the HTTP response message-headers.
        """
        self.sent_headers = True
        hkeys = [key.lower() for key, value in self.outheaders]
        status = int(self.status[:3])

        if status == 413:
            # Request Entity Too Large. Close conn to avoid garbage.
            self.close_connection = True
        elif "content-length" not in hkeys:
            # "All 1xx (informational), 204 (no content),
            # and 304 (not modified) responses MUST NOT
            # include a message-body." So no point chunking.
            if status < 200 or status in (204, 205, 304):
                pass
            else:
                if self.response_protocol == 'HTTP/1.1':
                    # Use the chunked transfer-coding
                    self.chunked_write = True
                    self.outheaders.append(("Transfer-Encoding", "chunked"))
                else:
                    # Closing the conn is the only way to determine len.
                    self.close_connection = True
                    
        if "connection" not in hkeys:
            if self.response_protocol == 'HTTP/1.1':
                if self.close_connection:
                    self.outheaders.append(("Connection", "close"))
            else:
                if not self.close_connection:
                    self.outheaders.append(("Connection", "Keep-Alive"))

        if "date" not in hkeys:
            self.outheaders.append(("Date", rfc822.formatdate()))
        
        server = self.server
        
        if "server" not in hkeys:
            self.outheaders.append(("Server", server.version))
        
        buf = [server.protocol, " ", self.status, RN]
        try:
            buf += [k + ": " + v + RN for k, v in self.outheaders]
        except TypeError:
            if not isinstance(k, str):
                raise TypeError("WSGI response header key %r is not a string.")
            if not isinstance(v, str):
                raise TypeError("WSGI response header value %r is not a string.")
            else:
                raise
        buf.append(RN)
        self.push(''.join(buf))

class WSGIServer(asyncore.dispatcher):
    version = "Asynwsgi Server/1.0 alpha"
    protocol = "HTTP/1.1"
    def __init__(self, bind_addr, wsgi_app, server_name=None):
        asyncore.dispatcher.__init__ (self)
        self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(bind_addr)
        self.listen(1024)
        self.keep_going = True
        self.wsgi_app = wsgi_app

        if not server_name:
            server_name = socket.gethostname()
        self.server_name = server_name

    def writable(self):
        return False

    def readable(self):
        return self.accepting

    def handle_accept(self):
        try:
            conn, addr = self.accept()
        except:
            return
        RequestHandler(conn, self)

    def reload(self, signum, frame):
        print 'reloading...'
        self.keep_going = False
        self.close()

    def stop(self, signum, frame):
        asyncore.close_all()

    def start(self):
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        asyncore.loop(timeout=0.1, use_poll=False)

def demo_app(environ, start_response):
    write = start_response('200 OK', [('content-type', 'text/html')])
    return ["<html><body><h1>Hello World!</h1><br />%s</body></html>"%time.ctime()]

def test_client(address='127.0.0.1:8000'):
    time.sleep(3)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ip,port = address.split(':',1)
    server.connect((ip,int(port)))
    server.send('GET /\r\n\r\n')
    while True:
        sys.stdout.write(server.recv(1))
    sys.stdout.write('CLOSE\n')

if __name__ == "__main__":
    #thread.start_new_thread(test_client,())
    #thread.start_new_thread(test_client,())
    #thread.start_new_thread(test_client,())
    WSGIServer(('127.0.0.1', 8000), demo_app).start()
