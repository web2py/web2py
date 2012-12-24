db=DAL()
db.define_table('person',Field('name'))
db.person.insert(name="max")
db.person.insert(name="max")
db.person.insert(name="max")
print db(db.person).select().xml(strict=True)

import pickle

print db.person[1]
s = pickle.dumps(db.person[1])
print pickle.loads(s)
