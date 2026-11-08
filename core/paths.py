# -*- coding: utf-8 -*-
"""Unified resource location for normal and frozen (PyInstaller) runs.

``app_root()`` returns the directory that holds the bundled resources
(``locales/`` and ``examples/``):

- Frozen: ``sys._MEIPASS`` when present (PyInstaller sets it in both
  onefile and onedir bundles), otherwise the executable directory.
- Normal: the repository root, one level above the ``core`` package,
  matching the pre-packaging behavior.

``resource_path(*parts)`` joins path parts under that root. All resource
lookups go through this module so the same code works in development and
inside the packaged applications.
"""
import os
import sys


def app_root():
    """Return the directory that holds the bundled resources."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return meipass
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*parts):
    """Join ``parts`` under the application root."""
    return os.path.join(app_root(), *parts)
