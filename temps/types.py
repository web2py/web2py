import copy
db =DAL()
db._adapter.types = copy.copy(db._adapter.types)
db._adapter.types['boolean']='INTEGER'
db._adapter.TRUE = 1
db._adapter.FALSE = 0
db.define_table('test',Field('b', 'boolean'))
db.test.insert(b=True)
db.test.insert(b=False)
rows = db(db.test).select()
print db.executesql(db(db.test)._select())
