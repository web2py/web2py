import contextlib
import io
import os
import re
import tempfile
import unittest
from unittest import mock

from gluon import main


class TestMain(unittest.TestCase):
    def test_save_password_random(self):
        port = 19879
        with tempfile.TemporaryDirectory() as temporary_directory:
            password_file = os.path.join(temporary_directory, "parameters_%i.py" % port)
            output = io.StringIO()
            with mock.patch.object(main, "abspath", return_value=password_file):
                with contextlib.redirect_stdout(output):
                    main.save_password("<random>", port)

            password_match = re.search(
                r'admin password is "([A-Za-z0-9]{8})"', output.getvalue()
            )
            self.assertIsNotNone(password_match)
            with open(password_file, encoding="utf-8") as parameter_file:
                stored_password = re.fullmatch(
                    r'password="([^"]+)"\n', parameter_file.read()
                ).group(1)
            self.assertNotEqual(stored_password, password_match.group(1))


if __name__ == "__main__":
    unittest.main()