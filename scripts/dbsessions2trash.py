#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from time import mktime
from time import sleep
from time import time

DB_URI = 'sqlite://sessions.sqlite'
EXPIRATION_MINUTES = 60
SLEEP_MINUTES = 5

while 1:  # Infinite loop
    now = time()  # get current Unix timestamp

    for row in db().select(db.web2py_session_welcome.ALL):
        t = row.modified_datetime
        # Convert to a Unix timestamp
        t = mktime(t.timetuple()) + 1e-6 * t.microsecond
        if now - t > EXPIRATION_MINUTES * 60:
            del db.web2py_session_welcome[row.id]

    db.commit()  # Write changes to database

    sleep(SLEEP_MINUTES * 60)
