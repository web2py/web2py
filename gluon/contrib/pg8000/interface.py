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

import socket
import protocol
import threading
from errors import *

def conninfo_parse(conninfo):
    "Conninfo parser routine based on libpq conninfo_parse"
    options = {}
    buf = conninfo + " "
    tmp = pname = ""
    quoted_string = False
    cp = 0
    while cp < len(buf):
        # Skip blanks before the parameter name
        c = buf[cp]
        if c.isspace() and tmp and not quoted_string and pname:
            options[pname] = tmp
            tmp = pname = ""
        elif c == "'":
            quoted_string = not quoted_string
        elif c == '\\':
            cp += 1
            tmp += buf[cp]      
        elif c == "=":
            if not tmp:
                raise RuntimeError("missing parameter name (conninfo:%s)" % cp)
            pname = tmp
            tmp = ""
        elif not c.isspace() or quoted_string:
            tmp += c
        cp += 1
    if quoted_string:
        raise RuntimeError("unterminated quoted string (conninfo:%s)" % cp)
    return options

class DataIterator(object):
    def __init__(self, obj, func):
        self.obj = obj
        self.func = func

    def __iter__(self):
        return self

    def next(self):
        retval = self.func(self.obj)
        if retval == None:
            raise StopIteration()
        return retval

statement_number_lock = threading.Lock()
statement_number = 0

##
# This class represents a prepared statement.  A prepared statement is
# pre-parsed on the server, which reduces the need to parse the query every
# time it is run.  The statement can have parameters in the form of $1, $2, $3,
# etc.  When parameters are used, the types of the parameters need to be
# specified when creating the prepared statement.
# <p>
# As of v1.01, instances of this class are thread-safe.  This means that a
# single PreparedStatement can be accessed by multiple threads without the
# internal consistency of the statement being altered.  However, the
# responsibility is on the client application to ensure that one thread reading
# from a statement isn't affected by another thread starting a new query with
# the same statement.
# <p>
# Stability: Added in v1.00, stability guaranteed for v1.xx.
#
# @param connection     An instance of {@link Connection Connection}.
#
# @param statement      The SQL statement to be represented, often containing
# parameters in the form of $1, $2, $3, etc.
#
# @param types          Python type objects for each parameter in the SQL
# statement.  For example, int, float, str.
class PreparedStatement(object):

    ##
    # Determines the number of rows to read from the database server at once.
    # Reading more rows increases performance at the cost of memory.  The
    # default value is 100 rows.  The affect of this parameter is transparent.
    # That is, the library reads more rows when the cache is empty
    # automatically.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.  It is
    # possible that implementation changes in the future could cause this
    # parameter to be ignored.
    row_cache_size = 100

    def __init__(self, connection, statement, *types, **kwargs):
        global statement_number
        if connection == None or connection.c == None:
            raise InterfaceError("connection not provided")
        try:
            statement_number_lock.acquire()
            self._statement_number = statement_number
            statement_number += 1
        finally:
            statement_number_lock.release()
        self.c = connection.c
        self._portal_name = None
        self._statement_name = kwargs.get("statement_name", "pg8000_statement_%s" % self._statement_number)
        self._row_desc = None
        self._cached_rows = []
        self._ongoing_row_count = 0
        self._command_complete = True
        self._parse_row_desc = self.c.parse(self._statement_name, statement, types)
        self._lock = threading.RLock()

    def close(self):
        if self._statement_name != "": # don't close unnamed statement
            self.c.close_statement(self._statement_name)
        if self._portal_name != None:
            self.c.close_portal(self._portal_name)
            self._portal_name = None

    row_description = property(lambda self: self._getRowDescription())
    def _getRowDescription(self):
        if self._row_desc == None:
            return None
        return self._row_desc.fields

    ##
    # Run the SQL prepared statement with the given parameters.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    def execute(self, *args, **kwargs):
        self._lock.acquire()
        try:
            if not self._command_complete:
                # cleanup last execute
                self._cached_rows = []
                self._ongoing_row_count = 0
            if self._portal_name != None:
                self.c.close_portal(self._portal_name)
            self._command_complete = False
            self._portal_name = "pg8000_portal_%s" % self._statement_number
            self._row_desc, cmd = self.c.bind(self._portal_name, self._statement_name, args, self._parse_row_desc, kwargs.get("stream"))
            if self._row_desc:
                # We execute our cursor right away to fill up our cache.  This
                # prevents the cursor from being destroyed, apparently, by a rogue
                # Sync between Bind and Execute.  Since it is quite likely that
                # data will be read from us right away anyways, this seems a safe
                # move for now.
                self._fill_cache()
            else:
                self._command_complete = True
                self._ongoing_row_count = -1
                if cmd != None and cmd.rows != None:
                    self._ongoing_row_count = cmd.rows
        finally:
            self._lock.release()

    def _fill_cache(self):
        self._lock.acquire()
        try:
            if self._cached_rows:
                raise InternalError("attempt to fill cache that isn't empty")
            end_of_data, rows = self.c.fetch_rows(self._portal_name, self.row_cache_size, self._row_desc)
            self._cached_rows = rows
            if end_of_data:
                self._command_complete = True
        finally:
            self._lock.release()

    def _fetch(self):
        if not self._row_desc:
            raise ProgrammingError("no result set")
        self._lock.acquire()
        try:
            if not self._cached_rows:
                if self._command_complete:
                    return None
                self._fill_cache()
                if self._command_complete and not self._cached_rows:
                    # fill cache tells us the command is complete, but yet we have
                    # no rows after filling our cache.  This is a special case when
                    # a query returns no rows.
                    return None
            row = self._cached_rows.pop(0)
            self._ongoing_row_count += 1
            return tuple(row)
        finally:
            self._lock.release()

    ##
    # Return a count of the number of rows relevant to the executed statement.
    # For a SELECT, this is the number of rows returned.  For UPDATE or DELETE,
    # this the number of rows affected.  For INSERT, the number of rows
    # inserted.  This property may have a value of -1 to indicate that there
    # was no row count.
    # <p>
    # During a result-set query (eg. SELECT, or INSERT ... RETURNING ...),
    # accessing this property requires reading the entire result-set into
    # memory, as reading the data to completion is the only way to determine
    # the total number of rows.  Avoid using this property in with
    # result-set queries, as it may cause unexpected memory usage.
    # <p>
    # Stability: Added in v1.03, stability guaranteed for v1.xx.
    row_count = property(lambda self: self._get_row_count())
    def _get_row_count(self):
        self._lock.acquire()
        try:
            if not self._command_complete:
                end_of_data, rows = self.c.fetch_rows(self._portal_name, 0, self._row_desc)
                self._cached_rows += rows
                if end_of_data:
                    self._command_complete = True
                else:
                    raise InternalError("fetch_rows(0) did not hit end of data")
            return self._ongoing_row_count + len(self._cached_rows)
        finally:
            self._lock.release()

    ##
    # Read a row from the database server, and return it in a dictionary
    # indexed by column name/alias.  This method will raise an error if two
    # columns have the same name.  Returns None after the last row.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    def read_dict(self):
        row = self._fetch()
        if row == None:
            return row
        retval = {}
        for i in range(len(self._row_desc.fields)):
            col_name = self._row_desc.fields[i]['name']
            if retval.has_key(col_name):
                raise InterfaceError("cannot return dict of row when two columns have the same name (%r)" % (col_name,))
            retval[col_name] = row[i]
        return retval

    ##
    # Read a row from the database server, and return it as a tuple of values.
    # Returns None after the last row.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    def read_tuple(self):
        return self._fetch()

    ##
    # Return an iterator for the output of this statement.  The iterator will
    # return a tuple for each row, in the same manner as {@link
    # #PreparedStatement.read_tuple read_tuple}.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    def iterate_tuple(self):
        return DataIterator(self, PreparedStatement.read_tuple)

    ##
    # Return an iterator for the output of this statement.  The iterator will
    # return a dict for each row, in the same manner as {@link
    # #PreparedStatement.read_dict read_dict}.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    def iterate_dict(self):
        return DataIterator(self, PreparedStatement.read_dict)


