#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Unit tests for cron """
import unittest, os
from gluon.newcron import Token, crondance

class TestCron(unittest.TestCase):


    def test_Token(self):
        appname_path = os.path.join(os.getcwd(), 'applications', 'welcome')
        t = Token(path=appname_path)
        self.assertNotEqual(t.acquire(), None)
        self.assertFalse(t.release())
        self.assertEqual(t.acquire(), None)
        self.assertTrue(t.release())
        return
        
    def test_crondance(self):
        #TODO update crondance to return something 
        crondance(os.getcwd())
        
        
