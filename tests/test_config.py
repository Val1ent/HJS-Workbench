# -*- coding: utf-8 -*-
"""Tests for persistent user configuration, isolated to a temp directory."""
import os
import tempfile
import unittest

from core import config


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self._old_appdata = os.environ.get("APPDATA")
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["APPDATA"] = self.tmp.name

    def tearDown(self):
        if self._old_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = self._old_appdata
        self.tmp.cleanup()

    def test_missing_file_loads_empty(self):
        self.assertEqual(config.load(), {})
        self.assertIsNone(config.get("anything"))

    def test_set_get_round_trip(self):
        config.set("sample_rate", 100000)
        self.assertEqual(config.get("sample_rate"), 100000)

    def test_save_and_load_dict(self):
        config.save({"a": 1, "b": "two"})
        self.assertEqual(config.load(), {"a": 1, "b": "two"})


if __name__ == "__main__":
    unittest.main()
