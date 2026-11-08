# -*- coding: utf-8 -*-
"""Version comparison and the per-package "last seen" marker.

The CLI and the GUI keep independent version numbers and their own seen
marker in the shared config file. A brand-new user never sees the release
notes: the first run records the current version as seen and shows nothing.
The caller renders the notes and calls ``mark_seen`` only after they have
actually been shown, so the prompt fires exactly once per version.
"""
from core.config import get as config_get, set as config_set

from .release_notes import RELEASE_NOTES

_SEEN_KEYS = {
    "cli": "cli_seen_version",
    "gui": "gui_seen_version",
}


def seen_key(kind):
    """Return the config key for a package: ``cli_seen_version`` or
    ``gui_seen_version``, where ``kind`` is ``"cli"`` or ``"gui"``."""
    return _SEEN_KEYS[kind]


def last_seen(kind):
    """Return the saved version for the package, or ``None``."""
    return config_get(seen_key(kind))


def pending_notes(kind, version):
    """Return the English note lines to show for ``version``.

    First run (nothing saved): save ``version`` as seen and return an empty
    list, so a brand-new user sees no prompt. An unchanged version returns
    an empty list. A changed version returns the English note lines for
    ``version`` from ``RELEASE_NOTES`` (empty when the version is unknown).
    """
    saved = last_seen(kind)
    if saved is None:
        mark_seen(kind, version)
        return []
    if saved == version:
        return []
    return list(RELEASE_NOTES.get(version, []))


def mark_seen(kind, version):
    """Persist ``version`` as the seen version for the package."""
    config_set(seen_key(kind), version)
