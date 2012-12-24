db =DAL()
db.define_table('person',Field('name'))

from gluon.dal import Expression
def IF(a,b,c,t=None):
    db,f = a.db, a.db._adapter.expand
    def r(x,represent=db._adapter.represent):        
        if x is None: return 'NULL'
        elif isinstance(x,Expression): return str(x)
        types = {type(True): 'boolean',
                 type(0): 'integer',
                 type(1.0): 'double'}
        return represent(x,types.get(type(x),'string'))
    return Expression(db,'CASE WHEN %s THEN %s ELSE %s END' % (f(a),r(b),r(c)))

db.person.insert(name='x')
db.person.insert(name='y')
db.person.insert(name='z')
print db().select(db.person.ALL, (db.person.name=='x').case('A',(db.person.name=='y').case('B','C')))
