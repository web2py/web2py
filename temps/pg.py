from gluon.dal import PostgreSQLAdapter
db = DAL()
db.define_table('test',Field('name'))
db._adapter.close()
db._adapter = PostgreSQLAdapter(db,'postgres://a:b@example.com/demo',do_connect=False)
print db(db.test)._select()
