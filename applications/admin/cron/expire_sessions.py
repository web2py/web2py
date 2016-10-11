
import os, time, stat, logging
from gluon._compat import pickle

EXPIRATION_MINUTES = 60

path = os.path.join(request.folder, 'sessions')
if not os.path.exists(path):
    os.mkdir(path)
now = time.time()
for path, dirs, files in os.walk(path, topdown=False):
    for x in files:
        fullpath = os.path.join(path, x)
        try:
            filetime = os.stat(fullpath)[stat.ST_MTIME]  # get it before our io
            try:
                session_data = pickle.load(open(fullpath, 'rb+'))
                expiration = session_data['auth']['expiration']
            except:
                expiration = EXPIRATION_MINUTES * 60
            if (now - filetime) > expiration:
                os.unlink(fullpath)
        except:
            logging.exception('failure to check %s' % fullpath)
    for d in dirs:
        dd = os.path.join(path, d)
        if not os.listdir(dd):
            os.rmdir(dd)
