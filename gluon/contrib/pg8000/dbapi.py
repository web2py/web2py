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

__version__ = "1.10"

import datetime
import time
import interface
import types
import threading
from errors import *

from warnings import warn

##
# The DBAPI level supported.  Currently 2.0.  This property is part of the
# DBAPI 2.0 specification.
apilevel = "2.0"

##
# Integer constant stating the level of thread safety the DBAPI interface
# supports.  This DBAPI interface supports sharing of the module, connections,
# and cursors.  This property is part of the DBAPI 2.0 specification.
threadsafety = 3

##
# String property stating the type of parameter marker formatting expected by
# the interface.  This value defaults to "format".  This property is part of
# the DBAPI 2.0 specification.
# <p>
# Unlike the DBAPI specification, this value is not constant.  It can be
# changed to any standard paramstyle value (ie. qmark, numeric, named, format,
# and pyformat).
paramstyle = 'format' # paramstyle can be changed to any DB-API paramstyle

def convert_paramstyle(src_style, query, args):
    # I don't see any way to avoid scanning the query string char by char,
    # so we might as well take that careful approach and create a
    # state-based scanner.  We'll use int variables for the state.
    #  0 -- outside quoted string
    #  1 -- inside single-quote string '...'
    #  2 -- inside quoted identifier   "..."
    #  3 -- inside escaped single-quote string, E'...'
    state = 0
    output_query = ""
    output_args = []
    if src_style == "numeric":
        output_args = args
    elif src_style in ("pyformat", "named"):
        mapping_to_idx = {}
    i = 0
    while 1:
        if i == len(query):
            break
        c = query[i]
        # print "begin loop", repr(i), repr(c), repr(state)
        if state == 0:
            if c == "'":
                i += 1
                output_query += c
                state = 1
            elif c == '"':
                i += 1
                output_query += c
                state = 2
            elif c == 'E':
                # check for escaped single-quote string
                i += 1
                if i < len(query) and i > 1 and query[i] == "'":
                    i += 1
                    output_query += "E'"
                    state = 3
                else:
                    output_query += c
            elif src_style == "qmark" and c == "?":
                i += 1
                param_idx = len(output_args)
                if param_idx == len(args):
                    raise QueryParameterIndexError("too many parameter fields, not enough parameters")
                output_args.append(args[param_idx])
                output_query += "$" + str(param_idx + 1)
            elif src_style == "numeric" and c == ":":
                i += 1
                if i < len(query) and i > 1 and query[i].isdigit():
                    output_query += "$" + query[i]
                    i += 1
                else:
                    raise QueryParameterParseError("numeric parameter : does not have numeric arg")
            elif src_style == "named" and c == ":":
                name = ""
                while 1:
                    i += 1
                    if i == len(query):
                        break
                    c = query[i]
                    if c.isalnum() or c == '_':
                        name += c
                    else:
                        break
                if name == "":
                    raise QueryParameterParseError("empty name of named parameter")
                idx = mapping_to_idx.get(name)
                if idx == None:
                    idx = len(output_args)
                    output_args.append(args[name])
                    idx += 1
                    mapping_to_idx[name] = idx
                output_query += "$" + str(idx)
            elif src_style == "format" and c == "%":
                i += 1
                if i < len(query) and i > 1:
                    if query[i] == "s":
                        param_idx = len(output_args)
                        if param_idx == len(args):
                            raise QueryParameterIndexError("too many parameter fields, not enough parameters")
                        output_args.append(args[param_idx])
                        output_query += "$" + str(param_idx + 1)
                    elif query[i] == "%":
                        output_query += "%"
                    else:
                        raise QueryParameterParseError("Only %s and %% are supported")
                    i += 1
                else:
                    raise QueryParameterParseError("format parameter % does not have format code")
            elif src_style == "pyformat" and c == "%":
                i += 1
                if i < len(query) and i > 1:
                    if query[i] == "(":
                        i += 1
                        # begin mapping name
                        end_idx = query.find(')', i)
                        if end_idx == -1:
                            raise QueryParameterParseError("began pyformat dict read, but couldn't find end of name")
                        else:
                            name = query[i:end_idx]
                            i = end_idx + 1
                            if i < len(query) and query[i] == "s":
                                i += 1
                                idx = mapping_to_idx.get(name)
                                if idx == None:
                                    idx = len(output_args)
                                    output_args.append(args[name])
                                    idx += 1
                                    mapping_to_idx[name] = idx
                                output_query += "$" + str(idx)
                            else:
                                raise QueryParameterParseError("format not specified or not supported (only %(...)s supported)")
                    elif query[i] == "%":
                        output_query += "%"
                    elif query[i] == "s":
                        # we have a %s in a pyformat query string.  Assume
                        # support for format instead.
                        i -= 1
                        src_style = "format"
                    else:
                        raise QueryParameterParseError("Only %(name)s, %s and %% are supported")
            else:
                i += 1
                output_query += c
        elif state == 1:
            output_query += c
            i += 1
            if c == "'":
                # Could be a double ''
                if i < len(query) and query[i] == "'":
                    # is a double quote.
                    output_query += query[i]
                    i += 1
                else:
                    state = 0
            elif src_style in ("pyformat","format") and c == "%":
                # hm... we're only going to support an escaped percent sign
                if i < len(query):
                    if query[i] == "%":
                        # good.  We already output the first percent sign.
                        i += 1
                    else:
                        raise QueryParameterParseError("'%" + query[i] + "' not supported in quoted string")
        elif state == 2:
            output_query += c
            i += 1
            if c == '"':
                state = 0
            elif src_style in ("pyformat","format") and c == "%":
                # hm... we're only going to support an escaped percent sign
                if i < len(query):
                    if query[i] == "%":
                        # good.  We already output the first percent sign.
                        i += 1
                    else:
                        raise QueryParameterParseError("'%" + query[i] + "' not supported in quoted string")
        elif state == 3:
            output_query += c
            i += 1
            if c == "\\":
                # check for escaped single-quote
                if i < len(query) and query[i] == "'":
                    output_query += "'"
                    i += 1
            elif c == "'":
                state = 0
            elif src_style in ("pyformat","format") and c == "%":
                # hm... we're only going to support an escaped percent sign
                if i < len(query):
                    if query[i] == "%":
                        # good.  We already output the first percent sign.
                        i += 1
                    else:
                        raise QueryParameterParseError("'%" + query[i] + "' not supported in quoted string")

    return output_query, tuple(output_args)

    
