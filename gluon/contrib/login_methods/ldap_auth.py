import sys
import logging
try:
    import ldap
    ldap.set_option(ldap.OPT_REFERRALS, 0)
except Exception, e:
    logging.error('missing ldap, try "easy_install python-ldap"')
    raise e


def ldap_auth(server='ldap', port=None,
            base_dn='ou=users,dc=domain,dc=com',
            mode='uid', secure=False, cert_path=None, bind_dn=None, bind_pw=None, filterstr='objectClass=*'):
    """
    to use ldap login with MS Active Directory::

        from gluon.contrib.login_methods.ldap_auth import ldap_auth
        auth.settings.login_methods.append(ldap_auth(
            mode='ad', server='my.domain.controller',
            base_dn='ou=Users,dc=domain,dc=com'))

    to use ldap login with Notes Domino::

        auth.settings.login_methods.append(ldap_auth(
            mode='domino',server='my.domino.server'))

    to use ldap login with OpenLDAP::

        auth.settings.login_methods.append(ldap_auth(
            server='my.ldap.server', base_dn='ou=Users,dc=domain,dc=com'))

    to use ldap login with OpenLDAP and subtree search and (optionally) multiple DNs:

        auth.settings.login_methods.append(ldap_auth(
            mode='uid_r', server='my.ldap.server',
            base_dn=['ou=Users,dc=domain,dc=com','ou=Staff,dc=domain,dc=com']))

    or (if using CN)::

        auth.settings.login_methods.append(ldap_auth(
            mode='cn', server='my.ldap.server',
            base_dn='ou=Users,dc=domain,dc=com'))

    If using secure ldaps:// pass secure=True and cert_path="..."

    If you need to bind to the directory with an admin account in order to search it then specify bind_dn & bind_pw to use for this.
    - currently only implemented for Active Directory

    If you need to restrict the set of allowed users (e.g. to members of a department) then specify
    a rfc4515 search filter string.
    - currently only implemented for mode in ['ad', 'company', 'uid_r']
    """

    def ldap_auth_aux(username,
                      password,
                      ldap_server=server,
                      ldap_port=port,
                      ldap_basedn=base_dn,
                      ldap_mode=mode,
                      ldap_binddn=bind_dn,
                      ldap_bindpw=bind_pw,
                      secure=secure,
                      cert_path=cert_path,
                      filterstr=filterstr):
        try:
            if secure:
                if not ldap_port:
                    ldap_port = 636
                con = ldap.initialize(
                    "ldaps://" + ldap_server + ":" + str(ldap_port))
                if cert_path:
                    con.set_option(ldap.OPT_X_TLS_CACERTDIR, cert_path)
            else:
                if not ldap_port:
                    ldap_port = 389
                con = ldap.initialize(
                    "ldap://" + ldap_server + ":" + str(ldap_port))

            if ldap_mode == 'ad':
                # Microsoft Active Directory
                if '@' not in username:
                    domain = []
                    for x in ldap_basedn.split(','):
                        if "DC=" in x.upper():
                            domain.append(x.split('=')[-1])
                    username = "%s@%s" % (username, '.'.join(domain))
                username_bare = username.split("@")[0]
                con.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
                # In cases where ForestDnsZones and DomainDnsZones are found, 
                # result will look like the following: 
                # ['ldap://ForestDnsZones.domain.com/DC=ForestDnsZones,DC=domain,DC=com'] 
                if not isinstance(result, dict): 
                    # result should be a dict in the form {'sAMAccountName': [username_bare]} 
                    return False 
                if ldap_binddn:
                    # need to search directory with an admin account 1st
                    con.simple_bind_s(ldap_binddn, ldap_bindpw)
                else:
                    # credentials should be in the form of username@domain.tld
                    con.simple_bind_s(username, password)
                # this will throw an index error if the account is not found
                # in the ldap_basedn
                result = con.search_ext_s(
                    ldap_basedn, ldap.SCOPE_SUBTREE,
                    "(&(sAMAccountName=%s)(%s))" % (username_bare, filterstr), ["sAMAccountName"])[0][1]
                if ldap_binddn:
                    # We know the user exists & is in the correct OU
                    # so now we just check the password
                    con.simple_bind_s(username, password)

            if ldap_mode == 'domino':
                # Notes Domino
                if "@" in username:
                    username = username.split("@")[0]
                con.simple_bind_s(username, password)

            if ldap_mode == 'cn':
                # OpenLDAP (CN)
                dn = "cn=" + username + "," + ldap_basedn
                con.simple_bind_s(dn, password)

            if ldap_mode == 'uid':
                # OpenLDAP (UID)
                dn = "uid=" + username + "," + ldap_basedn
                con.simple_bind_s(dn, password)

            if ldap_mode == 'company':
                # no DNs or password needed to search directory
                dn = ""
                pw = ""
                # bind anonymously
                con.simple_bind_s(dn, pw)
                # search by e-mail address
                filter = '(&(mail=' + username + ')(' + filterstr + '))'
                # find the uid
                attrs = ['uid']
                # perform the actual search
                company_search_result=con.search_s(ldap_basedn,
                                                   ldap.SCOPE_SUBTREE,
                                                   filter, attrs)
                dn = company_search_result[0][0]
                # perform the real authentication test
                con.simple_bind_s(dn, password)

            if ldap_mode == 'uid_r':
                # OpenLDAP (UID) with subtree search and multiple DNs
                if type(ldap_basedn) == type([]):
                    basedns = ldap_basedn
                else:
                    basedns = [ldap_basedn]
                filter = '(&(uid=%s)(%s))' % (username, filterstr)
                for basedn in basedns:
                    try:
                        result = con.search_s(basedn, ldap.SCOPE_SUBTREE, filter)
                        if result:
                            user_dn = result[0][0]
                            # Check the password
                            con.simple_bind_s(user_dn, password)
                            con.unbind()
                            return True
                    except ldap.LDAPError, detail:
                        (exc_type, exc_value) = sys.exc_info()[:2]
                        sys.stderr.write("ldap_auth: searching %s for %s resulted in %s: %s\n" %
                                         (basedn, filter, exc_type, exc_value))
                return False

            con.unbind()
            return True
        except ldap.LDAPError, e:
            return False
        except IndexError, ex: # for AD membership test
            return False

    if filterstr[0] == '(' and filterstr[-1] == ')': # rfc4515 syntax
        filterstr = filterstr[1:-1] # parens added again where used
    return ldap_auth_aux

