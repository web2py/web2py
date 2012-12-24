import os, time
from gluon.contrib.webclient import WebClient

s = WebClient('http://127.0.0.1:8000/test2/test/')
s.get('index')
print s.sessions
id = s.sessions['test2']
time.sleep(1)
#print os.path.getmtime(os.path.join('applications','test2','sessions',id))
s.get('index')
id = s.sessions['test2']
#print os.path.getmtime(os.path.join('applications','test2','sessions',id))




