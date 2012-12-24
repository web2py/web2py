db=DAL()
db.define_table('t',Field('a'))
db.t.insert(a='xxx')
rows = db(db.t).select()
import pickle
print pickle.loads(pickle.dumps(rows))
rows = db(db.t).select(cacheable=True)
s= pickle.dumps(rows)
print pickle.loads(s)
