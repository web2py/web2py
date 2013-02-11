# -*- coding: utf-8 -*-

# PyPyODBC is develped from RealPyODBC 0.1 beta released in 2004 by Michele Petrazzo. Thanks Michele.

# The MIT License (MIT)
# Copyright (c) 2012 Henry Zhou <jiangwen365@gmail.com>
# Copyright (c) 2004 Michele Petrazzo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated 
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions 
# of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO 
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO #EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.



import sys, os, datetime, ctypes
from decimal import Decimal

DEBUG = 0
# Comment out all "if DEBUG:" statements like below for production
if DEBUG: print 'DEBUGGING'

pooling = True
shared_env_h = None
apilevel = '2.0'
paramstyle = 'qmark'
threadsafety = 1
version = '0.8.7a'
lowercase=True
SQLWCHAR_SIZE = ctypes.sizeof(ctypes.c_wchar)

#determin the size of Py_UNICODE
#sys.maxunicode > 65536 and 'UCS4' or 'UCS2'
UNICODE_SIZE = sys.maxunicode > 65536 and 4 or 2 


# Define ODBC constants. They are widly used in ODBC documents and programs
# They are defined in cpp header files: sql.h sqlext.h sqltypes.h sqlucode.h
# and you can get these files from the mingw32-runtime_3.13-1_all.deb package
SQL_ATTR_ODBC_VERSION, SQL_OV_ODBC2, SQL_OV_ODBC3 = 200, 2, 3
SQL_DRIVER_NOPROMPT = 0
SQL_ATTR_CONNECTION_POOLING = 201; SQL_CP_ONE_PER_HENV = 2

SQL_FETCH_NEXT, SQL_FETCH_FIRST, SQL_FETCH_LAST = 0x01, 0x02, 0x04
SQL_NULL_HANDLE, SQL_HANDLE_ENV, SQL_HANDLE_DBC, SQL_HANDLE_STMT = 0, 1, 2, 3
SQL_SUCCESS, SQL_SUCCESS_WITH_INFO = 0, 1
SQL_NO_DATA = 100; SQL_NO_TOTAL = -4
SQL_ATTR_ACCESS_MODE = SQL_ACCESS_MODE = 101
SQL_ATTR_AUTOCOMMIT = SQL_AUTOCOMMIT = 102

SQL_MODE_DEFAULT = SQL_MODE_READ_WRITE = 0
SQL_MODE_READ_ONLY = 1
SQL_AUTOCOMMIT_OFF, SQL_AUTOCOMMIT_ON = 0, 1
SQL_IS_UINTEGER = -5
SQL_ATTR_LOGIN_TIMEOUT = 103; SQL_ATTR_CONNECTION_TIMEOUT = 113
SQL_COMMIT, SQL_ROLLBACK = 0, 1

SQL_INDEX_UNIQUE,SQL_INDEX_ALL = 0,1
SQL_QUICK,SQL_ENSURE = 0,1
SQL_FETCH_NEXT = 1
SQL_COLUMN_DISPLAY_SIZE = 6
SQL_INVALID_HANDLE = -2
SQL_NO_DATA_FOUND = 100
SQL_NULL_DATA = -1
SQL_HANDLE_DESCR = 4
SQL_TABLE_NAMES = 3
SQL_PARAM_INPUT = 1
SQL_PARAM_INPUT_OUTPUT = 2
SQL_RESET_PARAMS = 3
SQL_UNBIND = 2
SQL_CLOSE = 0

SQL_TYPE_NULL = 0
SQL_DECIMAL = 3
SQL_FLOAT = 6
SQL_DATE = 9
SQL_TIME = 10
SQL_TIMESTAMP = 11
SQL_VARCHAR = 12
SQL_LONGVARCHAR = -1
SQL_VARBINARY = -3
SQL_LONGVARBINARY = -4
SQL_BIGINT = -5
SQL_WVARCHAR = -9
SQL_WLONGVARCHAR = -10
SQL_ALL_TYPES = 0
SQL_SIGNED_OFFSET = -20

SQL_C_CHAR =            SQL_CHAR =          1
SQL_C_NUMERIC =         SQL_NUMERIC =       2
SQL_C_LONG =            SQL_INTEGER =       4
SQL_C_SLONG =           SQL_C_LONG + SQL_SIGNED_OFFSET
SQL_C_SHORT =           SQL_SMALLINT =      5
SQL_C_FLOAT =           SQL_REAL =          7
SQL_C_DOUBLE =          SQL_DOUBLE =        8
SQL_C_TYPE_DATE =       SQL_TYPE_DATE =     91
SQL_C_TYPE_TIME =       SQL_TYPE_TIME =     92
SQL_C_BINARY =          SQL_BINARY =        -2
SQL_C_SBIGINT =         SQL_BIGINT + SQL_SIGNED_OFFSET        
SQL_C_TINYINT =         SQL_TINYINT =       -6
SQL_C_BIT =             SQL_BIT =           -7
SQL_C_WCHAR =           SQL_WCHAR =         -8
SQL_C_GUID =            SQL_GUID =          -11  
SQL_C_TYPE_TIMESTAMP =  SQL_TYPE_TIMESTAMP = 93

SQL_DESC_DISPLAY_SIZE = SQL_COLUMN_DISPLAY_SIZE


def dttm_cvt(x):
    if x == '': return None
    else: return datetime.datetime(int(x[0:4]),int(x[5:7]),int(x[8:10]),int(x[10:13]),int(x[14:16]),int(x[17:19]),int(x[20:].ljust(6,'0')))

def tm_cvt(x):
    if x == '': return None
    else: return datetime.time(int(x[0:2]),int(x[3:5]),int(x[6:8]),int(x[9:].ljust(6,'0')))

def dt_cvt(x):
    if x == '': return None
    else: return datetime.date(int(x[0:4]),int(x[5:7]),int(x[8:10]))


create_buffer_u = ctypes.create_unicode_buffer
create_buffer = ctypes.create_string_buffer


# Below Datatype mappings referenced the document at
# http://infocenter.sybase.com/help/index.jsp?topic=/com.sybase.help.sdk_12.5.1.aseodbc/html/aseodbc/CACFDIGH.htm


SQL_data_type_dict = { \
#SQL Data TYPE        0.Python Data Type     1.Default Output Converter  2.Buffer Type     3.Buffer Allocator   4.Default Buffer Size
SQL_TYPE_NULL       : (None,                lambda x: None,             SQL_C_CHAR,         create_buffer,      2      ), 
SQL_CHAR            : (str,                 lambda x: x,                SQL_C_CHAR,         create_buffer,      2048   ),
SQL_NUMERIC         : (Decimal,             Decimal,                    SQL_C_CHAR,         create_buffer,      150    ),
SQL_DECIMAL         : (Decimal,             Decimal,                    SQL_C_CHAR,         create_buffer,      150    ),
SQL_INTEGER         : (int,                 int,                        SQL_C_CHAR,         create_buffer,      150    ),
SQL_SMALLINT        : (int,                 int,                        SQL_C_CHAR,         create_buffer,      150    ),
SQL_FLOAT           : (float,               float,                      SQL_C_CHAR,         create_buffer,      150    ),
SQL_REAL            : (float,               float,                      SQL_C_CHAR,         create_buffer,      150    ),
SQL_DOUBLE          : (float,               float,                      SQL_C_CHAR,         create_buffer,      200    ),
SQL_DATE            : (datetime.date,       dt_cvt,                     SQL_C_CHAR ,        create_buffer,      30     ),
SQL_TIME            : (datetime.time,       tm_cvt,                     SQL_C_CHAR,         create_buffer,      20     ),
SQL_TIMESTAMP       : (datetime.datetime,   dttm_cvt,                   SQL_C_CHAR,         create_buffer,      30     ),
SQL_VARCHAR         : (str,                 lambda x: x,                SQL_C_CHAR,         create_buffer,      2048   ),
SQL_LONGVARCHAR     : (str,                 lambda x: x,                SQL_C_CHAR,         create_buffer,      20500  ),
SQL_BINARY          : (bytearray,           bytearray,                  SQL_C_BINARY,       create_buffer,      5120   ),
SQL_VARBINARY       : (bytearray,           bytearray,                  SQL_C_BINARY,       create_buffer,      5120   ),
SQL_LONGVARBINARY   : (bytearray,           bytearray,                  SQL_C_BINARY,       create_buffer,      20500  ),
SQL_BIGINT          : (long,                long,                       SQL_C_CHAR,         create_buffer,      150    ),
SQL_TINYINT         : (int,                 int,                        SQL_C_CHAR,         create_buffer,      150    ),
SQL_BIT             : (bool,                lambda x:x=='1',            SQL_C_CHAR,         create_buffer,      2      ),
SQL_WCHAR           : (unicode,             lambda x: x,                SQL_C_WCHAR,        create_buffer_u,    2048   ),
SQL_WVARCHAR        : (unicode,             lambda x: x,                SQL_C_WCHAR,        create_buffer_u,    2048   ),
SQL_GUID            : (str,                 str,                        SQL_C_CHAR,         create_buffer,      50     ),
SQL_WLONGVARCHAR    : (unicode,             lambda x: x,                SQL_C_WCHAR,        create_buffer_u,    20500  ),
SQL_TYPE_DATE       : (datetime.date,       dt_cvt,                     SQL_C_CHAR,         create_buffer,      30     ),
SQL_TYPE_TIME       : (datetime.time,       tm_cvt,                     SQL_C_CHAR,         create_buffer,      20     ),
SQL_TYPE_TIMESTAMP  : (datetime.datetime,   dttm_cvt,                   SQL_C_CHAR,         create_buffer,      30      ), 
}


