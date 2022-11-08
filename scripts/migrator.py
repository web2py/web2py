# -*- coding: utf-8 -*-
'''
To use, e.g. python .\web2py.py -S APPNAME --force_migrate
To use, e.g. python .\web2py.py -S APPNAME --force_migrate --fake_migrate
'''

import logging

logger = logging.getLogger("web2py")


def get_databases(request):
    dbs = {}
    global_env = globals()
    for (key, value) in global_env.items():
        try:
            cond = isinstance(value, GQLDB)
        except:
            cond = isinstance(value, SQLDB)
        if cond:
            dbs[key] = value
    return dbs


logger.debug('Getting all databases')
databases = get_databases(None)
logger.debug('databases = %s', databases)
for db_name in databases:
    logger.debug('Migrating %s', db_name)
    db = databases[db_name]
    tables = db.tables
    for table_name in tables:
        # Force migration of lazy tables
        logger.debug("Ensuring migration of table '%s'", table_name)
        table = db[table_name]
        # virtual fields can actually cause problems with migrations because
        # the migration script uses db(table).isempty() to "unlazy" the table.
        # isempty is implemented with a select with limitby=(0, 1)
        # if the table is not empty the virtual fields will be processed
        # and if they query other tables you will have problems.
        table._virtual_fields = []        
        db(table).isempty()
    db.commit()
