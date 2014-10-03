# -*- coding: utf-8 -*-
from .sqlite import SQLiteAdapter, SpatiaLiteAdapter, JDBCSQLiteAdapter
from .mysql import MySQLAdapter
from .postgre import PostgreSQLAdapter, NewPostgreSQLAdapter, JDBCPostgreSQLAdapter
from .oracle import OracleAdapter
from .mssql import MSSQLAdapter, MSSQL2Adapter, MSSQL3Adapter, MSSQL4Adapter, \
    VerticaAdapter, SybaseAdapter
from .firebird import FireBirdAdapter
from .informix import InformixAdapter, InformixSEAdapter
from .db2 import DB2Adapter
from .teradata import TeradataAdapter
from .ingres import IngresAdapter, IngresUnicodeAdapter
from .sapdb import SAPDBAdapter
from .cubrid import CubridAdapter
from .google import GoogleDatastoreAdapter, GoogleSQLAdapter
from .couchdb import CouchDBAdapter
from .mongo import MongoDBAdapter
from .imap import IMAPAdapter


ADAPTERS = {
    'sqlite': SQLiteAdapter,
    'spatialite': SpatiaLiteAdapter,
    'sqlite:memory': SQLiteAdapter,
    'spatialite:memory': SpatiaLiteAdapter,
    'mysql': MySQLAdapter,
    'postgres': PostgreSQLAdapter,
    'postgres:psycopg2': PostgreSQLAdapter,
    'postgres:pg8000': PostgreSQLAdapter,
    'postgres2:psycopg2': NewPostgreSQLAdapter,
    'postgres2:pg8000': NewPostgreSQLAdapter,
    'oracle': OracleAdapter,
    'mssql': MSSQLAdapter,
    'mssql2': MSSQL2Adapter,
    'mssql3': MSSQL3Adapter,
    'mssql4' : MSSQL4Adapter,
    'vertica': VerticaAdapter,
    'sybase': SybaseAdapter,
    'db2': DB2Adapter,
    'teradata': TeradataAdapter,
    'informix': InformixAdapter,
    'informix-se': InformixSEAdapter,
    'firebird': FireBirdAdapter,
    'firebird_embedded': FireBirdAdapter,
    'ingres': IngresAdapter,
    'ingresu': IngresUnicodeAdapter,
    'sapdb': SAPDBAdapter,
    'cubrid': CubridAdapter,
    'jdbc:sqlite': JDBCSQLiteAdapter,
    'jdbc:sqlite:memory': JDBCSQLiteAdapter,
    'jdbc:postgres': JDBCPostgreSQLAdapter,
    'gae': GoogleDatastoreAdapter, # discouraged, for backward compatibility
    'google:datastore': GoogleDatastoreAdapter,
    'google:datastore+ndb': GoogleDatastoreAdapter,
    'google:sql': GoogleSQLAdapter,
    'couchdb': CouchDBAdapter,
    'mongodb': MongoDBAdapter,
    'imap': IMAPAdapter
}
