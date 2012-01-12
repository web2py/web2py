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
try:
    import ssl as sslmodule
except ImportError:
    sslmodule = None
import select
import threading
import struct
import hashlib
from cStringIO import StringIO

from errors import *
from util import MulticastDelegate
import types

##
# An SSLRequest message.  To initiate an SSL-encrypted connection, an
# SSLRequest message is used rather than a {@link StartupMessage
# StartupMessage}.  A StartupMessage is still sent, but only after SSL
# negotiation (if accepted).
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class SSLRequest(object):
    def __init__(self):
        pass

    # Int32(8) - Message length, including self.<br>
    # Int32(80877103) - The SSL request code.<br>
    def serialize(self):
        return struct.pack("!ii", 8, 80877103)


##
# A StartupMessage message.  Begins a DB session, identifying the user to be
# authenticated as and the database to connect to.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class StartupMessage(object):
    def __init__(self, user, database=None):
        self.user = user
        self.database = database

    # Int32 - Message length, including self.
    # Int32(196608) - Protocol version number.  Version 3.0.
    # Any number of key/value pairs, terminated by a zero byte:
    #   String - A parameter name (user, database, or options)
    #   String - Parameter value
    def serialize(self):
        protocol = 196608
        val = struct.pack("!i", protocol)
        val += "user\x00" + self.user + "\x00"
        if self.database:
            val += "database\x00" + self.database + "\x00"
        val += "\x00"
        val = struct.pack("!i", len(val) + 4) + val
        return val


##
# Parse message.  Creates a prepared statement in the DB session.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
#
# @param ps         Name of the prepared statement to create.
# @param qs         Query string.
# @param type_oids  An iterable that contains the PostgreSQL type OIDs for
#                   parameters in the query string.
class Parse(object):
    def __init__(self, ps, qs, type_oids):
        if isinstance(qs, unicode):
            raise TypeError("qs must be encoded byte data")
        self.ps = ps
        self.qs = qs
        self.type_oids = type_oids

    def __repr__(self):
        return "<Parse ps=%r qs=%r>" % (self.ps, self.qs)

    # Byte1('P') - Identifies the message as a Parse command.
    # Int32 -   Message length, including self.
    # String -  Prepared statement name.  An empty string selects the unnamed
    #           prepared statement.
    # String -  The query string.
    # Int16 -   Number of parameter data types specified (can be zero).
    # For each parameter:
    #   Int32 - The OID of the parameter data type.
    def serialize(self):
        val = self.ps + "\x00" + self.qs + "\x00"
        val = val + struct.pack("!h", len(self.type_oids))
        for oid in self.type_oids:
            # Parse message doesn't seem to handle the -1 type_oid for NULL
            # values that other messages handle.  So we'll provide type_oid 705,
            # the PG "unknown" type.
            if oid == -1: oid = 705
            val = val + struct.pack("!i", oid)
        val = struct.pack("!i", len(val) + 4) + val
        val = "P" + val
        return val


##
# Bind message.  Readies a prepared statement for execution.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
#
# @param portal     Name of the destination portal.
# @param ps         Name of the source prepared statement.
# @param in_fc      An iterable containing the format codes for input
#                   parameters.  0 = Text, 1 = Binary.
# @param params     The parameters.
# @param out_fc     An iterable containing the format codes for output
#                   parameters.  0 = Text, 1 = Binary.
# @param kwargs     Additional arguments to pass to the type conversion
#                   methods.
class Bind(object):
    def __init__(self, portal, ps, in_fc, params, out_fc, **kwargs):
        self.portal = portal
        self.ps = ps
        self.in_fc = in_fc
        self.params = []
        for i in range(len(params)):
            if len(self.in_fc) == 0:
                fc = 0
            elif len(self.in_fc) == 1:
                fc = self.in_fc[0]
            else:
                fc = self.in_fc[i]
            self.params.append(types.pg_value(params[i], fc, **kwargs))
        self.out_fc = out_fc

    def __repr__(self):
        return "<Bind p=%r s=%r>" % (self.portal, self.ps)

    # Byte1('B') - Identifies the Bind command.
    # Int32 - Message length, including self.
    # String - Name of the destination portal.
    # String - Name of the source prepared statement.
    # Int16 - Number of parameter format codes.
    # For each parameter format code:
    #   Int16 - The parameter format code.
    # Int16 - Number of parameter values.
    # For each parameter value:
    #   Int32 - The length of the parameter value, in bytes, not including this
    #           this length.  -1 indicates a NULL parameter value, in which no
    #           value bytes follow.
    #   Byte[n] - Value of the parameter.
    # Int16 - The number of result-column format codes.
    # For each result-column format code:
    #   Int16 - The format code.
    def serialize(self):
        retval = StringIO()
        retval.write(self.portal + "\x00")
        retval.write(self.ps + "\x00")
        retval.write(struct.pack("!h", len(self.in_fc)))
        for fc in self.in_fc:
            retval.write(struct.pack("!h", fc))
        retval.write(struct.pack("!h", len(self.params)))
        for param in self.params:
            if param == None:
                # special case, NULL value
                retval.write(struct.pack("!i", -1))
            else:
                retval.write(struct.pack("!i", len(param)))
                retval.write(param)
        retval.write(struct.pack("!h", len(self.out_fc)))
        for fc in self.out_fc:
            retval.write(struct.pack("!h", fc))
        val = retval.getvalue()
        val = struct.pack("!i", len(val) + 4) + val
        val = "B" + val
        return val


