# vim: sw=4:expandtab:foldmethod=marker
#
# Copyright (c) 2007-2009, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

__author__ = "Mathieu Fenniak"

class Warning(StandardError):
    pass

class Error(StandardError):
    pass

class InterfaceError(Error):
    pass

class ConnectionClosedError(InterfaceError):
    def __init__(self):
        InterfaceError.__init__(self, "connection is closed")

class CursorClosedError(InterfaceError):
    def __init__(self):
        InterfaceError.__init__(self, "cursor is closed")

class DatabaseError(Error):
    pass

class DataError(DatabaseError):
    pass

class OperationalError(DatabaseError):
    pass

class IntegrityError(DatabaseError):
    pass

class InternalError(DatabaseError):
    pass

class ProgrammingError(DatabaseError):
    pass

class NotSupportedError(DatabaseError):
    pass

##
# An exception that is thrown when an internal error occurs trying to
# decode binary array data from the server.
class ArrayDataParseError(InternalError):
    pass

##
# Thrown when attempting to transmit an array of unsupported data types.
class ArrayContentNotSupportedError(NotSupportedError):
    pass

##
# Thrown when attempting to send an array that doesn't contain all the same
# type of objects (eg. some floats, some ints).
class ArrayContentNotHomogenousError(ProgrammingError):
    pass

##
# Attempted to pass an empty array in, but it's not possible to determine the
# data type for an empty array.
class ArrayContentEmptyError(ProgrammingError):
    pass

##
# Attempted to use a multidimensional array with inconsistent array sizes.
class ArrayDimensionsNotConsistentError(ProgrammingError):
    pass

# A cursor's copy_to or copy_from argument was not provided a table or query
# to operate on.
class CopyQueryOrTableRequiredError(ProgrammingError):
    pass

# Raised if a COPY query is executed without using copy_to or copy_from
# functions to provide a data stream.
class CopyQueryWithoutStreamError(ProgrammingError):
    pass

# When query parameters don't match up with query args.
class QueryParameterIndexError(ProgrammingError):
    pass

# Some sort of parse error occured during query parameterization.
class QueryParameterParseError(ProgrammingError):
    pass

