import pickle
db=DAL()
db.define_table('person',Field('name'))
db.define_table('thing',Field('name'),Field('owner','reference person'))
id = db.person.insert(name='Tim')
db.thing.insert(name='chair',owner=id)
rows = db(db.person).select()

a = pickle.dumps(rows[0])
b = pickle.loads(a)
print b
print type(b)
print b.name

a = pickle.dumps(rows)
b = pickle.loads(a)
print b
print type(b)
print b.db == db

print b[0]['name']
print b.first().name
b.first().update_record(name='Max')
print b.first().thing.select()
