## Windows binaries

The windows binaries contain Python 64 bit version 3.7.3 or 2.7.16 with all the needed modules and the web2py in the specified version.
You don't need anything else to run them on Windows.  
At least on Windows 7, if you get an error stating that "api-ms-win-crt-runtime-l1-1-0.dll is missing" you have only to install the
free and official "Visual C++ Redistributable for Visual Studio" as described later


## Full Windows build recipe

1. get a clean Windows 10 (Windows 10 Professional English build 1809 64 bit, under Virtualbox in our case)
2. grab and install the official Python program: we've got version 3.7.3 or 2.7.16, 64 bit 
(https://www.python.org/ftp/python/3.7.2/python-3.7.2-amd64.exe ) + select  "add Python 3.7 to PATH" during its setup if Python 3. 
For Python 2 you need to manually add the folders for python27 and python27\Scripts to the system path.
3. update tools with   
"python -m pip install --upgrade pip"  
"pip install --upgrade setuptools"  
4. download and install python-win32, which is needed for web2py to work with all features enabled 
(https://github.com/mhammond/pywin32/releases/download/b224/pywin32-224.win-amd64-py3.7.exe)
5. grab latest web2py source from https://mdipierro.pythonanywhere.com/examples/static/web2py_src.zip (you need at least 2.18.3 for 
needed changes in gluon\admin.py). Unzip it in a dedicated folder, in this example C:\web2py - so that you have 
C:\web2py\web2py.py inside)
6. install PyInstaller with:  
        pip install pyinstaller  (we've got PyInstaller-3.4.tar.gz )  
7. download and install the free Microsoft Visual C++ Redistributable per Visual Studio 2017, 64 bit version, from 
 https://aka.ms/vs/15/release/vc_redist.x64.exe  
8. additional (but not required) packages to work better in the Windows world:  
pip install psycopg2 = psycopg2-2.7.7-cp37-cp37m-win_amd64.whl  
pip install pyodbc = pyodbc-4.0.26-cp37-cp37m-win_amd64.whl  
download the file python_ldap-3.1.0-cp37-cp37m-win_amd64.whl from https://www.lfd.uci.edu/~gohlke/pythonlibs/ and install it from that 
folder with the command 'pip install python_ldap-3.1.0-cp37-cp37m-win_amd64.whl'  

9. copy build_web2py.py, web2py.win.spec and web2py.win_no_console.spec from this folder to C:\web2py\  
10. (only for python 2) - due to a PyInstaller bug, you need to manually change the file gluon\rocket.py, line 26, from IS_JYTHON 
= platform.system() == 'Java'  to  IS_JYTHON = False
11. (optional, for having a full working interactive shell) change the fake site.py module included within the PyInstaller installation
with the content of the files web2py.site_37.py or web2py.site_27.py from this folder - see comments inside these files for details 
12. open a CMD and go to C:\web2py. Run:

    python build_web2py.py

If everything goes fine, you'll obtain the 64 bit binary build zipped as C:\web2py\web2py_win.zip.
If you try to run it in a 32 bit Windows system, you'll correctly get a 'web2py.exe not a valid Win32 application' error message.

## Gothca:
- at least on Windows 7, you can get an error stating that "api-ms-win-crt-runtime-l1-1-0.dll is missing". You can easily resolve it by
installing "Visual C++ Redistributable for Visual Studio" described earlier
