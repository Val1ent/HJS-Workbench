# -*- coding: utf-8 -*-
"""Tests for the sample-rate/mode policy, isolated to a temp directory."""
import unittest

from core import config, session
from tests._isolation import IsolatedConfig


class SessionTest(IsolatedConfig, unittest.TestCase):
    def test_save_and_effective_sample_rate(self):
        session.save_sample_rate(500000)
        self.assertEqual(session.effective_sample_rate(), 500000)

    def test_invalid_sample_rate_rejected(self):
        with self.assertRaises(ValueError):
            session.save_sample_rate(12345)
        self.assertNotIn("sample_rate", config.load())

    def test_save_and_effective_capture_mode(self):
        session.save_capture_mode("burst")
        self.assertEqual(session.effective_capture_mode(), "burst")

    def test_invalid_capture_mode_rejected(self):
        with self.assertRaises(ValueError):
            session.save_capture_mode("nope")

    def test_stale_value_falls_back_to_default(self):
        config.set("sample_rate", 999999)
        self.assertEqual(session.effective_sample_rate(),
                         config_load_rate())

    def test_reset_to_defaults(self):
        session.save_sample_rate(100000)
        session.save_capture_mode("burst")
        session.reset_to_defaults()
        self.assertEqual(config.load(), {})


def config_load_rate():
    from core.hal import current_backend
    return current_backend().capabilities.sample_rate


if __name__ == "__main__":
    unittest.main()
