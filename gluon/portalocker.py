#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cross-platform (posix/nt) API for flock-style file locking.

Synopsis::

   import portalocker
   file = open(\"somefile\", \"r+\")
   portalocker.lock(file, portalocker.LOCK_EX)
   file.seek(12)
   file.write(\"foo\")
   file.close()

If you know what you're doing, you may choose to::

   portalocker.unlock(file)

before closing the file, but why?

Methods::

   lock( file, flags )
   unlock( file )

Constants::

   LOCK_EX - exclusive lock
   LOCK_SH - shared lock
   LOCK_NB - don't lock when locking

Original
---------
http://code.activestate.com/recipes/65203-portalocker-cross-platform-posixnt-api-for-flock-s/

I learned the win32 technique for locking files from sample code
provided by John Nielsen <nielsenjf@my-deja.com> in the documentation
that accompanies the win32 modules.

Author: Jonathan Feinberg <jdf@pobox.com>



Roundup Changes
---------------
2012-11-28 (anatoly techtonik)
   - Ported to ctypes
   - Dropped support for Win95, Win98 and WinME
   - Added return result

Web2py Changes
--------------
2016-07-28 (niphlod)
   - integrated original recipe, web2py's GAE warnings and roundup in a unique
     solution

"""

import logging
import platform
logger = logging.getLogger("web2py")

os_locking = None
try:
    import google.appengine
    os_locking = 'gae'
except:
    try:
        import fcntl
        os_locking = 'posix'
    except:
        try:
            import msvcrt
            import ctypes
            from ctypes.wintypes import BOOL, DWORD, HANDLE
            from ctypes import windll
            os_locking = 'windows'
        except:
            pass

if os_locking == 'windows':
    LOCK_SH = 0    # the default
    LOCK_NB = 0x1  # LOCKFILE_FAIL_IMMEDIATELY
    LOCK_EX = 0x2  # LOCKFILE_EXCLUSIVE_LOCK

    # --- the code is taken from pyserial project ---
    #
    # detect size of ULONG_PTR
    def is_64bit():
        return ctypes.sizeof(ctypes.c_ulong) != ctypes.sizeof(ctypes.c_void_p)
    if is_64bit():
        ULONG_PTR = ctypes.c_int64
    else:
        ULONG_PTR = ctypes.c_ulong
    PVOID = ctypes.c_void_p

    # --- Union inside Structure by stackoverflow:3480240 ---
    class _OFFSET(ctypes.Structure):
        _fields_ = [
            ('Offset', DWORD),
            ('OffsetHigh', DWORD)]

    class _OFFSET_UNION(ctypes.Union):
        _anonymous_ = ['_offset']
        _fields_ = [
            ('_offset', _OFFSET),
            ('Pointer', PVOID)]

    class OVERLAPPED(ctypes.Structure):
        _anonymous_ = ['_offset_union']
        _fields_ = [
            ('Internal', ULONG_PTR),
            ('InternalHigh', ULONG_PTR),
            ('_offset_union', _OFFSET_UNION),
            ('hEvent', HANDLE)]

    LPOVERLAPPED = ctypes.POINTER(OVERLAPPED)

    # --- Define function prototypes for extra safety ---
    LockFileEx = windll.kernel32.LockFileEx
    LockFileEx.restype = BOOL
    LockFileEx.argtypes = [HANDLE, DWORD, DWORD, DWORD, DWORD, LPOVERLAPPED]
    UnlockFileEx = windll.kernel32.UnlockFileEx
    UnlockFileEx.restype = BOOL
    UnlockFileEx.argtypes = [HANDLE, DWORD, DWORD, DWORD, LPOVERLAPPED]

    def lock(file, flags):
        """ Return True on success, False otherwise """
        hfile = msvcrt.get_osfhandle(file.fileno())
        overlapped = OVERLAPPED()
        LockFileEx(hfile, flags, 0, 0, 0xFFFF0000, ctypes.byref(overlapped))

    def unlock(file):
        hfile = msvcrt.get_osfhandle(file.fileno())
        overlapped = OVERLAPPED()
        UnlockFileEx(hfile, 0, 0, 0xFFFF0000, ctypes.byref(overlapped))

elif os_locking == 'posix':
    LOCK_EX = fcntl.LOCK_EX
    LOCK_SH = fcntl.LOCK_SH
    LOCK_NB = fcntl.LOCK_NB

    def lock(file, flags):
        fcntl.flock(file.fileno(), flags)

    def unlock(file):
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)


else:
    if os_locking != 'gae':
        logger.debug('no file locking, this will cause problems')

    LOCK_EX = None
    LOCK_SH = None
    LOCK_NB = None

    def lock(file, flags):
        pass

    def unlock(file):
        pass


class LockedFile(object):
    def __init__(self, filename, mode='rb'):
        self.filename = filename
        self.mode = mode
        self.file = None
        if 'r' in mode:
            self.file = open(filename, mode)
            lock(self.file, LOCK_SH)
        elif 'w' in mode or 'a' in mode:
            self.file = open(filename, mode.replace('w', 'a'))
            lock(self.file, LOCK_EX)
            if not 'a' in mode:
                self.file.seek(0)
                self.file.truncate(0)
        else:
            raise RuntimeError("invalid LockedFile(...,mode)")

    def read(self, size=None):
        return self.file.read() if size is None else self.file.read(size)

    def readline(self):
        return self.file.readline()

    def readlines(self):
        return self.file.readlines()

    def write(self, data):
        self.file.write(data)
        self.file.flush()

    def close(self):
        if self.file is not None:
            unlock(self.file)
            self.file.close()
            self.file = None

    def __del__(self):
        if self.file is not None:
            self.close()


def read_locked(filename):
    fp = LockedFile(filename, 'rb')
    data = fp.read()
    fp.close()
    return data


def write_locked(filename, data):
    fp = LockedFile(filename, 'wb')
    data = fp.write(data)
    fp.close()

if __name__ == '__main__':
    import sys
    f = LockedFile('test.txt', mode='wb')
    f.write('test ok')
    f.close()
    f = LockedFile('test.txt', mode='rb')
    sys.stdout.write(f.read()+'\n')
    f.close()