##
# A Close message, used for closing prepared statements and portals.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
#
# @param typ    'S' for prepared statement, 'P' for portal.
# @param name   The name of the item to close.
class Close(object):
    def __init__(self, typ, name):
        if len(typ) != 1:
            raise InternalError("Close typ must be 1 char")
        self.typ = typ
        self.name = name

    # Byte1('C') - Identifies the message as a close command.
    # Int32 - Message length, including self.
    # Byte1 - 'S' for prepared statement, 'P' for portal.
    # String - The name of the item to close.
    def serialize(self):
        val = self.typ + self.name + "\x00"
        val = struct.pack("!i", len(val) + 4) + val
        val = "C" + val
        return val


##
# A specialized Close message for a portal.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class ClosePortal(Close):
    def __init__(self, name):
        Close.__init__(self, "P", name)


##
# A specialized Close message for a prepared statement.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class ClosePreparedStatement(Close):
    def __init__(self, name):
        Close.__init__(self, "S", name)


##
# A Describe message, used for obtaining information on prepared statements
# and portals.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
#
# @param typ    'S' for prepared statement, 'P' for portal.
# @param name   The name of the item to close.
class Describe(object):
    def __init__(self, typ, name):
        if len(typ) != 1:
            raise InternalError("Describe typ must be 1 char")
        self.typ = typ
        self.name = name

    # Byte1('D') - Identifies the message as a describe command.
    # Int32 - Message length, including self.
    # Byte1 - 'S' for prepared statement, 'P' for portal.
    # String - The name of the item to close.
    def serialize(self):
        val = self.typ + self.name + "\x00"
        val = struct.pack("!i", len(val) + 4) + val
        val = "D" + val
        return val


##
# A specialized Describe message for a portal.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class DescribePortal(Describe):
    def __init__(self, name):
        Describe.__init__(self, "P", name)

    def __repr__(self):
        return "<DescribePortal %r>" % (self.name)


##
# A specialized Describe message for a prepared statement.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class DescribePreparedStatement(Describe):
    def __init__(self, name):
        Describe.__init__(self, "S", name)

    def __repr__(self):
        return "<DescribePreparedStatement %r>" % (self.name)


##
# A Flush message forces the backend to deliver any data pending in its
# output buffers.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class Flush(object):
    # Byte1('H') - Identifies the message as a flush command.
    # Int32(4) - Length of message, including self.
    def serialize(self):
        return 'H\x00\x00\x00\x04'

    def __repr__(self):
        return "<Flush>"

##
# Causes the backend to close the current transaction (if not in a BEGIN/COMMIT
# block), and issue ReadyForQuery.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class Sync(object):
    # Byte1('S') - Identifies the message as a sync command.
    # Int32(4) - Length of message, including self.
    def serialize(self):
        return 'S\x00\x00\x00\x04'

    def __repr__(self):
        return "<Sync>"


##
# Transmits a password.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class PasswordMessage(object):
    def __init__(self, pwd):
        self.pwd = pwd

    # Byte1('p') - Identifies the message as a password message.
    # Int32 - Message length including self.
    # String - The password.  Password may be encrypted.
    def serialize(self):
        val = self.pwd + "\x00"
        val = struct.pack("!i", len(val) + 4) + val
        val = "p" + val
        return val


##
# Requests that the backend execute a portal and retrieve any number of rows.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
# @param row_count  The number of rows to return.  Can be zero to indicate the
#                   backend should return all rows. If the portal represents a
#                   query that does not return rows, no rows will be returned
#                   no matter what the row_count.
class Execute(object):
    def __init__(self, portal, row_count):
        self.portal = portal
        self.row_count = row_count

    # Byte1('E') - Identifies the message as an execute message.
    # Int32 -   Message length, including self.
    # String -  The name of the portal to execute.
    # Int32 -   Maximum number of rows to return, if portal contains a query that
    #           returns rows.  0 = no limit.
    def serialize(self):
        val = self.portal + "\x00" + struct.pack("!i", self.row_count)
        val = struct.pack("!i", len(val) + 4) + val
        val = "E" + val
        return val


class SimpleQuery(object):
    "Requests that the backend execute a Simple Query (SQL string)"
    
    def __init__(self, query_string):
        self.query_string = query_string

    # Byte1('Q') - Identifies the message as an query message.
    # Int32 -   Message length, including self.
    # String -  The query string itself.
    def serialize(self):
        val = self.query_string + "\x00"
        val = struct.pack("!i", len(val) + 4) + val
        val = "Q" + val
        return val

    def __repr__(self):
        return "<SimpleQuery qs=%r>" % (self.query_string)

##
# Informs the backend that the connection is being closed.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class Terminate(object):
    def __init__(self):
        pass

    # Byte1('X') - Identifies the message as a terminate message.
    # Int32(4) - Message length, including self.
    def serialize(self):
        return 'X\x00\x00\x00\x04'

