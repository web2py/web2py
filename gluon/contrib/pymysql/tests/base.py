from gluon.contrib import pymysql
import unittest

class PyMySQLTestCase(unittest.TestCase):
    databases = [
        {"host":"localhost","user":"root",
         "passwd":"","db":"test_pymysql", "use_unicode": True},
        {"host":"localhost","user":"root","passwd":"","db":"test_pymysql2"}]

    def setUp(self):
        try:
            self.connections = []

            for params in self.databases:
                self.connections.append(pymysql.connect(**params))
        except pymysql.err.OperationalError as e:
            self.skipTest('Cannot connect to MySQL - skipping pymysql tests because of (%s) %s' % (type(e), e))

    def tearDown(self):
        for connection in self.connections:
            connection.close()