# Below defines The constants for sqlgetinfo method, and their coresponding return types
SQL_QUALIFIER_LOCATION = 114
SQL_QUALIFIER_NAME_SEPARATOR = 41
SQL_QUALIFIER_TERM = 42
SQL_QUALIFIER_USAGE = 92
SQL_OWNER_TERM = 39
SQL_OWNER_USAGE = 91
SQL_ACCESSIBLE_PROCEDURES = 20
SQL_ACCESSIBLE_TABLES = 19
SQL_ACTIVE_ENVIRONMENTS = 116
SQL_AGGREGATE_FUNCTIONS = 169
SQL_ALTER_DOMAIN = 117
SQL_ALTER_TABLE = 86
SQL_ASYNC_MODE = 10021
SQL_BATCH_ROW_COUNT = 120
SQL_BATCH_SUPPORT = 121
SQL_BOOKMARK_PERSISTENCE = 82
SQL_CATALOG_LOCATION = SQL_QUALIFIER_LOCATION
SQL_CATALOG_NAME = 10003
SQL_CATALOG_NAME_SEPARATOR = SQL_QUALIFIER_NAME_SEPARATOR
SQL_CATALOG_TERM = SQL_QUALIFIER_TERM
SQL_CATALOG_USAGE = SQL_QUALIFIER_USAGE
SQL_COLLATION_SEQ = 10004
SQL_COLUMN_ALIAS = 87
SQL_CONCAT_NULL_BEHAVIOR = 22
SQL_CONVERT_FUNCTIONS = 48
SQL_CONVERT_VARCHAR = 70
SQL_CORRELATION_NAME = 74
SQL_CREATE_ASSERTION = 127
SQL_CREATE_CHARACTER_SET = 128
SQL_CREATE_COLLATION = 129
SQL_CREATE_DOMAIN = 130
SQL_CREATE_SCHEMA = 131
SQL_CREATE_TABLE = 132
SQL_CREATE_TRANSLATION = 133
SQL_CREATE_VIEW = 134
SQL_CURSOR_COMMIT_BEHAVIOR = 23
SQL_CURSOR_ROLLBACK_BEHAVIOR = 24
SQL_DATABASE_NAME = 16
SQL_DATA_SOURCE_NAME = 2
SQL_DATA_SOURCE_READ_ONLY = 25
SQL_DATETIME_LITERALS = 119
SQL_DBMS_NAME = 17
SQL_DBMS_VER = 18
SQL_DDL_INDEX = 170
SQL_DEFAULT_TXN_ISOLATION = 26
SQL_DESCRIBE_PARAMETER = 10002
SQL_DM_VER = 171
SQL_DRIVER_NAME = 6
SQL_DRIVER_ODBC_VER = 77
SQL_DRIVER_VER = 7
SQL_DROP_ASSERTION = 136
SQL_DROP_CHARACTER_SET = 137
SQL_DROP_COLLATION = 138
SQL_DROP_DOMAIN = 139
SQL_DROP_SCHEMA = 140
SQL_DROP_TABLE = 141
SQL_DROP_TRANSLATION = 142
SQL_DROP_VIEW = 143
SQL_DYNAMIC_CURSOR_ATTRIBUTES1 = 144
SQL_DYNAMIC_CURSOR_ATTRIBUTES2 = 145
SQL_EXPRESSIONS_IN_ORDERBY = 27
SQL_FILE_USAGE = 84
SQL_FORWARD_ONLY_CURSOR_ATTRIBUTES1 = 146
SQL_FORWARD_ONLY_CURSOR_ATTRIBUTES2 = 147
SQL_GETDATA_EXTENSIONS = 81
SQL_GROUP_BY = 88
SQL_IDENTIFIER_CASE = 28
SQL_IDENTIFIER_QUOTE_CHAR = 29
SQL_INDEX_KEYWORDS = 148
SQL_INFO_SCHEMA_VIEWS = 149
SQL_INSERT_STATEMENT = 172
SQL_INTEGRITY = 73
SQL_KEYSET_CURSOR_ATTRIBUTES1 = 150
SQL_KEYSET_CURSOR_ATTRIBUTES2 = 151
SQL_KEYWORDS = 89
SQL_LIKE_ESCAPE_CLAUSE = 113
SQL_MAX_ASYNC_CONCURRENT_STATEMENTS = 10022
SQL_MAX_BINARY_LITERAL_LEN = 112
SQL_MAX_CATALOG_NAME_LEN = 34
SQL_MAX_CHAR_LITERAL_LEN = 108
SQL_MAX_COLUMNS_IN_GROUP_BY = 97
SQL_MAX_COLUMNS_IN_INDEX = 98
SQL_MAX_COLUMNS_IN_ORDER_BY = 99
SQL_MAX_COLUMNS_IN_SELECT = 100
SQL_MAX_COLUMNS_IN_TABLE = 101
SQL_MAX_COLUMN_NAME_LEN = 30
SQL_MAX_CONCURRENT_ACTIVITIES = 1
SQL_MAX_CURSOR_NAME_LEN = 31
SQL_MAX_DRIVER_CONNECTIONS = 0
SQL_MAX_IDENTIFIER_LEN = 10005
SQL_MAX_INDEX_SIZE = 102
SQL_MAX_PROCEDURE_NAME_LEN = 33
SQL_MAX_ROW_SIZE = 104
SQL_MAX_ROW_SIZE_INCLUDES_LONG = 103
SQL_MAX_SCHEMA_NAME_LEN = 32
SQL_MAX_STATEMENT_LEN = 105
SQL_MAX_TABLES_IN_SELECT = 106
SQL_MAX_TABLE_NAME_LEN = 35
SQL_MAX_USER_NAME_LEN = 107
SQL_MULTIPLE_ACTIVE_TXN = 37
SQL_MULT_RESULT_SETS = 36
SQL_NEED_LONG_DATA_LEN = 111
SQL_NON_NULLABLE_COLUMNS = 75
SQL_NULL_COLLATION = 85
SQL_NUMERIC_FUNCTIONS = 49
SQL_ODBC_INTERFACE_CONFORMANCE = 152
SQL_ODBC_VER = 10
SQL_OJ_CAPABILITIES = 65003
SQL_ORDER_BY_COLUMNS_IN_SELECT = 90
SQL_PARAM_ARRAY_ROW_COUNTS = 153
SQL_PARAM_ARRAY_SELECTS = 154
SQL_PROCEDURES = 21
SQL_PROCEDURE_TERM = 40
SQL_QUOTED_IDENTIFIER_CASE = 93
SQL_ROW_UPDATES = 11
SQL_SCHEMA_TERM = SQL_OWNER_TERM
SQL_SCHEMA_USAGE = SQL_OWNER_USAGE
SQL_SCROLL_OPTIONS = 44
SQL_SEARCH_PATTERN_ESCAPE = 14
SQL_SERVER_NAME = 13
SQL_SPECIAL_CHARACTERS = 94
SQL_SQL92_DATETIME_FUNCTIONS = 155
SQL_SQL92_FOREIGN_KEY_DELETE_RULE = 156
SQL_SQL92_FOREIGN_KEY_UPDATE_RULE = 157
SQL_SQL92_GRANT = 158
SQL_SQL92_NUMERIC_VALUE_FUNCTIONS = 159
SQL_SQL92_PREDICATES = 160
SQL_SQL92_RELATIONAL_JOIN_OPERATORS = 161
SQL_SQL92_REVOKE = 162
SQL_SQL92_ROW_VALUE_CONSTRUCTOR = 163
SQL_SQL92_STRING_FUNCTIONS = 164
SQL_SQL92_VALUE_EXPRESSIONS = 165
SQL_SQL_CONFORMANCE = 118
SQL_STANDARD_CLI_CONFORMANCE = 166
SQL_STATIC_CURSOR_ATTRIBUTES1 = 167
SQL_STATIC_CURSOR_ATTRIBUTES2 = 168
SQL_STRING_FUNCTIONS = 50
SQL_SUBQUERIES = 95
SQL_SYSTEM_FUNCTIONS = 51
SQL_TABLE_TERM = 45
SQL_TIMEDATE_ADD_INTERVALS = 109
SQL_TIMEDATE_DIFF_INTERVALS = 110
SQL_TIMEDATE_FUNCTIONS = 52
SQL_TXN_CAPABLE = 46
SQL_TXN_ISOLATION_OPTION = 72
SQL_UNION = 96
SQL_USER_NAME = 47
SQL_XOPEN_CLI_YEAR = 10000


