# -*- coding: utf-8 -*-
"""Tests for the gettext wrapper and runtime language switching."""
import unittest

from core import i18n


class LanguageTest(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("en")

    def test_default_language_is_english(self):
        self.assertEqual(i18n.get_language(), "en")

    def test_english_returns_msgid_unchanged(self):
        i18n.set_language("en")
        self.assertEqual(i18n._("Some source text"), "Some source text")

    def test_unknown_code_falls_back_to_english(self):
        i18n.set_language("xx_XX")
        self.assertEqual(i18n.get_language(), "en")

    def test_supported_language_is_set(self):
        i18n.set_language("fr")
        self.assertEqual(i18n.get_language(), "fr")

    def test_unknown_msgid_returns_source(self):
        i18n.set_language("de")
        self.assertEqual(i18n._("A string that is definitely not translated"),
                         "A string that is definitely not translated")

    def test_supported_language_codes(self):
        codes = {c for c, _name in i18n.SUPPORTED_LANGUAGES}
        self.assertEqual(codes, {"en", "fr", "de", "zh_CN", "zh_TW"})


if __name__ == "__main__":
    unittest.main()
