"""Create web2py model (python code) to represent MS SQL Server tables.
Features:
* Uses ANSI Standard INFORMATION_SCHEMA (might work with other RDBMS)
* Detects legacy "keyed" tables (not having an "id" PK)
* Handles 'funny' column names. web2py requires all column names be valid python identifiers. This script uses rname
*   for column names that have spaces or are otherwise invalid python identifiers.
* Connects directly to running databases, no need to do a SQL dump
* Handles notnull, unique and referential constraints
* Detects most common datatypes and default values
* Supports running from the command line as well as from an IDE's debug menu. See the COMMAND_LINE_MODE constant below
*   for more info.

Requirements:
* Needs pyodbc python connector

Created by Kyle Flanagan. Based on a script by Mariano Reingart which was
based on a script to "generate schemas from dbs" (mysql) by Alexandre Andrade
"""

_author__ = "Kyle Flanagan <kyleflanagan@gmail.com>"

HELP = """
USAGE: extract_mssql_models db host port user passwd
Call with SQL Server database connection parameters,
web2py model will be printed on standard output.
EXAMPLE: python extract_mssql_models.py mydb localhost 3306 kflanaga pass
or
python extract_mssql_models.py mydb localhost 3306 kflanaga pass > db_model.py
"""

# Config options
DEBUG = False  # print debug messages to STDERR
SCHEMA = 'dbo'
COMMAND_LINE_MODE = True  # running from command prompt. Disable to specify variables and use in IDE
# Only specify values below if not running from command line
DB = None
HOST = None
USER = None
PASSWD = None
PORT = None

# Constant for Field keyword parameter order (and filter):
KWARGS = ('type', 'length', 'default', 'required', 'ondelete',
          'notnull', 'unique', 'label', 'comment', 'rname')

import sys
import re
# This is from pydal/helpers/regex.py as of 2016-06-16
# Use this to recognize if a field name need to have an rname representation
REGEX_VALID_TB_FLD = re.compile(r'^[^\d_][_0-9a-zA-Z]*\Z')
# For replacing invalid characters in field names
INVALID_CHARS = re.compile(r'[^a-zA-Z0-9_]')


def get_valid_column_name(field):
    """Return a valid column name that follows Python's rules for identifiers, which is what web2py requires for column
    names. Replaces invalid characters with underscores and leading digits with their associated English word."""
    if not REGEX_VALID_TB_FLD.match(field):
        # If the first character is a digit, replace it with its word counterpart
        if re.match(r'^[0-9]', field):
            numbers = ['Zero', 'One', 'Two', 'Three', 'Four',
                       'Five', 'Six', 'Seven', 'Eight', 'Nine']
            field = numbers[int(field[0])] + field[1:]

        field = INVALID_CHARS.sub('_', field)
    return field


def query(conn, sql, *args):
    "Execute a SQL query and return rows as a list of dicts"
    cur = conn.cursor()
    ret = []
    try:
        if DEBUG: print >> sys.stderr, "QUERY: ", sql % args
        cur.execute(sql % args)
        for row in cur:
            dic = {}
            for i, value in enumerate(row):
                field = cur.description[i][0]
                dic[field] = value
            if DEBUG: print >> sys.stderr, "RET: ", dic
            ret.append(dic)
        return ret
    finally:
        cur.close()


def get_tables(conn, schema=SCHEMA):
    "List table names in a given schema"
    rows = query(conn, """SELECT table_name FROM information_schema.tables
        WHERE table_schema = '%s'
        ORDER BY table_name""", schema)
    return [row['table_name'] for row in rows]


def get_fields(conn, table):
    "Retrieve field list for a given table"
    if DEBUG: print >> sys.stderr, "Processing TABLE", table
    rows = query(conn, """
        SELECT column_name, data_type,
            is_nullable,
            character_maximum_length,
            numeric_precision, numeric_precision_radix, numeric_scale,
            column_default
        FROM information_schema.columns
        WHERE table_name='%s'
        ORDER BY ordinal_position""", table)
    return rows


