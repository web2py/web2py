db = DAL(lazy_tables = True)

db.define_table('x',
                Field('name', 'string')
                )

db.define_table('y',
                Field('x', 'reference x'),
                Field('age', 'integer', default = 30)
                )

x_id = db.x.insert(name = 'barry')
db.y.insert(x = x_id, age = 99)

x = db(db.x.id > 0).select().first()
for y in x.y.select():
    print y
