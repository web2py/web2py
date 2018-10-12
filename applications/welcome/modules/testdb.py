# -*- coding: utf-8 -*-
##############################################################################
# Project:     Bancal - Gestión de almacén para los Bancos de Alimentos
# Language:    Python 2.7
# Date:        15-Ago-2013.
# Ver.:        20-Jul-2017.
# Copyright:   2013-2014 - José L. Redrejo Rodríguez  <jredrejo @nospam@ itais.net>
#
# * Dual licensed under the MIT and GPL licenses.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""Module to create a test db.
It only makes sense if used via py.test, from the web2py folder, i.e.
py.test applications/bancal/tests/

"""
from gluon import current


def create_users():
    from gluon.validators import CRYPT
    from gluon.tools import Auth
    db = current.db
    auth = Auth(db)

    my_crypt = CRYPT(key=auth.settings.hmac_key)
    crypted_passwd = my_crypt('password')[0]
    db.commit()
    db.auth_user.insert(email='admin@admin.com', first_name='Administrator', password=crypted_passwd)
    auth.add_group('admins', 'Application Administrators')
    auth.add_membership(1, 1)
    auth.add_permission(1, 'admins', db.auth_user)

    db.commit()


def cleanup_db():
    db = current.db
    db.rollback()
    for tab in db.tables:
        try:
            db[tab].truncate()
        except:
            pass  # the table does not exist yet
    db.commit()


def fill_tables(db):
    current.db = db
    cleanup_db()
    create_users()
    current.db.commit()