#!/bin/python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.sqlhtml
"""
import os
import sys
if sys.version < "2.7":
    import unittest2 as unittest
else:
    import unittest

from fix_path import fix_sys_path

fix_sys_path(__file__)

from sqlhtml import safe_int, SQLFORM, SQLTABLE

DEFAULT_URI = os.getenv('DB', 'sqlite:memory')

from gluon.dal import DAL, Field
from pydal.objects import Table
from tools import Auth, Mail
from gluon.globals import Request, Response, Session
from storage import Storage
from languages import translator
from gluon.http import HTTP
from validators import *

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

    def test_SQLFORM(self):
        form = SQLFORM(self.db.auth_user)
        self.assertEqual(form.xml(), '<form action="#" enctype="multipart/form-data" method="post"><table><tr id="auth_user_first_name__row"><td class="w2p_fl"><label class="" for="auth_user_first_name" id="auth_user_first_name__label">First name: </label></td><td class="w2p_fw"><input class="string" id="auth_user_first_name" name="first_name" type="text" value="" /></td><td class="w2p_fc"></td></tr><tr id="auth_user_last_name__row"><td class="w2p_fl"><label class="" for="auth_user_last_name" id="auth_user_last_name__label">Last name: </label></td><td class="w2p_fw"><input class="string" id="auth_user_last_name" name="last_name" type="text" value="" /></td><td class="w2p_fc"></td></tr><tr id="auth_user_email__row"><td class="w2p_fl"><label class="" for="auth_user_email" id="auth_user_email__label">E-mail: </label></td><td class="w2p_fw"><input class="string" id="auth_user_email" name="email" type="text" value="" /></td><td class="w2p_fc"></td></tr><tr id="auth_user_username__row"><td class="w2p_fl"><label class="" for="auth_user_username" id="auth_user_username__label">Username: </label></td><td class="w2p_fw"><input class="string" id="auth_user_username" name="username" type="text" value="" /></td><td class="w2p_fc"></td></tr><tr id="auth_user_password__row"><td class="w2p_fl"><label class="" for="auth_user_password" id="auth_user_password__label">Password: </label></td><td class="w2p_fw"><input class="password" id="auth_user_password" name="password" type="password" value="" /></td><td class="w2p_fc"></td></tr><tr id="submit_record__row"><td class="w2p_fl"></td><td class="w2p_fw"><input type="submit" value="Submit" /></td><td class="w2p_fc"></td></tr></table></form>')

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
        self.assertEqual(factory_form.xml(), '<form action="#" enctype="multipart/form-data" method="post"><table><tr id="no_table_field_one__row"><td class="w2p_fl"><label class="" for="no_table_field_one" id="no_table_field_one__label">Field One: </label></td><td class="w2p_fw"><input class="string" id="no_table_field_one" name="field_one" type="text" value="" /></td><td class="w2p_fc"></td></tr><tr id="no_table_field_two__row"><td class="w2p_fl"><label class="" for="no_table_field_two" id="no_table_field_two__label">Field Two: </label></td><td class="w2p_fw"><input class="string" id="no_table_field_two" name="field_two" type="text" value="" /></td><td class="w2p_fc"></td></tr><tr id="submit_record__row"><td class="w2p_fl"></td><td class="w2p_fw"><input type="submit" value="Submit" /></td><td class="w2p_fc"></td></tr></table></form>')

    #  def test_build_query(self):
    #     pass

    #  def test_search_menu(self):
    #     pass

    def test_grid(self):
        grid_form = SQLFORM.grid(self.db.auth_user)
        self.assertEqual(grid_form.xml(), '<div class="web2py_grid "><div class="web2py_console  "><form action="/a/c/f" enctype="multipart/form-data" method="GET"><input class="form-control" id="w2p_keywords" name="keywords" onfocus="jQuery(&#x27;#w2p_query_fields&#x27;).change();jQuery(&#x27;#w2p_query_panel&#x27;).slideDown();" type="text" value="" /><input class="btn btn-default" type="submit" value="Search" /><input class="btn btn-default" onclick="jQuery(&#x27;#w2p_keywords&#x27;).val(&#x27;&#x27;);" type="submit" value="Clear" /></form><div id="w2p_query_panel" style="display:none;"><select class="form-control" id="w2p_query_fields" onchange="jQuery(&#x27;.w2p_query_row&#x27;).hide();jQuery(&#x27;#w2p_field_&#x27;+jQuery(&#x27;#w2p_query_fields&#x27;).val().replace(&#x27;.&#x27;,&#x27;-&#x27;)).show();" style="float:left"><option value="auth_user.id">Id</option><option value="auth_user.first_name">First name</option><option value="auth_user.last_name">Last name</option><option value="auth_user.email">E-mail</option><option value="auth_user.username">Username</option></select><div class="w2p_query_row" id="w2p_field_auth_user-id" style="display:none"><select class="form-control"><option value="=">=</option><option value="!=">!=</option><option value="&lt;">&lt;</option><option value="&gt;">&gt;</option><option value="&lt;=">&lt;=</option><option value="&gt;=">&gt;=</option><option value="in">in</option><option value="not in">not in</option></select><input class="id form-control" id="w2p_value_auth_user-id" type="text" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;new&#x27;,&#x27;auth_user.id&#x27;)" title="Start building a new search" type="button" value="New Search" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;and&#x27;,&#x27;auth_user.id&#x27;)" title="Add this to the search as an AND term" type="button" value="+ And" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;or&#x27;,&#x27;auth_user.id&#x27;)" title="Add this to the search as an OR term" type="button" value="+ Or" /><input class="btn btn-default" onclick="jQuery(&#x27;#w2p_query_panel&#x27;).slideUp()" type="button" value="Close" /></div><div class="w2p_query_row" id="w2p_field_auth_user-first_name" style="display:none"><select class="form-control"><option value="=">=</option><option value="!=">!=</option><option value="&lt;">&lt;</option><option value="&gt;">&gt;</option><option value="&lt;=">&lt;=</option><option value="&gt;=">&gt;=</option><option value="starts with">starts with</option><option value="contains">contains</option><option value="in">in</option><option value="not in">not in</option></select><input class="string form-control" id="w2p_value_auth_user-first_name" type="text" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;new&#x27;,&#x27;auth_user.first_name&#x27;)" title="Start building a new search" type="button" value="New Search" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;and&#x27;,&#x27;auth_user.first_name&#x27;)" title="Add this to the search as an AND term" type="button" value="+ And" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;or&#x27;,&#x27;auth_user.first_name&#x27;)" title="Add this to the search as an OR term" type="button" value="+ Or" /><input class="btn btn-default" onclick="jQuery(&#x27;#w2p_query_panel&#x27;).slideUp()" type="button" value="Close" /></div><div class="w2p_query_row" id="w2p_field_auth_user-last_name" style="display:none"><select class="form-control"><option value="=">=</option><option value="!=">!=</option><option value="&lt;">&lt;</option><option value="&gt;">&gt;</option><option value="&lt;=">&lt;=</option><option value="&gt;=">&gt;=</option><option value="starts with">starts with</option><option value="contains">contains</option><option value="in">in</option><option value="not in">not in</option></select><input class="string form-control" id="w2p_value_auth_user-last_name" type="text" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;new&#x27;,&#x27;auth_user.last_name&#x27;)" title="Start building a new search" type="button" value="New Search" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;and&#x27;,&#x27;auth_user.last_name&#x27;)" title="Add this to the search as an AND term" type="button" value="+ And" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;or&#x27;,&#x27;auth_user.last_name&#x27;)" title="Add this to the search as an OR term" type="button" value="+ Or" /><input class="btn btn-default" onclick="jQuery(&#x27;#w2p_query_panel&#x27;).slideUp()" type="button" value="Close" /></div><div class="w2p_query_row" id="w2p_field_auth_user-email" style="display:none"><select class="form-control"><option value="=">=</option><option value="!=">!=</option><option value="&lt;">&lt;</option><option value="&gt;">&gt;</option><option value="&lt;=">&lt;=</option><option value="&gt;=">&gt;=</option><option value="starts with">starts with</option><option value="contains">contains</option><option value="in">in</option><option value="not in">not in</option></select><input class="string form-control" id="w2p_value_auth_user-email" type="text" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;new&#x27;,&#x27;auth_user.email&#x27;)" title="Start building a new search" type="button" value="New Search" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;and&#x27;,&#x27;auth_user.email&#x27;)" title="Add this to the search as an AND term" type="button" value="+ And" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;or&#x27;,&#x27;auth_user.email&#x27;)" title="Add this to the search as an OR term" type="button" value="+ Or" /><input class="btn btn-default" onclick="jQuery(&#x27;#w2p_query_panel&#x27;).slideUp()" type="button" value="Close" /></div><div class="w2p_query_row" id="w2p_field_auth_user-username" style="display:none"><select class="form-control"><option value="=">=</option><option value="!=">!=</option><option value="&lt;">&lt;</option><option value="&gt;">&gt;</option><option value="&lt;=">&lt;=</option><option value="&gt;=">&gt;=</option><option value="starts with">starts with</option><option value="contains">contains</option><option value="in">in</option><option value="not in">not in</option></select><input class="string form-control" id="w2p_value_auth_user-username" type="text" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;new&#x27;,&#x27;auth_user.username&#x27;)" title="Start building a new search" type="button" value="New Search" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;and&#x27;,&#x27;auth_user.username&#x27;)" title="Add this to the search as an AND term" type="button" value="+ And" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;or&#x27;,&#x27;auth_user.username&#x27;)" title="Add this to the search as an OR term" type="button" value="+ Or" /><input class="btn btn-default" onclick="jQuery(&#x27;#w2p_query_panel&#x27;).slideUp()" type="button" value="Close" /></div></div><script><!--\n\n        jQuery(\'#w2p_query_fields input,#w2p_query_fields select\').css(\n            \'width\',\'auto\');\n        jQuery(function(){web2py_ajax_fields(\'#w2p_query_fields\');});\n        function w2p_build_query(aggregator,a) {\n          var b=a.replace(\'.\',\'-\');\n          var option = jQuery(\'#w2p_field_\'+b+\' select\').val();\n          var value;\n          var $value_item = jQuery(\'#w2p_value_\'+b);\n          if ($value_item.is(\':checkbox\')){\n            if  ($value_item.is(\':checked\'))\n                    value = \'True\';\n            else  value = \'False\';\n          }\n          else\n          { value = $value_item.val().replace(\'"\',\'\\\\"\')}\n          var s=a+\' \'+option+\' "\'+value+\'"\';\n          var k=jQuery(\'#w2p_keywords\');\n          var v=k.val();\n          if(aggregator==\'new\') k.val(s); else k.val((v?(v+\' \'+ aggregator +\' \'):\'\')+s);\n        }\n        \n//--></script><div class="web2py_counter">1 records found</div></div><div class="web2py_table"><div class="web2py_htmltable" style="width:100%;overflow-x:auto;-ms-overflow-x:scroll"><table><colgroup><col data-column="1" id="auth_user-id" /><col data-column="2" id="auth_user-first_name" /><col data-column="3" id="auth_user-last_name" /><col data-column="4" id="auth_user-email" /><col data-column="5" id="auth_user-username" /><col data-column="6" /></colgroup><thead><tr class=""><th class=""><a href="/a/c/f?keywords=&amp;order=auth_user.id">Id</a></th><th class=""><a href="/a/c/f?keywords=&amp;order=auth_user.first_name">First name</a></th><th class=""><a href="/a/c/f?keywords=&amp;order=auth_user.last_name">Last name</a></th><th class=""><a href="/a/c/f?keywords=&amp;order=auth_user.email">E-mail</a></th><th class=""><a href="/a/c/f?keywords=&amp;order=auth_user.username">Username</a></th><th class=""></th></tr></thead><tbody><tr class="w2p_odd odd with_id" id="1"><td>1</td><td>Bart</td><td>Simpson</td><td>user1@test.com</td><td>user1</td><td class="row_buttons" nowrap="nowrap"><a class="button btn btn-default" href="/a/c/f/view/auth_user/1"><span class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"></span> <span class="buttontext button" title="View">View</span></a></td></tr></tbody></table></div></div><div class="w2p_export_menu">Export:<a class="btn btn-default" href="/a/c/f?_export_type=csv&amp;keywords=&amp;order=" title="Comma-separated export of visible columns. Fields from other tables are exported as they appear on-screen but this may be slow for many rows">CSV</a><a class="btn btn-default" href="/a/c/f?_export_type=csv_with_hidden_cols&amp;keywords=&amp;order=" title="Comma-separated export including columns not shown; fields from other tables are exported as raw values for faster export">CSV (hidden cols)</a><a class="btn btn-default" href="/a/c/f?_export_type=html&amp;keywords=&amp;order=" title="HTML export of visible columns">HTML</a><a class="btn btn-default" href="/a/c/f?_export_type=json&amp;keywords=&amp;order=" title="JSON export of visible columns">JSON</a><a class="btn btn-default" href="/a/c/f?_export_type=tsv&amp;keywords=&amp;order=" title="Spreadsheet-optimised export of tab-separated content, visible columns only. May be slow.">TSV (Spreadsheets)</a><a class="btn btn-default" href="/a/c/f?_export_type=tsv_with_hidden_cols&amp;keywords=&amp;order=" title="Spreadsheet-optimised export of tab-separated content including hidden columns. May be slow">TSV (Spreadsheets, hidden cols)</a><a class="btn btn-default" href="/a/c/f?_export_type=xml&amp;keywords=&amp;order=" title="XML export of columns shown">XML</a></div></div>')

    def test_smartgrid(self):
        smartgrid_form = SQLFORM.smartgrid(self.db.auth_user)
        self.assertEqual(smartgrid_form.xml(), '<div class="web2py_grid "><div class="web2py_breadcrumbs"><ul class=""><li class="active w2p_grid_breadcrumb_elem"><a href="/a/c/f/auth_user">Auth users</a></li></ul></div><div class="web2py_console  "><form action="/a/c/f/auth_user" enctype="multipart/form-data" method="GET"><input class="form-control" id="w2p_keywords" name="keywords" onfocus="jQuery(&#x27;#w2p_query_fields&#x27;).change();jQuery(&#x27;#w2p_query_panel&#x27;).slideDown();" type="text" value="" /><input class="btn btn-default" type="submit" value="Search" /><input class="btn btn-default" onclick="jQuery(&#x27;#w2p_keywords&#x27;).val(&#x27;&#x27;);" type="submit" value="Clear" /></form><div id="w2p_query_panel" style="display:none;"><select class="form-control" id="w2p_query_fields" onchange="jQuery(&#x27;.w2p_query_row&#x27;).hide();jQuery(&#x27;#w2p_field_&#x27;+jQuery(&#x27;#w2p_query_fields&#x27;).val().replace(&#x27;.&#x27;,&#x27;-&#x27;)).show();" style="float:left"><option value="auth_user.id">Id</option><option value="auth_user.first_name">First name</option><option value="auth_user.last_name">Last name</option><option value="auth_user.email">E-mail</option><option value="auth_user.username">Username</option></select><div class="w2p_query_row" id="w2p_field_auth_user-id" style="display:none"><select class="form-control"><option value="=">=</option><option value="!=">!=</option><option value="&lt;">&lt;</option><option value="&gt;">&gt;</option><option value="&lt;=">&lt;=</option><option value="&gt;=">&gt;=</option><option value="in">in</option><option value="not in">not in</option></select><input class="id form-control" id="w2p_value_auth_user-id" type="text" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;new&#x27;,&#x27;auth_user.id&#x27;)" title="Start building a new search" type="button" value="New Search" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;and&#x27;,&#x27;auth_user.id&#x27;)" title="Add this to the search as an AND term" type="button" value="+ And" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;or&#x27;,&#x27;auth_user.id&#x27;)" title="Add this to the search as an OR term" type="button" value="+ Or" /><input class="btn btn-default" onclick="jQuery(&#x27;#w2p_query_panel&#x27;).slideUp()" type="button" value="Close" /></div><div class="w2p_query_row" id="w2p_field_auth_user-first_name" style="display:none"><select class="form-control"><option value="=">=</option><option value="!=">!=</option><option value="&lt;">&lt;</option><option value="&gt;">&gt;</option><option value="&lt;=">&lt;=</option><option value="&gt;=">&gt;=</option><option value="starts with">starts with</option><option value="contains">contains</option><option value="in">in</option><option value="not in">not in</option></select><input class="string form-control" id="w2p_value_auth_user-first_name" type="text" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;new&#x27;,&#x27;auth_user.first_name&#x27;)" title="Start building a new search" type="button" value="New Search" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;and&#x27;,&#x27;auth_user.first_name&#x27;)" title="Add this to the search as an AND term" type="button" value="+ And" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;or&#x27;,&#x27;auth_user.first_name&#x27;)" title="Add this to the search as an OR term" type="button" value="+ Or" /><input class="btn btn-default" onclick="jQuery(&#x27;#w2p_query_panel&#x27;).slideUp()" type="button" value="Close" /></div><div class="w2p_query_row" id="w2p_field_auth_user-last_name" style="display:none"><select class="form-control"><option value="=">=</option><option value="!=">!=</option><option value="&lt;">&lt;</option><option value="&gt;">&gt;</option><option value="&lt;=">&lt;=</option><option value="&gt;=">&gt;=</option><option value="starts with">starts with</option><option value="contains">contains</option><option value="in">in</option><option value="not in">not in</option></select><input class="string form-control" id="w2p_value_auth_user-last_name" type="text" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;new&#x27;,&#x27;auth_user.last_name&#x27;)" title="Start building a new search" type="button" value="New Search" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;and&#x27;,&#x27;auth_user.last_name&#x27;)" title="Add this to the search as an AND term" type="button" value="+ And" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;or&#x27;,&#x27;auth_user.last_name&#x27;)" title="Add this to the search as an OR term" type="button" value="+ Or" /><input class="btn btn-default" onclick="jQuery(&#x27;#w2p_query_panel&#x27;).slideUp()" type="button" value="Close" /></div><div class="w2p_query_row" id="w2p_field_auth_user-email" style="display:none"><select class="form-control"><option value="=">=</option><option value="!=">!=</option><option value="&lt;">&lt;</option><option value="&gt;">&gt;</option><option value="&lt;=">&lt;=</option><option value="&gt;=">&gt;=</option><option value="starts with">starts with</option><option value="contains">contains</option><option value="in">in</option><option value="not in">not in</option></select><input class="string form-control" id="w2p_value_auth_user-email" type="text" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;new&#x27;,&#x27;auth_user.email&#x27;)" title="Start building a new search" type="button" value="New Search" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;and&#x27;,&#x27;auth_user.email&#x27;)" title="Add this to the search as an AND term" type="button" value="+ And" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;or&#x27;,&#x27;auth_user.email&#x27;)" title="Add this to the search as an OR term" type="button" value="+ Or" /><input class="btn btn-default" onclick="jQuery(&#x27;#w2p_query_panel&#x27;).slideUp()" type="button" value="Close" /></div><div class="w2p_query_row" id="w2p_field_auth_user-username" style="display:none"><select class="form-control"><option value="=">=</option><option value="!=">!=</option><option value="&lt;">&lt;</option><option value="&gt;">&gt;</option><option value="&lt;=">&lt;=</option><option value="&gt;=">&gt;=</option><option value="starts with">starts with</option><option value="contains">contains</option><option value="in">in</option><option value="not in">not in</option></select><input class="string form-control" id="w2p_value_auth_user-username" type="text" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;new&#x27;,&#x27;auth_user.username&#x27;)" title="Start building a new search" type="button" value="New Search" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;and&#x27;,&#x27;auth_user.username&#x27;)" title="Add this to the search as an AND term" type="button" value="+ And" /><input class="btn btn-default" onclick="w2p_build_query(&#x27;or&#x27;,&#x27;auth_user.username&#x27;)" title="Add this to the search as an OR term" type="button" value="+ Or" /><input class="btn btn-default" onclick="jQuery(&#x27;#w2p_query_panel&#x27;).slideUp()" type="button" value="Close" /></div></div><script><!--\n\n        jQuery(\'#w2p_query_fields input,#w2p_query_fields select\').css(\n            \'width\',\'auto\');\n        jQuery(function(){web2py_ajax_fields(\'#w2p_query_fields\');});\n        function w2p_build_query(aggregator,a) {\n          var b=a.replace(\'.\',\'-\');\n          var option = jQuery(\'#w2p_field_\'+b+\' select\').val();\n          var value;\n          var $value_item = jQuery(\'#w2p_value_\'+b);\n          if ($value_item.is(\':checkbox\')){\n            if  ($value_item.is(\':checked\'))\n                    value = \'True\';\n            else  value = \'False\';\n          }\n          else\n          { value = $value_item.val().replace(\'"\',\'\\\\"\')}\n          var s=a+\' \'+option+\' "\'+value+\'"\';\n          var k=jQuery(\'#w2p_keywords\');\n          var v=k.val();\n          if(aggregator==\'new\') k.val(s); else k.val((v?(v+\' \'+ aggregator +\' \'):\'\')+s);\n        }\n        \n//--></script><div class="web2py_counter">1 records found</div></div><div class="web2py_table"><div class="web2py_htmltable" style="width:100%;overflow-x:auto;-ms-overflow-x:scroll"><table><colgroup><col data-column="1" id="auth_user-id" /><col data-column="2" id="auth_user-first_name" /><col data-column="3" id="auth_user-last_name" /><col data-column="4" id="auth_user-email" /><col data-column="5" id="auth_user-username" /><col data-column="6" /></colgroup><thead><tr class=""><th class=""><a href="/a/c/f/auth_user?keywords=&amp;order=auth_user.id">Id</a></th><th class=""><a href="/a/c/f/auth_user?keywords=&amp;order=auth_user.first_name">First name</a></th><th class=""><a href="/a/c/f/auth_user?keywords=&amp;order=auth_user.last_name">Last name</a></th><th class=""><a href="/a/c/f/auth_user?keywords=&amp;order=auth_user.email">E-mail</a></th><th class=""><a href="/a/c/f/auth_user?keywords=&amp;order=auth_user.username">Username</a></th><th class=""></th></tr></thead><tbody><tr class="w2p_odd odd with_id" id="1"><td>1</td><td>Bart</td><td>Simpson</td><td>user1@test.com</td><td>user1</td><td class="row_buttons" nowrap="nowrap"><a href="/a/c/f/auth_user/auth_membership.user_id/1"><span>Auth memberships</span></a><a href="/a/c/f/auth_user/auth_event.user_id/1"><span>Auth events</span></a><a href="/a/c/f/auth_user/auth_cas.user_id/1"><span>Auth cases</span></a><a href="/a/c/f/auth_user/t0.created_by/1"><span>T0s(created_by)</span></a><a href="/a/c/f/auth_user/t0.modified_by/1"><span>T0s(modified_by)</span></a><a href="/a/c/f/auth_user/t0_archive.created_by/1"><span>T0 archives(created_by)</span></a><a href="/a/c/f/auth_user/t0_archive.modified_by/1"><span>T0 archives(modified_by)</span></a><a class="button btn btn-default" href="/a/c/f/auth_user/view/auth_user/1"><span class="icon magnifier icon-zoom-in glyphicon glyphicon-zoom-in"></span> <span class="buttontext button" title="View">View</span></a></td></tr></tbody></table></div></div><div class="w2p_export_menu">Export:<a class="btn btn-default" href="/a/c/f/auth_user?_export_type=csv&amp;keywords=&amp;order=" title="Comma-separated export of visible columns. Fields from other tables are exported as they appear on-screen but this may be slow for many rows">CSV</a><a class="btn btn-default" href="/a/c/f/auth_user?_export_type=csv_with_hidden_cols&amp;keywords=&amp;order=" title="Comma-separated export including columns not shown; fields from other tables are exported as raw values for faster export">CSV (hidden cols)</a><a class="btn btn-default" href="/a/c/f/auth_user?_export_type=html&amp;keywords=&amp;order=" title="HTML export of visible columns">HTML</a><a class="btn btn-default" href="/a/c/f/auth_user?_export_type=json&amp;keywords=&amp;order=" title="JSON export of visible columns">JSON</a><a class="btn btn-default" href="/a/c/f/auth_user?_export_type=tsv&amp;keywords=&amp;order=" title="Spreadsheet-optimised export of tab-separated content, visible columns only. May be slow.">TSV (Spreadsheets)</a><a class="btn btn-default" href="/a/c/f/auth_user?_export_type=tsv_with_hidden_cols&amp;keywords=&amp;order=" title="Spreadsheet-optimised export of tab-separated content including hidden columns. May be slow">TSV (Spreadsheets, hidden cols)</a><a class="btn btn-default" href="/a/c/f/auth_user?_export_type=xml&amp;keywords=&amp;order=" title="XML export of columns shown">XML</a></div></div>')


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
        self.assertEqual(sqltable.xml(), '<table><thead><tr><th>auth_user.id</th><th>auth_user.first_name</th><th>auth_user.last_name</th><th>auth_user.email</th><th>auth_user.username</th><th>auth_user.password</th><th>auth_user.registration_key</th><th>auth_user.reset_password_key</th><th>auth_user.registration_id</th></tr></thead><tbody><tr class="w2p_odd odd"><td>1</td><td>Bart</td><td>Simpson</td><td>user1@test.com</td><td>user1</td><td>password_123</td><td>None</td><td></td><td>None</td></tr></tbody></table>')


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


if __name__ == '__main__':
    unittest.main()