def require_open_cursor(fn):
    def _fn(self, *args, **kwargs):
        if self.cursor == None:
            raise CursorClosedError()
        return fn(self, *args, **kwargs)
    return _fn

##
# The class of object returned by the {@link #ConnectionWrapper.cursor cursor method}.
class CursorWrapper(object):
    def __init__(self, conn, connection):
        self.cursor = interface.Cursor(conn)
        self.arraysize = 1
        self._connection = connection
        self._override_rowcount = None

    ##
    # This read-only attribute returns a reference to the connection object on
    # which the cursor was created.
    # <p>
    # Stability: Part of a DBAPI 2.0 extension.  A warning "DB-API extension
    # cursor.connection used" will be fired.
    connection = property(lambda self: self._getConnection())

    def _getConnection(self):
        warn("DB-API extension cursor.connection used", stacklevel=3)
        return self._connection

    ##
    # This read-only attribute specifies the number of rows that the last
    # .execute*() produced (for DQL statements like 'select') or affected (for
    # DML statements like 'update' or 'insert').
    # <p>
    # The attribute is -1 in case no .execute*() has been performed on the
    # cursor or the rowcount of the last operation is cannot be determined by
    # the interface.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    rowcount = property(lambda self: self._getRowCount())

    @require_open_cursor
    def _getRowCount(self):
        if self._override_rowcount != None:
            return self._override_rowcount
        return self.cursor.row_count

    ##
    # This read-only attribute is a sequence of 7-item sequences.  Each value
    # contains information describing one result column.  The 7 items returned
    # for each column are (name, type_code, display_size, internal_size,
    # precision, scale, null_ok).  Only the first two values are provided by
    # this interface implementation.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    description = property(lambda self: self._getDescription())

    @require_open_cursor
    def _getDescription(self):
        if self.cursor.row_description == None:
            return None
        columns = []
        for col in self.cursor.row_description:
            columns.append((col["name"], col["type_oid"], None, None, None, None, None))
        return columns

    ##
    # Executes a database operation.  Parameters may be provided as a sequence
    # or mapping and will be bound to variables in the operation.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    @require_open_cursor
    def execute(self, operation, args=()):
        if not self._connection.in_transaction:
            self._connection.begin()
        self._override_rowcount = None
        self._execute(operation, args)

    def _execute(self, operation, args=()):
        new_query, new_args = convert_paramstyle(paramstyle, operation, args)
        try:
            self.cursor.execute(new_query, *new_args)
        except ConnectionClosedError:
            # can't rollback in this case
            raise
        except:
            # any error will rollback the transaction to-date
            self._connection.rollback()
            raise

    def copy_from(self, fileobj, table=None, sep='\t', null=None, query=None):
        if query == None:
            if table == None:
                raise CopyQueryOrTableRequiredError()
            query = "COPY %s FROM stdout DELIMITER '%s'" % (table, sep)
            if null is not None:
                query += " NULL '%s'" % (null,)
        self.copy_execute(fileobj, query)

    def copy_to(self, fileobj, table=None, sep='\t', null=None, query=None):
        if query == None:
            if table == None:
                raise CopyQueryOrTableRequiredError()
            query = "COPY %s TO stdout DELIMITER '%s'" % (table, sep)
            if null is not None:
                query += " NULL '%s'" % (null,)
        self.copy_execute(fileobj, query)
    
    @require_open_cursor
    def copy_execute(self, fileobj, query):
        try:
            self.cursor.execute(query, stream=fileobj)
        except ConnectionClosedError:
            # can't rollback in this case
            raise
        except:
            # any error will rollback the transaction to-date
            import traceback; traceback.print_exc()
            self._connection.rollback()
            raise

    ##
    # Prepare a database operation and then execute it against all parameter
    # sequences or mappings provided.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    @require_open_cursor
    def executemany(self, operation, parameter_sets):
        if not self._connection.in_transaction:
            self._connection.begin()
        self._override_rowcount = 0
        for parameters in parameter_sets:
            self._execute(operation, parameters)
            if self.cursor.row_count == -1 or self._override_rowcount == -1:
                self._override_rowcount = -1
            else:
                self._override_rowcount += self.cursor.row_count

    ##
    # Fetch the next row of a query result set, returning a single sequence, or
    # None when no more data is available.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    @require_open_cursor
    def fetchone(self):
        return self.cursor.read_tuple()

    ##
    # Fetch the next set of rows of a query result, returning a sequence of
    # sequences.  An empty sequence is returned when no more rows are
    # available.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    # @param size   The number of rows to fetch when called.  If not provided,
    #               the arraysize property value is used instead.
    def fetchmany(self, size=None):
        if size == None:
            size = self.arraysize
        rows = []
        for i in range(size):
            value = self.fetchone()
            if value == None:
                break
            rows.append(value)
        return rows

    ##
    # Fetch all remaining rows of a query result, returning them as a sequence
    # of sequences.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    @require_open_cursor
    def fetchall(self):
        return tuple(self.cursor.iterate_tuple())

    ##
    # Close the cursor.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    @require_open_cursor
    def close(self):
        self.cursor.close()
        self.cursor = None
        self._override_rowcount = None

    def next(self):
        warn("DB-API extension cursor.next() used", stacklevel=2)
        retval = self.fetchone()
        if retval == None:
            raise StopIteration()
        return retval

    def __iter__(self):
        warn("DB-API extension cursor.__iter__() used", stacklevel=2)
        return self

    def setinputsizes(self, sizes):
        pass

    def setoutputsize(self, size, column=None):
        pass

    @require_open_cursor
    def fileno(self):
        return self.cursor.fileno()
    
    @require_open_cursor
    def isready(self):
        return self.cursor.isready()