class SimpleStatement(PreparedStatement):
    "Internal wrapper to Simple Query protocol emulating a PreparedStatement"
    
    # This should be used internally only for trivial queries 
    # (not a true Prepared Statement, in fact it can have multiple statements)
    # See Simple Query Protocol limitations and trade-offs (send_simple_query)
    
    row_cache_size = None

    def __init__(self, connection, statement):
        if connection == None or connection.c == None:
            raise InterfaceError("connection not provided")
        self.c = connection.c
        self._row_desc = None
        self._cached_rows = []
        self._ongoing_row_count = -1
        self._command_complete = True
        self.statement = statement
        self._lock = threading.RLock()

    def close(self):
        # simple query doesn't have portals
        pass

    def execute(self, *args, **kwargs):
        "Run the SQL simple query stataments"
        self._lock.acquire()
        try:
            self._row_desc, cmd_complete, self._cached_rows = \
                self.c.send_simple_query(self.statement, kwargs.get("stream"))
            self._command_complete = True
            self._ongoing_row_count = -1
            if cmd_complete is not None and cmd_complete.rows is not None:
                self._ongoing_row_count = cmd_complete.rows
        finally:
            self._lock.release()

    def _fill_cache(self):
        # data rows are already fetched in _cached_rows
        pass

    def _fetch(self):
        if not self._row_desc:
            raise ProgrammingError("no result set")
        self._lock.acquire()
        try:
            if not self._cached_rows:
                return None
            row = self._cached_rows.pop(0)
            return tuple(row)
        finally:
            self._lock.release()

    def _get_row_count(self):
        return self._ongoing_row_count


