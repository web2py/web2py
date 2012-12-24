db=DAL()
db.define_table('test',Field('myid','id'),Field('name'))
db.test.insert(name='max')
row=db.test[1]
print row
