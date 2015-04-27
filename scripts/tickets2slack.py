#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Post error tickets to slack on a 5 minute schedule.
#
# Proper use depends on having created a web-hook through Slack, and having set
# that value in your app's model as the value of global_settings.slack_hook.
# Details on creating web-hooks can be found at https://slack.com/integrations
#
# requires the Requests module for posting to slack, other requirements are
# standard or provided by web2py
#
# Usage (on Unices), replace myapp with the name of your application and run:
#   nohup python web2py.py -S myapp -M -R scripts/tickets2slack.py &

import sys
import os
import time
import pickle
import json

try:
    import requests
except ImportError as e:
    print "missing module 'Requests', aborting."
    sys.exit(1)

from gluon import URL
from gluon.utils import md5_hash
from gluon.restricted import RestrictedError
from gluon.settings import global_settings


path = os.path.join(request.folder, 'errors')
sent_errors_file = os.path.join(path, 'slack_errors.pickle')
hashes = {}
if os.path.exists(sent_errors_file):
    try:
        with open(sent_errors_file, 'rb') as f:
            hashes = pickle.load(f)
    except Exception as _:
        pass

# ## CONFIGURE HERE
SLEEP_MINUTES = 5
ALLOW_DUPLICATES = False
global_settings.slack_hook = global_settings.slack_hook or \
    'https://hooks.slack.com/services/your_service'
# ## END CONFIGURATION

while 1:
    for file_name in os.listdir(path):
        if file_name == 'slack_errors.pickle':
            continue

        if not ALLOW_DUPLICATES:
            key = md5_hash(file_name)
            if key in hashes:
                continue
            hashes[key] = 1

        error = RestrictedError()

        try:
            error.load(request, request.application, file_name)
        except Exception as _:
            continue  # not an exception file?

        url = URL(a='admin', f='ticket', args=[request.application, file],
                  scheme=True)
        payload = json.dumps(dict(text="Error in %(app)s.\n%(url)s" %
                                       dict(app=request.application, url=url)))

        requests.post(global_settings.slack_hook, data=dict(payload=payload))

    with open(sent_errors_file, 'wb') as f:
        pickle.dump(hashes, f)
    time.sleep(SLEEP_MINUTES * 60)