##
# The Cursor class allows multiple queries to be performed concurrently with a
# single PostgreSQL connection.  The Cursor object is implemented internally by
# using a {@link PreparedStatement PreparedStatement} object, so if you plan to
# use a statement multiple times, you might as well create a PreparedStatement
# and save a small amount of reparsing time.
# <p>
# As of v1.01, instances of this class are thread-safe.  See {@link
# PreparedStatement PreparedStatement} for more information.
# <p>
# Stability: Added in v1.00, stability guaranteed for v1.xx.
#
# @param connection     An instance of {@link Connection Connection}.
class Cursor(object):
    def __init__(self, connection):
        self.connection = connection
        self._stmt = None

    def require_stmt(func):
        def retval(self, *args, **kwargs):
            if self._stmt == None:
                raise ProgrammingError("attempting to use unexecuted cursor")
            return func(self, *args, **kwargs)
        return retval

    row_description = property(lambda self: self._getRowDescription())
    def _getRowDescription(self):
        if self._stmt == None:
            return None
        return self._stmt.row_description

    ##
    # Run an SQL statement using this cursor.  The SQL statement can have
    # parameters in the form of $1, $2, $3, etc., which will be filled in by
    # the additional arguments passed to this function.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    # @param query      The SQL statement to execute.
    def execute(self, query, *args, **kwargs):
        if self.connection.is_closed:
            raise ConnectionClosedError()
        self.connection._unnamed_prepared_statement_lock.acquire()
        try:
            if kwargs.get("simple_query"):
                # no arguments and no statement name, 
                # use PostgreSQL Simple Query Protocol
                ## print "SimpleQuery:", query
                self._stmt = SimpleStatement(self.connection, query)
            else:
                # use PostgreSQL Extended Query Protocol
                self._stmt = PreparedStatement(self.connection, query, statement_name="", *[{"type": type(x), "value": x} for x in args])
            self._stmt.execute(*args, **kwargs)
        finally:
            self.connection._unnamed_prepared_statement_lock.release()

    ##
    # Return a count of the number of rows currently being read.  If possible,
    # please avoid using this function.  It requires reading the entire result
    # set from the database to determine the number of rows being returned.
    # <p>
    # Stability: Added in v1.03, stability guaranteed for v1.xx.
    # Implementation currently requires caching entire result set into memory,
    # avoid using this property.
    row_count = property(lambda self: self._get_row_count())

    @require_stmt
    def _get_row_count(self):
        return self._stmt.row_count

    ##
    # Read a row from the database server, and return it in a dictionary
    # indexed by column name/alias.  This method will raise an error if two
    # columns have the same name.  Returns None after the last row.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    @require_stmt
    def read_dict(self):
        return self._stmt.read_dict()

    ##
    # Read a row from the database server, and return it as a tuple of values.
    # Returns None after the last row.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    @require_stmt
    def read_tuple(self):
        return self._stmt.read_tuple()

    ##
    # Return an iterator for the output of this statement.  The iterator will
    # return a tuple for each row, in the same manner as {@link
    # #PreparedStatement.read_tuple read_tuple}.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    @require_stmt
    def iterate_tuple(self):
        return self._stmt.iterate_tuple()

    ##
    # Return an iterator for the output of this statement.  The iterator will
    # return a dict for each row, in the same manner as {@link
    # #PreparedStatement.read_dict read_dict}.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    @require_stmt
    def iterate_dict(self):
        return self._stmt.iterate_dict()

    def close(self):
        if self._stmt != None:
            self._stmt.close()
            self._stmt = None


    ##
    # Return the fileno of the underlying socket for this cursor's connection.
    # <p>
    # Stability: Added in v1.07, stability guaranteed for v1.xx.
    def fileno(self):
        return self.connection.fileno()

    ##
    # Poll the underlying socket for this cursor and sync if there is data waiting
    # to be read. This has the effect of flushing asynchronous messages from the
    # backend. Returns True if messages were read, False otherwise.
    # <p>
    # Stability: Added in v1.07, stability guaranteed for v1.xx.
    def isready(self):
        return self.connection.isready()
    