##
# Base class of all Authentication[*] messages.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class AuthenticationRequest(object):
    def __init__(self, data):
        pass

    # Byte1('R') - Identifies the message as an authentication request.
    # Int32(8) - Message length, including self.
    # Int32 -   An authentication code that represents different
    #           authentication messages:
    #               0 = AuthenticationOk
    #               5 = MD5 pwd
    #               2 = Kerberos v5 (not supported by pg8000)
    #               3 = Cleartext pwd (not supported by pg8000)
    #               4 = crypt() pwd (not supported by pg8000)
    #               6 = SCM credential (not supported by pg8000)
    #               7 = GSSAPI (not supported by pg8000)
    #               8 = GSSAPI data (not supported by pg8000)
    #               9 = SSPI (not supported by pg8000)
    # Some authentication messages have additional data following the
    # authentication code.  That data is documented in the appropriate class.
    def createFromData(data):
        ident = struct.unpack("!i", data[:4])[0]
        klass = authentication_codes.get(ident, None)
        if klass != None:
            return klass(data[4:])
        else:
            raise NotSupportedError("authentication method %r not supported" % (ident,))
    createFromData = staticmethod(createFromData)

    def ok(self, conn, user, **kwargs):
        raise InternalError("ok method should be overridden on AuthenticationRequest instance")

##
# A message representing that the backend accepting the provided username
# without any challenge.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class AuthenticationOk(AuthenticationRequest):
    def ok(self, conn, user, **kwargs):
        return True


##
# A message representing the backend requesting an MD5 hashed password
# response.  The response will be sent as md5(md5(pwd + login) + salt).
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class AuthenticationMD5Password(AuthenticationRequest):
    # Additional message data:
    #  Byte4 - Hash salt.
    def __init__(self, data):
        self.salt = "".join(struct.unpack("4c", data))

    def ok(self, conn, user, password=None, **kwargs):
        if password == None:
            raise InterfaceError("server requesting MD5 password authentication, but no password was provided")
        pwd = "md5" + hashlib.md5(hashlib.md5(password + user).hexdigest() + self.salt).hexdigest()
        conn._send(PasswordMessage(pwd))
        conn._flush()

        reader = MessageReader(conn)
        reader.add_message(AuthenticationRequest, lambda msg, reader: reader.return_value(msg.ok(conn, user)), reader)
        reader.add_message(ErrorResponse, self._ok_error)
        return reader.handle_messages()

    def _ok_error(self, msg):
        if msg.code == "28000":
            raise InterfaceError("md5 password authentication failed")
        else:
            raise msg.createException()

authentication_codes = {
    0: AuthenticationOk,
    5: AuthenticationMD5Password,
}


##
# ParameterStatus message sent from backend, used to inform the frotnend of
# runtime configuration parameter changes.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class ParameterStatus(object):
    def __init__(self, key, value):
        self.key = key
        self.value = value

    # Byte1('S') - Identifies ParameterStatus
    # Int32 - Message length, including self.
    # String - Runtime parameter name.
    # String - Runtime parameter value.
    def createFromData(data):
        key = data[:data.find("\x00")]
        value = data[data.find("\x00")+1:-1]
        return ParameterStatus(key, value)
    createFromData = staticmethod(createFromData)


##
# BackendKeyData message sent from backend.  Contains a connection's process
# ID and a secret key.  Can be used to terminate the connection's current
# actions, such as a long running query.  Not supported by pg8000 yet.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class BackendKeyData(object):
    def __init__(self, process_id, secret_key):
        self.process_id = process_id
        self.secret_key = secret_key

    # Byte1('K') - Identifier.
    # Int32(12) - Message length, including self.
    # Int32 - Process ID.
    # Int32 - Secret key.
    def createFromData(data):
        process_id, secret_key = struct.unpack("!2i", data)
        return BackendKeyData(process_id, secret_key)
    createFromData = staticmethod(createFromData)


##
# Message representing a query with no data.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class NoData(object):
    # Byte1('n') - Identifier.
    # Int32(4) - Message length, including self.
    def createFromData(data):
        return NoData()
    createFromData = staticmethod(createFromData)


##
# Message representing a successful Parse.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class ParseComplete(object):
    # Byte1('1') - Identifier.
    # Int32(4) - Message length, including self.
    def createFromData(data):
        return ParseComplete()
    createFromData = staticmethod(createFromData)


##
# Message representing a successful Bind.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class BindComplete(object):
    # Byte1('2') - Identifier.
    # Int32(4) - Message length, including self.
    def createFromData(data):
        return BindComplete()
    createFromData = staticmethod(createFromData)


##
# Message representing a successful Close.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class CloseComplete(object):
    # Byte1('3') - Identifier.
    # Int32(4) - Message length, including self.
    def createFromData(data):
        return CloseComplete()
    createFromData = staticmethod(createFromData)


##
# Message representing data from an Execute has been received, but more data
# exists in the portal.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class PortalSuspended(object):
    # Byte1('s') - Identifier.
    # Int32(4) - Message length, including self.
    def createFromData(data):
        return PortalSuspended()
    createFromData = staticmethod(createFromData)


##
# Message representing the backend is ready to process a new query.
# <p>
# Stability: This is an internal class.  No stability guarantee is made.
class ReadyForQuery(object):
    def __init__(self, status):
        self._status = status

    ##
    # I = Idle, T = Idle in Transaction, E = idle in failed transaction.
    status = property(lambda self: self._status)

    def __repr__(self):
        return "<ReadyForQuery %s>" % \
                {"I": "Idle", "T": "Idle in Transaction", "E": "Idle in Failed Transaction"}[self.status]

    # Byte1('Z') - Identifier.
    # Int32(5) - Message length, including self.
    # Byte1 -   Status indicator.
    def createFromData(data):
        return ReadyForQuery(data)
    createFromData = staticmethod(createFromData)


