# -*- coding: utf-8 -*-
"""Tests for unified resource location in normal and frozen runs."""
import os
import sys
import unittest
from unittest.mock import patch

from core import paths


class AppRootTest(unittest.TestCase):
    def test_normal_run_returns_repo_root(self):
        root = paths.app_root()
        self.assertTrue(os.path.isdir(os.path.join(root, "core")))

    def test_resource_path_joins_parts(self):
        joined = paths.resource_path("locales", "en")
        self.assertEqual(joined, os.path.join(paths.app_root(), "locales", "en"))

    def test_frozen_with_meipass(self):
        bundle_dir = os.path.abspath(os.path.join(os.sep, "tmp", "bundle"))
        with patch.object(sys, "frozen", True, create=True), \
                patch.object(sys, "_MEIPASS", bundle_dir, create=True):
            self.assertEqual(paths.app_root(), bundle_dir)

    def test_frozen_without_meipass_uses_executable_dir(self):
        exe = os.path.abspath(os.path.join(os.sep, "tmp", "app", "prog.exe"))
        with patch.object(sys, "frozen", True, create=True), \
                patch.object(sys, "executable", exe), \
                patch.object(sys, "_MEIPASS", None, create=True):
            self.assertEqual(paths.app_root(), os.path.dirname(exe))


if __name__ == "__main__":
    unittest.main()
