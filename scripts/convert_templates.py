import glob, os

delimiters = ('<%','%>')

filenames = glob.glob('views/*')+glob.glob('views/*/*')
for filename in filenames:
    if not os.path.isdir(filename):
        page = open(filename,'rb').read()
        page = page.replace('{{',delimiters[0]+' ').replace('}}',' '+delimiters[1])
        open(filename,'wb').write(page)
code = open('models/db.py','rb').read()
code = code + '\n\n# custom delimiters for ractive.js or angular.js\nresponse.delimiters = %s\n' % repr(delimiters)
open('models/db.py','wb').write(code)
