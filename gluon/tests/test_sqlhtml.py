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

from sqlhtml import safe_int

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


# class TestSQLFORM(unittest.TestCase):
#     def test___add__(self):
#         pass

#     def test___delitem__(self):
#         pass

#     def test___getitem__(self):
#         pass

#     def test___init__(self):
#         pass

#     def test___len__(self):
#         pass

#     def test___mul__(self):
#         pass

#     def test___nonzero__(self):
#         pass

#     def test___setitem__(self):
#         pass

#     def test___str__(self):
#         pass

#     def test__fixup(self):
#         pass

#     def test__postprocessing(self):
#         pass

#     def test__setnode(self):
#         pass

#     def test__traverse(self):
#         pass

#     def test__validate(self):
#         pass

#     def test__wrap_components(self):
#         pass

#     def test__xml(self):
#         pass

#     def test_accepts(self):
#         pass

#     def test_add_button(self):
#         pass

#     def test_add_class(self):
#         pass

#     def test_append(self):
#         pass

#     def test_as_dict(self):
#         pass

#     def test_as_json(self):
#         pass

#     def test_as_xml(self):
#         pass

#     def test_as_yaml(self):
#         pass

#     def test_assert_status(self):
#         pass

#     def test_createform(self):
#         pass

#     def test_element(self):
#         pass

#     def test_elements(self):
#         pass

#     def test_flatten(self):
#         pass

#     def test_get(self):
#         pass

#     def test_hidden_fields(self):
#         pass

#     def test_insert(self):
#         pass

#     def test_process(self):
#         pass

#     def test_remove_class(self):
#         pass

#     def test_sibling(self):
#         pass

#     def test_siblings(self):
#         pass

#     def test_update(self):
#         pass

#     def test_validate(self):
#         pass

#     def test_xml(self):
#         pass


# class TestSQLTABLE(unittest.TestCase):
#     def test___add__(self):
#         pass

#     def test___delitem__(self):
#         pass

#     def test___getitem__(self):
#         pass

#     def test___init__(self):
#         pass

#     def test___len__(self):
#         pass

#     def test___mul__(self):
#         pass

#     def test___nonzero__(self):
#         pass

#     def test___setitem__(self):
#         pass

#     def test___str__(self):
#         pass

#     def test__fixup(self):
#         pass

#     def test__postprocessing(self):
#         pass

#     def test__setnode(self):
#         pass

#     def test__traverse(self):
#         pass

#     def test__validate(self):
#         pass

#     def test__wrap_components(self):
#         pass

#     def test__xml(self):
#         pass

#     def test_add_class(self):
#         pass

#     def test_append(self):
#         pass

#     def test_element(self):
#         pass

#     def test_elements(self):
#         pass

#     def test_flatten(self):
#         pass

#     def test_get(self):
#         pass

#     def test_insert(self):
#         pass

#     def test_remove_class(self):
#         pass

#     def test_sibling(self):
#         pass

#     def test_siblings(self):
#         pass

#     def test_style(self):
#         pass

#     def test_update(self):
#         pass

#     def test_xml(self):
#         pass


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