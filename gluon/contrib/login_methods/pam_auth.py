from gluon.contrib.pam import authenticate

def pam_auth():
    """
    to use pam_login:
    from gluon.contrib.login_methods.pam_auth import pam_auth
    auth.settings.login_methods.append(pam_auth())
    """

    def pam_auth_aux(username, password):
        return authenticate(username, password)

    return pam_auth_aux

