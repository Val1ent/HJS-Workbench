# -*- coding: utf-8 -*-
"""Translation engine: a small GNU gettext wrapper with runtime switching.

The catalog domain is ``hjs_workbench`` and the compiled catalogs live in
the ``locales/`` directory under the application root (the repository root
in normal runs, the bundle root in frozen runs). English is the msgid
source and the fallback, so no English catalog exists.
"""
import gettext

from .paths import resource_path

DOMAIN = "hjs_workbench"
DEFAULT_LANGUAGE = "en"

# (code, native name) pairs. Native names are shown directly by the language
# pickers so they work before any language has been chosen.
SUPPORTED_LANGUAGES = [
    ("en", "English"),
    ("zh_CN", "简体中文"),
    ("zh_TW", "繁體中文"),
]

_LOCALE_DIR = resource_path("locales")

_translation = gettext.NullTranslations()
_language = DEFAULT_LANGUAGE


def locale_dir():
    """Return the directory that holds the compiled catalogs."""
    return _LOCALE_DIR


def set_language(code):
    """Install the translation for ``code``.

    English installs a NullTranslations; any other code loads the compiled
    catalog with ``fallback=True`` so a missing catalog never crashes.
    Unknown codes fall back to English.
    """
    global _translation, _language
    known = {c for c, _name in SUPPORTED_LANGUAGES}
    if code not in known:
        code = DEFAULT_LANGUAGE
    if code == DEFAULT_LANGUAGE:
        _translation = gettext.NullTranslations()
    else:
        _translation = gettext.translation(
            DOMAIN, localedir=_LOCALE_DIR, languages=[code], fallback=True)
    _language = code


def get_language():
    """Return the active language code."""
    return _language


def _(message):
    """Translate ``message`` through the active catalog."""
    return _translation.gettext(message)
