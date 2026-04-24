#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import pickle
import subprocess
import unittest

from gluon.restricted import safe_load, safe_loads


class TestRestrictedPickle(unittest.TestCase):
    def test_safe_unpickler_loads_basic_types(self):
        payload = {"traceback": "test error", "layer": "test"}
        pickled = pickle.dumps(payload, pickle.HIGHEST_PROTOCOL)

        self.assertEqual(safe_loads(pickled), payload)
        self.assertEqual(safe_load(io.BytesIO(pickled)), payload)

    def test_safe_unpickler_rejects_unsafe_classes(self):
        pickled = pickle.dumps({"bad": subprocess.Popen}, pickle.HIGHEST_PROTOCOL)
        with self.assertRaises(pickle.UnpicklingError):
            safe_loads(pickled)