def define_field(conn, table, field, pks):
    "Determine field type, default value, references, etc."
    f = {}
    ref = references(conn, table, field['column_name'])
    if ref:
        f.update(ref)
    elif field['column_default'] and \
            field['column_default'].startswith("nextval") and \
                    field['column_name'] in pks:
        f['type'] = "'id'"
    elif field['data_type'].startswith('character'):
        f['type'] = "'string'"
        if field['character_maximum_length']:
            f['length'] = field['character_maximum_length']
    elif field['data_type'] in ('text', 'ntext'):
        f['type'] = "'text'"
    elif field['data_type'] in ('boolean', 'bit'):
        f['type'] = "'boolean'"
    elif field['data_type'] in ('tinyint', 'smallint', 'bigint', 'int'):
        f['type'] = "'integer'"
    elif field['data_type'] in ('real', 'float'):
        f['type'] = "'double'"
    elif field['data_type'] in ('datetime', 'datetime2', 'smalldatetime'):
        f['type'] = "'datetime'"
    elif field['data_type'] in ('timestamp',):
        f['type'] = "'datetime'"
        f['default'] = "request.now"
        f['update'] = "request.now"
    elif field['data_type'] in ('date',):
        f['type'] = "'date'"
    elif field['data_type'] in ('time',):
        f['type'] = "'time'"
    elif field['data_type'] in ('numeric', 'money', 'smallmoney', 'decimal'):
        f['type'] = "'decimal'"
        f['precision'] = field['numeric_precision']
        f['scale'] = field['numeric_scale'] or 0
    elif field['data_type'] in ('binary', 'varbinary', 'image'):
        f['type'] = "'blob'"
    elif field['data_type'] in ('point', 'lseg', 'polygon', 'unknown', 'USER-DEFINED', 'sql_variant'):
        f['type'] = ""  # unsupported?
    elif field['data_type'] in ('varchar', 'char', 'nchar', 'nvarchar', 'uniqueidentifer'):
        f['type'] = "'string'"
    else:
        raise RuntimeError("Data Type not supported: %s " % str(field))

    try:
        if field['column_default']:
            if field['column_default'] == "now()":
                d = "request.now"
            elif field['column_default'] == "true":
                d = "True"
            elif field['column_default'] == "false":
                d = "False"
            else:
                d = repr(eval(field['column_default']))
            f['default'] = str(d)
    except (ValueError, SyntaxError):
        pass
    except Exception, e:
        raise RuntimeError("Default unsupported '%s'" % field['column_default'])

    if not field['is_nullable']:
        f['notnull'] = "True"

    # For field names that are not valid python identifiers, we need to add a reference to their actual name
    # in the back end database
    if not REGEX_VALID_TB_FLD.match(field['column_name']):
        f['rname'] = "'[%s]'" % field['column_name']

    return f


def is_unique(conn, table, field):
    "Find unique columns (incomplete support)"
    rows = query(conn, """
        SELECT c.column_name
        FROM information_schema.table_constraints t
        INNER JOIN information_schema.constraint_column_usage c
        ON (t.CONSTRAINT_CATALOG =    c.CONSTRAINT_CATALOG
            AND t.CONSTRAINT_NAME =   c.CONSTRAINT_NAME
            AND t.CONSTRAINT_SCHEMA = c.CONSTRAINT_SCHEMA
            AND t.TABLE_CATALOG =     c.TABLE_CATALOG
            AND t.TABLE_NAME =        c.TABLE_NAME
            AND t.TABLE_SCHEMA =      c.TABLE_SCHEMA)
        WHERE t.table_name='%s'
          AND c.column_name='%s'
          AND t.constraint_type='UNIQUE'
        ;""", table, field['column_name'])
    return rows and True or False


def primarykeys(conn, table):
    "Find primary keys"
    rows = query(conn, """
        SELECT c.column_name
        FROM information_schema.table_constraints t
        INNER JOIN information_schema.constraint_column_usage c
                ON (t.CONSTRAINT_CATALOG =    c.CONSTRAINT_CATALOG
            AND t.CONSTRAINT_NAME =   c.CONSTRAINT_NAME
            AND t.CONSTRAINT_SCHEMA = c.CONSTRAINT_SCHEMA
            AND t.TABLE_CATALOG =     c.TABLE_CATALOG
            AND t.TABLE_NAME =        c.TABLE_NAME
            AND t.TABLE_SCHEMA =      c.TABLE_SCHEMA)
        WHERE t.table_name='%s'
          AND t.constraint_type='PRIMARY KEY'
        ;""", table)
    return [row['column_name'] for row in rows]


