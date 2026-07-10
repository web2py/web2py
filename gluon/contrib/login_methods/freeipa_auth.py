import logging
import sys

try:
    import ldap
except Exception as detail:
    logging.error('missing ldap, try "pip install python-ldap"')
    raise detail


def freeipa_auth(server, basedn, group, self_signed_certificate=False):
    """
    custom module for freeIPA auth in web2py
    server: freeipa ip
    base_dn: root of ldap tree containing user & groups
    group: group authing user has to be a member of
    self_signed_certificate: accept an untrusted (e.g. self-signed) server
        certificate on the ldaps connection. Defaults to False so the server
        certificate is verified; only set it True for a server whose
        certificate cannot be validated (same opt-in as ldap_auth).

    """
    logger = logging.getLogger("web2py.auth.freeipa_auth")

    def freeipa_auth_aux(username, password):
        if password == "" or username == "":
            logger.warning("blank username / password not allowed")
            return False

        bind_user_base = "uid=" + username + ",cn=users," + basedn
        ldap_filter = "memberof=cn=" + group + ",cn=groups," + basedn

        session = ldap.initialize("ldaps://" + server + ":636")
        if self_signed_certificate:
            session.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
            session.set_option(ldap.OPT_X_TLS_NEWCTX, 0)
        try:
            session.bind_s(bind_user_base, password)
        except ldap.LDAPError:
            import traceback

            logger.warning("[%s] Error in ldap bind" % str(username))
            logger.debug(traceback.format_exc())
            return False

        try:
            result = session.search_s(
                bind_user_base, ldap.SCOPE_SUBTREE, ldap_filter, ["member"]
            )
            session.unbind()
        except ldap.LDAPError as detail:
            logger.warning(
                "ldap_auth: searc %s for %s resulted in %s: %s\n"
                % (bind_user_base, ldap_filter, exc_type, exc_value)
            )

        try:
            if result == list():
                return False
            return True
        except:
            return False

    return freeipa_auth_aux
