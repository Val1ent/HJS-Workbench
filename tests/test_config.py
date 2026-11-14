# -*- coding: utf-8 -*-
"""Tests for persistent user configuration, isolated to a temp directory."""
import unittest

from core import config
from tests._isolation import IsolatedConfig


class ConfigTest(IsolatedConfig, unittest.TestCase):
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
