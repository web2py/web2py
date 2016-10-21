from .base import AuthAPI
from .base import DEFAULT
from gluon import current
from gluon.utils import web2py_uuid
from gluon.validators import IS_NOT_IN_DB, IS_NOT_EMPTY, IS_LOWER, IS_EMAIL


class DIDO(AuthAPI):
    """
    Dict In -> Dict Out

    NOTES: * It does not support all the callbacks Traditional Auth does yet.
             Some of the callbacks will not be supported.
             Check the method signatures to find out which ones are supported.
           * register_fields and profile_fields settings are ignored for now.

    WARNING: No builtin CSRF protection whatsoever.
    """

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
        table_user = self.auth().table_user()

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

        validated, error = userfield_validator(userfield_value)

        if error:
            return {'errors': {userfield: error}, 'message': self.messages.invalid_login, 'user': None}

        # Get the user for this userfield and check it
        user = table_user(**{userfield: userfield_value})

        if user is None:
            return {'errors': {userfield: self.messages.invalid_user}, 'message': self.messages.invalid_login, 'user': None}

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
            self.auth().login_user(user)
            session.auth.expiration = \
                kwargs.get('remember_me', False) and \
                settings.long_expiration or \
                settings.expiration
            session.auth.remember_me = kwargs.get('remember_me', False)
            self.auth().log_event(log, user)
            return {'errors': None, 'message': self.messages.logged_in, 'user': {k: user[k] for k in user.as_dict() if table_user[k].readable}}
        else:
            self.auth().log_event(self.messages['login_failed_log'], kwargs)
            return {'errors': {passfield: self.settings.invalid_password}, 'message': self.messages.invalid_login, 'user': None}

    def logout(self, log=DEFAULT, onlogout=DEFAULT, **kwargs):
        """
        Logs out user
        """
        settings = self.settings
        session = current.session

        if onlogout is DEFAULT:
            onlogout = settings.logout_onlogout
        if onlogout:
            onlogout(self.auth().user)
        if log is DEFAULT:
            log = self.messages['logout_log']
        if self.auth().user:
            self.auth().log_event(log, self.auth().user)

        session.auth = None
        self.auth().user = None
        if settings.renew_session_onlogout:
            session.renew(clear_session=not settings.keep_session_onlogout)

        return {'errors': None, 'message': self.messages.logged_out, 'user': None}

    def register(self, log=DEFAULT, **kwargs):
        """
        Register a user.
        """

        table_user = self.auth().table_user()
        settings = self.settings

        if self.auth().is_logged_in():
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
        unique_validator = IS_NOT_IN_DB(self.auth().db, table_user[userfield])
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
        formstyle = self.settings.formstyle
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

        message = settings.registration_successful

        if settings.create_user_groups:
            d = user.as_dict()
            description = self.messages.group_description % d
            group_id = self.auth().add_group(settings.create_user_groups % d, description)
            self.auth().add_membership(group_id, result.id)

        if self.settings.everybody_group_id:
            self.auth().add_membership(self.settings.everybody_group_id, result)

        if settings.registration_requires_verification:
            link = self.auth().url(settings.function, args=('verify_email', key), scheme=True)
            d = user.as_dict()
            d.update(dict(key=key, link=link, username=kwargs[userfield]))
            if not (settings.mailer and settings.mailer.send(
                    to=kwargs['email'],
                    subject=self.messages.verify_email_subject,
                    message=self.messages.verify_email % d)):
                self.auth().db.rollback()
                return {'errors': None, 'message': self.messages.unable_send_email, 'user': None}
            message = self.messages.email_sent

        if settings.registration_requires_approval and not settings.registration_requires_verification:
            user.update_record(registration_key='pending')
            message = self.messages.registration_pending
        elif (not settings.registration_requires_verification or settings.login_after_registration):
            if not settings.registration_requires_verification:
                user.update_record(registration_key='')
            self.auth().login_user(user)
            message = self.messages.logged_in

        self.auth().log_event(log, user)

        return {'errors': None, 'message': message, 'user': {k: user[k] for k in user.as_dict() if table_user[k].readable}}

    def profile(self, log=DEFAULT, **kwargs):
        """
        Lets the user change his/her profile

        Keyword Args:
            delete_this_record (boolean) - delete the record
        """

        table_user = self.auth().table_user()
        settings = self.settings
        table_user[settings.password_field].writable = False

        if not self.auth().is_logged_in():
            raise AssertionError('User is not logged in')

        if not kwargs:
            user = table_user[self.auth().user.id]
            return {'errors': None, 'message': None, 'user': {k: user[k] for k in user.as_dict() if table_user[k].readable}}

        result = self.auth().db(table_user.id == self.auth().user.id).validate_and_update(**kwargs)
        user = table_user[self.auth().user.id]

        if result.errors:
            return {'errors': result.errors, 'message': None, 'user': {k: user[k] for k in user.as_dict() if table_user[k].readable}}
        
        if log is DEFAULT:
            log = self.messages['profile_log']
        self.auth().log_event(log, user)
        self.auth().user.update(**kwargs)
        return {'errors': None, 'message': self.messages.profile_updated, 'user': {k: user[k] for k in user.as_dict() if table_user[k].readable}}
