# -*- coding: utf-8 -*-
"""Tests for theme identifiers, tokens, and persisted theme config."""
import unittest

from core import theme
from tests._isolation import IsolatedConfig


class NormalizeTest(unittest.TestCase):
    def test_known_themes_pass_through(self):
        self.assertEqual(theme.normalize("dark"), "dark")
        self.assertEqual(theme.normalize("light"), "light")

    def test_unknown_theme_uses_default(self):
        self.assertEqual(theme.normalize("purple"), theme.DEFAULT_THEME)
        self.assertEqual(theme.normalize(None), theme.DEFAULT_THEME)


class ThemeConfigTest(IsolatedConfig, unittest.TestCase):
    def test_default_theme_when_unset(self):
        self.assertEqual(theme.get_theme(), "dark")

    def test_set_and_get_theme(self):
        theme.set_theme("light")
        self.assertEqual(theme.get_theme(), "light")

    def test_invalid_theme_persists_fallback(self):
        stored = theme.set_theme("neon")
        self.assertEqual(stored, "dark")
        self.assertEqual(theme.get_theme(), "dark")

    def test_tokens_return_theme_dict(self):
        dark = theme.tokens("dark")
        self.assertEqual(dark["window"], theme.THEMES["dark"]["window"])
        self.assertIn("channels", dark)
        self.assertEqual(len(dark["channels"]), 8)

    def test_tokens_default_to_saved_theme(self):
        theme.set_theme("light")
        self.assertEqual(theme.tokens()["window"],
                         theme.THEMES["light"]["window"])


if __name__ == "__main__":
    unittest.main()