aInfoTypes = {
SQL_ACCESSIBLE_PROCEDURES : 'GI_YESNO',SQL_ACCESSIBLE_TABLES : 'GI_YESNO',SQL_ACTIVE_ENVIRONMENTS : 'GI_USMALLINT',
SQL_AGGREGATE_FUNCTIONS : 'GI_UINTEGER',SQL_ALTER_DOMAIN : 'GI_UINTEGER',
SQL_ALTER_TABLE : 'GI_UINTEGER',SQL_ASYNC_MODE : 'GI_UINTEGER',SQL_BATCH_ROW_COUNT : 'GI_UINTEGER',
SQL_BATCH_SUPPORT : 'GI_UINTEGER',SQL_BOOKMARK_PERSISTENCE : 'GI_UINTEGER',SQL_CATALOG_LOCATION : 'GI_USMALLINT',
SQL_CATALOG_NAME : 'GI_YESNO',SQL_CATALOG_NAME_SEPARATOR : 'GI_STRING',SQL_CATALOG_TERM : 'GI_STRING',
SQL_CATALOG_USAGE : 'GI_UINTEGER',SQL_COLLATION_SEQ : 'GI_STRING',SQL_COLUMN_ALIAS : 'GI_YESNO',
SQL_CONCAT_NULL_BEHAVIOR : 'GI_USMALLINT',SQL_CONVERT_FUNCTIONS : 'GI_UINTEGER',
SQL_CONVERT_VARCHAR : 'GI_UINTEGER',SQL_CORRELATION_NAME : 'GI_USMALLINT',
SQL_CREATE_ASSERTION : 'GI_UINTEGER',SQL_CREATE_CHARACTER_SET : 'GI_UINTEGER',
SQL_CREATE_COLLATION : 'GI_UINTEGER',SQL_CREATE_DOMAIN : 'GI_UINTEGER',SQL_CREATE_SCHEMA : 'GI_UINTEGER',
SQL_CREATE_TABLE : 'GI_UINTEGER',SQL_CREATE_TRANSLATION : 'GI_UINTEGER',SQL_CREATE_VIEW : 'GI_UINTEGER',
SQL_CURSOR_COMMIT_BEHAVIOR : 'GI_USMALLINT',SQL_CURSOR_ROLLBACK_BEHAVIOR : 'GI_USMALLINT',SQL_DATABASE_NAME : 'GI_STRING',
SQL_DATA_SOURCE_NAME : 'GI_STRING',SQL_DATA_SOURCE_READ_ONLY : 'GI_YESNO',SQL_DATETIME_LITERALS : 'GI_UINTEGER',
SQL_DBMS_NAME : 'GI_STRING',SQL_DBMS_VER : 'GI_STRING',SQL_DDL_INDEX : 'GI_UINTEGER',
SQL_DEFAULT_TXN_ISOLATION : 'GI_UINTEGER',SQL_DESCRIBE_PARAMETER : 'GI_YESNO',SQL_DM_VER : 'GI_STRING',
SQL_DRIVER_NAME : 'GI_STRING',SQL_DRIVER_ODBC_VER : 'GI_STRING',SQL_DRIVER_VER : 'GI_STRING',
SQL_DROP_ASSERTION : 'GI_UINTEGER',SQL_DROP_CHARACTER_SET : 'GI_UINTEGER',
SQL_DROP_COLLATION : 'GI_UINTEGER',SQL_DROP_DOMAIN : 'GI_UINTEGER',
SQL_DROP_SCHEMA : 'GI_UINTEGER',SQL_DROP_TABLE : 'GI_UINTEGER',SQL_DROP_TRANSLATION : 'GI_UINTEGER',
SQL_DROP_VIEW : 'GI_UINTEGER',SQL_DYNAMIC_CURSOR_ATTRIBUTES1 : 'GI_UINTEGER',SQL_DYNAMIC_CURSOR_ATTRIBUTES2 : 'GI_UINTEGER',
SQL_EXPRESSIONS_IN_ORDERBY : 'GI_YESNO',SQL_FILE_USAGE : 'GI_USMALLINT',
SQL_FORWARD_ONLY_CURSOR_ATTRIBUTES1 : 'GI_UINTEGER',SQL_FORWARD_ONLY_CURSOR_ATTRIBUTES2 : 'GI_UINTEGER',
SQL_GETDATA_EXTENSIONS : 'GI_UINTEGER',SQL_GROUP_BY : 'GI_USMALLINT',SQL_IDENTIFIER_CASE : 'GI_USMALLINT',
SQL_IDENTIFIER_QUOTE_CHAR : 'GI_STRING',SQL_INDEX_KEYWORDS : 'GI_UINTEGER',SQL_INFO_SCHEMA_VIEWS : 'GI_UINTEGER',
SQL_INSERT_STATEMENT : 'GI_UINTEGER',SQL_INTEGRITY : 'GI_YESNO',SQL_KEYSET_CURSOR_ATTRIBUTES1 : 'GI_UINTEGER',
SQL_KEYSET_CURSOR_ATTRIBUTES2 : 'GI_UINTEGER',SQL_KEYWORDS : 'GI_STRING',
SQL_LIKE_ESCAPE_CLAUSE : 'GI_YESNO',SQL_MAX_ASYNC_CONCURRENT_STATEMENTS : 'GI_UINTEGER',
SQL_MAX_BINARY_LITERAL_LEN : 'GI_UINTEGER',SQL_MAX_CATALOG_NAME_LEN : 'GI_USMALLINT',
SQL_MAX_CHAR_LITERAL_LEN : 'GI_UINTEGER',SQL_MAX_COLUMNS_IN_GROUP_BY : 'GI_USMALLINT',
SQL_MAX_COLUMNS_IN_INDEX : 'GI_USMALLINT',SQL_MAX_COLUMNS_IN_ORDER_BY : 'GI_USMALLINT',
SQL_MAX_COLUMNS_IN_SELECT : 'GI_USMALLINT',SQL_MAX_COLUMNS_IN_TABLE : 'GI_USMALLINT',
SQL_MAX_COLUMN_NAME_LEN : 'GI_USMALLINT',SQL_MAX_CONCURRENT_ACTIVITIES : 'GI_USMALLINT',
SQL_MAX_CURSOR_NAME_LEN : 'GI_USMALLINT',SQL_MAX_DRIVER_CONNECTIONS : 'GI_USMALLINT',
SQL_MAX_IDENTIFIER_LEN : 'GI_USMALLINT',SQL_MAX_INDEX_SIZE : 'GI_UINTEGER',
SQL_MAX_PROCEDURE_NAME_LEN : 'GI_USMALLINT',SQL_MAX_ROW_SIZE : 'GI_UINTEGER',
SQL_MAX_ROW_SIZE_INCLUDES_LONG : 'GI_YESNO',SQL_MAX_SCHEMA_NAME_LEN : 'GI_USMALLINT',
SQL_MAX_STATEMENT_LEN : 'GI_UINTEGER',SQL_MAX_TABLES_IN_SELECT : 'GI_USMALLINT',
SQL_MAX_TABLE_NAME_LEN : 'GI_USMALLINT',SQL_MAX_USER_NAME_LEN : 'GI_USMALLINT',
SQL_MULTIPLE_ACTIVE_TXN : 'GI_YESNO',SQL_MULT_RESULT_SETS : 'GI_YESNO',
SQL_NEED_LONG_DATA_LEN : 'GI_YESNO',SQL_NON_NULLABLE_COLUMNS : 'GI_USMALLINT',
SQL_NULL_COLLATION : 'GI_USMALLINT',SQL_NUMERIC_FUNCTIONS : 'GI_UINTEGER',
SQL_ODBC_INTERFACE_CONFORMANCE : 'GI_UINTEGER',SQL_ODBC_VER : 'GI_STRING',SQL_OJ_CAPABILITIES : 'GI_UINTEGER',
SQL_ORDER_BY_COLUMNS_IN_SELECT : 'GI_YESNO',SQL_PARAM_ARRAY_ROW_COUNTS : 'GI_UINTEGER',
SQL_PARAM_ARRAY_SELECTS : 'GI_UINTEGER',SQL_PROCEDURES : 'GI_YESNO',SQL_PROCEDURE_TERM : 'GI_STRING',
SQL_QUOTED_IDENTIFIER_CASE : 'GI_USMALLINT',SQL_ROW_UPDATES : 'GI_YESNO',SQL_SCHEMA_TERM : 'GI_STRING',
SQL_SCHEMA_USAGE : 'GI_UINTEGER',SQL_SCROLL_OPTIONS : 'GI_UINTEGER',SQL_SEARCH_PATTERN_ESCAPE : 'GI_STRING',
SQL_SERVER_NAME : 'GI_STRING',SQL_SPECIAL_CHARACTERS : 'GI_STRING',SQL_SQL92_DATETIME_FUNCTIONS : 'GI_UINTEGER',
SQL_SQL92_FOREIGN_KEY_DELETE_RULE : 'GI_UINTEGER',SQL_SQL92_FOREIGN_KEY_UPDATE_RULE : 'GI_UINTEGER',
SQL_SQL92_GRANT : 'GI_UINTEGER',SQL_SQL92_NUMERIC_VALUE_FUNCTIONS : 'GI_UINTEGER',
SQL_SQL92_PREDICATES : 'GI_UINTEGER',SQL_SQL92_RELATIONAL_JOIN_OPERATORS : 'GI_UINTEGER',
SQL_SQL92_REVOKE : 'GI_UINTEGER',SQL_SQL92_ROW_VALUE_CONSTRUCTOR : 'GI_UINTEGER',
SQL_SQL92_STRING_FUNCTIONS : 'GI_UINTEGER',SQL_SQL92_VALUE_EXPRESSIONS : 'GI_UINTEGER',
SQL_SQL_CONFORMANCE : 'GI_UINTEGER',SQL_STANDARD_CLI_CONFORMANCE : 'GI_UINTEGER',
SQL_STATIC_CURSOR_ATTRIBUTES1 : 'GI_UINTEGER',SQL_STATIC_CURSOR_ATTRIBUTES2 : 'GI_UINTEGER',
SQL_STRING_FUNCTIONS : 'GI_UINTEGER',SQL_SUBQUERIES : 'GI_UINTEGER',
SQL_SYSTEM_FUNCTIONS : 'GI_UINTEGER',SQL_TABLE_TERM : 'GI_STRING',SQL_TIMEDATE_ADD_INTERVALS : 'GI_UINTEGER',
SQL_TIMEDATE_DIFF_INTERVALS : 'GI_UINTEGER',SQL_TIMEDATE_FUNCTIONS : 'GI_UINTEGER',
SQL_TXN_CAPABLE : 'GI_USMALLINT',SQL_TXN_ISOLATION_OPTION : 'GI_UINTEGER',
SQL_UNION : 'GI_UINTEGER',SQL_USER_NAME : 'GI_STRING',SQL_XOPEN_CLI_YEAR : 'GI_STRING',
}

#Definations for types
BINARY = bytearray
Binary = bytearray
DATETIME = datetime.datetime
Date = datetime.date
Time = datetime.time
Timestamp = datetime.datetime
STRING = str
NUMBER = float
ROWID = int
DateFromTicks = datetime.date.fromtimestamp
TimeFromTicks = lambda x: datetime.datetime.fromtimestamp(x).time()
TimestampFromTicks = datetime.datetime.fromtimestamp


# When Null is used in a binary parameter, database usually would not
# accept the None for a binary field, so the work around is to use a 
# Specical None that the pypyodbc moudle would know this NULL is for
# a binary field.
class BinaryNullType(): pass
BinaryNull = BinaryNullType()


