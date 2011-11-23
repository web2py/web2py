#########################################################################
## This scaffolding model makes your app work on Google App Engine too
#########################################################################

if request.controller.endswith('_examples'): response.generic_patterns.append('*')

from gluon.settings import settings

# if running on Google App Engine
if settings.web2py_runtime_gae:
    from gluon.contrib.gql import *
    # connect to Google BigTable
    db = DAL('gae')
    # and store sessions there
    session.connect(request, response, db=db)
else:
    # if not, use SQLite or other DB
    db = DAL('sqlite://storage.sqlite')

db.define_table(
    'users',
    Field('name'),
    Field('email')
    )

# ONE (users) TO MANY (dogs)

db.define_table(
    'dogs',
    Field('owner_id', db.users),
    Field('name'),
    Field('type'),
    Field('vaccinated', 'boolean', default=False),
    Field('picture', 'upload', default=''),
    )

db.define_table(
    'products',
    Field('name'),
    Field('description', 'text')
    )

# MANY (users) TO MANY (purchases)

db.define_table(
    'purchases',
    Field('buyer_id', db.users),
    Field('product_id', db.products),
    Field('quantity', 'integer')
    )

# if running on Google App Engine
if settings.web2py_runtime_gae:
    # quick hack to skip the join
    purchased = None
else:
    # use a joined view
    purchased = (db.users.id == db.purchases.buyer_id) & (db.products.id
                 == db.purchases.product_id)

db.users.name.requires = IS_NOT_EMPTY()
db.users.email.requires = [IS_EMAIL(), IS_NOT_IN_DB(db, 'users.email')]
db.dogs.owner_id.requires = IS_IN_DB(db, 'users.id', 'users.name')
db.dogs.name.requires = IS_NOT_EMPTY()
db.dogs.type.requires = IS_IN_SET(['small', 'medium', 'large'])
db.purchases.buyer_id.requires = IS_IN_DB(db, 'users.id', 'users.name')
db.purchases.product_id.requires = IS_IN_DB(db, 'products.id',
        'products.name')
db.purchases.quantity.requires = IS_INT_IN_RANGE(0, 10)
