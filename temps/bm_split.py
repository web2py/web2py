import os
import time
import re
N = 100000
r = re.compile('^(\S+)\s*\:\s*(.*?)\s*$')

a = "hello : world\r\n"

t0 = time.time()
for k in xrange(N):
    items = a.split(':',1)
    x,y = items[0].strip(),items[1].strip()
print (time.time()-t0)/N

from gluon.utils import fast_urandom16

t0 = time.time()
for k in xrange(N):
    x,y = a.split(':',1)
    x,y = x.strip(), y.strip()
print (time.time()-t0)/N
print x,y
