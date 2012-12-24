import asyncore
import asynchat
import socket
import time
import sys
import thread
import string

RN = '\r\n'
STATUS_READING_HEADERS = 0
STATUS_READING_BODY = 1
STATUS_SENDING_RESPONSE = 2

class http_request_handler(asynchat.async_chat):

    def __init__(self, sock, addr, sessions, log):
        asynchat.async_chat.__init__(self, sock=sock)
        self.addr = addr
        self.sessions = sessions
        self.ibuffer = []
        self.obuffer = ""
        self.set_terminator(RN+RN)
        self.reading_headers = True
        self.handling = False
        self.cgi_data = None
        self.log = log
        self.status = STATUS_READING_HEADERS

    def collect_incoming_data(self, data):
        """Buffer the data"""
        self.ibuffer.append(data)

    def parse_headers(self,data):  
        if '\0' in data:
            
        first_line, headers = data.split(RM,1)
        self.op, self.path_info = first_line.split(' ',1)
        lines = headers.replace(RN+' ',' ').replace(RN+'\t',' ').split(RN)
        items = [line.split(':',1) for line in lines.split(RN) if ':' in line]
        self.headers = dict((item[0].upper(),item[1]) for item in items)
        self.close()

    def found_terminator(self):
        if self.status==STATUS_READING_HEADERS:
            self.parse_headers(string.join(self.ibuffer,'')+'\r\n')
            self.ibuffer = []
            if self.op.upper() == "POST":
                clen = self.headers.getheader("content-length")
                self.set_terminator(int(clen))
                self.status=STATUS_READ_BODY
            else:
                self.status=STATUS_SEND_RESPONSE
        elif self.status==STATUS_READ_BODY:
            self.ibuffer
            
                self.set_terminator(None)
                for data in self.run_app():
                    self.push(data)
                    time.sleep(1)
                self.close()
        elif not self.handling:
            self.set_terminator(None) # browsers sometimes over-send
            self.cgi_data = parse(self.headers, "".join(self.ibuffer))
            self.handling = True
            self.ibuffer = []
            self.handle_request()

    def handle_write(self):
        print 'handle_write', self.buffer
        self.send(self.buffer)
        self.buffer = ''

    def run_app(self):
        return ['200 OK\r\n\r\n','Hello\n','World\n','%s\n' % time.ctime()]

class HTTPServer(asyncore.dispatcher):
    def __init__(self, host, port, app):
        asyncore.dispatcher.__init__(self)
        self.host = host
        self.port = port
        self.app = app
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(20)
        
    def handle_accept(self):
        pair = self.accept()
        if not pair is None:
            sock, addr = pair
            print 'Incoming connection from %s' % repr(addr)
            handler = http_request_handler(sock, addr, SESSIONS, None)
            handler.server = self

def test_client(address='127.0.0.1:8000'):
    time.sleep(3)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ip,port = address.split(':',1)
    server.connect((ip,int(port)))
    server.send('GET /\r\n\r\nthis the body')
    while True:
        sys.stdout.write(server.recv(1))
    sys.stdout.write('CLOSE\n')
            
thread.start_new_thread(test_client,())
thread.start_new_thread(test_client,())
thread.start_new_thread(test_client,())
server = HTTPServer('localhost', 8000, lambda e,r: ['data'])
asyncore.loop()
