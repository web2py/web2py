#!/bin/python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.sqlhtml
"""
import os
import sys
import unittest

from gluon.sqlhtml import safe_int, SQLFORM, SQLTABLE

DEFAULT_URI = os.getenv('DB', 'sqlite:memory')

from gluon.dal import DAL, Field
from pydal.objects import Table
from gluon.tools import Auth, Mail
from gluon.globals import Request, Response, Session
from gluon.storage import Storage
from gluon.languages import translator
from gluon.http import HTTP
from gluon.validators import *

# TODO: Create these test...

# class Test_add_class(unittest.TestCase):
#     def test_add_class(self):
#         pass


# class Test_represent(unittest.TestCase):
#     def test_represent(self):
#         pass


# class TestCacheRepresenter(unittest.TestCase):
#     def test___call__(self):
#         pass

#     def test___init__(self):
#         pass


class Test_safe_int(unittest.TestCase):
    def test_safe_int(self):
        # safe int
        self.assertEqual(safe_int(1), 1)
        # not safe int
        self.assertEqual(safe_int('1x'), 0)
        # not safe int (alternate default)
        self.assertEqual(safe_int('1x', 1), 1)


# class Test_safe_float(unittest.TestCase):
#     def test_safe_float(self):
#         pass


# class Test_show_if(unittest.TestCase):
#     def test_show_if(self):
#         pass


# class TestFormWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestStringWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestIntegerWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestDoubleWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestDecimalWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestDateWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestDatetimeWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestTextWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestJSONWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestBooleanWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestListWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestMultipleOptionsWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestRadioWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestCheckboxesWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestPasswordWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_widget(self):
#         pass


# class TestUploadWidget(unittest.TestCase):
#     def test__attributes(self):
#         pass

#     def test_represent(self):
#         pass

#     def test_widget(self):
#         pass


# class TestAutocompleteWidget(unittest.TestCase):
#     def test___call__(self):
#         pass

#     def test___init__(self):
#         pass

#     def test_callback(self):
#         pass


# class Test_formstyle_table3cols(unittest.TestCase):
#     def test_formstyle_table3cols(self):
#         pass


# class Test_formstyle_table2cols(unittest.TestCase):
#     def test_formstyle_table2cols(self):
#         pass


# class Test_formstyle_divs(unittest.TestCase):
#     def test_formstyle_divs(self):
#         pass


# class Test_formstyle_inline(unittest.TestCase):
#     def test_formstyle_inline(self):
#         pass


# class Test_formstyle_ul(unittest.TestCase):
#     def test_formstyle_ul(self):
#         pass


# class Test_formstyle_bootstrap(unittest.TestCase):
#     def test_formstyle_bootstrap(self):
#         pass


# class Test_formstyle_bootstrap3_stacked(unittest.TestCase):
#     def test_formstyle_bootstrap3_stacked(self):
#         pass


# class Test_formstyle_bootstrap3_inline_factory(unittest.TestCase):
#     def test_formstyle_bootstrap3_inline_factory(self):
#         pass


class TestSQLFORM(unittest.TestCase):

    def setUp(self):
        request = Request(env={})
        request.application = 'a'
        request.controller = 'c'
        request.function = 'f'
        request.folder = 'applications/admin'
        response = Response()
        session = Session()
        T = translator('', 'en')
        session.connect(request, response)
        from gluon.globals import current
        current.request = request
        current.response = response
        current.session = session
        current.T = T
        self.db = DAL(DEFAULT_URI, check_reserved=['all'])
        self.auth = Auth(self.db)
        self.auth.define_tables(username=True, signature=False)
        self.db.define_table('t0', Field('tt', default='web2py'), self.auth.signature)
        self.auth.enable_record_versioning(self.db)
        # Create a user
        self.db.auth_user.insert(first_name='Bart',
                                 last_name='Simpson',
                                 username='user1',
                                 email='user1@test.com',
                                 password='password_123',
                                 registration_key=None,
                                 registration_id=None)

        self.db.commit()

    
    def test_SQLFORM(self):
        form = SQLFORM(self.db.auth_user)
        self.assertEqual(form.xml()[:5], b'<form')

    def test_represent_SQLFORM(self):
        id = self.db.t0.insert()
        self.db.t0.tt.represent = lambda value: value.capitalize()
        self.db.t0.tt.writable = False
        self.db.t0.tt.readable = True
        form = SQLFORM(self.db.t0, id)
        self.assertTrue(b'Web2py' in form.xml())
        self.db.t0.tt.represent = lambda value, row: value.capitalize()
        form = SQLFORM(self.db.t0, id)
        self.assertTrue(b'Web2py' in form.xml())

    # def test_assert_status(self):
    #     pass

    #  def test_createform(self):
    #     pass

    #  def test_accepts(self):
    #     pass

    #  def test_dictform(self):
    #     pass

    #  def test_smartdictform(self):
    #     pass

    def test_factory(self):
        factory_form = SQLFORM.factory(Field('field_one', 'string', IS_NOT_EMPTY()),
                                       Field('field_two', 'string'))
        self.assertEqual(factory_form.xml()[:5], b'<form')

    #  def test_build_query(self):
    #     pass

    #  def test_search_menu(self):
    #     pass

    def test_grid(self):
        grid_form = SQLFORM.grid(self.db.auth_user)
        self.assertEqual(grid_form.xml()[:4], b'<div')

    def test_smartgrid(self):
        smartgrid_form = SQLFORM.smartgrid(self.db.auth_user)
        self.assertEqual(smartgrid_form.xml()[:4], b'<div')

class TestSQLTABLE(unittest.TestCase):
    def setUp(self):
        request = Request(env={})
        request.application = 'a'
        request.controller = 'c'
        request.function = 'f'
        request.folder = 'applications/admin'
        response = Response()
        session = Session()
        T = translator('', 'en')
        session.connect(request, response)
        from gluon.globals import current
        current.request = request
        current.response = response
        current.session = session
        current.T = T
        self.db = DAL(DEFAULT_URI, check_reserved=['all'])
        self.auth = Auth(self.db)
        self.auth.define_tables(username=True, signature=False)
        self.db.define_table('t0', Field('tt'), self.auth.signature)
        self.auth.enable_record_versioning(self.db)
        # Create a user
        self.db.auth_user.insert(first_name='Bart',
                                 last_name='Simpson',
                                 username='user1',
                                 email='user1@test.com',
                                 password='password_123',
                                 registration_key=None,
                                 registration_id=None)

        self.db.commit()

    def test_SQLTABLE(self):
        rows = self.db(self.db.auth_user.id > 0).select(self.db.auth_user.ALL)
        sqltable = SQLTABLE(rows)
        self.assertEqual(sqltable.xml()[:7], b'<table>')


# class TestExportClass(unittest.TestCase):
#     def test___init__(self):
#         pass

#     def test_export(self):
#         pass

#     def test_represented(self):
#         pass


# class TestExporterTSV(unittest.TestCase):
#     def test___init__(self):
#         pass

#     def test_export(self):
#         pass

#     def test_represented(self):
#         pass


# class TestExporterCSV(unittest.TestCase):
#     def test___init__(self):
#         pass

#     def test_export(self):
#         pass

#     def test_represented(self):
#         pass


# class TestExporterCSV_hidden(unittest.TestCase):
#     def test___init__(self):
#         pass

#     def test_export(self):
#         pass

#     def test_represented(self):
#         pass


# class TestExporterHTML(unittest.TestCase):
#     def test___init__(self):
#         pass

#     def test_export(self):
#         pass

#     def test_represented(self):
#         pass


# class TestExporterXML(unittest.TestCase):
#     def test___init__(self):
#         pass

#     def test_export(self):
#         pass

#     def test_represented(self):
#         pass


# class TestExporterJSON(unittest.TestCase):
#     def test___init__(self):
#         pass

#     def test_export(self):
#         pass

#     def test_represented(self):
#         pass
