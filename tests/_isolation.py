# -*- coding: utf-8 -*-
"""Helpers to isolate persistent configuration into a temporary directory.

core.config resolves its directory from APPDATA on Windows and from
XDG_CONFIG_HOME on Linux, so both variables are redirected; otherwise the
isolation works on Windows but silently falls back to the real user config
on Linux and the test classes pollute each other.
"""
import os
import tempfile


class IsolatedConfig:
    """Mixin pointing the config location at a temp directory for one test."""

    def setUp(self):
        self._old_env = {
            key: os.environ.get(key)
            for key in ("APPDATA", "XDG_CONFIG_HOME")
        }
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["APPDATA"] = self.tmp.name
        os.environ["XDG_CONFIG_HOME"] = self.tmp.name

    def tearDown(self):
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()