def require_open_connection(fn):
    def _fn(self, *args, **kwargs):
        if self.conn == None:
            raise ConnectionClosedError()
        return fn(self, *args, **kwargs)
    return _fn

##
# The class of object returned by the {@link #connect connect method}.
class ConnectionWrapper(object):
    # DBAPI Extension: supply exceptions as attributes on the connection
    Warning = property(lambda self: self._getError(Warning))
    Error = property(lambda self: self._getError(Error))
    InterfaceError = property(lambda self: self._getError(InterfaceError))
    DatabaseError = property(lambda self: self._getError(DatabaseError))
    OperationalError = property(lambda self: self._getError(OperationalError))
    IntegrityError = property(lambda self: self._getError(IntegrityError))
    InternalError = property(lambda self: self._getError(InternalError))
    ProgrammingError = property(lambda self: self._getError(ProgrammingError))
    NotSupportedError = property(lambda self: self._getError(NotSupportedError))

    def _getError(self, error):
        warn("DB-API extension connection.%s used" % error.__name__, stacklevel=3)
        return error

    @property
    def in_transaction(self):
        if self.conn:
             return self.conn.in_transaction
        return False

    def __init__(self, **kwargs):
        self.conn = interface.Connection(**kwargs)
        self.notifies = []
        self.notifies_lock = threading.Lock()
        self.conn.NotificationReceived += self._notificationReceived
        # Two Phase Commit internal attributes:
        self.__tpc_xid = None
        self.__tpc_prepared = None

    def set_autocommit(self, state):
        if self.conn.in_transaction and state and not self.conn.autocommit:
            warn("enabling autocommit in an open transaction!")
        self.conn.autocommit = state

    def get_autocommit(self):
        return self.conn.autocommit
    
    autocommit = property(get_autocommit, set_autocommit)

    @require_open_connection
    def begin(self):
        self.conn.begin()

    def _notificationReceived(self, notice):
        try:
        # psycopg2 compatible notification interface
            self.notifies_lock.acquire()
            self.notifies.append((notice.backend_pid, notice.condition))
        finally:
            self.notifies_lock.release()

    ##
    # Creates a {@link #CursorWrapper CursorWrapper} object bound to this
    # connection.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    @require_open_connection
    def cursor(self):
        return CursorWrapper(self.conn, self)

    ##
    # Commits the current database transaction.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    @require_open_connection
    def commit(self):
        # There's a threading bug here.  If a query is sent after the
        # commit, but before the begin, it will be executed immediately
        # without a surrounding transaction.  Like all threading bugs -- it
        # sounds unlikely, until it happens every time in one
        # application...  however, to fix this, we need to lock the
        # database connection entirely, so that no cursors can execute
        # statements on other threads.  Support for that type of lock will
        # be done later.
        if self.__tpc_xid:
            raise ProgrammingError("Cannot do a normal commit() inside a "
                                   "TPC transaction!")
        self.conn.commit()

    ##
    # Rolls back the current database transaction.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    @require_open_connection
    def rollback(self):
        # see bug description in commit.
        if self.__tpc_xid:
            raise ProgrammingError("Cannot do a normal rollback() inside a "
                                   "TPC transaction!")
        self.conn.rollback()

    ##
    # Closes the database connection.
    # <p>
    # Stability: Part of the DBAPI 2.0 specification.
    @require_open_connection
    def close(self):
        self.conn.close()
        self.conn = None

    ##
    # Returns the "server_version" string provided by the connected server.
    # <p>
    # Stability: Extension of the DBAPI 2.0 specification.
    @property
    @require_open_connection
    def server_version(self):
        return self.conn.server_version()

    # Stability: psycopg2 compatibility
    @require_open_connection
    def set_client_encoding(self, encoding=None):
        "Set the client encoding for the current session"
        if encoding:
            self.conn.execute("SET client_encoding TO '%s';" % (encoding, ), simple_query=True)
        return self.conn.encoding()

        
    def xid(self,format_id, global_transaction_id, branch_qualifier):
        """Create a Transaction IDs (only global_transaction_id is used in pg)
        format_id and branch_qualifier are not used in postgres
        global_transaction_id may be any string identifier supported by postgres
        returns a tuple (format_id, global_transaction_id, branch_qualifier)"""
        return (format_id, global_transaction_id, branch_qualifier)

    @require_open_connection
    def tpc_begin(self,xid):
        "Begin a two-phase transaction"
        # set auto-commit mode to begin a TPC transaction
        self.autocommit = False
        # (actually in postgres at this point it is a normal one)
        if self.conn.in_transaction:
            warn("tpc_begin() should be called outside a transaction block", 
                 stacklevel=3)
        self.conn.begin()
        # store actual TPC transaction id
        self.__tpc_xid = xid
        self.__tpc_prepared = False

    @require_open_connection    
    def tpc_prepare(self):
        "Prepare a two-phase transaction"
        if not self.__tpc_xid:
            raise ProgrammingError("tpc_prepare() outside a TPC transaction "
                                   "is not allowed!")
        # Prepare the TPC
        self.conn.execute("PREPARE TRANSACTION '%s';" % (self.__tpc_xid[1],), 
                          simple_query=True)
        self.conn.in_transaction = False
        self.__tpc_prepared = True
    
    @require_open_connection
    def tpc_commit(self, xid=None):
        "Commit a prepared two-phase transaction"
        try:
            # save current autocommit status (to be recovered later)
            previous_autocommit_mode = self.autocommit
            if not xid:
                # use current tpc transaction
                tpc_xid = self.__tpc_xid
            else:
                # use a recovered tpc transaction
                tpc_xid = xid
                if not xid in self.tpc_recover():
                    raise ProgrammingError("Requested TPC transaction is not "
                                           "prepared!")
            if not tpc_xid:
                raise ProgrammingError("Cannot tpc_commit() without a TPC "
                                       "transaction!")
            if self.__tpc_prepared or (xid != self.__tpc_xid and xid):
                # a two-phase commit:
                # set the auto-commit mode for TPC commit
                self.autocommit = True
                try:
                    self.conn.execute("COMMIT PREPARED '%s';" % (tpc_xid[1], ), 
                                      simple_query=True)
                finally:
                    # return to previous auto-commit mode
                    self.autocommit = previous_autocommit_mode
            else:
                try:
                    # a single-phase commit
                    self.conn.commit()
                finally:
                    # return to previous auto-commit mode
                    self.autocommit = previous_autocommit_mode
        finally:
            # transaction is done, clear xid
            self.__tpc_xid = None

    @require_open_connection
    def tpc_rollback(self, xid=None):
        "Commit a prepared two-phase transaction"
        try:
            # save current autocommit status (to be recovered later)
            previous_autocommit_mode = self.autocommit
            if not xid:
                # use current tpc transaction
                tpc_xid = self.__tpc_xid 
            else:
                # use a recovered tpc transaction
                tpc_xid = xid
                if not xid in self.tpc_recover():
                    raise ProgrammingError("Requested TPC transaction is not prepared!")
            if not tpc_xid:
                raise ProgrammingError("Cannot tpc_rollback() without a TPC prepared transaction!")
            if self.__tpc_prepared or (xid != self.__tpc_xid and xid):
                # a two-phase rollback
                # set auto-commit for the TPC rollback
                self.autocommit = True
                try:
                    self.conn.execute("ROLLBACK PREPARED '%s';" % (tpc_xid[1],), 
                                      simple_query=True)
                finally:
                    # return to previous auto-commit mode
                    self.autocommit = previous_autocommit_mode
            else:
                # a single-phase rollback
                try:
                    self.conn.rollback()
                finally:
                    # return to previous auto-commit mode
                    self.autocommit = previous_autocommit_mode                  
        finally:
            # transaction is done, clear xid
            self.__tpc_xid = None

    @require_open_connection
    def tpc_recover(self):
        "Returns a list of pending transaction IDs"
        previous_autocommit_mode = self.autocommit 
        if not self.conn.in_transaction and not self.autocommit:
            self.autocommit = True
        elif not self.autocommit:
            warn("tpc_recover() will open a transaction block", stacklevel=3)

        curs = self.cursor()
        xids = []
        try:
            # query system view that stores open (prepared) TPC transactions 
            curs.execute("SELECT gid FROM pg_prepared_xacts;");
            xids.extend([self.xid(0,row[0],'') for row in curs])
        finally:
            curs.close()
            # return to previous auto-commit mode
            self.autocommit = previous_autocommit_mode
        # return a list of TPC transaction ids (xid)
        return xids