def references(conn, table, field):
    "Find a FK (fails if multiple)"
    rows1 = query(conn, """
        SELECT k.table_name, k.column_name, k.constraint_name,
               r.update_rule, r.delete_rule, k.ordinal_position
        FROM information_schema.key_column_usage k
        INNER JOIN information_schema.referential_constraints r
        ON (k.CONSTRAINT_CATALOG =    r.CONSTRAINT_CATALOG
            AND k.CONSTRAINT_NAME =   r.CONSTRAINT_NAME
            AND k.CONSTRAINT_SCHEMA = r.CONSTRAINT_SCHEMA)
        INNER JOIN information_schema.table_constraints t
        ON (r.CONSTRAINT_CATALOG =    t.CONSTRAINT_CATALOG
            AND r.CONSTRAINT_NAME =   t.CONSTRAINT_NAME
            AND r.CONSTRAINT_SCHEMA = t.CONSTRAINT_SCHEMA)

        WHERE k.table_name='%s'
          AND k.column_name='%s'
          AND t.constraint_type='FOREIGN KEY'
          ;""", table, field)
    if len(rows1) == 1:
        rows2 = query(conn, """
            SELECT table_name, column_name, *
            FROM information_schema.constraint_column_usage
            WHERE constraint_name='%s'
            """, rows1[0]['constraint_name'])
        row = None
        if len(rows2) > 1:
            row = rows2[int(rows1[0]['ordinal_position']) - 1]
            keyed = True
        if len(rows2) == 1:
            row = rows2[0]
            keyed = False
        if row:
            if keyed:  # THIS IS BAD, DON'T MIX "id" and primarykey!!!
                ref = {'type': "'reference %s.%s'" % (row['table_name'],
                                                      row['column_name'])}
            else:
                ref = {'type': "'reference %s'" % (row['table_name'],)}
            if rows1[0]['delete_rule'] != "NO ACTION":
                ref['ondelete'] = repr(rows1[0]['delete_rule'])
            return ref
        elif rows2:
            raise RuntimeError("Unsupported foreign key reference: %s" %
                               str(rows2))

    elif rows1:
        raise RuntimeError("Unsupported referential constraint: %s" %
                           str(rows1))


def define_table(conn, table):
    "Output single table definition"
    fields = get_fields(conn, table)
    pks = primarykeys(conn, table)
    print "db.define_table('%s'," % (table,)
    for field in fields:
        fname = field['column_name']
        fdef = define_field(conn, table, field, pks)
        if fname not in pks and is_unique(conn, table, field):
            fdef['unique'] = "True"
        if fdef['type'] == "'id'" and fname in pks:
            pks.pop(pks.index(fname))
        print "    Field('%s', %s)," % (get_valid_column_name(fname),
                                        ', '.join(["%s=%s" % (k, fdef[k]) for k in KWARGS
                                                   if k in fdef and fdef[k]]))
    if pks:
        print "    primarykey=[%s]," % ", ".join(["'%s'" % pk for pk in pks])
    print     "    migrate=migrate)"
    print


def define_db(conn, db, host, port, user, passwd):
    "Output database definition (model)"
    dal = 'db = DAL("mssql4://%s:%s@%s:%s/%s", pool_size=10, decode_credentials=True)'
    print dal % (
        user.replace('@', '%40').replace(':', '%3A'), passwd.replace('@', '%40').replace(':', '%3A'), host, port, db)
    print
    print "migrate = False"
    print
    for table in get_tables(conn):
        define_table(conn, table)


if __name__ == "__main__":
    # Parse arguments from command line:
    if len(sys.argv) < 6 and COMMAND_LINE_MODE:
        print HELP
    else:
        # Parse arguments from command line:
        if COMMAND_LINE_MODE:
            db, host, port, user, passwd = sys.argv[1:6]
        else:
            db = DB
            host = HOST
            user = USER
            passwd = PASSWD
            port = PORT

        # Make the database connection (change driver if required)
        import pyodbc
        # cnn = pyodbc.connect(database=db, host=host, port=port,
        #                        user=user, password=passwd,
        #                        )
        cnn = pyodbc.connect(
            r'DRIVER={{SQL Server Native Client 11.0}};SERVER={server};PORT={port};DATABASE={db};UID={user};PWD={passwd}'.format(
                server=host, port=port, db=db, user=user, passwd=passwd)
        )
        # Start model code generation:
        define_db(cnn, db, host, port, user, passwd)
