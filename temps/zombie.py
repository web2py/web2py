import sys
sys.path.append('../')
from gluon.dal import DAL, THREAD_LOCAL
import pickle

db =DAL()
s = pickle.dumps(db)
db.close()
a = pickle.loads(s)
print THREAD_LOCAL.db_instances, THREAD_LOCAL.db_instances_zombie
db =DAL()
print a is db
print THREAD_LOCAL.db_instances, THREAD_LOCAL.db_instances_zombie
b = pickle.loads(s)
print THREAD_LOCAL.db_instances, THREAD_LOCAL.db_instances_zombie
print a is b
c = DAL()
print a is c
