import sys
import logging
try:
    import ldap
    import ldap.filter
    ldap.set_option( ldap.OPT_REFERRALS, 0 )
except Exception, e:
    logging.error( 'missing ldap, try "easy_install python-ldap"' )
    raise e

def ldap_auth( server = 'ldap', port = None,
            base_dn = 'ou=users,dc=domain,dc=com',
            mode = 'uid', secure = False, cert_path = None,
            bind_dn = None, bind_pw = None, filterstr = 'objectClass=*',
            allowed_groups = None,
            manage_groups = False,
            db = None,
            group_dn = 'ou=groups,dc=domain,dc=com',
            group_name_attrib = 'cn',
            group_member_attrib = 'memberUid',
            group_filterstr = 'objectClass=*' ):
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
    
    If you need group control from ldap to web2py app's database feel free to set:

        auth.settings.login_methods.append(ldap_auth(...as usual...,
            manage_groups = True,
            db = db,
            group_dn = 'ou=Groups,dc=domain,dc=com',
            group_name_attrib = 'cn',
            group_member_attrib = 'memberUid',
            group_filterstr = 'objectClass=*'
            ))
        
        Where:
        manage_group - let web2py handle the groups from ldap
        db - is the database object (need to have auth_user, auth_group, auth_membership)
        group_dn - the ldap branch of the groups
        group_name_attrib - the attribute where the group name is stored
        group_member_attrib - the attibute containing the group members name
        group_filterstr - as the filterstr but for group select
    
    You can restrict login access to specific groups if you specify:
    
        auth.settings.login_methods.append(ldap_auth(...as usual...,
            allowed_groups = [...],
            group_dn = 'ou=Groups,dc=domain,dc=com',
            group_name_attrib = 'cn',
            group_member_attrib = 'memberUid',
            group_filterstr = 'objectClass=*'
            ))

        Where:
        allowed_groups - a list with allowed ldap group names
        group_dn - the ldap branch of the groups
        group_name_attrib - the attribute where the group name is stored
        group_member_attrib - the attibute containing the group members name
        group_filterstr - as the filterstr but for group select
    """

    def ldap_auth_aux( username,
                      password,
                      ldap_server = server,
                      ldap_port = port,
                      ldap_basedn = base_dn,
                      ldap_mode = mode,
                      ldap_binddn = bind_dn,
                      ldap_bindpw = bind_pw,
                      secure = secure,
                      cert_path = cert_path,
                      filterstr = filterstr,
                      manage_groups = manage_groups,
                      allowed_groups = allowed_groups ):
        try:
            con = init_ldap()
            if allowed_groups:
                if not is_user_in_allowed_groups( username ):
                    return False
            if ldap_mode == 'ad':
                # Microsoft Active Directory
                if '@' not in username:
                    domain = []
                    for x in ldap_basedn.split( ',' ):
                        if "DC=" in x.upper():
                            domain.append( x.split( '=' )[-1] )
                    username = "%s@%s" % ( username, '.'.join( domain ) )
                username_bare = username.split( "@" )[0]
                con.set_option( ldap.OPT_PROTOCOL_VERSION, 3 )
                # In cases where ForestDnsZones and DomainDnsZones are found, 
                # result will look like the following: 
                # ['ldap://ForestDnsZones.domain.com/DC=ForestDnsZones,DC=domain,DC=com'] 
                if ldap_binddn:
                    # need to search directory with an admin account 1st
                    con.simple_bind_s( ldap_binddn, ldap_bindpw )
                else:
                    # credentials should be in the form of username@domain.tld
                    con.simple_bind_s( username, password )
                # this will throw an index error if the account is not found
                # in the ldap_basedn
                result = con.search_ext_s( 
                    ldap_basedn, ldap.SCOPE_SUBTREE,
                    "(&(sAMAccountName=%s)(%s))" % ( ldap.filter.escape_filter_chars( username_bare ), filterstr ), ["sAMAccountName"] )[0][1]
                if not isinstance( result, dict ):
                    # result should be a dict in the form {'sAMAccountName': [username_bare]} 
                    return False
                if ldap_binddn:
                    # We know the user exists & is in the correct OU
                    # so now we just check the password
                    con.simple_bind_s( username, password )

            if ldap_mode == 'domino':
                # Notes Domino
                if "@" in username:
                    username = username.split( "@" )[0]
                con.simple_bind_s( username, password )

            if ldap_mode == 'cn':
                # OpenLDAP (CN)
                dn = "cn=" + username + "," + ldap_basedn
                con.simple_bind_s( dn, password )

            if ldap_mode == 'uid':
                # OpenLDAP (UID)
                dn = "uid=" + username + "," + ldap_basedn
                con.simple_bind_s( dn, password )

            if ldap_mode == 'company':
                # no DNs or password needed to search directory
                dn = ""
                pw = ""
                # bind anonymously
                con.simple_bind_s( dn, pw )
                # search by e-mail address
                filter = '(&(mail=' + ldap.filter.escape_filter_chars( username ) + \
                         ')(' + filterstr + '))'
                # find the uid
                attrs = ['uid']
                # perform the actual search
                company_search_result = con.search_s( ldap_basedn,
                                                   ldap.SCOPE_SUBTREE,
                                                   filter, attrs )
                dn = company_search_result[0][0]
                # perform the real authentication test
                con.simple_bind_s( dn, password )

            if ldap_mode == 'uid_r':
                # OpenLDAP (UID) with subtree search and multiple DNs
                if type( ldap_basedn ) == type( [] ):
                    basedns = ldap_basedn
                else:
                    basedns = [ldap_basedn]
                filter = '(&(uid=%s)(%s))' % ( ldap.filter.escape_filter_chars( username ), filterstr )
                for basedn in basedns:
                    try:
                        result = con.search_s( basedn, ldap.SCOPE_SUBTREE, filter )
                        if result:
                            user_dn = result[0][0]
                            # Check the password
                            con.simple_bind_s( user_dn, password )
                            con.unbind()
                            if manage_groups:
                                do_manage_groups( username )
                            return True
                    except ldap.LDAPError, detail:
                        ( exc_type, exc_value ) = sys.exc_info()[:2]
                        sys.stderr.write( "ldap_auth: searching %s for %s resulted in %s: %s\n" %
                                         ( basedn, filter, exc_type, exc_value ) )
                return False

            con.unbind()
            if manage_groups:
                do_manage_groups( username )

            return True
        except ldap.LDAPError, e:
            return False
        except IndexError, ex: # for AD membership test
            return False

    def is_user_in_allowed_groups( username,
                                  allowed_groups = allowed_groups
                                  ):
        '''
            Figure out if the username is a member of an allowed group in ldap or not
        '''
        #
        # Get all group name where the user is in actually in ldap
        # #########################################################
        ldap_groups_of_the_user = get_user_groups_from_ldap( username )

        # search for allowed group names
        if type( allowed_groups ) != type( list() ):
            allowed_groups = [allowed_groups]
        for group in allowed_groups:
            if ldap_groups_of_the_user.count( group ) > 0:
                # Match
                return True
        # No match
        return False

    def do_manage_groups( username,
                      db = db,
                      ):
        '''
            Manage user groups
            
            Get all user's group from ldap and refresh the already stored
            ones in web2py's application database or create new groups
            according to ldap.
        '''
        #
        # Get all group name where the user is in actually in ldap
        # #########################################################
        ldap_groups_of_the_user = get_user_groups_from_ldap( username )

        #
        # Get all group name where the user is in actually in local db
        # #############################################################
        try:
            db_user_id = db( db.auth_user.username == username ).select( db.auth_user.id ).first().id
        except:
            db_user_id = db( db.auth_user.email == username ).select( db.auth_user.id ).first().id
        if not db_user_id:
            logging.error( 'There is no username or email for %s!' % username )
            raise
        db_group_search = db( ( db.auth_membership.user_id == db_user_id ) & \
                            ( db.auth_user.id == db.auth_membership.user_id ) & \
                             ( db.auth_group.id == db.auth_membership.group_id ) )
        db_groups_of_the_user = list()
        db_group_id = dict()

        if db_group_search.count() > 0:
            for group in db_group_search.select( db.auth_group.id, db.auth_group.role, distinct = True ):
                db_group_id[group.role] = group.id
                db_groups_of_the_user.append( group.role )
        logging.debug( 'db groups of user %s: %s' % ( username, str( db_groups_of_the_user ) ) )

        #
        # Delete user membership from groups where user is not anymore
        # #############################################################
        for group_to_del in db_groups_of_the_user:
            if ldap_groups_of_the_user.count( group_to_del ) == 0:
                db( ( db.auth_membership.user_id == db_user_id ) & \
                   ( db.auth_membership.group_id == db_group_id[group_to_del] ) ).delete()

        #
        # Create user membership in groups where user is not in already
        # ##############################################################
        for group_to_add in ldap_groups_of_the_user:
            if db_groups_of_the_user.count( group_to_add ) == 0:
                if db( db.auth_group.role == group_to_add ).count() == 0:
                    gid = db.auth_group.insert( role = group_to_add,
                                         description = 'Generated from LDAP' )
                else:
                    gid = db( db.auth_group.role == group_to_add ).select( db.auth_group.id ).first().id
                db.auth_membership.insert( user_id = db_user_id,
                                          group_id = gid )

    def init_ldap( 
                      ldap_server = server,
                      ldap_port = port,
                      ldap_basedn = base_dn,
                      ldap_mode = mode,
                      secure = secure,
                      cert_path = cert_path,
                ):
        '''
            Inicialize ldap connection
        '''
        if secure:
            if not ldap_port:
                ldap_port = 636
            con = ldap.initialize( 
                "ldaps://" + ldap_server + ":" + str( ldap_port ) )
            if cert_path:
                con.set_option( ldap.OPT_X_TLS_CACERTDIR, cert_path )
        else:
            if not ldap_port:
                ldap_port = 389
            con = ldap.initialize( 
                "ldap://" + ldap_server + ":" + str( ldap_port ) )
        return con

    def get_user_groups_from_ldap( username,
                      ldap_binddn = bind_dn,
                      ldap_bindpw = bind_pw,
                      group_dn = group_dn,
                      group_name_attrib = group_name_attrib,
                      group_member_attrib = group_member_attrib,
                      group_filterstr = group_filterstr,
                      ):
        '''
            Get all group names from ldap where the user is in
        '''
        #
        # Get all group name where the user is in actually in ldap
        # #########################################################
        # Inicialize ldap
        con = init_ldap()
        if ldap_binddn:
            # need to search directory with an bind_dn account 1st
            con.simple_bind_s( ldap_binddn, ldap_bindpw )
        else:
            # bind as anonymous
            con.simple_bind_s( '', '' )

        # search for groups where user is in
        filter = '(&(%s=%s)(%s))' % ( ldap.filter.escape_filter_chars( group_member_attrib ),
                                    ldap.filter.escape_filter_chars( username ),
                                     group_filterstr )
        group_search_result = con.search_s( group_dn,
                                                   ldap.SCOPE_SUBTREE,
                                                   filter, [group_name_attrib] )
        ldap_groups_of_the_user = list()
        for group_row in group_search_result:
            group = group_row[1]
            ldap_groups_of_the_user.extend( group[group_name_attrib] )

        con.unbind()
        return list( ldap_groups_of_the_user )


    if filterstr[0] == '(' and filterstr[-1] == ')': # rfc4515 syntax
        filterstr = filterstr[1:-1] # parens added again where used
    return ldap_auth_aux

