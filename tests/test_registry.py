# -*- coding: utf-8 -*-
"""Tests for the decoder registry and terminal event printing."""
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from core import registry


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self._saved = dict(registry.DECKS)

    def tearDown(self):
        registry.DECKS.clear()
        registry.DECKS.update(self._saved)

    def test_register_stores_entry(self):
        def decode(samples, rate):
            return []

        def make(rate):
            return []

        registry.register("unit_test_dec", decode, make, "a test decoder")
        entry = registry.DECKS["unit_test_dec"]
        self.assertIs(entry["decode"], decode)
        self.assertIs(entry["make"], make)
        self.assertEqual(entry["desc"], "a test decoder")

    def test_register_overwrites_same_name(self):
        registry.register("unit_test_dup", lambda s, r: [], lambda r: [], "first")
        registry.register("unit_test_dup", lambda s, r: [], lambda r: [], "second")
        self.assertEqual(registry.DECKS["unit_test_dup"]["desc"], "second")

    def test_selftest_runs_make_and_decode(self):
        made = [1, 2, 3]
        decoded = [{"t": 0, "ch": 0, "type": "x", "text": "y"}]
        fake_backend = MagicMock()
        fake_backend.capabilities.sample_rate = 10000
        registry.register("unit_test_self", lambda s, r: decoded, lambda r: made)
        with patch("core.hal.current_backend", return_value=fake_backend):
            events, samples = registry.selftest("unit_test_self")
        self.assertEqual(samples, made)
        self.assertEqual(events, decoded)


class PrintEventsTest(unittest.TestCase):
    def test_empty_events_message(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            registry.print_events([])
        self.assertIn("(no events decoded)", buf.getvalue())

    def test_event_line_contains_fields(self):
        events = [{"t": 0.001, "ch": 2, "type": "data", "text": "hello"}]
        buf = io.StringIO()
        with redirect_stdout(buf):
            registry.print_events(events)
        out = buf.getvalue()
        self.assertIn("1.000", out)
        self.assertIn("D2", out)
        self.assertIn("data", out)
        self.assertIn("hello", out)

    def test_custom_channel_name(self):
        events = [{"t": 0.0, "ch": 0, "type": "edge", "text": "x"}]
        buf = io.StringIO()
        with redirect_stdout(buf):
            registry.print_events(events, ch_name=7)
        self.assertIn("D7", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
