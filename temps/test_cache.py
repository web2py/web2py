import sys, time
sys.path.append('/Users/massimodipierro/Dropbox/web2py')
from gluon.cache import CacheOnDisk
from gluon.storage import Storage
request = Storage()
request.folder = '/Users/massimodipierro/Dropbox/web2py/applications/welcome'
c = CacheOnDisk(request)
hello = c('key',lambda:'hello',0)
print hello
hello = c('key',lambda:'world',None)
print hello
hello = c('key',lambda:'world',1)
print hello
time.sleep(2)
hello = c('key',lambda:'world',1)
print hello
