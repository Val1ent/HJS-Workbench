# -*- coding: utf-8 -*-
"""Tests for event construction and merging."""
import unittest

from core.events import event, merge_events


class EventTest(unittest.TestCase):
    def test_event_fields_and_types(self):
        e = event(1.5, 2, "ALERT", "value=3")
        self.assertEqual(e["t"], 1.5)
        self.assertEqual(e["ch"], 2)
        self.assertEqual(e["type"], "ALERT")
        self.assertEqual(e["text"], "value=3")
        self.assertIsInstance(e["t"], float)
        self.assertIsInstance(e["ch"], int)


class MergeEventsTest(unittest.TestCase):
    def test_merge_sorts_by_time(self):
        a = [event(3, 0, "X", "x"), event(1, 0, "X", "x")]
        b = [event(2, 1, "Y", "y")]
        out = merge_events(a, b)
        self.assertEqual([e["t"] for e in out], [1, 2, 3])

    def test_merge_keeps_all_entries(self):
        a = [event(0, 0, "X", "x")]
        b = [event(1, 1, "Y", "y"), event(2, 2, "Z", "z")]
        self.assertEqual(len(merge_events(a, b)), 3)


if __name__ == "__main__":
    unittest.main()