##
# Represents a notice sent from the server.  This is not the same as a
# notification.  A notice is just additional information about a query, such
# as a notice that a primary key has automatically been created for a table.
# <p>
# A NoticeResponse instance will have properties containing the data sent
# from the server:
# <ul>
# <li>severity -- "ERROR", "FATAL', "PANIC", "WARNING", "NOTICE", "DEBUG",
# "INFO", or "LOG".  Always present.</li>
# <li>code -- the SQLSTATE code for the error.  See Appendix A of the
# PostgreSQL documentation for specific error codes.  Always present.</li>
# <li>msg -- human-readable error message.  Always present.</li>
# <li>detail -- Optional additional information.</li>
# <li>hint -- Optional suggestion about what to do about the issue.</li>
# <li>position -- Optional index into the query string.</li>
# <li>where -- Optional context.</li>
# <li>file -- Source-code file.</li>
# <li>line -- Source-code line.</li>
# <li>routine -- Source-code routine.</li>
# </ul>
# <p>
# Stability: Added in pg8000 v1.03.  Required properties severity, code, and
# msg are guaranteed for v1.xx.  Other properties should be checked with
# hasattr before accessing.
class NoticeResponse(object):
    responseKeys = {
        "S": "severity",  # always present
        "C": "code",      # always present
        "M": "msg",       # always present
        "D": "detail",
        "H": "hint",
        "P": "position",
        "p": "_position",
        "q": "_query",
        "W": "where",
        "F": "file",
        "L": "line",
        "R": "routine",
    }

    def __init__(self, **kwargs):
        for arg, value in kwargs.items():
            setattr(self, arg, value)

    def __repr__(self):
        return "<NoticeResponse %s %s %r>" % (self.severity, self.code, self.msg)

    def dataIntoDict(data):
        retval = {}
        for s in data.split("\x00"):
            if not s: continue
            key, value = s[0], s[1:]
            key = NoticeResponse.responseKeys.get(key, key)
            retval[key] = value
        return retval
    dataIntoDict = staticmethod(dataIntoDict)

    # Byte1('N') - Identifier
    # Int32 - Message length
    # Any number of these, followed by a zero byte:
    #   Byte1 - code identifying the field type (see responseKeys)
    #   String - field value
    def createFromData(data):
        return NoticeResponse(**NoticeResponse.dataIntoDict(data))
    createFromData = staticmethod(createFromData)


##
# A message sent in case of a server-side error.  Contains the same properties
# that {@link NoticeResponse NoticeResponse} contains.
# <p>
# Stability: Added in pg8000 v1.03.  Required properties severity, code, and
# msg are guaranteed for v1.xx.  Other properties should be checked with
# hasattr before accessing.
class ErrorResponse(object):
    def __init__(self, **kwargs):
        for arg, value in kwargs.items():
            setattr(self, arg, value)

    def __repr__(self):
        return "<ErrorResponse %s %s %r>" % (self.severity, self.code, self.msg)

    def createException(self):
        return ProgrammingError(self.severity, self.code, self.msg)

    def createFromData(data):
        return ErrorResponse(**NoticeResponse.dataIntoDict(data))
    createFromData = staticmethod(createFromData)


##
# A message sent if this connection receives a NOTIFY that it was LISTENing for.
# <p>
# Stability: Added in pg8000 v1.03.  When limited to accessing properties from
# a notification event dispatch, stability is guaranteed for v1.xx.
class NotificationResponse(object):
    def __init__(self, backend_pid, condition, additional_info):
        self._backend_pid = backend_pid
        self._condition = condition
        self._additional_info = additional_info

    ##
    # An integer representing the process ID of the backend that triggered
    # the NOTIFY.
    # <p>
    # Stability: Added in pg8000 v1.03, stability guaranteed for v1.xx.
    backend_pid = property(lambda self: self._backend_pid)

    ##
    # The name of the notification fired.
    # <p>
    # Stability: Added in pg8000 v1.03, stability guaranteed for v1.xx.
    condition = property(lambda self: self._condition)

    ##
    # Currently unspecified by the PostgreSQL documentation as of v8.3.1.
    # <p>
    # Stability: Added in pg8000 v1.03, stability guaranteed for v1.xx.
    additional_info = property(lambda self: self._additional_info)

    def __repr__(self):
        return "<NotificationResponse %s %s %r>" % (self.backend_pid, self.condition, self.additional_info)

    def createFromData(data):
        backend_pid = struct.unpack("!i", data[:4])[0]
        data = data[4:]
        null = data.find("\x00")
        condition = data[:null]
        data = data[null+1:]
        null = data.find("\x00")
        additional_info = data[:null]
        return NotificationResponse(backend_pid, condition, additional_info)
    createFromData = staticmethod(createFromData)


class ParameterDescription(object):
    def __init__(self, type_oids):
        self.type_oids = type_oids
    def createFromData(data):
        count = struct.unpack("!h", data[:2])[0]
        type_oids = struct.unpack("!" + "i"*count, data[2:])
        return ParameterDescription(type_oids)
    createFromData = staticmethod(createFromData)


