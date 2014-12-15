# -*- coding: utf-8 -*-

from gluon.pydal import DAL as pyDAL
from gluon.pydal import Field, SQLCustomType, geoPoint, geoLine, geoPolygon


from gluon import serializers as w2p_serializers
from gluon import validators as w2p_validators
from gluon.utils import web2py_uuid
from gluon import sqlhtml


class DAL(pyDAL):
    serializers = w2p_serializers
    validators = w2p_validators
    uuid = web2py_uuid
    representers = {
        'rows_render': sqlhtml.represent,
        'rows_xml': sqlhtml.SQLTABLE
    }
