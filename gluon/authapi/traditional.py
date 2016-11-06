from .base import AuthAPI
from .base import DEFAULT
from gluon import current
from gluon import redirect
from gluon.sqlhtml import SQLFORM
from gluon.validators import IS_NOT_IN_DB, IS_NOT_EMPTY, IS_LOWER, IS_EMAIL, IS_EQUAL_TO, IS_EXPR, CRYPT
from gluon.utils import web2py_uuid
from pydal.objects import Row, Field


def callback(actions, form, tablename=None):
    if actions:
        if tablename and isinstance(actions, dict):
            actions = actions.get(tablename, [])
        if not isinstance(actions, (list, tuple)):
            actions = [actions]
        [action(form) for action in actions]


def replace_id(url, form):
    if url:
        url = url.replace('[id]', str(form.vars.id))
        if url[0] == '/' or url[:4] == 'http':
            return url
    return URL(url)


class Traditional(AuthAPI):

    def login(self,
              next=DEFAULT,
              onvalidation=DEFAULT,
              onaccept=DEFAULT,
              log=DEFAULT,
              ):
        """
        Returns a login form
        """
        settings = self.settings
        request = current.request
        response = current.response
        session = current.session

        # use session for federated login
        snext = self.auth().get_vars_next()

        if snext:
            session._auth_next = snext
        elif session._auth_next:
            snext = session._auth_next
        # pass

        if next is DEFAULT:
            # important for security
            next = settings.login_next
            if callable(next):
                next = next()
            user_next = snext
            if user_next:
                external = user_next.split('://')
                if external[0].lower() in ['http', 'https', 'ftp']:
                    host_next = user_next.split('//', 1)[-1].split('/')[0]
                    if host_next in settings.cas_domains:
                        next = user_next
                else:
                    next = user_next
                    # Avoid asking unnecessary user credentials when user is logged in
                    self.auth().when_is_logged_in_bypass_next_in_url(next=next, session=session)

        # Moved here to avoid unnecessary execution in case of redirection to next in case of logged in user
        table_user = self.auth().table_user()
        if 'username' in table_user.fields or \
                not settings.login_email_validate:
            tmpvalidator = IS_NOT_EMPTY(error_message=self.messages.is_empty)
            if not settings.username_case_sensitive:
                tmpvalidator = [IS_LOWER(), tmpvalidator]
        else:
            tmpvalidator = IS_EMAIL(error_message=self.messages.invalid_email)
            if not settings.email_case_sensitive:
                tmpvalidator = [IS_LOWER(), tmpvalidator]

        passfield = settings.password_field
        try:
            table_user[passfield].requires[-1].min_length = 0
        except:
            pass

        if onvalidation is DEFAULT:
            onvalidation = settings.login_onvalidation
        if onaccept is DEFAULT:
            onaccept = settings.login_onaccept
        if log is DEFAULT:
            log = self.messages['login_log']

        onfail = settings.login_onfail

        user = None  # default

        # Setup the default field used for the form
        multi_login = False
        if self.settings.login_userfield:
            username = self.settings.login_userfield
        else:
            if 'username' in table_user.fields:
                username = 'username'
            else:
                username = 'email'
            if self.settings.multi_login:
                multi_login = True
        old_requires = table_user[username].requires
        table_user[username].requires = tmpvalidator

        # If two-factor authentication is enabled, and the maximum
        # number of tries allowed is used up, reset the session to
        # pre-login state with two-factor auth
        if session.auth_two_factor_enabled and session.auth_two_factor_tries_left < 1:
            # Exceeded maximum allowed tries for this code. Require user to enter
            # username and password again.
            user = None
            accepted_form = False
            self.auth()._reset_two_factor_auth(session)
            # Redirect to the default 'next' page without logging
            # in. If that page requires login, user will be redirected
            # back to the main login form
            redirect(next, client_side=settings.client_side)

        # Before showing the default login form, check whether
        # we are already on the second step of two-step authentication.
        # If we are, then skip this login form and use the form for the
        # second challenge instead.
        # Note to devs: The code inside the if-block is unchanged from the
        # previous version of this file, other than for indentation inside
        # to put it inside the if-block
        if session.auth_two_factor_user is None:

            if settings.remember_me_form:
                extra_fields = [
                    Field('remember_me', 'boolean', default=False,
                          label=self.messages.label_remember_me)]
            else:
                extra_fields = []

            # do we use our own login form, or from a central source?
            if settings.login_form == self.auth():
                form = SQLFORM(table_user,
                               fields=[username, passfield],
                               hidden=dict(_next=next),
                               showid=settings.showid,
                               submit_button=self.messages.login_button,
                               delete_label=self.messages.delete_label,
                               formstyle=settings.formstyle,
                               separator=settings.label_separator,
                               extra_fields=extra_fields,
                               )

                captcha = settings.login_captcha or \
                    (settings.login_captcha is not False and settings.captcha)
                if captcha:
                    addrow(form, captcha.label, captcha, captcha.comment,
                           settings.formstyle, 'captcha__row')
                accepted_form = False

                if form.accepts(request, session if self.auth().csrf_prevention else None,
                                formname='login', dbio=False,
                                onvalidation=onvalidation,
                                hideerror=settings.hideerror):

                    accepted_form = True
                    # check for username in db
                    entered_username = form.vars[username]
                    if multi_login and '@' in entered_username:
                        # if '@' in username check for email, not username
                        user = table_user(email=entered_username)
                    else:
                        user = table_user(**{username: entered_username})
                    if user:
                        # user in db, check if registration pending or disabled
                        temp_user = user
                        if (temp_user.registration_key or '').startswith('pending'):
                            response.flash = self.messages.registration_pending
                            return form
                        elif temp_user.registration_key in ('disabled', 'blocked'):
                            response.flash = self.messages.login_disabled
                            return form
                        elif (temp_user.registration_key is not None and temp_user.registration_key.strip()):
                            response.flash = \
                                self.messages.registration_verifying
                            return form
                        # try alternate logins 1st as these have the
                        # current version of the password
                        user = None
                        for login_method in settings.login_methods:
                            if login_method != self.auth() and \
                                    login_method(request.vars[username],
                                                 request.vars[passfield]):
                                if self not in settings.login_methods:
                                    # do not store password in db
                                    form.vars[passfield] = None
                                user = self.auth().get_or_create_user(
                                    form.vars, settings.update_fields)
                                break
                        if not user:
                            # alternates have failed, maybe because service inaccessible
                            if settings.login_methods[0] == self.auth():
                                # try logging in locally using cached credentials
                                if form.vars.get(passfield, '') == temp_user[passfield]:
                                    # success
                                    user = temp_user
                    else:
                        # user not in db
                        if not settings.alternate_requires_registration:
                            # we're allowed to auto-register users from external systems
                            for login_method in settings.login_methods:
                                if login_method != self.auth() and \
                                        login_method(request.vars[username],
                                                     request.vars[passfield]):
                                    if self not in settings.login_methods:
                                        # do not store password in db
                                        form.vars[passfield] = None
                                    user = self.auth().get_or_create_user(
                                        form.vars, settings.update_fields)
                                    break
                    if not user:
                        self.auth().log_event(self.messages['login_failed_log'],
                                              request.post_vars)
                        # invalid login
                        session.flash = self.messages.invalid_login
                        callback(onfail, None)
                        redirect(
                            self.auth().url(args=request.args, vars=request.get_vars),
                            client_side=settings.client_side)

            else:  # use a central authentication server
                cas = settings.login_form
                cas_user = cas.get_user()

                if cas_user:
                    cas_user[passfield] = None
                    user = self.auth().get_or_create_user(
                        table_user._filter_fields(cas_user),
                        settings.update_fields)
                elif hasattr(cas, 'login_form'):
                    return cas.login_form()
                else:
                    # we need to pass through login again before going on
                    next = self.auth().url(settings.function, args='login')
                    redirect(cas.login_url(next),
                             client_side=settings.client_side)

        # Extra login logic for two-factor authentication
        #################################################
        # If the 'user' variable has a value, this means that the first
        # authentication step was successful (i.e. user provided correct
        # username and password at the first challenge).
        # Check if this user is signed up for two-factor authentication
        # If auth.settings.auth_two_factor_enabled it will enable two factor
        # for all the app. Another way to anble two factor is that the user
        # must be part of a group that is called auth.settings.two_factor_authentication_group
        if user and self.settings.auth_two_factor_enabled == True:
            session.auth_two_factor_enabled = True
        elif user and self.settings.two_factor_authentication_group:
            role = self.settings.two_factor_authentication_group
            session.auth_two_factor_enabled = self.auth().has_membership(user_id=user.id, role=role)
        # challenge
        if session.auth_two_factor_enabled:
            form = SQLFORM.factory(
                Field('authentication_code',
                      label=self.messages.label_two_factor,
                      required=True,
                      comment=self.messages.two_factor_comment),
                hidden=dict(_next=next),
                formstyle=settings.formstyle,
                separator=settings.label_separator
            )
            # accepted_form is used by some default web2py code later in the
            # function that handles running specified functions before redirect
            # Set it to False until the challenge form is accepted.
            accepted_form = False
            # Handle the case when a user has submitted the login/password
            # form successfully, and the password has been validated, but
            # the two-factor form has not been displayed or validated yet.
            if session.auth_two_factor_user is None and user is not None:
                session.auth_two_factor_user = user  # store the validated user and associate with this session
                session.auth_two_factor = random.randint(100000, 999999)
                session.auth_two_factor_tries_left = self.settings.auth_two_factor_tries_left
                # Set the way we generate the code or we send the code. For example using SMS...
                two_factor_methods = self.settings.two_factor_methods

                if two_factor_methods == []:
                    # TODO: Add some error checking to handle cases where email cannot be sent
                    self.settings.mailer.send(
                        to=user.email,
                        subject=self.messages.retrieve_two_factor_code_subject,
                        message=self.messages.retrieve_two_factor_code.format(session.auth_two_factor))
                else:
                    # Check for all method. It is possible to have multiples
                    for two_factor_method in two_factor_methods:
                        try:
                            # By default we use session.auth_two_factor generated before.
                            session.auth_two_factor = two_factor_method(user, session.auth_two_factor)
                        except:
                            pass
                        else:
                            break

            if form.accepts(request, session if self.auth().csrf_prevention else None,
                            formname='login', dbio=False,
                            onvalidation=onvalidation,
                            hideerror=settings.hideerror):
                accepted_form = True

                '''
                The lists is executed after form validation for each of the corresponding action.
                For example, in your model:

                In your models copy and paste:

                #Before define tables, we add some extra field to auth_user
                auth.settings.extra_fields['auth_user'] = [
                    Field('motp_secret', 'password', length=512, default='', label='MOTP Secret'),
                    Field('motp_pin', 'string', length=128, default='', label='MOTP PIN')]

                OFFSET = 60 #Be sure is the same in your OTP Client

                #Set session.auth_two_factor to None. Because the code is generated by external app.
                # This will avoid to use the default setting and send a code by email.
                def _set_two_factor(user, auth_two_factor):
                    return None

                def verify_otp(user, otp):
                import time
                from hashlib import md5
                epoch_time = int(time.time())
                time_start = int(str(epoch_time - OFFSET)[:-1])
                time_end = int(str(epoch_time + OFFSET)[:-1])
                for t in range(time_start - 1, time_end + 1):
                    to_hash = str(t) + user.motp_secret + user.motp_pin
                    hash = md5(to_hash).hexdigest()[:6]
                    if otp == hash:
                    return hash

                auth.settings.auth_two_factor_enabled = True
                auth.messages.two_factor_comment = "Verify your OTP Client for the code."
                auth.settings.two_factor_methods = [lambda user, auth_two_factor: _set_two_factor(user, auth_two_factor)]
                auth.settings.two_factor_onvalidation = [lambda user, otp: verify_otp(user, otp)]

                '''
                if self.settings.two_factor_onvalidation != []:

                    for two_factor_onvalidation in self.settings.two_factor_onvalidation:
                        try:
                            session.auth_two_factor = two_factor_onvalidation(session.auth_two_factor_user, form.vars['authentication_code'])
                        except:
                            pass
                        else:
                            break

                if form.vars['authentication_code'] == str(session.auth_two_factor):
                    # Handle the case when the two-factor form has been successfully validated
                    # and the user was previously stored (the current user should be None because
                    # in this case, the previous username/password login form should not be displayed.
                    # This will allow the code after the 2-factor authentication block to proceed as
                    # normal.
                    if user is None or user == session.auth_two_factor_user:
                        user = session.auth_two_factor_user
                    # For security, because the username stored in the
                    # session somehow does not match the just validated
                    # user. Should not be possible without session stealing
                    # which is hard with SSL.
                    elif user != session.auth_two_factor_user:
                        user = None
                    # Either way, the user and code associated with this session should
                    # be removed. This handles cases where the session login may have
                    # expired but browser window is open, so the old session key and
                    # session usernamem will still exist
                    self.auth()._reset_two_factor_auth(session)
                else:
                    session.auth_two_factor_tries_left -= 1
                    # If the number of retries are higher than auth_two_factor_tries_left
                    # Require user to enter username and password again.
                    if session.auth_two_factor_enabled and session.auth_two_factor_tries_left < 1:
                        # Exceeded maximum allowed tries for this code. Require user to enter
                        # username and password again.
                        user = None
                        accepted_form = False
                        self.auth()._reset_two_factor_auth(session)
                        # Redirect to the default 'next' page without logging
                        # in. If that page requires login, user will be redirected
                        # back to the main login form
                        redirect(next, client_side=settings.client_side)
                    response.flash = self.messages.invalid_two_factor_code.format(session.auth_two_factor_tries_left)
                    return form
            else:
                return form
        # End login logic for two-factor authentication

        # process authenticated users
        if user:
            user = Row(table_user._filter_fields(user, id=True))
            # process authenticated users
            # user wants to be logged in for longer
            self.auth().login_user(user)
            session.auth.expiration = \
                request.post_vars.remember_me and \
                settings.long_expiration or \
                settings.expiration
            session.auth.remember_me = 'remember_me' in request.post_vars
            self.auth().log_event(log, user)
            session.flash = self.messages.logged_in

        # how to continue
        if settings.login_form == self.auth():
            if accepted_form:
                callback(onaccept, form)
                if next == session._auth_next:
                    session._auth_next = None
                next = replace_id(next, form)
                redirect(next, client_side=settings.client_side)

            table_user[username].requires = old_requires
            return form
        elif user:
            callback(onaccept, None)

        if next == session._auth_next:
            del session._auth_next
        redirect(next, client_side=settings.client_side)

    def logout(self, next=DEFAULT, onlogout=DEFAULT, log=DEFAULT):
        """
        Logouts and redirects to login
        """

        # Clear out 2-step authentication information if user logs
        # out. This information is also cleared on successful login.
        self.auth()._reset_two_factor_auth(current.session)

        if next is DEFAULT:
            next = self.auth().get_vars_next() or self.settings.logout_next
        if onlogout is DEFAULT:
            onlogout = self.settings.logout_onlogout
        if onlogout:
            onlogout(self.auth().user)
        if log is DEFAULT:
            log = self.messages['logout_log']
        if self.auth().user:
            self.auth().log_event(log, self.auth().user)
        if self.settings.login_form != self.auth():
            cas = self.settings.login_form
            cas_user = cas.get_user()
            if cas_user:
                next = cas.logout_url(next)

        current.session.auth = None
        self.auth().user = None
        if self.settings.renew_session_onlogout:
            current.session.renew(clear_session=not self.settings.keep_session_onlogout)
        current.session.flash = self.messages.logged_out
        if next is not None:
            redirect(next)

    def register(self,
                 next=DEFAULT,
                 onvalidation=DEFAULT,
                 onaccept=DEFAULT,
                 log=DEFAULT,
                 ):
        """
        Returns a registration form
        """
        request = current.request
        response = current.response
        session = current.session
        if self.auth().is_logged_in():
            redirect(self.settings.logged_url,
                     client_side=self.settings.client_side)
        if next is DEFAULT:
            next = self.auth().get_vars_next() or self.settings.register_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.register_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.register_onaccept
        if log is DEFAULT:
            log = self.messages['register_log']

        table_user = self.auth().table_user()
        if self.settings.login_userfield:
            username = self.settings.login_userfield
        elif 'username' in table_user.fields:
            username = 'username'
        else:
            username = 'email'

        # Ensure the username field is unique.
        unique_validator = IS_NOT_IN_DB(self.auth().db, table_user[username])
        if not table_user[username].requires:
            table_user[username].requires = unique_validator
        elif isinstance(table_user[username].requires, (list, tuple)):
            if not any([isinstance(validator, IS_NOT_IN_DB) for validator in
                        table_user[username].requires]):
                if isinstance(table_user[username].requires, list):
                    table_user[username].requires.append(unique_validator)
                else:
                    table_user[username].requires += (unique_validator, )
        elif not isinstance(table_user[username].requires, IS_NOT_IN_DB):
            table_user[username].requires = [table_user[username].requires,
                                             unique_validator]

        passfield = self.settings.password_field
        formstyle = self.settings.formstyle
        try:  # Make sure we have our original minimum length as other auth forms change it
            table_user[passfield].requires[-1].min_length = self.settings.password_min_length
        except:
            pass

        if self.settings.register_verify_password:
            if self.settings.register_fields is None:
                self.settings.register_fields = [f.name for f in table_user if f.writable]
                k = self.settings.register_fields.index(passfield)
                self.settings.register_fields.insert(k + 1, "password_two")
            extra_fields = [
                Field("password_two", "password",
                      requires=IS_EQUAL_TO(request.post_vars.get(passfield, None),
                                           error_message=self.messages.mismatched_password),
                      label=current.T("Confirm Password"))]
        else:
            extra_fields = []
        form = SQLFORM(table_user,
                       fields=self.settings.register_fields,
                       hidden=dict(_next=next),
                       showid=self.settings.showid,
                       submit_button=self.messages.register_button,
                       delete_label=self.messages.delete_label,
                       formstyle=formstyle,
                       separator=self.settings.label_separator,
                       extra_fields=extra_fields
                       )

        captcha = self.settings.register_captcha or self.settings.captcha
        if captcha:
            addrow(form, captcha.label, captcha,
                   captcha.comment, self.settings.formstyle, 'captcha__row')

        # Add a message if specified
        if self.settings.pre_registration_div:
            addrow(form, '',
                   DIV(_id="pre-reg", *self.settings.pre_registration_div),
                   '', formstyle, '')

        key = web2py_uuid()
        if self.settings.registration_requires_approval:
            key = 'pending-' + key

        table_user.registration_key.default = key
        if form.accepts(request, session if self.auth().csrf_prevention else None,
                        formname='register',
                        onvalidation=onvalidation,
                        hideerror=self.settings.hideerror):
            description = self.messages.group_description % form.vars
            if self.settings.create_user_groups:
                group_id = self.auth().add_group(self.settings.create_user_groups % form.vars, description)
                self.auth().add_membership(group_id, form.vars.id)
            if self.settings.everybody_group_id:
                self.auth().add_membership(self.settings.everybody_group_id, form.vars.id)
            if self.settings.registration_requires_verification:
                link = self.auth().url(
                    self.settings.function, args=('verify_email', key), scheme=True)
                d = dict(form.vars)
                d.update(dict(key=key, link=link, username=form.vars[username]))
                if not (self.settings.mailer and self.settings.mailer.send(
                        to=form.vars.email,
                        subject=self.messages.verify_email_subject,
                        message=self.messages.verify_email % d)):
                    self.auth().db.rollback()
                    response.flash = self.messages.unable_send_email
                    return form
                session.flash = self.messages.email_sent
            if self.settings.registration_requires_approval and \
               not self.settings.registration_requires_verification:
                table_user[form.vars.id] = dict(registration_key='pending')
                session.flash = self.messages.registration_pending
            elif (not self.settings.registration_requires_verification or self.settings.login_after_registration):
                if not self.settings.registration_requires_verification:
                    table_user[form.vars.id] = dict(registration_key='')
                session.flash = self.messages.registration_successful
                user = table_user(**{username: form.vars[username]})
                self.auth().login_user(user)
                session.flash = self.messages.logged_in
            self.auth().log_event(log, form.vars)
            callback(onaccept, form)
            if not next:
                next = self.auth().url(args=request.args)
            else:
                next = replace_id(next, form)
            redirect(next, client_side=self.settings.client_side)

        return form

    def profile(self,
                next=DEFAULT,
                onvalidation=DEFAULT,
                onaccept=DEFAULT,
                log=DEFAULT,
                ):
        """
        Returns a form that lets the user change his/her profile
        """

        table_user = self.auth().table_user()
        if not self.auth().is_logged_in():
            redirect(self.settings.login_url,
                     client_side=self.settings.client_side)
        passfield = self.settings.password_field
        table_user[passfield].writable = False
        request = current.request
        session = current.session
        if next is DEFAULT:
            next = self.auth().get_vars_next() or self.settings.profile_next
        if onvalidation is DEFAULT:
            onvalidation = self.settings.profile_onvalidation
        if onaccept is DEFAULT:
            onaccept = self.settings.profile_onaccept
        if log is DEFAULT:
            log = self.messages['profile_log']
        form = SQLFORM(
            table_user,
            self.auth().user.id,
            fields=self.settings.profile_fields,
            hidden=dict(_next=next),
            showid=self.settings.showid,
            submit_button=self.messages.profile_save_button,
            delete_label=self.messages.delete_label,
            upload=self.settings.download_url,
            formstyle=self.settings.formstyle,
            separator=self.settings.label_separator,
            deletable=self.settings.allow_delete_accounts,
        )
        if form.accepts(request, session,
                        formname='profile',
                        onvalidation=onvalidation,
                        hideerror=self.settings.hideerror):
            self.auth().user.update(table_user._filter_fields(form.vars))
            session.flash = self.messages.profile_updated
            self.auth().log_event(log, self.auth().user)
            callback(onaccept, form)
            if form.deleted:
                return self.logout()
            if not next:
                next = self.auth().url(args=request.args)
            else:
                next = replace_id(next, form)
            redirect(next, client_side=self.settings.client_side)
        return form

    def change_password(self,
                        next=DEFAULT,
                        onvalidation=DEFAULT,
                        onaccept=DEFAULT,
                        log=DEFAULT,
                        ):
        """
        Returns a form that lets the user change password
        """
        settings = self.settings
        messages = self.messages

        if not self.auth().is_logged_in():
            redirect(settings.login_url,
                     client_side=settings.client_side)
        db = self.auth().db
        table_user = self.auth().table_user()
        s = db(table_user.id == self.auth().user.id)

        request = current.request
        session = current.session

        if next is DEFAULT:
            next = self.auth().get_vars_next() or settings.change_password_next
        if onvalidation is DEFAULT:
            onvalidation = settings.change_password_onvalidation
        if onaccept is DEFAULT:
            onaccept = settings.change_password_onaccept
        if log is DEFAULT:
            log = messages['change_password_log']
        passfield = settings.password_field
        requires = table_user[passfield].requires
        if not isinstance(requires, (list, tuple)):
            requires = [requires]
        requires = list(filter(lambda t: isinstance(t, CRYPT), requires))
        if requires:
            requires[0].min_length = 0
        form = SQLFORM.factory(
            Field('old_password', 'password', requires=requires,
                  label=messages.old_password),
            Field('new_password', 'password',
                  label=messages.new_password,
                  requires=table_user[passfield].requires),
            Field('new_password2', 'password',
                  label=messages.verify_password,
                  requires=[IS_EXPR('value==%s' % repr(request.vars.new_password),
                                    messages.mismatched_password)]),
            submit_button=messages.password_change_button,
            hidden=dict(_next=next),
            formstyle=settings.formstyle,
            separator=settings.label_separator
        )
        if form.accepts(request, session,
                        formname='change_password',
                        onvalidation=onvalidation,
                        hideerror=settings.hideerror):

            current_user = s.select(limitby=(0, 1), orderby_on_limitby=False).first()
            if not form.vars['old_password'] == current_user[passfield]:
                form.errors['old_password'] = messages.invalid_password
            else:
                d = {passfield: str(form.vars.new_password)}
                s.update(**d)
                session.flash = messages.password_changed
                self.auth().log_event(log, self.auth().user)
                callback(onaccept, form)
                if not next:
                    next = self.auth().url(args=request.args)
                else:
                    next = replace_id(next, form)
                redirect(next, client_side=settings.client_side)
        return form