class RowDescription(object):
    def __init__(self, fields):
        self.fields = fields

    def createFromData(data):
        count = struct.unpack("!h", data[:2])[0]
        data = data[2:]
        fields = []
        for i in range(count):
            null = data.find("\x00")
            field = {"name": data[:null]}
            data = data[null+1:]
            field["table_oid"], field["column_attrnum"], field["type_oid"], field["type_size"], field["type_modifier"], field["format"] = struct.unpack("!ihihih", data[:18])
            data = data[18:]
            fields.append(field)
        return RowDescription(fields)
    createFromData = staticmethod(createFromData)

class CommandComplete(object):
    def __init__(self, command, rows=None, oid=None):
        self.command = command
        self.rows = rows
        self.oid = oid

    def createFromData(data):
        values = data[:-1].split(" ")
        args = {}
        args['command'] = values[0]
        if args['command'] in ("INSERT", "DELETE", "UPDATE", "MOVE", "FETCH", "COPY", "SELECT"):
            args['rows'] = int(values[-1])
            if args['command'] == "INSERT":
                args['oid'] = int(values[1])
        else:
            args['command'] = data[:-1]
        return CommandComplete(**args)
    createFromData = staticmethod(createFromData)


class DataRow(object):
    def __init__(self, fields):
        self.fields = fields

    def createFromData(data):
        count = struct.unpack("!h", data[:2])[0]
        data = data[2:]
        fields = []
        for i in range(count):
            val_len = struct.unpack("!i", data[:4])[0]
            data = data[4:]
            if val_len == -1:
                fields.append(None)
            else:
                fields.append(data[:val_len])
                data = data[val_len:]
        return DataRow(fields)
    createFromData = staticmethod(createFromData)


class CopyData(object):
    # "d": CopyData,
    def __init__(self, data):
        self.data = data

    def createFromData(data):
        return CopyData(data)
    createFromData = staticmethod(createFromData)
    
    def serialize(self):
        return 'd' + struct.pack('!i', len(self.data) + 4) + self.data


class CopyDone(object):
    # Byte1('c') - Identifier.
    # Int32(4) - Message length, including self.

    def createFromData(data):
        return CopyDone()

    createFromData = staticmethod(createFromData)
    
    def serialize(self):
        return 'c\x00\x00\x00\x04'

class CopyOutResponse(object):
    # Byte1('H')
    # Int32(4) - Length of message contents in bytes, including self.
    # Int8(1) - 0 textual, 1 binary
    # Int16(2) - Number of columns
    # Int16(N) - Format codes for each column (0 text, 1 binary)

    def __init__(self, is_binary, column_formats):
        self.is_binary = is_binary
        self.column_formats = column_formats
    
    def createFromData(data):
        is_binary, num_cols = struct.unpack('!bh', data[:3])
        column_formats = struct.unpack('!' + ('h' * num_cols), data[3:])
        return CopyOutResponse(is_binary, column_formats)

    createFromData = staticmethod(createFromData)


class CopyInResponse(object):
    # Byte1('G')
    # Otherwise the same as CopyOutResponse
    
    def __init__(self, is_binary, column_formats):
        self.is_binary = is_binary
        self.column_formats = column_formats
    
    def createFromData(data):
        is_binary, num_cols = struct.unpack('!bh', data[:3])
        column_formats = struct.unpack('!' + ('h' * num_cols), data[3:])
        return CopyInResponse(is_binary, column_formats)

    createFromData = staticmethod(createFromData)


class EmptyQueryResponse(object):
    # Byte1('I')
    # Response to an empty query string. (This substitutes for CommandComplete.)
    
    def createFromData(data):
        return EmptyQueryResponse()
    createFromData = staticmethod(createFromData)


class MessageReader(object):
    def __init__(self, connection):
        self._conn = connection
        self._msgs = []

        # If true, raise exception from an ErrorResponse after messages are
        # processed.  This can be used to leave the connection in a usable
        # state after an error response, rather than having unconsumed
        # messages that won't be understood in another context.
        self.delay_raising_exception = False

        self.ignore_unhandled_messages = False

    def add_message(self, msg_class, handler, *args, **kwargs):
        self._msgs.append((msg_class, handler, args, kwargs))

    def clear_messages(self):
        self._msgs = []

    def return_value(self, value):
        self._retval = value
    
    def handle_messages(self):
        exc = None
        while 1:
            msg = self._conn._read_message()
            msg_handled = False
            for (msg_class, handler, args, kwargs) in self._msgs:
                if isinstance(msg, msg_class):
                    msg_handled = True
                    retval = handler(msg, *args, **kwargs)
                    if retval:
                        # The handler returned a true value, meaning that the
                        # message loop should be aborted.
                        if exc != None:
                            raise exc
                        return retval
                    elif hasattr(self, "_retval"):
                        # The handler told us to return -- used for non-true
                        # return values
                        if exc != None:
                            raise exc
                        return self._retval
            if msg_handled:
                continue
            elif isinstance(msg, ErrorResponse):
                exc = msg.createException()
                if not self.delay_raising_exception:
                    raise exc
            elif isinstance(msg, NoticeResponse):
                self._conn.handleNoticeResponse(msg)
            elif isinstance(msg, ParameterStatus):
                self._conn.handleParameterStatus(msg)
            elif isinstance(msg, NotificationResponse):
                self._conn.handleNotificationResponse(msg)
            elif not self.ignore_unhandled_messages:
                raise InternalError("Unexpected response msg %r" % (msg))