#Define exceptions
class OdbcNoLibrary(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
class OdbcLibraryError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
class OdbcInvalidHandle(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
class OdbcGenericError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class Warning(StandardError):
    def __init__(self, error_code, error_desc):
        self.value = (error_code, error_desc)
        self.args = (error_code, error_desc)
    

class Error(StandardError):
    def __init__(self, error_code, error_desc):
        self.value = (error_code, error_desc)
        self.args = (error_code, error_desc)

class InterfaceError(Error):
    def __init__(self, error_code, error_desc):
        self.value = (error_code, error_desc)
        self.args = (error_code, error_desc)


class DatabaseError(Error):
    def __init__(self, error_code, error_desc):
        self.value = (error_code, error_desc)
        self.args = (error_code, error_desc)

    
class InternalError(DatabaseError):
    def __init__(self, error_code, error_desc):
        self.value = (error_code, error_desc)
        self.args = (error_code, error_desc)


class ProgrammingError(DatabaseError):
    def __init__(self, error_code, error_desc):
        self.value = (error_code, error_desc)
        self.args = (error_code, error_desc)

class DataError(DatabaseError):
    def __init__(self, error_code, error_desc):
        self.value = (error_code, error_desc)
        self.args = (error_code, error_desc)

class IntegrityError(DatabaseError):
    def __init__(self, error_code, error_desc):
        self.value = (error_code, error_desc)
        self.args = (error_code, error_desc)

class NotSupportedError(Error):
    def __init__(self, error_code, error_desc):
        self.value = (error_code, error_desc)
        self.args = (error_code, error_desc)

class OperationalError(DatabaseError):
    def __init__(self, error_code, error_desc):
        self.value = (error_code, error_desc)
        self.args = (error_code, error_desc)



# Get the References of the platform's ODBC functions via ctypes 
if sys.platform in ('win32','cli'):
    ODBC_API = ctypes.windll.odbc32
else:
    # Set the library location on linux 
    lib_paths = ("/usr/lib/libodbc.so","/usr/lib/i386-linux-gnu/libodbc.so","/usr/lib/x86_64-linux-gnu/libodbc.so")
    lib_paths = [path for path in lib_paths if os.path.exists(path)]
    if len(lib_paths) == 0 :
        raise OdbcNoLibrary, 'ODBC Library is not found'
    library = lib_paths[0]
    try:
        ODBC_API = ctypes.cdll.LoadLibrary(library)
    except:
        raise OdbcLibraryError, 'Error while loading %s' % library



# Define the python return type for ODBC functions with ret result.
funcs_with_ret = ["SQLNumParams","SQLBindParameter","SQLExecute","SQLNumResultCols","SQLDescribeCol","SQLColAttribute",
        "SQLGetDiagRec","SQLAllocHandle","SQLSetEnvAttr","SQLExecDirect","SQLExecDirectW","SQLRowCount",
        "SQLFetch","SQLBindCol","SQLCloseCursor","SQLSetConnectAttr","SQLDriverConnect","SQLDriverConnectW",
        "SQLConnect","SQLTables","SQLStatistics","SQLFetchScroll","SQLMoreResults","SQLGetInfo","SQLGetData",
        "SQLDataSources","SQLFreeHandle","SQLFreeStmt","SQLDisconnect","SQLEndTran","SQLPrepare","SQLPrepareW",
        "SQLDescribeParam","SQLGetTypeInfo","SQLPrimaryKeys","SQLForeignKeys","SQLProcedures"]

for func_name in funcs_with_ret: getattr(ODBC_API,func_name).restype = ctypes.c_short


ODBC_API.SQLFetch.argtypes = [ctypes.c_int]
ODBC_API.SQLExecute.argtypes = [ctypes.c_int]
ODBC_API.SQLPrepare.argtypes = [ctypes.c_int,ctypes.c_char_p,ctypes.c_int]
ODBC_API.SQLPrepareW.argtypes = [ctypes.c_int,ctypes.c_wchar_p,ctypes.c_int]
ODBC_API.SQLExecDirect.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
ODBC_API.SQLExecDirectW.argtypes = [ctypes.c_int, ctypes.c_wchar_p, ctypes.c_int]
ODBC_API.SQLTables.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]

# Set the alias for the ctypes functions for beter code readbility or performance.
ADDR = ctypes.byref
SQLFetch = ODBC_API.SQLFetch
SQLExecute = ODBC_API.SQLExecute
SQLBindParameter = ODBC_API.SQLBindParameter





def ctrl_err(ht, h, val_ret):
    """Classify type of ODBC error from (type of handle, handle, return value)
    , and raise with a list"""
    state = create_buffer(5)
    NativeError = ctypes.c_int()
    Message = create_buffer(1024*10)
    Buffer_len = ctypes.c_int()
    err_list = []
    number_errors = 1
    
    while 1:
        ret = ODBC_API.SQLGetDiagRec(ht, h, number_errors, state, \
            NativeError, Message, len(Message), ADDR(Buffer_len))
        if ret == SQL_NO_DATA_FOUND:
            #No more data, I can raise
            if DEBUG: print err_list[0][1]
            state = err_list[0][0]
            err_text = '['+state+'] '+err_list[0][1]
            if state[:2] in ('24','25','42'):
                raise ProgrammingError(state,err_text)
            elif state[:2] in ('22'):
                raise DataError(state,err_text)
            elif state[:2] in ('23') or state == '40002':
                raise IntegrityError(state,err_text)
            elif state == '0A000':
                raise NotSupportedError(state,err_text)
            elif state in ('HYT00','HYT01'):
                raise OperationalError(state,err_text)
            elif state[:2] in ('IM','HY'):
                raise Error(state,err_text)
            else:
                raise DatabaseError(state,err_text)
            break
        elif ret == SQL_INVALID_HANDLE:
            #The handle passed is an invalid handle
            raise ProgrammingError('', 'SQL_INVALID_HANDLE')
        elif ret == SQL_SUCCESS:
            err_list.append((state.value, Message.value, NativeError.value))
            number_errors += 1

            
def validate(ret, handle_type, handle):
    """ Validate return value, if not success, raise exceptions based on the handle """
    if ret not in (SQL_SUCCESS, SQL_SUCCESS_WITH_INFO, SQL_NO_DATA):
        ctrl_err(handle_type, handle, ret)
            
            
def AllocateEnv():
    if pooling:
        ret = ODBC_API.SQLSetEnvAttr(SQL_NULL_HANDLE, SQL_ATTR_CONNECTION_POOLING, SQL_CP_ONE_PER_HENV, SQL_IS_UINTEGER)
        validate(ret, SQL_HANDLE_ENV, SQL_NULL_HANDLE)

    ''' 
    Allocate an ODBC environment by initializing the handle shared_env_h
    ODBC enviroment needed to be created, so connections can be created under it
    connections pooling can be shared under one environment
    '''
    global shared_env_h 
    shared_env_h  = ctypes.c_int()
    ret = ODBC_API.SQLAllocHandle(SQL_HANDLE_ENV, SQL_NULL_HANDLE, ADDR(shared_env_h))
    validate(ret, SQL_HANDLE_ENV, shared_env_h)

    # Set the ODBC environment's compatibil leve to ODBC 3.0
    ret = ODBC_API.SQLSetEnvAttr(shared_env_h, SQL_ATTR_ODBC_VERSION, SQL_OV_ODBC3, 0)
    validate(ret, SQL_HANDLE_ENV, shared_env_h)
    

#
#The ROW Class. It is defined to inheritant the built-in "list" object type,
#So that the object of ROW can use the "setattribute" method
class ROW(list):
    pass

# The get_type function is used to determine if parameters need to be re-binded 
# against the changed parameter types
def get_type(v):
    if v == BinaryNull:
        return 'BNull'

    t = type(v)
    if t == str:
        if len(v) >= 255:
            t = 's'
    if t == unicode:
        if len(v) >= 255:
            t = 'u'
    if t == Decimal:
        sv = str(v).replace('-','').strip('0').split('.')
        if len(sv)>1:
            t = (len(sv[0])+len(sv[1]),len(sv[1]))
        else:
            t = (len(sv[0]),0)
    return t



# The Cursor Class.
class Cursor:
    def __init__(self, conx):
        """ Initialize self._stmt_h, which is the handle of a statement
        A statement is actually the basis of a python"cursor" object
        """
        self._stmt_h = ctypes.c_int()
        self.connection = conx
        self.statement = None
        self._last_param_types = None
        self._ParamBufferList = []
        self._ColBufferList = []
        self._buf_cvt_func = []
        self.rowcount = -1
        self.description = None
        self.autocommit = None
        self._ColTypeCodeList = []
        self._outputsize = {}
        self._inputsizers = []
        self.arraysize = 1
        ret = ODBC_API.SQLAllocHandle(SQL_HANDLE_STMT, self.connection.dbc_h, ADDR(self._stmt_h))
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)
        self.closed = False

    
    def execute(self, query_string, *args, **kargs):
        """ Execute the query string, with optional parameters.
        If parameters are provided, the query would first be prepared, then executed with parameters;
        If parameters are not provided, only th query sting, it would be executed directly 
        """

        many_mode = kargs.get('many_mode',False)
        callproc_mode = kargs.get('call_mode',False)
        
        self._free_results('FREE_STATEMENT')
        if len(args) > 0:
            if len(args) == 1 and type(args[0]) in (tuple, list, set, ROW):
                params = args[0]
            else:
                params = args
        else:
            params = None
            

        if params != None:
            # If parameters exist, first prepare the query then executed with parameters
            if not type(params) in (tuple, list, set, ROW):
                raise TypeError("Params must be in a list, tuple, or Row")
            
            if not many_mode:
                if query_string != self.statement:
                    # if the query is not same as last query, then it is not prepared
                    self.prepare(query_string)
            
    
            param_types = map(get_type, params)

            if callproc_mode:
                self._BindParams(param_types, SQL_PARAM_INPUT_OUTPUT)
            else:
                if param_types != self._last_param_types:
                    self._BindParams(param_types)
                
            
            # With query prepared, now put parameters into buffers
            col_num = 0
            for param_buffer, param_buffer_len in self._ParamBufferList:
                c_char_buf, c_buf_len = '', 0
                param_val = params[col_num]
                if param_val in (None,BinaryNull):
                    c_buf_len = -1
                    
                elif type(param_val) == datetime.datetime:
                    c_buf_len = self.connection.type_size_dic[SQL_TYPE_TIMESTAMP][0]
                    datetime_str = param_val.isoformat().replace('T',' ') 
                    if len(datetime_str) == 19:
                        datetime_str += '.000'
                    c_char_buf = datetime_str[:c_buf_len]
                    # print c_buf_len, c_char_buf
                    
                elif type(param_val) == datetime.date:
                    if self.connection.type_size_dic.has_key(SQL_TYPE_DATE):
                        c_buf_len = self.connection.type_size_dic[SQL_TYPE_DATE][0]
                    else:
                        c_buf_len = 10
                    c_char_buf = param_val.isoformat()[:c_buf_len]
                    #print c_char_buf
                    
                elif type(param_val) == datetime.time:
                    if self.connection.type_size_dic.has_key(SQL_TYPE_TIME):
                        c_buf_len = self.connection.type_size_dic[SQL_TYPE_TIME][0]
                        c_char_buf = param_val.isoformat()[0:c_buf_len]
                    else:
                        c_buf_len = self.connection.type_size_dic[SQL_TYPE_TIMESTAMP][0]
                        time_str = param_val.isoformat()
                        if len(time_str) == 8:
                            time_str += '.000'
                        c_char_buf = '1900-01-01 '+time_str[0:c_buf_len - 11]
                    #print c_buf_len, c_char_buf
                    
                elif type(param_val) == bool:
                    if param_val == True:
                        c_char_buf = '1'
                    else:
                        c_char_buf = '0'
                    c_buf_len = 1
                    
                elif type(param_val) in (float, Decimal):
                    c_char_buf = str(param_val)
                    c_buf_len = len(c_char_buf)
                    
                elif type(param_val) in (str, 's'):
                    c_char_buf = param_val
                    
                elif type(param_val) in (unicode, 'u'):
                    c_char_buf = param_val
                    
                elif type(param_val) in (bytearray,buffer):
                    c_char_buf = str(param_val)
                    c_buf_len = len(c_char_buf)
                    
                else:
                    c_char_buf = param_val
            
    
                if type(param_val) in (bytearray,buffer):
                    param_buffer.raw = c_char_buf
                    
                else:
                    param_buffer.value = c_char_buf
                    #print param_buffer, param_buffer.value
                    
                if type(param_val) not in (unicode,str,'u','s'):
                    #ODBC driver will find NUL in unicode and string to determine their length
                    param_buffer_len.value = c_buf_len
    
                col_num += 1
            ret = SQLExecute(self._stmt_h)
            if ret != SQL_SUCCESS:
                validate(ret, SQL_HANDLE_STMT, self._stmt_h)
            

            if not many_mode:
                self._NumOfRows()
                self._UpdateDesc()
                #self._BindCols()
            
        else:
            self.execdirect(query_string)
        return (self)
    
    
    def _SQLExecute(self):
        ret = SQLExecute(self._stmt_h)
        if ret != SQL_SUCCESS:
            validate(ret, SQL_HANDLE_STMT, self._stmt_h)

        

            
    def prepare(self, query_string):
        """prepare a query"""
        if type(query_string) == unicode:
            ret = ODBC_API.SQLPrepareW(self._stmt_h, query_string, len(query_string))
        else:
            ret = ODBC_API.SQLPrepare(self._stmt_h, query_string, len(query_string))
        if ret != SQL_SUCCESS:
            validate(ret, SQL_HANDLE_STMT, self._stmt_h)
        self.statement = query_string
        
    
    def execdirect(self, query_string):
        """Execute a query directly"""
        if type(query_string) == unicode:
            ret = ODBC_API.SQLExecDirectW(self._stmt_h, query_string, len(query_string))
        else:
            ret = ODBC_API.SQLExecDirect(self._stmt_h, query_string, len(query_string))
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)
        self._NumOfRows()
        self._UpdateDesc()
        #self._BindCols()
        self.statement = None
        return (self)
        
        
    def callproc(self, procname, args):
        call_escape = '{CALL '+procname
        if args:
            call_escape += '(' + ','.join(['?' for params in args]) + ')'
        call_escape += '}'
        print call_escape
        self.execute(call_escape, args, call_mode = True)
        for p in self._ParamBufferList:
            for f in p:
                print f.value, type(f.value)
                
    
    def executemany(self, query_string, params_list = [None]):
        self.prepare(query_string)
        for params in params_list:
            self.execute(query_string, params, many_mode = True)
        self._NumOfRows()
        self.rowcount = -1
        self._UpdateDesc()
        #self._BindCols()


    def _BindParams(self, param_types, InputOutputType = SQL_PARAM_INPUT):
        """Create parameter buffers based on param types, and bind them to the statement"""
        # Get the number of query parameters judged by database.
        NumParams = ctypes.c_int()
        ret = ODBC_API.SQLNumParams(self._stmt_h, ADDR(NumParams))
        if ret != SQL_SUCCESS:
            validate(ret, SQL_HANDLE_STMT, self._stmt_h)
        
        if len(param_types) != NumParams.value:
            # In case number of parameters provided do not same as number required
            error_desc = "The SQL contains %d parameter markers, but %d parameters were supplied" \
                        %(NumParams.value,len(param_types))
            raise ProgrammingError('HY000',error_desc)
        
        
        # Every parameter needs to be binded to a buffer
        ParamBufferList = []
        for col_num in range(NumParams.value):
            '''
            DataType = ctypes.c_int()
            ParamSize = ctypes.c_long()
            DecimalDigits = ctypes.c_short()
            Nullable = ctypes.c_bool()                        
            ret = ODBC_API.SQLDescribeParam(self._stmt_h, col_num + 1, ADDR(DataType), ADDR(ParamSize), \
                ADDR(DecimalDigits), ADDR(Nullable))
            validate(ret, SQL_HANDLE_STMT, self._stmt_h)
            '''
            col_size = 0            
            buf_size = 512
        
            if param_types[col_num] in (int,):
                sql_c_type = SQL_C_LONG            
                sql_type = SQL_INTEGER                
                ParameterBuffer = ctypes.c_long()            
                
            elif param_types[col_num] in (long,):
                sql_c_type = SQL_C_SBIGINT           
                sql_type = SQL_BIGINT                
                ParameterBuffer = ctypes.c_longlong()
                
                
            elif param_types[col_num] == float:
                sql_c_type = SQL_C_CHAR
                sql_type = SQL_DOUBLE                
                ParameterBuffer = create_buffer(buf_size)
                
            elif param_types[col_num] == bool:
                sql_c_type = SQL_C_CHAR
                sql_type = SQL_BIT                
                ParameterBuffer = ctypes.c_char()
                
                
            elif type(param_types[col_num]) == tuple: #Decimal
                sql_c_type = SQL_C_CHAR
                sql_type = SQL_NUMERIC
                buf_size = param_types[col_num][0]
                
                ParameterBuffer = create_buffer(buf_size+4)
                col_size = param_types[col_num][1]
                if DEBUG: print param_types[col_num][0],param_types[col_num][1]
                
            elif param_types[col_num] == datetime.datetime:
                sql_c_type = SQL_C_CHAR
                sql_type = SQL_TYPE_TIMESTAMP
                buf_size = self.connection.type_size_dic[SQL_TYPE_TIMESTAMP][0]                
                ParameterBuffer = create_buffer(buf_size)
                col_size = self.connection.type_size_dic[SQL_TYPE_TIMESTAMP][1]
                
                
            elif param_types[col_num] == datetime.date:
                sql_c_type = SQL_C_CHAR
                if self.connection.type_size_dic.has_key(SQL_TYPE_DATE):
                    if DEBUG: print 'conx.type_size_dic.has_key(SQL_TYPE_DATE)'
                    sql_type = SQL_TYPE_DATE
                    buf_size = self.connection.type_size_dic[SQL_TYPE_DATE][0]
                    
                    ParameterBuffer = create_buffer(buf_size)
                    col_size = self.connection.type_size_dic[SQL_TYPE_DATE][1]
                    
                else:
                    #SQL Sever use -9 to represent date, instead of SQL_TYPE_DATE
                    sql_type = SQL_TYPE_TIMESTAMP 
                    buf_size = 10                    
                    ParameterBuffer = create_buffer(buf_size)
                    
    
            elif param_types[col_num] == datetime.time:
                sql_c_type = SQL_C_CHAR
                if self.connection.type_size_dic.has_key(SQL_TYPE_TIME):
                    sql_type = SQL_TYPE_TIME
                    buf_size = self.connection.type_size_dic[SQL_TYPE_TIME][0]                    
                    ParameterBuffer = create_buffer(buf_size)
                    col_size = self.connection.type_size_dic[SQL_TYPE_TIME][1]                   
                else:
                    sql_type = SQL_TYPE_TIMESTAMP #SQL Sever use -9 to represent date, instead of SQL_TYPE_DATE
                    buf_size = self.connection.type_size_dic[SQL_TYPE_TIMESTAMP][0]                    
                    ParameterBuffer = create_buffer(buf_size)
                    col_size = 3
                    
            elif param_types[col_num] == unicode:
                sql_c_type = SQL_C_WCHAR
                sql_type = SQL_WVARCHAR 
                buf_size = 255                 
                ParameterBuffer = create_buffer_u(buf_size)                
                    
            elif param_types[col_num] == str:
                sql_c_type = SQL_C_CHAR
                sql_type = SQL_VARCHAR
                buf_size = 255                 
                ParameterBuffer = create_buffer(buf_size)

            elif param_types[col_num] == 'u':
                sql_c_type = SQL_C_WCHAR
                sql_type = SQL_WLONGVARCHAR 
                buf_size = len(self._inputsizers)>col_num and self._inputsizers[col_num] or 20500                
                ParameterBuffer = create_buffer_u(buf_size)                
                    
            elif param_types[col_num] == 's':
                sql_c_type = SQL_C_CHAR
                sql_type = SQL_LONGVARCHAR
                buf_size = len(self._inputsizers)>col_num and self._inputsizers[col_num] or 20500                
                ParameterBuffer = create_buffer(buf_size)
                
    
            elif param_types[col_num] in (bytearray, buffer):
                sql_c_type = SQL_C_BINARY
                sql_type = SQL_LONGVARBINARY 
                buf_size = len(self._inputsizers)>col_num and self._inputsizers[col_num] or 20500                
                ParameterBuffer = create_buffer(buf_size)
            
            
            elif param_types[col_num] == 'BNull':
                sql_c_type = SQL_C_BINARY
                sql_type = SQL_VARBINARY 
                buf_size = 1                 
                ParameterBuffer = create_buffer(buf_size)                
                
            else:
                sql_c_type = SQL_C_CHAR
                sql_type = SQL_LONGVARCHAR
                buf_size = len(self._inputsizers)>col_num and self._inputsizers[col_num] or 20500                
                ParameterBuffer = create_buffer(buf_size)
                
            BufferLen = ctypes.c_long(buf_size)
            LenOrIndBuf = ctypes.c_long()
                
            if param_types[col_num] in (unicode,str,'u','s'):
                ret = SQLBindParameter(self._stmt_h, col_num + 1, InputOutputType, sql_c_type, sql_type, buf_size,\
                        col_size, ADDR(ParameterBuffer), BufferLen,None)
            else:
                ret = SQLBindParameter(self._stmt_h, col_num + 1, InputOutputType, sql_c_type, sql_type, buf_size,\
                        col_size, ADDR(ParameterBuffer), BufferLen,ADDR(LenOrIndBuf))
            if ret != SQL_SUCCESS:    
                validate(ret, SQL_HANDLE_STMT, self._stmt_h)
            # Append the value buffer and the lenth buffer to the array
            ParamBufferList.append((ParameterBuffer,LenOrIndBuf))
                
        self._last_param_types = param_types
        self._ParamBufferList = ParamBufferList
        
    

    def _CreateColBuf(self):
        NOC = self._NumOfCols()
        self._ColBufferList = []
        for col_num in range(NOC):
            col_name = self.description[col_num][0]            
            
            col_sql_data_type = self._ColTypeCodeList[col_num]            

            # set default size base on the column's sql data type
            total_buf_len = SQL_data_type_dict[col_sql_data_type][4] 
            # over-write if there's preset size value for "large columns"
            if total_buf_len >= 20500: 
                total_buf_len = self._outputsize.get(None,total_buf_len)
            # over-write if there's preset size value for the "col_num" column 
            total_buf_len = self._outputsize.get(col_num, total_buf_len)


            alloc_buffer = SQL_data_type_dict[col_sql_data_type][3](total_buf_len)

            used_buf_len = ctypes.c_long()
            
            target_type = SQL_data_type_dict[col_sql_data_type][2]
            force_unicode = self.connection.unicode_results
    
            if force_unicode and col_sql_data_type in (SQL_CHAR,SQL_VARCHAR,SQL_LONGVARCHAR):
                target_type = SQL_C_WCHAR
                alloc_buffer = create_buffer_u(total_buf_len)
            
            buf_cvt_func = self.connection.output_converter[self._ColTypeCodeList[col_num]]
            
            self._ColBufferList.append([col_name, target_type, used_buf_len, alloc_buffer, total_buf_len, buf_cvt_func])     
        
    
    def _GetData(self):
        '''Bind buffers for the record set columns'''
        
        value_list = ROW()
        col_num = 0
        for col_name, target_type, used_buf_len, alloc_buffer, total_buf_len, buf_cvt_func in self._ColBufferList:
            
            blocks = []
            while True:
                ret = ODBC_API.SQLGetData(self._stmt_h, col_num + 1, target_type, ADDR(alloc_buffer), total_buf_len,\
                                ADDR(used_buf_len))
                validate(ret, SQL_HANDLE_STMT, self._stmt_h)    
                
                if ret == SQL_SUCCESS:
                    if used_buf_len.value == SQL_NULL_DATA:
                        blocks.append(None)                    
                    else:
                        if target_type == SQL_C_BINARY:
                            blocks.append(alloc_buffer.raw[:used_buf_len.value])
                        else:
                            #print col_name, target_type, alloc_buffer.value
                            blocks.append(alloc_buffer.value)
                            
                    break                    
                
                if ret == SQL_SUCCESS_WITH_INFO:
                    if target_type == SQL_C_BINARY:
                        blocks.append(alloc_buffer.raw)
                    else:
                        blocks.append(alloc_buffer.value)  
     
                if ret == SQL_NO_DATA:
                    break

                
            if len(blocks) == 1:
                raw_value = blocks[0]
            else:
                raw_value = ''.join(blocks)

            if raw_value == None:
                value_list.append(None)
            else:
                value_list.append(buf_cvt_func(raw_value))
            setattr(value_list,col_name,value_list[-1])
            col_num += 1
        value_list.cursor_description = self.description
        return value_list
        
        
    
    def _UpdateDesc(self):
        "Get the information of (name, type_code, display_size, internal_size, col_precision, scale, null_ok)"  
        Cname = create_buffer(1024)
        Cname_ptr = ctypes.c_int()
        Ctype_code = ctypes.c_short()
        Csize = ctypes.c_int()
        Cdisp_size = ctypes.c_int(0)
        CDecimalDigits = ctypes.c_int()
        Cnull_ok = ctypes.c_int()
        ColDescr = []
        self._ColTypeCodeList = []
        NOC = self._NumOfCols()
        for col in range(1, NOC+1):
            ret = ODBC_API.SQLColAttribute(self._stmt_h, col, SQL_DESC_DISPLAY_SIZE, ADDR(create_buffer(10)), 
                10, ADDR(ctypes.c_int()),ADDR(Cdisp_size))
            validate(ret, SQL_HANDLE_STMT, self._stmt_h)
            
            ret = ODBC_API.SQLDescribeCol(self._stmt_h, col, ADDR(Cname), len(Cname), ADDR(Cname_ptr),\
                ADDR(Ctype_code),ADDR(Csize),ADDR(CDecimalDigits), ADDR(Cnull_ok))
            validate(ret, SQL_HANDLE_STMT, self._stmt_h)
            
            col_name = Cname.value
            if lowercase:
                col_name = str.lower(col_name)
            #(name, type_code, display_size, 
            #   internal_size, col_precision, scale, null_ok)
            ColDescr.append((col_name, SQL_data_type_dict.get(Ctype_code.value,(Ctype_code.value))[0],Cdisp_size.value,\
                Csize.value, Csize.value,CDecimalDigits.value,Cnull_ok.value == 1 and True or False))
            self._ColTypeCodeList.append(Ctype_code.value)
        
        if len(ColDescr) > 0:
            self.description = ColDescr
        else:
            self.description = None
        self._CreateColBuf()
    
    
    def _NumOfRows(self):
        """Get the number of rows"""
        NOR = ctypes.c_int()
        ret = ODBC_API.SQLRowCount(self._stmt_h, ADDR(NOR))
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)
        self.rowcount = NOR.value
        return self.rowcount    

    
    def _NumOfCols(self):
        """Get the number of cols"""
        NOC = ctypes.c_int()
        ret = ODBC_API.SQLNumResultCols(self._stmt_h, ADDR(NOC))
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)
        return NOC.value


    def fetchall(self):
        rows = []
        while True:
            row = self.fetchone()
            if row == None:
                break
            rows.append(row)
        return rows


    def fetchmany(self, num = None):
        if num == None:
            num = self.arraysize
        rows, row_num = [], 0
        
        while row_num < num:
            row = self.fetchone()
            if row == None:
                break
            rows.append(row)
            row_num += 1
        return rows


    def fetchone(self):
        ret = SQLFetch(self._stmt_h)
        if ret == SQL_SUCCESS:
            return self._GetData()
        else:
            if ret == SQL_NO_DATA_FOUND:
                return None
            else:
                validate(ret, SQL_HANDLE_STMT, self._stmt_h)
    
    def next(self):
        row = self.fetchone()
        if row == None:
            raise(StopIteration)
        return row
    
    def __iter__(self):
        return self

    
    def skip(self, count = 0):
        for i in xrange(count):
            ret = ODBC_API.SQLFetchScroll(self._stmt_h, SQL_FETCH_NEXT, 0)
            if ret != SQL_SUCCESS:
                validate(ret, SQL_HANDLE_STMT, self._stmt_h)
        return None    
    
    
        
    def nextset(self):
        ret = ODBC_API.SQLMoreResults(self._stmt_h)
        if ret not in (SQL_SUCCESS, SQL_NO_DATA):
            validate(ret, SQL_HANDLE_STMT, self._stmt_h)
            
        if ret == SQL_NO_DATA:
            self._free_results('FREE_STATEMENT')
            return False
        else:
            self._NumOfRows()
            self._UpdateDesc()
            #self._BindCols()
        return True
    
    
    def _free_results(self, free_statement):
        if not self.connection.connected:
            raise ProgrammingError('HY000','Attempt to use a closed connection.')
        
        self.description = None
        if free_statement == 'FREE_STATEMENT':
            ret = ODBC_API.SQLFreeStmt(self._stmt_h, SQL_CLOSE)
            validate(ret, SQL_HANDLE_STMT, self._stmt_h)
        else:
            ret = ODBC_API.SQLFreeStmt(self._stmt_h, SQL_UNBIND)
            validate(ret, SQL_HANDLE_STMT, self._stmt_h)
            
            ret = ODBC_API.SQLFreeStmt(self._stmt_h, SQL_RESET_PARAMS)
            validate(ret, SQL_HANDLE_STMT, self._stmt_h)
    
        self.rowcount = -1
        
    
    
    def getTypeInfo(self, sqlType = None):
        if sqlType == None:
            type = SQL_ALL_TYPES
        else:
            type = sqlType
        ret = ODBC_API.SQLGetTypeInfo(self._stmt_h, type)
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)
    
        self._NumOfRows()
        self._UpdateDesc()
        #self._BindCols()
        return (self)
    
    
    def tables(self, table=None, catalog=None, schema=None, tableType=None):
        """Return a list with all tables""" 
        l_catalog = l_schema = l_table = l_tableType = 0
        
        if catalog != None:
            l_catalog = len(catalog)
            catalog = ctypes.c_char_p(catalog) 

        if schema != None: 
            l_schema = len(schema)
            schema = ctypes.c_char_p(schema)
            
        if table != None:
            l_table = len(table)
            table = ctypes.c_char_p(table)
            
        if tableType != None: 
            l_tableType = len(tableType)
            tableType = ctypes.c_char_p(tableType)
        
        self._free_results('FREE_STATEMENT')
        self.statement = None
        ret = ODBC_API.SQLTables(self._stmt_h,
                                catalog, l_catalog,
                                schema, l_schema, 
                                table, l_table,
                                tableType, l_tableType)
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)
    
        self._NumOfRows()
        self._UpdateDesc()
        #self._BindCols()
        return (self)
    
    
    def columns(self, table=None, catalog=None, schema=None, column=None):
        """Return a list with all columns"""        
        l_catalog = l_schema = l_table = l_column = 0
        if catalog != None: 
            l_catalog = len(catalog)
            catalog = ctypes.c_char_p(catalog)
        if schema != None:
            l_schema = len(schema)
            schema = ctypes.c_char_p(schema)
        if table != None: 
            l_table = len(table)
            table = ctypes.c_char_p(table)
        if column != None: 
            l_column = len(column)
            column = ctypes.c_char_p(column)
            
        self._free_results('FREE_STATEMENT')
        self.statement = None
            
        ret = ODBC_API.SQLColumns(self._stmt_h,
                            catalog, l_catalog,
                            schema, l_schema,
                            table, l_table,
                            column, l_column)
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)

        self._NumOfRows()
        self._UpdateDesc()
        #self._BindCols()
        return (self)
    
    
    def primaryKeys(self, table=None, catalog=None, schema=None):
        l_catalog = l_schema = l_table = 0
        if catalog != None: 
            l_catalog = len(catalog)
            catalog = ctypes.c_char_p(catalog)
            
        if schema != None: 
            l_schema = len(schema)
            schema = ctypes.c_char_p(schema)
            
        if table != None: 
            l_table = len(table)
            table = ctypes.c_char_p(table)
            
        self._free_results('FREE_STATEMENT')
        self.statement = None
            
        ret = ODBC_API.SQLPrimaryKeys(self._stmt_h,
                            catalog, l_catalog,
                            schema, l_schema,
                            table, l_table)
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)
        
        self._NumOfRows()
        self._UpdateDesc()
        #self._BindCols()
        return (self)
    
        
    def foreignKeys(self, table=None, catalog=None, schema=None, foreignTable=None, foreignCatalog=None, foreignSchema=None):
        l_catalog = l_schema = l_table = l_foreignTable = l_foreignCatalog = l_foreignSchema = 0
        if catalog != None: 
            l_catalog = len(catalog)
            catalog = ctypes.c_char_p(catalog)
        if schema != None: 
            l_schema = len(schema)
            schema = ctypes.c_char_p(schema)
        if table != None: 
            l_table = len(table)
            table = ctypes.c_char_p(table)
        if foreignTable != None: 
            l_foreignTable = len(foreignTable)
            foreignTable = ctypes.c_char_p(foreignTable)
        if foreignCatalog != None: 
            l_foreignCatalog = len(foreignCatalog)
            foreignCatalog = ctypes.c_char_p(foreignCatalog)
        if foreignSchema != None: 
            l_foreignSchema = len(foreignSchema)
            foreignSchema = ctypes.c_char_p(foreignSchema)
        
        self._free_results('FREE_STATEMENT')
        self.statement = None
        
        ret = ODBC_API.SQLForeignKeys(self._stmt_h,
                            catalog, l_catalog,
                            schema, l_schema,
                            table, l_table,
                            foreignCatalog, l_foreignCatalog,
                            foreignSchema, l_foreignSchema,
                            foreignTable, l_foreignTable)
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)
        
        self._NumOfRows()
        self._UpdateDesc()
        #self._BindCols()
        return (self)
    
    
    def procedures(self, procedure=None, catalog=None, schema=None):
        l_catalog = l_schema = l_procedure = 0
        if catalog != None: 
            l_catalog = len(catalog)
            catalog = ctypes.c_char_p(catalog)
        if schema != None: 
            l_schema = len(schema)
            schema = ctypes.c_char_p(schema)
        if procedure != None: 
            l_procedure = len(procedure)
            procedure = ctypes.c_char_p(procedure)
            
        
        self._free_results('FREE_STATEMENT')
        self.statement = None
            
        ret = ODBC_API.SQLProcedures(self._stmt_h,
                            catalog, l_catalog,
                            schema, l_schema,
                            procedure, l_procedure)
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)
        
        self._NumOfRows()
        self._UpdateDesc()
        #self._BindCols()
        return (self)


    def statistics(self, table, catalog=None, schema=None, unique=False, quick=True):
        l_table = l_catalog = l_schema = 0
    
        if catalog != None: 
            l_catalog = len(catalog)
            catalog = ctypes.c_char_p(catalog)
        if schema != None: 
            l_schema = len(schema)
            schema = ctypes.c_char_p(schema)
        if table != None: 
            l_table = len(table)
            table = ctypes.c_char_p(table)
            
        if unique:
            Unique = SQL_INDEX_UNIQUE
        else:
            Unique = SQL_INDEX_ALL
        if quick:
            Reserved = SQL_QUICK
        else:
            Reserved = SQL_ENSURE
        
        self._free_results('FREE_STATEMENT')
        self.statement = None
        
        ret = ODBC_API.SQLStatistics(self._stmt_h,
                                catalog, l_catalog,
                                schema, l_schema, 
                                table, l_table,
                                Unique, Reserved)
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)
    
        self._NumOfRows()
        self._UpdateDesc()
        #self._BindCols()
        return (self)
    

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()
    
    def setoutputsize(self, size, column = None):
        self._outputsize[column] = size
    
    def setinputsizes(self, sizes):
        self._inputsizers = [size for size in sizes]


    def close(self):
        """ Call SQLCloseCursor API to free the statement handle"""
