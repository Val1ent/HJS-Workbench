# -*- coding: utf-8 -*-
"""Persistent user configuration in a platform-standard location.

The config is a single JSON file:

- Windows: %APPDATA%\\HJS-Workbench\\config.json
- macOS:   ~/Library/Application Support/HJS-Workbench/config.json
- Linux:   ~/.config/HJS-Workbench/config.json

A missing file or key must not raise; it simply means "no choice yet".
The directory is resolved at call time so tests and packagers can point the
platform environment variables at an isolated location.
"""
import json
import os
import sys

APP_DIR_NAME = "HJS-Workbench"
FILE_NAME = "config.json"


def _config_dir():
    """Return the platform-specific config directory for this app."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        if not base:
            base = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        return os.path.join(base, APP_DIR_NAME)
    if sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~"), "Library", "Application Support",
            APP_DIR_NAME)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config")
    return os.path.join(base, APP_DIR_NAME)


def config_path():
    """Return the full path of the config file."""
    return os.path.join(_config_dir(), FILE_NAME)


def load():
    """Load the config as a dict; a missing file or bad JSON returns {}."""
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(data):
    """Write the dict to the config file; write failures are ignored."""
    try:
        os.makedirs(_config_dir(), exist_ok=True)
        with open(config_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def get(key, default=None):
    """Return the saved value for ``key`` or ``default``."""
    return load().get(key, default)


def set(key, value):
    """Store ``value`` under ``key`` and persist the config."""
    data = load()
    data[key] = value
    save(data)
