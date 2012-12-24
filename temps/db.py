import sys
sys.path.append('/Users/massimodipierro/Dropbox/web2py/')
import pickle
from gluon import *
db = DAL()
print db
s = pickle.dumps(db)
db.close()
del db

a = pickle.loads(s)
print repr(a)
print str(a)
print BEAUTIFY(a).xml()
