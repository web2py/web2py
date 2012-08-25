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
from gluon.fileutils import readlines_file
from glob import glob
import fnmatch
import os
import shutil
import sys
import re
import zipfile

#read web2py version from VERSION file
web2py_version_line = readlines_file('VERSION')[0]
#use regular expression to get just the version number
v_re = re.compile('[0-9]+\.[0-9]+\.[0-9]+')
web2py_version = v_re.search(web2py_version_line).group(0)

#pull in preferences from config file
import ConfigParser
Config = ConfigParser.ConfigParser()
Config.read('setup_exe.conf')
remove_msft_dlls = Config.getboolean("Setup", "remove_microsoft_dlls")
copy_apps = Config.getboolean("Setup", "copy_apps")
copy_site_packages = Config.getboolean("Setup", "copy_site_packages")
copy_scripts = Config.getboolean("Setup", "copy_scripts")
make_zip = Config.getboolean("Setup", "make_zip")
zip_filename = Config.get("Setup", "zip_filename")
remove_build_files = Config.getboolean("Setup", "remove_build_files")


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

def copy_folders(source, destination):
    """Copy files & folders from source to destination (within dist/)"""
    if os.path.exists(os.path.join('dist',destination)):
        shutil.rmtree(os.path.join('dist',destination))
    shutil.copytree(os.path.join(source), os.path.join('dist',destination))

#should we remove Windows OS dlls user is unlikely to be able to distribute

if remove_msft_dlls:
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
            #sys.exit(1)


#Should we include applications?
if copy_apps:
    copy_folders('applications', 'applications')
    print "Your application(s) have been added"
else:
    #only copy web2py's default applications
    copy_folders('applications/admin', 'applications/admin')
    copy_folders('applications/welcome', 'applications/welcome')
    copy_folders('applications/examples', 'applications/examples')
    print "Only web2py's admin, examples & welcome applications have been added"


#should we copy project's site-packages into dist/site-packages
if copy_site_packages:
    #copy site-packages
    copy_folders('site-packages', 'site-packages')
else:
    #no worries, web2py will create the (empty) folder first run
    print "Skipping site-packages"
    pass

#should we copy project's scripts into dist/scripts
if copy_scripts:
    #copy scripts
    copy_folders('scripts', 'scripts')
else:
    #no worries, web2py will create the (empty) folder first run
    print "Skipping scripts"
    pass



#borrowed from http://bytes.com/topic/python/answers/851018-how-zip-directory-python-using-zipfile
def recursive_zip(zipf, directory, folder = ""):
   for item in os.listdir(directory):
      if os.path.isfile(os.path.join(directory, item)):
         zipf.write(os.path.join(directory, item), folder + os.sep + item)
      elif os.path.isdir(os.path.join(directory, item)):
         recursive_zip(zipf, os.path.join(directory, item), folder + os.sep + item)

#should we create a zip file of the build?

if make_zip:
    #to keep consistent with how official web2py windows zip file is setup,
    #create a web2py folder & copy dist's files into it
    shutil.copytree('dist','zip_temp/web2py')
    #create zip file
    #use filename specified via command line
    zipf = zipfile.ZipFile(zip_filename+".zip", "w", compression=zipfile.ZIP_DEFLATED )
    path = 'zip_temp' #just temp so the web2py directory is included in our zip file
    recursive_zip(zipf, path) #leave the first folder as None, as path is root.
    zipf.close()
    shutil.rmtree('zip_temp')
    print "Your Windows binary version of web2py can be found in "+zip_filename+".zip"
    print "You may extract the archive anywhere and then run web2py/web2py.exe"

#should py2exe build files be removed?
if remove_build_files:
    shutil.rmtree('build')
    shutil.rmtree('deposit')
    shutil.rmtree('dist')
    print "py2exe build files removed"

#final info
if not make_zip and not remove_build_files:
    print "Your Windows binary & associated files can also be found in /dist"

print "Finished!"
print "Enjoy web2py " +web2py_version_line





