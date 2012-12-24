import os
import time
N = 100000

t0 = time.time()
for k in xrange(N):
    os.urandom(16)
print (time.time()-t0)/N

from gluon.utils import fast_urandom16

t0 = time.time()
for k in xrange(N):
    fast_urandom16()
print (time.time()-t0)/N