##
# Creates a DBAPI 2.0 compatible interface to a PostgreSQL database.
# <p>
# Stability: Part of the DBAPI 2.0 specification.
#
# @param user   The username to connect to the PostgreSQL server with.  This
# parameter is required.
#
# @keyparam host   The hostname of the PostgreSQL server to connect with.
# Providing this parameter is necessary for TCP/IP connections.  One of either
# host, or unix_sock, must be provided.
#
# @keyparam unix_sock   The path to the UNIX socket to access the database
# through, for example, '/tmp/.s.PGSQL.5432'.  One of either unix_sock or host
# must be provided.  The port parameter will have no affect if unix_sock is
# provided.
#
# @keyparam port   The TCP/IP port of the PostgreSQL server instance.  This
# parameter defaults to 5432, the registered and common port of PostgreSQL
# TCP/IP servers.
#
# @keyparam database   The name of the database instance to connect with.  This
# parameter is optional, if omitted the PostgreSQL server will assume the
# database name is the same as the username.
#
# @keyparam password   The user password to connect to the server with.  This
# parameter is optional.  If omitted, and the database server requests password
# based authentication, the connection will fail.  On the other hand, if this
# parameter is provided and the database does not request password
# authentication, then the password will not be used.
#
# @keyparam socket_timeout  Socket connect timeout measured in seconds.
# Defaults to 60 seconds.
#
# @keyparam ssl     Use SSL encryption for TCP/IP socket.  Defaults to False.
#
# @return An instance of {@link #ConnectionWrapper ConnectionWrapper}.
def connect(dsn="", user=None, host=None, unix_sock=None, port=5432, database=None, password=None, socket_timeout=60, ssl=False):
    return ConnectionWrapper(dsn=dsn, user=user, host=host,
            unix_sock=unix_sock, port=port, database=database,
            password=password, socket_timeout=socket_timeout, ssl=ssl)

def Date(year, month, day):
    return datetime.date(year, month, day)

def Time(hour, minute, second):
    return datetime.time(hour, minute, second)

def Timestamp(year, month, day, hour, minute, second):
    return datetime.datetime(year, month, day, hour, minute, second)

def DateFromTicks(ticks):
    return Date(*time.localtime(ticks)[:3])

def TimeFromTicks(ticks):
    return Time(*time.localtime(ticks)[3:6])

def TimestampFromTicks(ticks):
    return Timestamp(*time.localtime(ticks)[:6])

##
# Construct an object holding binary data.
def Binary(value):
    return types.Bytea(value)

# I have no idea what this would be used for by a client app.  Should it be
# TEXT, VARCHAR, CHAR?  It will only compare against row_description's
# type_code if it is this one type.  It is the varchar type oid for now, this
# appears to match expectations in the DB API 2.0 compliance test suite.
STRING = 1043

# bytea type_oid
BINARY = 17

# numeric type_oid
NUMBER = 1700

# timestamp type_oid
DATETIME = 1114

# oid type_oid
ROWID = 26


