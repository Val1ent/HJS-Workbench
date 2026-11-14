# -*- coding: utf-8 -*-
"""Tests for version comparison and the per-package seen marker."""
import unittest

from core import updates
from tests._isolation import IsolatedConfig


class SeenKeyTest(unittest.TestCase):
    def test_seen_keys(self):
        self.assertEqual(updates.seen_key("cli"), "cli_seen_version")
        self.assertEqual(updates.seen_key("gui"), "gui_seen_version")

    def test_unknown_kind_raises(self):
        with self.assertRaises(KeyError):
            updates.seen_key("web")


class PendingNotesTest(IsolatedConfig, unittest.TestCase):
    def test_last_seen_empty_on_first_run(self):
        self.assertIsNone(updates.last_seen("cli"))

    def test_first_run_shows_no_notes_and_marks_seen(self):
        notes = updates.pending_notes("cli", "0.6.2")
        self.assertEqual(notes, [])
        self.assertEqual(updates.last_seen("cli"), "0.6.2")

    def test_same_version_shows_no_notes(self):
        updates.mark_seen("gui", "0.6.2")
        self.assertEqual(updates.pending_notes("gui", "0.6.2"), [])

    def test_changed_version_returns_notes(self):
        updates.mark_seen("cli", "0.5.0")
        notes = updates.pending_notes("cli", "0.6.2")
        self.assertEqual(notes, list(updates.RELEASE_NOTES["0.6.2"]))
        self.assertTrue(notes)

    def test_unknown_version_returns_empty(self):
        updates.mark_seen("cli", "0.5.0")
        self.assertEqual(updates.pending_notes("cli", "9.9.9"), [])

    def test_cli_and_gui_markers_are_independent(self):
        updates.pending_notes("cli", "0.6.2")
        self.assertIsNone(updates.last_seen("gui"))


if __name__ == "__main__":
    unittest.main()
