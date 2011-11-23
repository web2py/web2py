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
    'person',
    Field('name'),
    Field('email'),
    format = '%(name)s',
    singular = 'Person',
    plural = 'Persons',
    )

# ONE (person) TO MANY (dogs)

db.define_table(
    'dog',
    Field('owner_id', db.person),
    Field('name'),
    Field('type'),
    Field('vaccinated', 'boolean', default=False),
    Field('picture', 'upload', default=''),
    format = '%(name)s',
    singular = 'Dog',
    plural = 'Dogs',
    )

db.define_table(
    'product',
    Field('name'),
    Field('description', 'text'),
    format = '%(name)s',
    singular = 'Product',
    plural = 'Products',
    )

# MANY (persons) TO MANY (purchases)

db.define_table(
    'purchase',
    Field('buyer_id', db.person),
    Field('product_id', db.product),
    Field('quantity', 'integer'),
    format = '%(quantity)s %(product_id)s -> %(buyer_id)s',
    singular = 'Purchase',
    plural = 'Purchases',
    )

purchased = \
    (db.person.id==db.purchase.buyer_id)&\
    (db.product.id==db.purchase.product_id)

db.person.name.requires = IS_NOT_EMPTY()
db.person.email.requires = [IS_EMAIL(), IS_NOT_IN_DB(db, 'person.email')]
db.dog.name.requires = IS_NOT_EMPTY()
db.dog.type.requires = IS_IN_SET(('small', 'medium', 'large'))
db.purchase.quantity.requires = IS_INT_IN_RANGE(0, 10)
