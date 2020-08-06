# -*- mode: python -*-

block_cipher = None


a = Analysis(['web2py.py'],
             pathex=['.'],
             binaries=[('/System/Library/Frameworks/Tk.framework/Tk', 'tk'), ('/System/Library/Frameworks/Tcl.framework/Tcl', 'tcl')],
             datas=[],
             hiddenimports=['site-packages', 'argparse', 'cgi', 'cgitb', 'code', 'concurrent', 'concurrent.futures', 
              'concurrent.futures._base', 'concurrent.futures.process', 'concurrent.futures.thread', 'configparser', 'cProfile', 'csv', 'ctypes.wintypes',
              'email.mime', 'email.mime.base', 'email.mime.multipart', 'email.mime.nonmultipart', 'email.mime.text', 'html.parser', 'http.cookies',
              'ipaddress', 'imaplib', 'imp', 'json', 'json.decoder', 'json.encoder', 'json.scanner', 'logging.config', 'logging.handlers', 'profile', 'pstats',
              'psycopg2', 'psycopg2._ipaddress', 'psycopg2._json', 'psycopg2._range', 'psycopg2.extensions', 'psycopg2.extras', 'psycopg2.sql',
              'psycopg2.tz', 'pyodbc', 'python-ldap', 'rlcompleter', 'sched', 'site', 'smtplib', 'sqlite3', 'sqlite3.dbapi2', 'sqlite3.dump', 'timeit', 'tkinter',
              'tkinter.commondialog', 'tkinter.constants', 'tkinter.messagebox', 'uuid', 'win32evtlogutil', 'wsgiref',
              'wsgiref.handlers', 'wsgiref.headers', 'wsgiref.simple_server', 'wsgiref.util', 'xml.dom', 'xml.dom.NodeFilter', 'xml.dom.domreg',
              'xml.dom.expatbuilder', 'xml.dom.minicompat', 'xml.dom.minidom', 'xml.dom.pulldom', 'xml.dom.xmlbuilder', 'xmlrpc.server'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['gluon'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='web2py',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon='extras/icons/web2py.icns')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='web2py')
app = BUNDLE(coll,
             name='web2py.app',
             icon='extras/icons/web2py.icns',
             bundle_identifier=None,
             info_plist={
            'NSPrincipleClass': 'NSApplication',
            'NSAppleScriptEnabled': False})
