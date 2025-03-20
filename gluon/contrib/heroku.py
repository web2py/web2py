"""
Usage: in web2py models/db.py

from gluon.contrib.heroku import get_db
db = get_db()

"""

import os

from pydal.adapters import PostgrePsyco, adapters
from pydal.helpers.classes import DatabaseStoredFile

from gluon import *


@adapters.register_for("postgres")
class HerokuPostgresAdapter(DatabaseStoredFile, PostgrePsyco):
    uploads_in_blob = True


def get_db(name=None, pool_size=10):
    if not name:
        names = [
            n for n in os.environ.keys() if n[:18] + n[-4:] == "HEROKU_POSTGRESQL__URL"
        ]
        if names:
            name = names[0]
    if name:
        db = DAL(os.environ[name], pool_size=pool_size)
        current.session.connect(current.request, current.response, db=db)
    else:
        db = DAL("sqlite://heroku.test.sqlite")
    return db
