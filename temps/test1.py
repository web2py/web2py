from gluon.storage import Storage as Storage
n=10000
import time

s = Storage()
t0 = time.time()
for k in range(n):
    s.x = 1
    y = s.x
print (time.time()-t0)/n
    