def sync_on_error(fn):
    def _fn(self, *args, **kwargs):
        try:
            self._sock_lock.acquire()
            return fn(self, *args, **kwargs)
        except:
            self._sync()
            raise
        finally:
            self._sock_lock.release()
    return _fn

class Connection(object):
    def __init__(self, unix_sock=None, host=None, port=5432, socket_timeout=60, ssl=False):
        self._client_encoding = "ascii"
        self._integer_datetimes = False
        self._server_version = None
        self._sock_buf = ""
        self._sock_buf_pos = 0
        self._send_sock_buf = []
        self._block_size = 8192
        self._sock_lock = threading.Lock()
        if unix_sock == None and host != None:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        elif unix_sock != None:
            if not hasattr(socket, "AF_UNIX"):
                raise InterfaceError("attempt to connect to unix socket on unsupported platform")
            self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        else:
            raise ProgrammingError("one of host or unix_sock must be provided")
        if unix_sock == None and host != None:
            self._sock.connect((host, port))
        elif unix_sock != None:
            self._sock.connect(unix_sock)
        if ssl:
            self._sock_lock.acquire()
            try:
                self._send(SSLRequest())
                self._flush()
                resp = self._sock.recv(1)
                if resp == 'S' and sslmodule is not None:
                    self._sock = sslmodule.wrap_socket(self._sock)
                elif sslmodule is None:
                    raise InterfaceError("SSL required but ssl module not available in this python installation")
                else:
                    raise InterfaceError("server refuses SSL")
            finally:
                self._sock_lock.release()
        else:
            # settimeout causes ssl failure, on windows.  Python bug 1462352.
            self._sock.settimeout(socket_timeout)
        self._state = "noauth"
        self._backend_key_data = None

        self.NoticeReceived = MulticastDelegate()
        self.ParameterStatusReceived = MulticastDelegate()
        self.NotificationReceived = MulticastDelegate()

        self.ParameterStatusReceived += self._onParameterStatusReceived

    def verifyState(self, state):
        if self._state != state:
            raise InternalError("connection state must be %s, is %s" % (state, self._state))

    def _send(self, msg):
        assert self._sock_lock.locked()
        ##print "_send(%r)" % msg
        data = msg.serialize()
        if not isinstance(data, str):
            raise TypeError("bytes data expected")
        self._send_sock_buf.append(data)
    
    def _flush(self):
        assert self._sock_lock.locked()
        self._sock.sendall("".join(self._send_sock_buf))
        del self._send_sock_buf[:]

    def _read_bytes(self, byte_count):
        retval = []
        bytes_read = 0
        while bytes_read < byte_count:
            if self._sock_buf_pos == len(self._sock_buf):
                self._sock_buf = self._sock.recv(1024)
                self._sock_buf_pos = 0
            rpos = min(len(self._sock_buf), self._sock_buf_pos + (byte_count - bytes_read))
            addt_data = self._sock_buf[self._sock_buf_pos:rpos]
            bytes_read += (rpos - self._sock_buf_pos)
            assert bytes_read <= byte_count
            self._sock_buf_pos = rpos
            retval.append(addt_data)
        return "".join(retval)

    def _read_message(self):
        assert self._sock_lock.locked()
        bytes = self._read_bytes(5)
        message_code = bytes[0]
        data_len = struct.unpack("!i", bytes[1:])[0] - 4
        bytes = self._read_bytes(data_len)
        assert len(bytes) == data_len
        msg = message_types[message_code].createFromData(bytes)
        ##print "_read_message() -> %r" % msg
        return msg

    def authenticate(self, user, **kwargs):
        self.verifyState("noauth")
        self._sock_lock.acquire()
        try:
            self._send(StartupMessage(user, database=kwargs.get("database",None)))
            self._flush()

            reader = MessageReader(self)
            reader.add_message(AuthenticationRequest, self._authentication_request(user, **kwargs))
            reader.handle_messages()
        finally:
            self._sock_lock.release()

    def _authentication_request(self, user, **kwargs):
        def _func(msg):
            assert self._sock_lock.locked()
            if not msg.ok(self, user, **kwargs):
                raise InterfaceError("authentication method %s failed" % msg.__class__.__name__)
            self._state = "auth"
            reader = MessageReader(self)
            reader.add_message(ReadyForQuery, self._ready_for_query)
            reader.add_message(BackendKeyData, self._receive_backend_key_data)
            reader.handle_messages()
            return 1
        return _func

    def _ready_for_query(self, msg):
        self._state = "ready"
        return True

    def _receive_backend_key_data(self, msg):
        self._backend_key_data = msg

    @sync_on_error
    def parse(self, statement, qs, param_types):
        self.verifyState("ready")

        type_info = [types.pg_type_info(x) for x in param_types]
        param_types, param_fc = [x[0] for x in type_info], [x[1] for x in type_info] # zip(*type_info) -- fails on empty arr
        if isinstance(qs, unicode):
            qs = qs.encode(self._client_encoding)
        self._send(Parse(statement, qs, param_types))
        self._send(DescribePreparedStatement(statement))
        self._send(Flush())
        self._flush()

        reader = MessageReader(self)

        # ParseComplete is good.
        reader.add_message(ParseComplete, lambda msg: 0)

        # Well, we don't really care -- we're going to send whatever we
        # want and let the database deal with it.  But thanks anyways!
        reader.add_message(ParameterDescription, lambda msg: 0)

        # We're not waiting for a row description.  Return something
        # destinctive to let bind know that there is no output.
        reader.add_message(NoData, lambda msg: (None, param_fc))

        # Common row description response
        reader.add_message(RowDescription, lambda msg: (msg, param_fc))

        return reader.handle_messages()

    @sync_on_error
    def bind(self, portal, statement, params, parse_data, copy_stream):
        self.verifyState("ready")

        row_desc, param_fc = parse_data
        if row_desc == None:
            # no data coming out
            output_fc = ()
        else:
            # We've got row_desc that allows us to identify what we're going to
            # get back from this statement.
            output_fc = [types.py_type_info(f) for f in row_desc.fields]
        self._send(Bind(portal, statement, param_fc, params, output_fc, client_encoding = self._client_encoding, integer_datetimes = self._integer_datetimes))
        # We need to describe the portal after bind, since the return
        # format codes will be different (hopefully, always what we
        # requested).
        self._send(DescribePortal(portal))
        self._send(Flush())
        self._flush()

        # Read responses from server...
        reader = MessageReader(self)

        # BindComplete is good -- just ignore
        reader.add_message(BindComplete, lambda msg: 0)

        # NoData in this case means we're not executing a query.  As a
        # result, we won't be fetching rows, so we'll never execute the
        # portal we just created... unless we execute it right away, which
        # we'll do.
        reader.add_message(NoData, self._bind_nodata, portal, reader, copy_stream)

        # Return the new row desc, since it will have the format types we
        # asked the server for
        reader.add_message(RowDescription, lambda msg: (msg, None))

        return reader.handle_messages()

    def _copy_in_response(self, copyin, fileobj, old_reader):
        if fileobj == None:
            raise CopyQueryWithoutStreamError()
        while True:
            data = fileobj.read(self._block_size)
            if not data:
                break
            self._send(CopyData(data))
            self._flush()
        self._send(CopyDone())
        self._send(Sync())
        self._flush()

    def _copy_out_response(self, copyout, fileobj, old_reader):
        if fileobj == None:
            raise CopyQueryWithoutStreamError()
        reader = MessageReader(self)
        reader.add_message(CopyData, self._copy_data, fileobj)
        reader.add_message(CopyDone, lambda msg: 1)
        reader.handle_messages()

    def _copy_data(self, copydata, fileobj):
        fileobj.write(copydata.data)

    def _bind_nodata(self, msg, portal, old_reader, copy_stream):
        # Bind message returned NoData, causing us to execute the command.
        self._send(Execute(portal, 0))
        self._send(Sync())
        self._flush()

        output = {}
        reader = MessageReader(self)
        reader.add_message(CopyOutResponse, self._copy_out_response, copy_stream, reader)
        reader.add_message(CopyInResponse, self._copy_in_response, copy_stream, reader)
        reader.add_message(CommandComplete, lambda msg, out: out.setdefault('msg', msg) and False, output)
        reader.add_message(ReadyForQuery, lambda msg: 1)
        reader.delay_raising_exception = True
        reader.handle_messages()

        old_reader.return_value((None, output['msg']))

    @sync_on_error
    def send_simple_query(self, query_string, copy_stream=None):
        "Submit a simple query (PQsendQuery)"

        # Only use this for trivial queries, as its use is discouraged because:
        # CONS:
        # - Parameter are "injected" (they should be escaped by the app)
        # - Exesive memory usage (allways returns all rows on completion)
        # - Inneficient transmission of data in plain text (except for FETCH)
        # - No Prepared Statement support, each query is parsed every time
        # - Basic implementation: minimal error recovery and type support
        # PROS: 
        # - compact: equivalent to Parse, Bind, Describe, Execute, Close, Sync
        # - doesn't returns ParseComplete, BindComplete, CloseComplete, NoData
        # - it supports multiple statements in a single query string
        # - it is available when the Streaming Replication Protocol is actived
        # NOTE: this is the protocol used by psycopg2
        #       (they also uses named cursors to overcome some drawbacks)

        self.verifyState("ready")

        if isinstance(query_string, unicode):
            query_string = query_string.encode(self._client_encoding)

        self._send(SimpleQuery(query_string))
        self._flush()
        
        # define local storage for message handlers:
        output = {}
        rows = []

        # create and add handlers for all the possible messages:
        reader = MessageReader(self)
        
        # read row description but continue processing messages... (return false)
        reader.add_message(RowDescription, lambda msg, out: out.setdefault('row_desc', msg) and False, output)
        reader.add_message(DataRow, lambda msg: self._fetch_datarow(msg, rows, output['row_desc']))
        reader.add_message(EmptyQueryResponse, lambda msg: False)
        reader.add_message(CommandComplete, lambda msg, out: out.setdefault('complete', msg) and False, output)        
        reader.add_message(CopyInResponse, self._copy_in_response, copy_stream, reader)
        reader.add_message(CopyOutResponse, self._copy_out_response, copy_stream, reader)
        # messages  indicating that we've hit the end of the available data for this command
        reader.add_message(ReadyForQuery, lambda msg: 1)
        # process all messages and then raise exceptions (if any)
        reader.delay_raising_exception = True
        # start processing the messages from the backend:
        retval = reader.handle_messages()

        # return a dict with command complete / row description message values
        return output.get('row_desc'), output.get('complete'), rows
        
    @sync_on_error
    def fetch_rows(self, portal, row_count, row_desc):
        self.verifyState("ready")

        self._send(Execute(portal, row_count))
        self._send(Flush())
        self._flush()
        rows = []

        reader = MessageReader(self)
        reader.add_message(DataRow, self._fetch_datarow, rows, row_desc)
        reader.add_message(PortalSuspended, lambda msg: 1)
        reader.add_message(CommandComplete, self._fetch_commandcomplete, portal)
        retval = reader.handle_messages()

        # retval = 2 when command complete, indicating that we've hit the
        # end of the available data for this command
        return (retval == 2), rows

    def _fetch_datarow(self, msg, rows, row_desc):
        rows.append(
            [
                types.py_value(
                    msg.fields[i],
                    row_desc.fields[i],
                    client_encoding=self._client_encoding,
                    integer_datetimes=self._integer_datetimes,
                )
                for i in range(len(msg.fields))
            ]
        )

    def _fetch_commandcomplete(self, msg, portal):
        self._send(ClosePortal(portal))
        self._send(Sync())
        self._flush()

        reader = MessageReader(self)
        reader.add_message(ReadyForQuery, self._fetch_commandcomplete_rfq)
        reader.add_message(CloseComplete, lambda msg: False)
        reader.handle_messages()

        return 2  # signal end-of-data

    def _fetch_commandcomplete_rfq(self, msg):
        self._state = "ready"
        return True

    # Send a Sync message, then read and discard all messages until we
    # receive a ReadyForQuery message.
    def _sync(self):
        # it is assumed _sync is called from sync_on_error, which holds
        # a _sock_lock throughout the call
        self._send(Sync())
        self._flush()
        reader = MessageReader(self)
        reader.ignore_unhandled_messages = True
        reader.add_message(ReadyForQuery, lambda msg: True)
        reader.handle_messages()

    def close_statement(self, statement):
        if self._state == "closed":
            return
        self.verifyState("ready")
        self._sock_lock.acquire()
        try:
            self._send(ClosePreparedStatement(statement))
            self._send(Sync())
            self._flush()

            reader = MessageReader(self)
            reader.add_message(CloseComplete, lambda msg: 0)
            reader.add_message(ReadyForQuery, lambda msg: 1)
            reader.handle_messages()
        finally:
            self._sock_lock.release()

    def close_portal(self, portal):
        if self._state == "closed":
            return
        self.verifyState("ready")
        self._sock_lock.acquire()
        try:
            self._send(ClosePortal(portal))
            self._send(Sync())
            self._flush()

            reader = MessageReader(self)
            reader.add_message(CloseComplete, lambda msg: 0)
            reader.add_message(ReadyForQuery, lambda msg: 1)
            reader.handle_messages()
        finally:
            self._sock_lock.release()

    def close(self):
        self._sock_lock.acquire()
        try:
            self._send(Terminate())
            self._flush()
            self._sock.close()
            self._state = "closed"
        finally:
            self._sock_lock.release()

    def _onParameterStatusReceived(self, msg):
        if msg.key == "client_encoding":
            self._client_encoding = types.encoding_convert(msg.value)
            ##print "_onParameterStatusReceived client_encoding", self._client_encoding
        elif msg.key == "integer_datetimes":
            self._integer_datetimes = (msg.value == "on")
        elif msg.key == "server_version":
            self._server_version = msg.value
        else:
            ##print "_onParameterStatusReceived ", msg.key, msg.value
            pass
            
    def handleNoticeResponse(self, msg):
        self.NoticeReceived(msg)

    def handleParameterStatus(self, msg):
        self.ParameterStatusReceived(msg)

    def handleNotificationResponse(self, msg):
        self.NotificationReceived(msg)

    def fileno(self):
        # This should be safe to do without a lock
        return self._sock.fileno()
    
    def isready(self):
        self._sock_lock.acquire()
        try:
            rlst, _wlst, _xlst = select.select([self], [], [], 0)
            if not rlst:
                return False
                
            self._sync()
            return True
        finally:
            self._sock_lock.release()

    def server_version(self):
        self.verifyState("ready")
        if not self._server_version:
            raise InterfaceError("Server did not provide server_version parameter.")
        return self._server_version

    def encoding(self):
        return self._client_encoding
        

message_types = {
    "N": NoticeResponse,
    "R": AuthenticationRequest,
    "S": ParameterStatus,
    "K": BackendKeyData,
    "Z": ReadyForQuery,
    "T": RowDescription,
    "E": ErrorResponse,
    "D": DataRow,
    "C": CommandComplete,
    "1": ParseComplete,
    "2": BindComplete,
    "3": CloseComplete,
    "s": PortalSuspended,
    "n": NoData,
    "I": EmptyQueryResponse,
    "t": ParameterDescription,
    "A": NotificationResponse,
    "c": CopyDone,
    "d": CopyData,
    "G": CopyInResponse,
    "H": CopyOutResponse,
    }


