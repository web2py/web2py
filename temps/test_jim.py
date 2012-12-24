import datetime
import os

db = DAL()
from gluon.tools import Auth

auth = Auth(db) # authentication/authorization

auth_user = db.define_table(
 auth.settings.table_user_name,
 Field('first_name', length=128, default='', required=True),
 Field('last_name', length=128, default='', required=True),
 Field('email', length=128, unique=True, required=True),
 Field('password', 'password', length=512,
 readable=True, writable=True, label='Password'),
 Field('registration_key', length=512,
 writable=False, readable=False, default=''),
 Field('reset_password_key', length=512,
 writable=False, readable=False, default=''),
 Field('registration_id', length=512,
 writable=False, readable=False, default=''),
 Field('brillLogon', length=10, default='', label='Brill Logon'),
 Field('technician', 'boolean', default=False),
 Field('dispatcher', 'boolean', default=False),
 Field('lastFirst', compute=lambda u: '%s, %s' % (u['last_name'], u['first_name']), label='Name'),
 Field('firstLast', compute=lambda u: '%s %s' % (u['first_name'], u['last_name']), label='Name'),
 format='%(last_name)s, %(first_name)s')

auth_user.first_name.requires = IS_NOT_EMPTY(error_message=auth.messages.is_empty)
auth_user.last_name.requires = IS_NOT_EMPTY(error_message=auth.messages.is_empty)
auth_user.password.requires = [CRYPT()]
auth_user.email.requires = [IS_EMAIL(error_message=auth.messages.invalid_email),
 IS_NOT_IN_DB(db, auth_user.email), 
 IS_NOT_EMPTY(error_message=auth.messages.is_empty)]
auth_user.id.readable = False
auth_user._plural = 'Users'

auth.settings.table_user = auth_user
auth.define_tables() # creates all needed tables

warehouse = db.define_table('warehouse',
 Field('warehouseId', 'id'),
 Field('warehouseNumber', 'integer', required=True, unique=True, label='Warehouse #'),

 Field('name', length=50, required=True, unique=True),

 Field('allowPricesToFall', 'boolean', default=False,
 label='Allow Prices to Fall'),
 Field('hin', length=10),
 Field('active', 'boolean', default=True),
 format='%(warehouseNumber)s - %(name)s')

warehouse.warehouseNumber.requires = [IS_NOT_EMPTY(error_message=auth.messages.is_empty),
 IS_NOT_IN_DB(db, warehouse.warehouseNumber)]
warehouse.name.requires = [IS_NOT_IN_DB(db, warehouse.name), 
 IS_NOT_EMPTY(error_message=auth.messages.is_empty)]
warehouse._plural = 'Warehouses'


link = db.define_table('link', 
 Field('linkId', 'id', readable=False),
 Field('name', length=50, required=True, unique=True),
 Field('parentLinkId', 'reference link', required=True,
 label='Parent Link'),
 Field('controller', length=512, required=True),
 Field('method', length=512, required=True),
 Field('picture', length=512, required=False),
 Field('permissionId', db.auth_permission, label='Rqd Permission'),
 Field('groupId', db.auth_group, label='Rqd Group'),
 Field('description', 'text', required=True),
 format='%(name)s')
