#!/usr/bin/env python
# -*- coding: utf-8 -*-

# up to 2019, we have used py2applet, py2exe and bbfreeze for building web2py binaries
# The original scripts can be found on GitHub for web2py up to version 2.18.4
# See also Niphlod's work on http://www.web2pyslices.com/slice/show/1726/build-windows-binaries
# Then we switched to Pyinstaller in order to fully support Python 3

from distutils.core import setup
from gluon.import_all import base_modules, contributed_modules
from gluon.fileutils import readlines_file
from glob import glob
import os
import shutil
import sys
import re
import zipfile
import subprocess
import platform


USAGE = """
build_web2py - make web2py Windows and MacOS binaries with pyinstaller 
Usage:
    Install the pyinstaller program, copy this file (plus web2py.*.spec files) 
    to web2py root folder and run:
    
    python build_py3.py
    
    (tested with python 3.7.3 and 2.7.16 with PyInstaller 3.4)
"""
BUILD_DEBUG = False
"""
If BUILD_DEBUG is set to False, no gluon modules will be embedded inside the binary web2py.exe. 
    Thus, you can easily update the build version by changing the gluon folder inside the resulting ZIP file.
In case of problem , set BUILD_DEBUG to True. Then all the gluon modules will be analyzed and embedded, too.
    You can later analyze the .exe with 'pyi-archive_viewer web2py.exe' and then 'o PYZ-00.pyz'
    in order to check for missing system modules to be manually inserted in the SPEC file
 """

if len(sys.argv) != 1 or not os.path.isfile('web2py.py'):
    print(USAGE)
    sys.exit(1)
os_version = platform.system()
if os_version not in ('Windows', 'Darwin'):
    print('Unsupported system: %s' % os_version)
    sys.exit(1)


def unzip(source_filename, dest_dir):
    with zipfile.ZipFile(source_filename) as zf:
        zf.extractall(dest_dir)

# borrowed from http://bytes.com/topic/python/answers/851018-how-zip-directory-python-using-zipfile


def recursive_zip(zipf, directory, folder=""):
    for item in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, item)):
            zipf.write(os.path.join(directory, item), folder + os.sep + item)
        elif os.path.isdir(os.path.join(directory, item)):
            recursive_zip(
                zipf, os.path.join(directory, item), folder + os.sep + item)


# read web2py version from VERSION file
web2py_version_line = readlines_file('VERSION')[0]
# use regular expression to get just the version number
v_re = re.compile('[0-9]+\.[0-9]+\.[0-9]+')
web2py_version = v_re.search(web2py_version_line).group(0)

# Python base version
python_version = sys.version_info[:3]


if os_version == 'Windows':
    print("\nBuilding binary web2py for Windows\n")
    if BUILD_DEBUG: # debug only
        subprocess.call('pyinstaller --clean  --icon=extras/icons/web2py.ico \
                        --hidden-import=site-packages --hidden-import=gluon.packages.dal.pydal \
                        --hidden-import=gluon.packages.yatl.yatl web2py.py')
        zip_filename = 'web2py_win_debug'
    else: # normal run    
        subprocess.call('pyinstaller --clean  web2py.win.spec')
        subprocess.call('pyinstaller --clean  web2py.win_no_console.spec')
        source_no_console = 'dist/web2py_no_console/'
        files = 'web2py_no_console.exe'
        shutil.move(os.path.join(source_no_console, files), 'dist')
        shutil.rmtree(source_no_console)
        shutil.rmtree('build')
        zip_filename = 'web2py_win'

    source = 'dist/web2py/'
    for files in os.listdir(source):
        shutil.move(os.path.join(source, files), 'dist')
    shutil.rmtree(source)
    os.unlink('dist/web2py.exe.manifest')



    bin_folders = ['dist',]


elif os_version == 'Darwin':
    print("\nBuilding binary web2py for MacOS\n")

    if BUILD_DEBUG: #debug only    
        subprocess.call("pyinstaller --clean --icon=extras/icons/web2py.icns --hidden-import=gluon.packages.dal.pydal  --hidden-import=gluon.packages.yatl.yatl \
                        --hidden-import=site-packages --windowed web2py.py", shell=True)
        zip_filename = 'web2py_osx_debug'
    else: # normal run
        subprocess.call("pyinstaller --clean web2py.mac.spec", shell=True)
        # cleanup + move binary files to dist folder
        #shutil.rmtree(os.path.join('dist', 'web2py'))
        shutil.rmtree('build')
        zip_filename = 'web2py_osx'

    shutil.move((os.path.join('dist', 'web2py')),(os.path.join('dist', 'web2py_cmd')))
    bin_folders = [(os.path.join('dist', 'web2py.app/Contents/MacOS')), (os.path.join('dist', 'web2py_cmd'))]
    print("\nWeb2py binary successfully built!\n")


# add data_files
for req in ['CHANGELOG', 'LICENSE', 'VERSION']:
    for bin_folder in bin_folders:
        shutil.copy(req, os.path.join(bin_folder, req))
# cleanup unuseful binary cache
for dirpath, dirnames, files in os.walk('.'):
    if dirpath.endswith('__pycache__'):
        print('Deleting cached binary directory : %s' % dirpath)
        shutil.rmtree(dirpath)
for dirpath, dirnames, files in os.walk('.'):
    for file in files:
        if file.endswith('.pyc'):
            print('Deleting cached binary file : %s' % file)
            os.unlink(os.path.join(dirpath, file))
        
print("\nPreparing package ...")
# misc
for folders in ['gluon', 'extras', 'site-packages', 'scripts', 'applications', 'examples', 'handlers']:
    for bin_folder in bin_folders:
        shutil.copytree(folders, os.path.join(bin_folder, folders))
        if not os.path.exists(os.path.join(bin_folder, 'logs')):
             os.mkdir(os.path.join(bin_folder, 'logs'))


# create a web2py folder & copy dist's files into it
shutil.copytree('dist', 'zip_temp/web2py')
# create zip file
zipf = zipfile.ZipFile(zip_filename + ".zip",
                        "w", compression=zipfile.ZIP_DEFLATED)
# just temp so the web2py directory is included in our zip file
path = 'zip_temp'
# leave the first folder as None, as path is root.
recursive_zip(zipf, path)
zipf.close()
shutil.rmtree('zip_temp')
shutil.rmtree('dist')


print("Your binary version of web2py can be found in " + \
    zip_filename + ".zip")
print("You may extract the archive anywhere and then run web2py without worrying about dependency")
print("\nEnjoy binary web2py " + web2py_version_line + "\n with embedded Python " + sys.version + "\n")