#        ret = ODBC_API.SQLCloseCursor(self._stmt_h)
#        validate(ret, SQL_HANDLE_STMT, self._stmt_h)
#        
        ret = ODBC_API.SQLFreeStmt(self._stmt_h, SQL_CLOSE)
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)

        ret = ODBC_API.SQLFreeStmt(self._stmt_h, SQL_UNBIND)
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)

        ret = ODBC_API.SQLFreeStmt(self._stmt_h, SQL_RESET_PARAMS)
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)

        ret = ODBC_API.SQLFreeHandle(SQL_HANDLE_STMT, self._stmt_h)
        validate(ret, SQL_HANDLE_STMT, self._stmt_h)
        
        self.closed = True

    
    
    def __del__(self):  
        if not self.closed:
            if DEBUG: print 'auto closing cursor: ',
            try:
                self.close()
            except:
                if DEBUG: print 'failed'
                pass
            else:
                if DEBUG: print 'succeed'
                pass
    
    def __exit__(self, type, value, traceback):
        if value:
            self.rollback()
        else:
            self.commit()
            
        self.close()
    
            
    def __enter__(self):
        return self

    
# This class implement a odbc connection. 
#
#

class Connection:
    def __init__(self, connectString = '', autocommit = False, ansi = False, timeout = 0, unicode_results = False, readonly = False, **kargs):
        """Init variables and connect to the engine"""
        self.connected = 0
        self.type_size_dic = {}
        self.unicode_results = False
        self.dbc_h = ctypes.c_int()
        self.autocommit = autocommit
        self.readonly = False
        self.timeout = 0

        for key, value in kargs.items():
            connectString = connectString + key + '=' + value + ';'
        self.connectString = connectString

        
        self.clear_output_converters()

        
        if shared_env_h == None:
            #Initialize an enviroment if it is not created.
            AllocateEnv()
            
        # Allocate an DBC handle self.dbc_h under the environment shared_env_h
        # This DBC handle is actually the basis of a "connection"
        # The handle of self.dbc_h will be used to connect to a certain source 
        # in the self.connect and self.ConnectByDSN method
        
        ret = ODBC_API.SQLAllocHandle(SQL_HANDLE_DBC, shared_env_h, ADDR(self.dbc_h))
        validate(ret, SQL_HANDLE_DBC, self.dbc_h)
        
        self.connect(connectString, autocommit, ansi, timeout, unicode_results, readonly)
        
            
     
    def connect(self, connectString = '', autocommit = False, ansi = False, timeout = 0, unicode_results = False, readonly = False):
        """Connect to odbc, using connect strings and set the connection's attributes like autocommit and timeout
        by calling SQLSetConnectAttr
        """ 

        # Before we establish the connection by the connection string
        # Set the connection's attribute of "timeout" (Actully LOGIN_TIMEOUT)
        if timeout != 0:
            ret = ODBC_API.SQLSetConnectAttr(self.dbc_h, SQL_ATTR_LOGIN_TIMEOUT, timeout, SQL_IS_UINTEGER);
            validate(ret, SQL_HANDLE_DBC, self.dbc_h)


        # Create one connection with a connect string by calling SQLDriverConnect
        # and make self.dbc_h the handle of this connection


        # Convert the connetsytring to encoded string
        # so it can be converted to a ctypes c_char array object 

        
        
        if not ansi:
            c_connectString = ctypes.c_wchar_p(self.connectString)
            ret = ODBC_API.SQLDriverConnectW(self.dbc_h, 0, c_connectString, len(self.connectString), 0, 0, 0, SQL_DRIVER_NOPROMPT)
        else:
            c_connectString = ctypes.c_char_p(self.connectString)
            ret = ODBC_API.SQLDriverConnect(self.dbc_h, 0, c_connectString, len(self.connectString), 0, 0, 0, SQL_DRIVER_NOPROMPT)
        validate(ret, SQL_HANDLE_DBC, self.dbc_h)
            
        
        # Set the connection's attribute of "autocommit" 
        #
        self.autocommit = autocommit
        
        if self.autocommit == True:
            ret = ODBC_API.SQLSetConnectAttr(self.dbc_h, SQL_ATTR_AUTOCOMMIT, SQL_AUTOCOMMIT_ON, SQL_IS_UINTEGER)
        else:
            ret = ODBC_API.SQLSetConnectAttr(self.dbc_h, SQL_ATTR_AUTOCOMMIT, SQL_AUTOCOMMIT_OFF, SQL_IS_UINTEGER)
    
        validate(ret, SQL_HANDLE_DBC, self.dbc_h)
       
        # Set the connection's attribute of "readonly" 
        #
        self.readonly = readonly
        
        ret = ODBC_API.SQLSetConnectAttr(self.dbc_h, SQL_ATTR_ACCESS_MODE, self.readonly and SQL_MODE_READ_ONLY or SQL_MODE_READ_WRITE, SQL_IS_UINTEGER)
        validate(ret, SQL_HANDLE_DBC, self.dbc_h)
        
        self.unicode_results = unicode_results
        self.update_type_size_info()
        self.connected = 1
        
    def clear_output_converters(self):
        self.output_converter = {}
        for sqltype, profile in SQL_data_type_dict.items():
            self.output_converter[sqltype] = profile[1]
        
        
    def add_output_converter(self, sqltype, func):
        self.output_converter[sqltype] = func
    
    def settimeout(self, timeout):
        ret = ODBC_API.SQLSetConnectAttr(self.dbc_h, SQL_ATTR_CONNECTION_TIMEOUT, timeout, SQL_IS_UINTEGER);
        validate(ret, SQL_HANDLE_DBC, self.dbc_h)
        self.timeout = timeout
        

    def ConnectByDSN(self, dsn, user, passwd = ''):
        """Connect to odbc, we need dsn, user and optionally password"""
        self.dsn = dsn
        self.user = user
        self.passwd = passwd

        sn = create_buffer(dsn)
        un = create_buffer(user)        
        pw = create_buffer(passwd)
        
        ret = ODBC_API.SQLConnect(self.dbc_h, sn, len(sn), un, len(un), pw, len(pw))
        validate(ret, SQL_HANDLE_DBC, self.dbc_h)

        self.update_type_size_info()
        self.connected = 1
        
        
    def cursor(self): 
        #self.settimeout(self.timeout)
        if not self.connected:
            raise ProgrammingError('HY000','Attempt to use a closed connection.')
        
        
        return Cursor(self)   

    def update_type_size_info(self):
        #Get the scale information for SQL_TYPE_TIMESTAMP
        cur = Cursor(self)
        info_tuple = cur.getTypeInfo(SQL_TYPE_TIMESTAMP).fetchone()
        if info_tuple != None:
            self.type_size_dic[SQL_TYPE_TIMESTAMP] = info_tuple[2], info_tuple[13]
        cur.close()
        
        cur = Cursor(self)
        info_tuple = cur.getTypeInfo(SQL_TYPE_TIME).fetchone()
        if info_tuple != None:        
            self.type_size_dic[SQL_TYPE_TIME] = info_tuple[2], info_tuple[13]
        cur.close()
        
        
        cur = Cursor(self)
        if DEBUG: print 'SQL_TYPE_DATE:',
        info_tuple = cur.getTypeInfo(SQL_TYPE_DATE).fetchone()
        if info_tuple != None:        
            self.type_size_dic[SQL_TYPE_DATE] = info_tuple[2], info_tuple[13]
            
            if DEBUG: print info_tuple[2], info_tuple[13]
        cur.close()
        
        
        cur = Cursor(self)
        info_tuple = cur.getTypeInfo(SQL_TIME).fetchone()
        if info_tuple != None:        
            self.type_size_dic[SQL_TIME] = info_tuple[2], info_tuple[13]
        cur.close()

    
    def commit(self):
        if not self.connected:
            raise ProgrammingError('HY000','Attempt to use a closed connection.')
        
        
        ret = ODBC_API.SQLEndTran(SQL_HANDLE_DBC, self.dbc_h, SQL_COMMIT);
        validate(ret, SQL_HANDLE_DBC, self.dbc_h)

    def rollback(self):
        if not self.connected:
            raise ProgrammingError('HY000','Attempt to use a closed connection.')
        
        
        ret = ODBC_API.SQLEndTran(SQL_HANDLE_DBC, self.dbc_h, SQL_ROLLBACK);
        validate(ret, SQL_HANDLE_DBC, self.dbc_h)
        
    
    
    def getinfo(self,infotype):
        if infotype not in aInfoTypes.keys():
            raise ProgrammingError('HY000','Invalid getinfo value: '+str(infotype)) 
        
        
        if aInfoTypes[infotype] == 'GI_UINTEGER':
            total_buf_len = 1000
            alloc_buffer = ctypes.c_ulong()
            used_buf_len = ctypes.c_long()
            ret = ODBC_API.SQLGetInfo(self.dbc_h,infotype,ADDR(alloc_buffer), total_buf_len,\
                    ADDR(used_buf_len))
            validate(ret, SQL_HANDLE_DBC, self.dbc_h)
            result = alloc_buffer.value
            
        elif aInfoTypes[infotype] == 'GI_USMALLINT':
            total_buf_len = 1000
            alloc_buffer = ctypes.c_ushort()
            used_buf_len = ctypes.c_long()
            ret = ODBC_API.SQLGetInfo(self.dbc_h,infotype,ADDR(alloc_buffer), total_buf_len,\
                    ADDR(used_buf_len))
            validate(ret, SQL_HANDLE_DBC, self.dbc_h)
            result = alloc_buffer.value

        else:
            total_buf_len = 1000
            alloc_buffer = create_buffer(total_buf_len)
            used_buf_len = ctypes.c_long()
            ret = ODBC_API.SQLGetInfo(self.dbc_h,infotype,ADDR(alloc_buffer), total_buf_len,\
                    ADDR(used_buf_len))
            validate(ret, SQL_HANDLE_DBC, self.dbc_h)
            result = alloc_buffer.value
            if aInfoTypes[infotype] == 'GI_YESNO':
                if result[0] == 'Y':
                    result = True
                else:
                    result = False
                    
        return result
        
    def __exit__(self, type, value, traceback):
        if value:
            self.rollback()
        else:
            self.commit()
            
        if self.connected:
            self.close()
    
            
    def __enter__(self):
        return self

    def __del__(self):
        if self.connected:
            self.close()
        
    def close(self):
        if not self.connected:
            raise ProgrammingError('HY000','Attempt to close a closed connection.')
        
        
        if self.connected:
            if DEBUG: print 'disconnect'
            if not self.autocommit:
                self.rollback()
            ret = ODBC_API.SQLDisconnect(self.dbc_h)
            validate(ret, SQL_HANDLE_DBC, self.dbc_h)
        if DEBUG: print 'free dbc'
        ret = ODBC_API.SQLFreeHandle(SQL_HANDLE_DBC, self.dbc_h)
        validate(ret, SQL_HANDLE_DBC, self.dbc_h)
