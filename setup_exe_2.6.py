#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Usage:
    Install py2exe: http://sourceforge.net/projects/py2exe/files/
    Copy script to the web2py directory
    c:\bin\python26\python build_windows_exe.py py2exe

Adapted from http://bazaar.launchpad.net/~flavour/sahana-eden/trunk/view/head:/static/scripts/tools/standalone_exe.py
"""

from distutils.core import setup
import py2exe
from gluon.import_all import base_modules, contributed_modules
from glob import glob
import fnmatch
import os
import shutil
import sys
import re
import zipfile

# Python base version
python_version = sys.version[:3]

# List of modules deprecated in python2.6 that are in the above set
py26_deprecated = ['mhlib', 'multifile', 'mimify', 'sets', 'MimeWriter']

if python_version == '2.6':
    base_modules += ['json', 'multiprocessing']
    base_modules = list(set(base_modules).difference(set(py26_deprecated)))


#I don't know if this is even necessary
if python_version == '2.6':
    # Python26 compatibility: http://www.py2exe.org/index.cgi/Tutorial#Step52
    try:
        shutil.copytree('C:\Bin\Microsoft.VC90.CRT', 'dist/')
    except:
        print "You MUST copy Microsoft.VC90.CRT folder into the dist directory"

#read web2py version from VERSION file
web2py_version_line = readlines_file('VERSION')[0]
#use regular expression to get just the version number
v_re = re.compile('[0-9]+\.[0-9]+\.[0-9]+')
web2py_version = v_re.search(web2py_version_line).group(0)

setup(
  console=['web2py.py'],
  windows=[{'script':'web2py.py',
    'dest_base':'web2py_no_console' # MUST NOT be just 'web2py' otherwise it overrides the standard web2py.exe
    }],
  name="web2py",
  version=web2py_version,
  description="web2py web framework",
  author="Massimo DiPierro",
  license = "LGPL v3",
  data_files=[
        'ABOUT',
        'LICENSE',
        'VERSION',
        'splashlogo.gif',
        'logging.example.conf',
        'options_std.py',
        'app.example.yaml',
        'queue.example.yaml'
        ],
  options={'py2exe': {
    'packages': contributed_modules,
    'includes': base_modules,
    }},
  )

print "web2py binary successfully built"

#offer to remove Windows OS dlls user is unlikely to be able to distribute
print "The process of building a windows executable often includes copying files that belong to Windows."
delete_ms_files = raw_input("Delete API-MS-Win-* files that are probably unsafe for distribution? (Y/n) ")
if delete_ms_files.lower().startswith("y"):
    print "Deleted Microsoft files not licensed for open source distribution"
    print "You are still responsible for making sure you have the rights to distribute any other included files!"
    #delete the API-MS-Win-Core DLLs
    for f in glob ('dist/API-MS-Win-*.dll'):
        os.unlink (f)
    #then delete some other files belonging to Microsoft
    other_ms_files = ['KERNELBASE.dll', 'MPR.dll', 'MSWSOCK.dll', 'POWRPROF.dll']
    for f in other_ms_files:
        try:
            os.unlink(os.path.join('dist',f))
        except:
            print "unable to delete dist/"+f
            sys.exit(1)

#Offer to include applications
copy_apps = raw_input("Include your web2py application(s)? (Y/n) ")
if os.path.exists('dist/applications'):
    shutil.rmtree('dist/applications')
if copy_apps.lower().startswith("y"):
    shutil.copytree('applications', 'dist/applications')
    print "Your application(s) have been added"
else:
    shutil.copytree('applications/admin', 'dist/applications/admin')
    shutil.copytree('applications/welcome', 'dist/applications/welcome')
    shutil.copytree('applications/examples', 'dist/applications/examples')
    print "Only web2py's admin/welcome/examples applications have been added"
print ""

#Offer to copy project's site-packages into dist/site-packages
copy_apps = raw_input("Include your web2py site-packages & scripts folders? (Y/n) ")
if copy_apps.lower().startswith("y"):
    #copy site-packages
    if os.path.exists('dist/site-packages')
        shutil.rmtree('dist/site-packages')
    shutil.copytree('site-packages', 'dist/site-packages')
    #copy scripts
    if os.path.exists('dist/scripts'):
        shutil.rmtree('dist/scripts')
    shutil.copytree('scripts', 'dist/scripts')
else:
    #no worries, web2py will create the (empty) folder first run
    print "Skipping site-packages & scripts"
    pass


print ""

#borrowed from http://bytes.com/topic/python/answers/851018-how-zip-directory-python-using-zipfile
def recursive_zip(zipf, directory, folder = ""):
   for item in os.listdir(directory):
      if os.path.isfile(os.path.join(directory, item)):
         zipf.write(os.path.join(directory, item), folder + os.sep + item)
      elif os.path.isdir(os.path.join(directory, item)):
         recursive_zip(zipf, os.path.join(directory, item), folder + os.sep + item)

create_zip = raw_input("Create a zip file of web2py for Windows (Y/n)? ")
if create_zip.lower().startswith("y"):
    #to keep consistent with how official web2py windows zip file is setup,
    #create a web2py folder & copy dist's files into it
    shutil.copytree('dist','zip_temp/web2py')
    #create zip file
    zipf = zipfile.ZipFile("web2py_win.zip", "w", compression=zipfile.ZIP_DEFLATED )
    path = 'zip_temp' #just temp so the web2py directory is included in our zip file
    recursive_zip(zipf, path) #leave the first folder as None, as path is root.
    zipf.close()
    shutil.rmtree('zip_temp')
    print "Your Windows binary version of web2py can be found in web2py_win.zip"
    print "You may extract the archive anywhere and then run web2py/web2py.exe"

    # offer to clear up
    print "Since you created a zip file you likely do not need the build, deposit and dist folders used while building binary."
    clean_up_files = raw_input("Delete these un-necessary folders/files? (Y/n) ")
    if clean_up_files.lower().startswith("y"):
        shutil.rmtree('build')
        shutil.rmtree('deposit')
        shutil.rmtree('dist')
    else:
        print "Your Windows binary & associated files can also be found in /dist"
else:
    #Didn't want zip file created
    print ""
    print "Creation of web2py Windows binary completed."
    print "You should copy the /dist directory and its contents."
    print "To run use web2py.exe"
print "Finished!"
print "Enjoy web2py " +web2py_version_line





