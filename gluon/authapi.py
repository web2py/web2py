# -*- coding: utf-8 -*-
"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""
from gluon._compat import long
from gluon import current
from gluon.storage import Messages, Settings, Storage
from gluon.utils import web2py_uuid
from gluon.validators import CRYPT, IS_EMAIL, IS_EQUAL_TO, IS_INT_IN_RANGE, IS_LOWER, IS_MATCH, IS_NOT_EMPTY, \
    IS_NOT_IN_DB
from pydal.objects import Table, Field, Row
import datetime
from gluon.settings import global_settings

DEFAULT = lambda: None


class AuthAPI(object):
    """
    AuthAPI is a barebones Auth implementation which does not have a concept of
    HTML forms or redirects, emailing or even an URL, you are responsible for
    all that if you use it.
    The main Auth functions such as login, logout, register, profile are designed
    in a Dict In -> Dict Out logic so, for instance, if you set
    registration_requires_verification you are responsible for sending the key to
    the user and even rolling back the transaction if you can't do it.

    NOTES: * It does not support all the callbacks Traditional Auth does yet.
             Some of the callbacks will not be supported.
             Check the method signatures to find out which ones are supported.
           * register_fields and profile_fields settings are ignored for now.

    WARNING: No builtin CSRF protection whatsoever.
    """

    default_settings = {
        'create_user_groups': 'user_%(id)s',
        'email_case_sensitive': False,
        'everybody_group_id': None,
        'expiration': 3600,
        'keep_session_onlogin': True,
        'keep_session_onlogout': False,
        'logging_enabled': True,
        'login_after_registration': False,
        'login_email_validate': True,
        'login_userfield': None,
        'logout_onlogout': None,
        'long_expiration': 3600 * 24 * 30,
        'ondelete': 'CASCADE',
        'password_field': 'password',
        'password_min_length': 4,
        'registration_requires_approval': False,
        'registration_requires_verification': False,
        'renew_session_onlogin': True,
        'renew_session_onlogout': True,
        'table_event_name': 'auth_event',
        'table_group_name': 'auth_group',
        'table_membership_name': 'auth_membership',
        'table_permission_name': 'auth_permission',
        'table_user_name': 'auth_user',
        'use_username': False,
        'username_case_sensitive': True
    }

    default_messages = {
        'add_group_log': 'Group %(group_id)s created',
        'add_membership_log': None,
        'add_permission_log': None,
        'change_password_log': 'User %(id)s Password changed',
        'del_group_log': 'Group %(group_id)s deleted',
        'del_membership_log': None,
        'del_permission_log': None,
        'email_taken': 'This email already has an account',
        'group_description': 'Group uniquely assigned to user %(id)s',
        'has_membership_log': None,
        'has_permission_log': None,
        'invalid_email': 'Invalid email',
        'key_verified': 'Key verified',
        'invalid_login': 'Invalid login',
        'invalid_password': 'Invalid password',
        'invalid_user': 'Invalid user',
        'invalid_key': 'Invalid key',
        'invalid_username': 'Invalid username',
        'logged_in': 'Logged in',
        'logged_out': 'Logged out',
        'login_failed_log': None,
        'login_log': 'User %(id)s Logged-in',
        'logout_log': 'User %(id)s Logged-out',
        'mismatched_password': "Password fields don't match",
        'password_changed': 'Password changed',
        'profile_log': 'User %(id)s Profile updated',
        'profile_updated': 'Profile updated',
        'register_log': 'User %(id)s Registered',
        'registration_pending': 'Registration is pending approval',
        'registration_successful': 'Registration successful',
        'registration_verifying': 'Registration needs verification',
        'username_taken': 'Username already taken',
        'verify_log': 'User %(id)s verified registration key'
    }

    def __init__(self, db=None, hmac_key=None, signature=True):
        self.db = db
        session = current.session
        auth = session.auth
        self.user_groups = auth and auth.user_groups or {}
        now = current.request.now
        # if we have auth info
        #    if not expired it, used it
        #    if expired, clear the session
        # else, only clear auth info in the session
        if auth:
            delta = datetime.timedelta(days=0, seconds=auth.expiration)
            if auth.last_visit and auth.last_visit + delta > now:
                self.user = auth.user
                # this is a trick to speed up sessions to avoid many writes
                if (now - auth.last_visit).seconds > (auth.expiration // 10):
                    auth.last_visit = now
            else:
                self.user = None
                if session.auth:
                    del session.auth
                session.renew(clear_session=True)
        else:
            self.user = None
            if session.auth:
                del session.auth

        settings = self.settings = Settings(self.__class__.default_settings)
        settings.update(
            extra_fields={},
            hmac_key=hmac_key,
        )
        settings.lock_keys = True
        messages = self.messages = Messages(current.T)
        messages.update(self.default_messages)
        messages.lock_keys = True
        if signature is True:
            self.define_signature()
        else:
            self.signature = signature or None

    def __validate(self, value, requires):
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        for validator in requires:
            (value, error) = validator(value)
            if error:
                return (value, error)
        return (value, None)

    def _get_migrate(self, tablename, migrate=True):

        if type(migrate).__name__ == 'str':
            return (migrate + tablename + '.table')
        elif not migrate:
            return False
        else:
            return True

    def _get_user_id(self):
        """accessor for auth.user_id"""
        return self.user and self.user.id or None

    user_id = property(_get_user_id, doc="user.id or None")

    def table_user(self):
        return self.db[self.settings.table_user_name]

    def table_group(self):
        return self.db[self.settings.table_group_name]

    def table_membership(self):
        return self.db[self.settings.table_membership_name]

    def table_permission(self):
        return self.db[self.settings.table_permission_name]

    def table_event(self):
        return self.db[self.settings.table_event_name]

    def define_signature(self):
        db = self.db
        settings = self.settings
        request = current.request
        T = current.T
        reference_user = 'reference %s' % settings.table_user_name

        def lazy_user(auth=self):
            return auth.user_id

        def represent(id, record=None, s=settings):
            try:
                user = s.table_user(id)
                return '%s %s' % (user.get("first_name", user.get("email")),
                                  user.get("last_name", ''))
            except:
                return id
        ondelete = self.settings.ondelete
        self.signature = Table(
            self.db, 'auth_signature',
            Field('is_active', 'boolean',
                  default=True,
                  readable=False, writable=False,
                  label=T('Is Active')),
            Field('created_on', 'datetime',
                  default=request.now,
                  writable=False, readable=False,
                  label=T('Created On')),
            Field('created_by',
                  reference_user,
                  default=lazy_user, represent=represent,
                  writable=False, readable=False,
                  label=T('Created By'), ondelete=ondelete),
            Field('modified_on', 'datetime',
                  update=request.now, default=request.now,
                  writable=False, readable=False,
                  label=T('Modified On')),
            Field('modified_by',
                  reference_user, represent=represent,
                  default=lazy_user, update=lazy_user,
                  writable=False, readable=False,
                  label=T('Modified By'),  ondelete=ondelete))

    def define_tables(self, username=None, signature=None, migrate=None,
                      fake_migrate=None):
        """
        To be called unless tables are defined manually

        Examples:
            Use as::

                # defines all needed tables and table files
                # 'myprefix_auth_user.table', ...
                auth.define_tables(migrate='myprefix_')

                # defines all needed tables without migration/table files
                auth.define_tables(migrate=False)

        """

        db = self.db
        if migrate is None:
            migrate = db._migrate
        if fake_migrate is None:
            fake_migrate = db._fake_migrate

        settings = self.settings
        if username is None:
            username = settings.use_username
        else:
            settings.use_username = username

        if not self.signature:
            self.define_signature()
        if signature is True:
            signature_list = [self.signature]
        elif not signature:
            signature_list = []
        elif isinstance(signature, Table):
            signature_list = [signature]
        else:
            signature_list = signature
        self._table_signature_list = signature_list  # Should it defined in __init__ first??

        is_not_empty = IS_NOT_EMPTY(error_message=self.messages.is_empty)
        is_crypted = CRYPT(key=settings.hmac_key,
                           min_length=settings.password_min_length)
        is_unique_email = [
            IS_EMAIL(error_message=self.messages.invalid_email),
            IS_NOT_IN_DB(db, '%s.email' % settings.table_user_name,
                         error_message=self.messages.email_taken)]
        if not settings.email_case_sensitive:
            is_unique_email.insert(1, IS_LOWER())
        if settings.table_user_name not in db.tables:
            passfield = settings.password_field
            extra_fields = settings.extra_fields.get(
                settings.table_user_name, []) + signature_list
            # cas_provider Will always be None here but we compare it anyway so subclasses can use our define_tables
            if username or settings.cas_provider:
                is_unique_username = \
                    [IS_MATCH('[\w\.\-]+', strict=True,
                              error_message=self.messages.invalid_username),
                     IS_NOT_IN_DB(db, '%s.username' % settings.table_user_name,
                                  error_message=self.messages.username_taken)]
                if not settings.username_case_sensitive:
                    is_unique_username.insert(1, IS_LOWER())
                db.define_table(
                    settings.table_user_name,
                    Field('first_name', length=128, default='',
                          label=self.messages.label_first_name,
                          requires=is_not_empty),
                    Field('last_name', length=128, default='',
                          label=self.messages.label_last_name,
                          requires=is_not_empty),
                    Field('email', length=512, default='',
                          label=self.messages.label_email,
                          requires=is_unique_email),
                    Field('username', length=128, default='',
                          label=self.messages.label_username,
                          requires=is_unique_username),
                    Field(passfield, 'password', length=512,
                          readable=False, label=self.messages.label_password,
                          requires=[is_crypted]),
                    Field('registration_key', length=512,
                          writable=False, readable=False, default='',
                          label=self.messages.label_registration_key),
                    Field('reset_password_key', length=512,
                          writable=False, readable=False, default='',
                          label=self.messages.label_reset_password_key),
                    Field('registration_id', length=512,
                          writable=False, readable=False, default='',
                          label=self.messages.label_registration_id),
                    *extra_fields,
                    **dict(
                        migrate=self._get_migrate(settings.table_user_name,
                                                  migrate),
                        fake_migrate=fake_migrate,
                        format='%(username)s'))
            else:
                db.define_table(
                    settings.table_user_name,
                    Field('first_name', length=128, default='',
                          label=self.messages.label_first_name,
                          requires=is_not_empty),
                    Field('last_name', length=128, default='',
                          label=self.messages.label_last_name,
                          requires=is_not_empty),
                    Field('email', length=512, default='',
                          label=self.messages.label_email,
                          requires=is_unique_email),
                    Field(passfield, 'password', length=512,
                          readable=False, label=self.messages.label_password,
                          requires=[is_crypted]),
                    Field('registration_key', length=512,
                          writable=False, readable=False, default='',
                          label=self.messages.label_registration_key),
                    Field('reset_password_key', length=512,
                          writable=False, readable=False, default='',
                          label=self.messages.label_reset_password_key),
                    Field('registration_id', length=512,
                          writable=False, readable=False, default='',
                          label=self.messages.label_registration_id),
                    *extra_fields,
                    **dict(
                        migrate=self._get_migrate(settings.table_user_name,
                                                  migrate),
                        fake_migrate=fake_migrate,
                        format='%(first_name)s %(last_name)s (%(id)s)'))
        reference_table_user = 'reference %s' % settings.table_user_name
        if settings.table_group_name not in db.tables:
            extra_fields = settings.extra_fields.get(
                settings.table_group_name, []) + signature_list
            db.define_table(
                settings.table_group_name,
                Field('role', length=512, default='',
                      label=self.messages.label_role,
                      requires=IS_NOT_IN_DB(db, '%s.role' % settings.table_group_name)),
                Field('description', 'text',
                      label=self.messages.label_description),
                *extra_fields,
                **dict(
                    migrate=self._get_migrate(
                        settings.table_group_name, migrate),
                    fake_migrate=fake_migrate,
                    format='%(role)s (%(id)s)'))
        reference_table_group = 'reference %s' % settings.table_group_name
        if settings.table_membership_name not in db.tables:
            extra_fields = settings.extra_fields.get(
                settings.table_membership_name, []) + signature_list
            db.define_table(
                settings.table_membership_name,
                Field('user_id', reference_table_user,
                      label=self.messages.label_user_id),
                Field('group_id', reference_table_group,
                      label=self.messages.label_group_id),
                *extra_fields,
                **dict(
                    migrate=self._get_migrate(
                        settings.table_membership_name, migrate),
                    fake_migrate=fake_migrate))
        if settings.table_permission_name not in db.tables:
            extra_fields = settings.extra_fields.get(
                settings.table_permission_name, []) + signature_list
            db.define_table(
                settings.table_permission_name,
                Field('group_id', reference_table_group,
                      label=self.messages.label_group_id),
                Field('name', default='default', length=512,
                      label=self.messages.label_name,
                      requires=is_not_empty),
                Field('table_name', length=512,
                      label=self.messages.label_table_name),
                Field('record_id', 'integer', default=0,
                      label=self.messages.label_record_id,
                      requires=IS_INT_IN_RANGE(0, 10 ** 9)),
                *extra_fields,
                **dict(
                    migrate=self._get_migrate(
                        settings.table_permission_name, migrate),
                    fake_migrate=fake_migrate))
        if settings.table_event_name not in db.tables:
            db.define_table(
                settings.table_event_name,
                Field('time_stamp', 'datetime',
                      default=current.request.now,
                      label=self.messages.label_time_stamp),
                Field('client_ip',
                      default=current.request.client,
                      label=self.messages.label_client_ip),
                Field('user_id', reference_table_user, default=None,
                      label=self.messages.label_user_id),
                Field('origin', default='auth', length=512,
                      label=self.messages.label_origin,
                      requires=is_not_empty),
                Field('description', 'text', default='',
                      label=self.messages.label_description,
                      requires=is_not_empty),
                *settings.extra_fields.get(settings.table_event_name, []),
                **dict(
                    migrate=self._get_migrate(
                        settings.table_event_name, migrate),
                    fake_migrate=fake_migrate))

        return self

    def log_event(self, description, vars=None, origin='auth'):
        """
        Examples:
            Use as::

                auth.log_event(description='this happened', origin='auth')

        """
        if not self.settings.logging_enabled or not description:
            return
        elif self.is_logged_in():
            user_id = self.user.id
        else:
            user_id = None  # user unknown
        vars = vars or {}
        # log messages should not be translated
        if type(description).__name__ == 'lazyT':
            description = description.m
        if not user_id or self.table_user()[user_id]:
            self.table_event().insert(
                description=str(description % vars), origin=origin, user_id=user_id)

    def id_group(self, role):
        """
        Returns the group_id of the group specified by the role
        """
        rows = self.db(self.table_group().role == role).select()
        if not rows:
            return None
        return rows[0].id

    def user_group(self, user_id=None):
        """
        Returns the group_id of the group uniquely associated to this user
        i.e. `role=user:[user_id]`
        """
        return self.id_group(self.user_group_role(user_id))

    def user_group_role(self, user_id=None):
        if not self.settings.create_user_groups:
            return None
        if user_id:
            user = self.table_user()[user_id]
        else:
            user = self.user
        return self.settings.create_user_groups % user

    def add_group(self, role, description=''):
        """
        Creates a group associated to a role
        """
        group_id = self.table_group().insert(role=role, description=description)
        self.log_event(self.messages['add_group_log'], dict(group_id=group_id, role=role))
        return group_id

    def del_group(self, group_id):
        """
        Deletes a group
        """
        self.db(self.table_group().id == group_id).delete()
        self.db(self.table_membership().group_id == group_id).delete()
        self.db(self.table_permission().group_id == group_id).delete()
        if group_id in self.user_groups:
            del self.user_groups[group_id]
        self.log_event(self.messages.del_group_log, dict(group_id=group_id))

    def update_groups(self):
        if not self.user:
            return
        user_groups = self.user_groups = {}
        if current.session.auth:
            current.session.auth.user_groups = self.user_groups
        table_group = self.table_group()
        table_membership = self.table_membership()
        memberships = self.db(
            table_membership.user_id == self.user.id).select()
        for membership in memberships:
            group = table_group(membership.group_id)
            if group:
                user_groups[membership.group_id] = group.role

    def add_membership(self, group_id=None, user_id=None, role=None):
        """
        Gives user_id membership of group_id or role
        if user is None than user_id is that of current logged in user
        """

        group_id = group_id or self.id_group(role)
        try:
            group_id = int(group_id)
        except:
            group_id = self.id_group(group_id)  # interpret group_id as a role
        if not user_id and self.user:
            user_id = self.user.id
        if not group_id:
            raise ValueError('group_id not provided or invalid')
        if not user_id:
            raise ValueError('user_id not provided or invalid')
        membership = self.table_membership()
        db = membership._db
        record = db((membership.user_id == user_id) &
                    (membership.group_id == group_id),
                    ignore_common_filters=True).select().first()
        if record:
            if hasattr(record, 'is_active') and not record.is_active:
                record.update_record(is_active=True)
            return record.id
        else:
            id = membership.insert(group_id=group_id, user_id=user_id)
        if role and user_id == self.user_id:
            self.user_groups[group_id] = role
        else:
            self.update_groups()
        self.log_event(self.messages['add_membership_log'],
                       dict(user_id=user_id, group_id=group_id))
        return id

    def del_membership(self, group_id=None, user_id=None, role=None):
        """
        Revokes membership from group_id to user_id
        if user_id is None than user_id is that of current logged in user
        """

        group_id = group_id or self.id_group(role)
        try:
            group_id = int(group_id)
        except:
            group_id = self.id_group(group_id)  # interpret group_id as a role
        if not user_id and self.user:
            user_id = self.user.id
        membership = self.table_membership()
        self.log_event(self.messages['del_membership_log'],
                       dict(user_id=user_id, group_id=group_id))
        ret = self.db(membership.user_id == user_id)(membership.group_id == group_id).delete()
        if group_id in self.user_groups and user_id == self.user_id:
            del self.user_groups[group_id]
        return ret

    def has_membership(self, group_id=None, user_id=None, role=None, cached=False):
        """
        Checks if user is member of group_id or role

        NOTE: To avoid database query at each page load that use auth.has_membership, someone can use cached=True.
              If cached is set to True has_membership() check group_id or role only against auth.user_groups variable
              which is populated properly only at login time. This means that if an user membership change during a
              given session the user has to log off and log in again in order to auth.user_groups to be properly
              recreated and reflecting the user membership modification. There is one exception to this log off and
              log in process which is in case that the user change his own membership, in this case auth.user_groups
              can be properly update for the actual connected user because web2py has access to the proper session
              user_groups variable. To make use of this exception someone has to place an "auth.update_groups()"
              instruction in his app code to force auth.user_groups to be updated. As mention this will only work if it
              the user itself that change it membership not if another user, let say an administrator, change someone
              else's membership.
        """
        if not user_id and self.user:
            user_id = self.user.id
        if cached:
            id_role = group_id or role
            r = (user_id and id_role in self.user_groups.values()) or (user_id and id_role in self.user_groups)
        else:
            group_id = group_id or self.id_group(role)
            try:
                group_id = int(group_id)
            except:
                group_id = self.id_group(group_id)  # interpret group_id as a role
            membership = self.table_membership()
            if group_id and user_id and self.db((membership.user_id == user_id) &
                                                (membership.group_id == group_id)).select():
                r = True
            else:
                r = False
        self.log_event(self.messages['has_membership_log'],
                       dict(user_id=user_id, group_id=group_id, check=r))
        return r

    def add_permission(self,
                       group_id,
                       name='any',
                       table_name='',
                       record_id=0,
                       ):
        """
        Gives group_id 'name' access to 'table_name' and 'record_id'
        """

        permission = self.table_permission()
        if group_id == 0:
            group_id = self.user_group()
        record = self.db((permission.group_id == group_id) &
                         (permission.name == name) &
                         (permission.table_name == str(table_name)) &
                         (permission.record_id == long(record_id)),
                         ignore_common_filters=True
                         ).select(limitby=(0, 1), orderby_on_limitby=False).first()
        if record:
            if hasattr(record, 'is_active') and not record.is_active:
                record.update_record(is_active=True)
            id = record.id
        else:
            id = permission.insert(group_id=group_id, name=name,
                                   table_name=str(table_name),
                                   record_id=long(record_id))
        self.log_event(self.messages['add_permission_log'],
                       dict(permission_id=id, group_id=group_id,
                            name=name, table_name=table_name,
                            record_id=record_id))
        return id

    def del_permission(self,
                       group_id,
                       name='any',
                       table_name='',
                       record_id=0,
                       ):
        """
        Revokes group_id 'name' access to 'table_name' and 'record_id'
        """

        permission = self.table_permission()
        self.log_event(self.messages['del_permission_log'],
                       dict(group_id=group_id, name=name,
                            table_name=table_name, record_id=record_id))
        return self.db(permission.group_id ==
                       group_id)(permission.name ==
                                 name)(permission.table_name ==
                                       str(table_name))(permission.record_id ==
                                                        long(record_id)).delete()

    def has_permission(self,
                       name='any',
                       table_name='',
                       record_id=0,
                       user_id=None,
                       group_id=None,
                       ):
        """
        Checks if user_id or current logged in user is member of a group
        that has 'name' permission on 'table_name' and 'record_id'
        if group_id is passed, it checks whether the group has the permission
        """

        if not group_id and self.settings.everybody_group_id and \
                self.has_permission(name, table_name, record_id, user_id=None,
                                    group_id=self.settings.everybody_group_id):
                return True

        if not user_id and not group_id and self.user:
            user_id = self.user.id
        if user_id:
            membership = self.table_membership()
            rows = self.db(membership.user_id == user_id).select(membership.group_id)
            groups = set([row.group_id for row in rows])
            if group_id and group_id not in groups:
                return False
        else:
            groups = set([group_id])
        permission = self.table_permission()
        rows = self.db(permission.name ==
                       name)(permission.table_name ==
                             str(table_name))(permission.record_id ==
                                              record_id).select(permission.group_id)
        groups_required = set([row.group_id for row in rows])
        if record_id:
            rows = self.db(permission.name ==
                           name)(permission.table_name ==
                                 str(table_name))(permission.record_id ==
                                                  0).select(permission.group_id)
            groups_required = groups_required.union(set([row.group_id for row in rows]))
        if groups.intersection(groups_required):
            r = True
        else:
            r = False
        if user_id:
            self.log_event(self.messages['has_permission_log'],
                           dict(user_id=user_id, name=name,
                                table_name=table_name, record_id=record_id))
        return r

    def is_logged_in(self):
        """
        Checks if the user is logged in and returns True/False.
        If so user is in auth.user as well as in session.auth.user
        """
        if self.user:
            return True
        return False

    def _update_session_user(self, user):
        if global_settings.web2py_runtime_gae:
            user = Row(self.table_user()._filter_fields(user, id=True))
            delattr(user, self.settings.password_field)
        else:
            user = Row(user)
            for key in list(user.keys()):
                value = user[key]
                if callable(value) or key == self.settings.password_field:
                    delattr(user, key)
        current.session.auth = Storage(user=user,
                                       last_visit=current.request.now,
                                       expiration=self.settings.expiration,
                                       hmac_key=web2py_uuid())
        return user

    def login_user(self, user):
        """
        Logins the `user = db.auth_user(id)`
        """
        user = self._update_session_user(user)
        if self.settings.renew_session_onlogin:
            current.session.renew(clear_session=not self.settings.keep_session_onlogin)
        self.user = user
        self.update_groups()

    def login(self, log=DEFAULT, **kwargs):
        """
        Login a user

        Keyword Args:
            username/email/name_of_your_username_field (string) - username
            password/name_of_your_passfield (string) - user's password
            remember_me (boolean) - extend the duration of the login to settings.long_expiration
        """
        settings = self.settings
        session = current.session
        table_user = self.table_user()

        if 'username' in table_user.fields or \
                not settings.login_email_validate:
            userfield_validator = IS_NOT_EMPTY(error_message=self.messages.is_empty)
            if not settings.username_case_sensitive:
                userfield_validator = [IS_LOWER(), userfield_validator]
        else:
            userfield_validator = IS_EMAIL(error_message=self.messages.invalid_email)
            if not settings.email_case_sensitive:
                userfield_validator = [IS_LOWER(), userfield_validator]

        passfield = settings.password_field

        if log is DEFAULT:
            log = self.messages['login_log']

        user = None

        # Setup the default field used for the userfield
        if self.settings.login_userfield:
            userfield = self.settings.login_userfield
        else:
            if 'username' in table_user.fields:
                userfield = 'username'
            else:
                userfield = 'email'

        # Get the userfield from kwargs and validate it
        userfield_value = kwargs.get(userfield)
        if userfield_value is None:
            raise KeyError('%s not found in kwargs' % userfield)

        validated, error = self.__validate(userfield_value, userfield_validator)

        if error:
            return {'errors': {userfield: error}, 'message': self.messages.invalid_login, 'user': None}

        # Get the user for this userfield and check it
        user = table_user(**{userfield: validated})

        if user is None:
            return {'errors': {userfield: self.messages.invalid_user},
                    'message': self.messages.invalid_login, 'user': None}

        if (user.registration_key or '').startswith('pending'):
            return {'errors': None, 'message': self.messages.registration_pending, 'user': None}
        elif user.registration_key in ('disabled', 'blocked'):
            return {'errors': None, 'message': self.messages.login_disabled, 'user': None}
        elif (user.registration_key is not None and user.registration_key.strip()):
            return {'errors': None, 'message': self.messages.registration_verifying, 'user': None}

        # Finally verify the password
        passfield = settings.password_field
        password = table_user[passfield].validate(kwargs.get(passfield, ''))[0]

        if password == user[passfield]:
            self.login_user(user)
            session.auth.expiration = \
                kwargs.get('remember_me', False) and \
                settings.long_expiration or \
                settings.expiration
            session.auth.remember_me = kwargs.get('remember_me', False)
            self.log_event(log, user)
            return {'errors': None, 'message': self.messages.logged_in,
                    'user': {k: user[k] for k in table_user.fields if table_user[k].readable}}
        else:
            self.log_event(self.messages['login_failed_log'], kwargs)
            return {'errors': {passfield: self.messages.invalid_password},
                    'message': self.messages.invalid_login, 'user': None}

    def logout(self, log=DEFAULT, onlogout=DEFAULT, **kwargs):
        """
        Logs out user
        """
        settings = self.settings
        session = current.session

        if onlogout is DEFAULT:
            onlogout = settings.logout_onlogout
        if onlogout:
            onlogout(self.user)
        if log is DEFAULT:
            log = self.messages['logout_log']
        if self.user:
            self.log_event(log, self.user)

        session.auth = None
        self.user = None
        if settings.renew_session_onlogout:
            session.renew(clear_session=not settings.keep_session_onlogout)

        return {'errors': None, 'message': self.messages.logged_out, 'user': None}

    def register(self, log=DEFAULT, **kwargs):
        """
        Register a user.
        """

        table_user = self.table_user()
        settings = self.settings

        if self.is_logged_in():
            raise AssertionError('User trying to register is logged in')

        if log is DEFAULT:
            log = self.messages['register_log']

        if self.settings.login_userfield:
            userfield = self.settings.login_userfield
        elif 'username' in table_user.fields:
            userfield = 'username'
        else:
            userfield = 'email'

        # Ensure the username field is unique.
        unique_validator = IS_NOT_IN_DB(self.db, table_user[userfield])
        userfield_validator = table_user[userfield].requires
        if userfield_validator is None:
            userfield_validator = unique_validator
        elif isinstance(userfield_validator, (list, tuple)):
            if not any([isinstance(validator, IS_NOT_IN_DB) for validator in
                        userfield_validator]):
                if isinstance(userfield_validator, list):
                    userfield_validator.append(unique_validator)
                else:
                    userfield_validator += (unique_validator, )
        elif not isinstance(userfield_validator, IS_NOT_IN_DB):
            userfield_validator = [userfield_validator, unique_validator]
        table_user[userfield].requires = userfield_validator

        passfield = settings.password_field

        try:  # Make sure we have our original minimum length
            table_user[passfield].requires[-1].min_length = settings.password_min_length
        except:
            pass

        key = web2py_uuid()
        if settings.registration_requires_approval:
            key = 'pending-' + key

        table_user.registration_key.default = key

        result = table_user.validate_and_insert(**kwargs)
        if result.errors:
            return {'errors': result.errors.as_dict(), 'message': None, 'user': None}

        user = table_user[result.id]

        message = self.messages.registration_successful

        if settings.create_user_groups:
            d = user.as_dict()
            description = self.messages.group_description % d
            group_id = self.add_group(settings.create_user_groups % d, description)
            self.add_membership(group_id, result.id)

        if self.settings.everybody_group_id:
            self.add_membership(self.settings.everybody_group_id, result)

        if settings.registration_requires_verification:
            d = {k: user[k] for k in table_user.fields if table_user[k].readable}
            d['key'] = key
            if settings.login_after_registration and not settings.registration_requires_approval:
                self.login_user(user)
            return {'errors': None, 'message': None, 'user': d}

        if settings.registration_requires_approval:
            user.update_record(registration_key='pending')
            message = self.messages.registration_pending
        elif settings.login_after_registration:
            user.update_record(registration_key='')
            self.login_user(user)
            message = self.messages.logged_in

        self.log_event(log, user)

        return {'errors': None, 'message': message,
                'user': {k: user[k] for k in table_user.fields if table_user[k].readable}}

    def profile(self, log=DEFAULT, **kwargs):
        """
        Lets the user change his/her profile
        """

        table_user = self.table_user()
        settings = self.settings
        table_user[settings.password_field].writable = False

        if not self.is_logged_in():
            raise AssertionError('User is not logged in')

        if not kwargs:
            user = table_user[self.user.id]
            return {'errors': None, 'message': None,
                    'user': {k: user[k] for k in table_user.fields if table_user[k].readable}}

        result = self.db(table_user.id == self.user.id).validate_and_update(**kwargs)
        user = table_user[self.user.id]

        if result.errors:
            return {'errors': result.errors, 'message': None,
                    'user': {k: user[k] for k in table_user.fields if table_user[k].readable}}

        if log is DEFAULT:
            log = self.messages['profile_log']

        self.log_event(log, user)
        self._update_session_user(user)
        return {'errors': None, 'message': self.messages.profile_updated,
                'user': {k: user[k] for k in table_user.fields if table_user[k].readable}}

    def change_password(self, log=DEFAULT, **kwargs):
        """
        Lets the user change password

        Keyword Args:
            old_password (string) - User's current password
            new_password (string) - User's new password
            new_password2 (string) - Verify the new password
        """
        settings = self.settings
        messages = self.messages

        if not self.is_logged_in():
            raise AssertionError('User is not logged in')

        db = self.db
        table_user = self.table_user()
        s = db(table_user.id == self.user.id)

        request = current.request
        session = current.session
        passfield = settings.password_field

        requires = table_user[passfield].requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        requires = list(filter(lambda t: isinstance(t, CRYPT), requires))
        if requires:
            requires[0] = CRYPT(**requires[0].__dict__) # Copy the existing CRYPT attributes
            requires[0].min_length = 0 # But do not enforce minimum length for the old password

        old_password = kwargs.get('old_password', '')
        new_password = kwargs.get('new_password', '')
        new_password2 = kwargs.get('new_password2', '')

        validator_old = requires
        validator_pass2 = IS_EQUAL_TO(new_password, error_message=messages.mismatched_password)

        old_password, error_old = self.__validate(old_password, validator_old)
        new_password2, error_new2 = self.__validate(new_password2, validator_pass2)

        errors = {}
        if error_old:
            errors['old_password'] = error_old
        if error_new2:
            errors['new_password2'] = error_new2
        if errors:
            return {'errors': errors, 'message': None}

        current_user = s.select(limitby=(0, 1), orderby_on_limitby=False).first()
        if not old_password == current_user[passfield]:
            return {'errors': {'old_password': messages.invalid_password}, 'message': None}
        else:
            d = {passfield: new_password}
            resp = s.validate_and_update(**d)
            if resp.errors:
                return {'errors': {'new_password': resp.errors[passfield]}, 'message': None}
            if log is DEFAULT:
                log = messages['change_password_log']
            self.log_event(log, self.user)
            return {'errors': None, 'message': messages.password_changed}

    def verify_key(self,
                   key=None,
                   ignore_approval=False,
                   log=DEFAULT,
                   ):
        """
        Verify a given registration_key actually exists in the user table.
        Resets the key to empty string '' or 'pending' if
        setttings.registration_requires_approval is true.

        Keyword Args:
            key (string) - User's registration key
        """
        table_user = self.table_user()
        user = table_user(registration_key=key)
        if (user is None) or (key is None):
            return {'errors': {'key': self.messages.invalid_key}, 'message': self.messages.invalid_key}

        if self.settings.registration_requires_approval:
            user.update_record(registration_key='pending')
            result = {'errors': None, 'message': self.messages.registration_pending}
        else:
            user.update_record(registration_key='')
            result = {'errors': None, 'message': self.messages.key_verified}
        # make sure session has same user.registration_key as db record
        if current.session.auth and current.session.auth.user:
            current.session.auth.user.registration_key = user.registration_key
        if log is DEFAULT:
            log = self.messages['verify_log']
        self.log_event(log, user)
        return result
