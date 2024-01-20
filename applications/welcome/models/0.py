# -*- coding: utf-8 -*-

import os
from gluon import current
import logging.config

configfile = os.path.join(current.request.folder, 'private', 'logconfig.ini')
if not os.path.isfile(configfile):
    raise HTTP(500, configfile + ' - not exist!')


logging.config.fileConfig(configfile, None, False)
#logger = logging.getLogger('') ## [logger_root] see private/logconfig.ini
#logger = logging.getLogger('app') ## [ logger_app] see private/logconfig.ini
logger = logging.getLogger('debug') ## [logger_debug] see private/logconfig.ini
current.logger = logger

## app configuration made easy. Look inside private/appconfig.ini
from gluon.contrib.appconfig import AppConfig

## once in production, remove reload=True to gain full speed
myconf = AppConfig(reload=True)

curent.DEVELOP = DEVELOP = myconf.take('app.develop', cast=bool)
current.IS_LOCAL = IS_LOCAL = request.is_local
current.IS_MOBILE = IS_MOBILE = request.user_agent().is_mobile
current.IS_TABLET = IS_TABLET = request.user_agent().is_tablet

CACHE_EXP_TIME = request.is_local and 5 or 360

if DEVELOP:
    logger.debug("develop mode is used!")