#        if shared_env_h.value:
#            if DEBUG: print 'env'
#            ret = ODBC_API.SQLFreeHandle(SQL_HANDLE_ENV, shared_env_h)
#            validate(ret, SQL_HANDLE_ENV, shared_env_h)
        self.connected = 0
        
odbc = Connection
connect = odbc
'''
def connect(connectString = '', autocommit = False, ansi = False, timeout = 0, unicode_results = False, readonly = False, **kargs):
    return odbc(connectString, autocommit, ansi, timeout, unicode_results, readonly, kargs)
'''

def win_create_mdb(mdb_path, sort_order = "General\0\0"):
    #CREATE_DB=<path name> <sort order>
    c_Path = "CREATE_DB=" + mdb_path + " " + sort_order
    ODBC_ADD_SYS_DSN = 1
    ctypes.windll.ODBCCP32.SQLConfigDataSource(None,ODBC_ADD_SYS_DSN,"Microsoft Access Driver (*.mdb)", c_Path)


def win_compact_mdb(mdb_path, compacted_mdb_path, sort_order = "General\0\0"):
    #COMPACT_DB=<source path> <destination path> <sort order>
    c_Path = "COMPACT_DB=" + mdb_path + " " + compacted_mdb_path + " " + sort_order
    ODBC_ADD_SYS_DSN = 1
    ctypes.windll.ODBCCP32.SQLConfigDataSource(None,ODBC_ADD_SYS_DSN,"Microsoft Access Driver (*.mdb)", c_Path)


def dataSources():
    """Return a list with [name, descrition]"""
    dsn = create_buffer(1024)
    desc = create_buffer(1024)
    dsn_len = ctypes.c_int()
    desc_len = ctypes.c_int()
    dsn_list = {}
    if shared_env_h == None:
        AllocateEnv()
    while 1:
        ret = ODBC_API.SQLDataSources(shared_env_h, SQL_FETCH_NEXT, \
            dsn, len(dsn), ADDR(dsn_len), desc, len(desc), ADDR(desc_len))
        if ret == SQL_NO_DATA_FOUND:
            break
        elif not ret in (SQL_SUCCESS, SQL_SUCCESS_WITH_INFO):
            ctrl_err(SQL_HANDLE_ENV, shared_env_h, ret)
        else:
            dsn_list[dsn.value] = desc.value
    return dsn_list
