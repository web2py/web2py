# run with web2py.py -S welcome -N -R thisfile.py
import time

db=DAL()
db.define_table('test',Field('one'))
db(db.test).delete()
for k in range(1000):
    db.test.insert(one='one')
db.commit()

n = 100
t0 = time.time()
for k in range(n):
    y = db.test.one
print 'time to access field obj',(time.time()-t0)/n

t0 = time.time()
for k in range(n):
    rows = db(db.test).select(cacheable=False) # (*)
print 'time to select 1000 recods',(time.time()-t0)/n/1000

row = db(db.test).select().first()
t0 = time.time()
for k in range(n):
    y = row.id
    y = row.one
print 'time to access field values',(time.time()-t0)/n

"""
Results:

web2py 1.99.7

time to access field obj     5.068 (microseconds)
time to select 1000 recods  38.441 (microseconds)
time to access field values  7.710 (microseconds)
total time to access one field for each of 1000 records: 7748 (microseconds) 

web2py 2.0
time to access field obj     0.579 (microseconds)
time to select 1000 recods  33.820 (microseconds)
time to access field values  0.338 (microseconds)
total time to access one field for each of 1000 records: 371 (microseconds)
 
web2py 2.0 w cacheable = True (*)

time to access field obj     0.579 (microseconds)
time to select 1000 recods  24.741 (microseconds)
time to access field values  0.300 (microseconds)
total time to access one field for each of 1000 records: 324 (microseconds)

(benhcmarks with SQLite on Mac Air and python 2.7)
"""