##
# This class represents a connection to a PostgreSQL database.
# <p>
# The database connection is derived from the {@link #Cursor Cursor} class,
# which provides a default cursor for running queries.  It also provides
# transaction control via the 'begin', 'commit', and 'rollback' methods.
# Without beginning a transaction explicitly, all statements will autocommit to
# the database.
# <p>
# As of v1.01, instances of this class are thread-safe.  See {@link
# PreparedStatement PreparedStatement} for more information.
# <p>
# Stability: Added in v1.00, stability guaranteed for v1.xx.
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
class Connection(Cursor):
    def __init__(self, dsn="", user=None, host=None, unix_sock=None, port=5432, database=None, password=None, socket_timeout=60, ssl=False):
        self._row_desc = None
        if dsn:
            # update connection parameters parsed of the conninfo dsn
            opts = conninfo_parse(dsn)
            database = opts.get("dbname", database)
            user = opts.get("user", user)
            password = opts.get("password", user)
            host = opts.get("host", host)
            port = int(opts.get("port", port))
            ssl = opts.get("sslmode", 'disable') != 'disable'
        try:
            self.c = protocol.Connection(unix_sock=unix_sock, host=host, port=port, socket_timeout=socket_timeout, ssl=ssl)
            self.c.authenticate(user, password=password, database=database)
        except socket.error, e:
            raise InterfaceError("communication error", e)
        Cursor.__init__(self, self)
        self._begin = PreparedStatement(self, "BEGIN TRANSACTION")
        self._commit = PreparedStatement(self, "COMMIT TRANSACTION")
        self._rollback = PreparedStatement(self, "ROLLBACK TRANSACTION")
        self._unnamed_prepared_statement_lock = threading.RLock()
        self.in_transaction = False
        self.autocommit = False

    ##
    # An event handler that is fired when NOTIFY occurs for a notification that
    # has been LISTEN'd for.  The value of this property is a
    # util.MulticastDelegate.  A callback can be added by using
    # connection.NotificationReceived += SomeMethod.  The method will be called
    # with a single argument, an object that has properties: backend_pid,
    # condition, and additional_info.  Callbacks can be removed with the -=
    # operator.
    # <p>
    # Stability: Added in v1.03, stability guaranteed for v1.xx.
    NotificationReceived = property(
            lambda self: getattr(self.c, "NotificationReceived"),
            lambda self, value: setattr(self.c, "NotificationReceived", value)
    )

    ##
    # An event handler that is fired when the database server issues a notice.
    # The value of this property is a util.MulticastDelegate.  A callback can
    # be added by using connection.NotificationReceived += SomeMethod.  The
    # method will be called with a single argument, an object that has
    # properties: severity, code, msg, and possibly others (detail, hint,
    # position, where, file, line, and routine).  Callbacks can be removed with
    # the -= operator.
    # <p>
    # Stability: Added in v1.03, stability guaranteed for v1.xx.
    NoticeReceived = property(
            lambda self: getattr(self.c, "NoticeReceived"),
            lambda self, value: setattr(self.c, "NoticeReceived", value)
    )

    ##
    # An event handler that is fired when a runtime configuration option is
    # changed on the server.  The value of this property is a
    # util.MulticastDelegate.  A callback can be added by using
    # connection.NotificationReceived += SomeMethod.  Callbacks can be removed
    # with the -= operator.  The method will be called with a single argument,
    # an object that has properties "key" and "value".
    # <p>
    # Stability: Added in v1.03, stability guaranteed for v1.xx.
    ParameterStatusReceived = property(
            lambda self: getattr(self.c, "ParameterStatusReceived"),
            lambda self, value: setattr(self.c, "ParameterStatusReceived", value)
    )

    ##
    # Begins a new transaction.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    def begin(self):
        if self.is_closed:
            raise ConnectionClosedError()
        if self.autocommit:
            return
        self._begin.execute()
        self.in_transaction = True


    ##
    # Commits the running transaction.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    def commit(self):
        if self.is_closed:
            raise ConnectionClosedError()
        self._commit.execute()
        self.in_transaction = False

    ##
    # Rolls back the running transaction.
    # <p>
    # Stability: Added in v1.00, stability guaranteed for v1.xx.
    def rollback(self):
        if self.is_closed:
            raise ConnectionClosedError()
        self._rollback.execute()
        self.in_transaction = False

    ##
    # Closes an open connection.
    def close(self):
        if self.is_closed:
            raise ConnectionClosedError()
        self.c.close()
        self.c = None

    is_closed = property(lambda self: self.c == None)

    ##
    # Return the fileno of the underlying socket for this connection.
    # <p>
    # Stability: Added in v1.07, stability guaranteed for v1.xx.
    def fileno(self):
        return self.c.fileno()

    ##
    # Poll the underlying socket for this connection and sync if there is data
    # waiting to be read. This has the effect of flushing asynchronous
    # messages from the backend. Returns True if messages were read, False
    # otherwise.
    # <p>
    # Stability: Added in v1.07, stability guaranteed for v1.xx.
    def isready(self):
        return self.c.isready()

    ##
    # Return the server_version as reported from the connected server.
    # Raises InterfaceError if no version has been reported from the server.
    def server_version(self):
        return self.c.server_version()

    def encoding(self, encoding=None):
        "Returns the client_encoding as reported from the connected server"
        return self.c.encoding()