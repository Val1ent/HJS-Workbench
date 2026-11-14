# -*- coding: utf-8 -*-
"""Theme identifiers, color tokens, and config helpers (plain data only).

The core never imports a GUI toolkit: this module is pure dictionaries
and config access, so the CLI (which has no graphical surface) keeps no
theme state of its own. The GUI owns every style-sheet and plot-styling
concern and reads the tokens from here.

Two fixed themes exist: ``dark`` (the default) and ``light``. The active
identifier is persisted in the user config under ``theme``. A missing or
unknown identifier always falls back to the default and never raises.
"""

from .config import get as _config_get
from .config import set as _config_set

DEFAULT_THEME = "dark"
CONFIG_KEY = "theme"

# Ordered identifier list; the order also defines the presentation order
# of future theme pickers.
THEME_IDS = ("dark", "light")

# Display labels for the theme pickers. These are static msgids: the GUI
# passes them through the translation layer, so this module stays free of
# any toolkit and any language-specific text.
THEME_LABELS = {
    "dark": "Dark",
    "light": "Light",
}

THEMES = {
    "dark": {
        "window": "#1e1e1e",
        "base": "#2b2b2b",
        "alternate": "#333333",
        "text": "#e6e6e6",
        "muted": "#a0a0a0",
        "accent": "#42d4f4",
        "accent_text": "#101418",
        "button": "#3a3a3a",
        "border": "#4a4a4a",
        "plot_background": "#141414",
        "plot_foreground": "#d0d0d0",
        "grid": "#555555",
        "grid_alpha": 0.3,
        "channels": [
            "#e6194b", "#3cb44b", "#4363d8", "#f58231",
            "#911eb4", "#42d4f4", "#f032e6", "#bfef45",
        ],
    },
    "light": {
        "window": "#f5f5f5",
        "base": "#ffffff",
        "alternate": "#ececec",
        "text": "#1a1a1a",
        "muted": "#555555",
        "accent": "#0288d1",
        "accent_text": "#ffffff",
        "button": "#e8e8e8",
        "border": "#c8c8c8",
        "plot_background": "#ffffff",
        "plot_foreground": "#333333",
        "grid": "#999999",
        "grid_alpha": 0.4,
        # Darker channel palette: the dark-theme colors wash out on white.
        "channels": [
            "#d62728", "#2ca02c", "#1f77b4", "#d35400",
            "#7d3c98", "#0e7c86", "#b03a8e", "#6b8e23",
        ],
    },
}


def normalize(theme_id):
    """Return ``theme_id`` when known, otherwise the default theme."""
    if theme_id in THEMES:
        return theme_id
    return DEFAULT_THEME


def tokens(theme_id=None):
    """Return the color token dict for a theme (the saved one by default)."""
    return THEMES[normalize(theme_id if theme_id is not None
                            else get_theme())]


def get_theme():
    """Read the saved theme identifier; missing/unknown values fall back
    to the default and never raise."""
    return normalize(_config_get(CONFIG_KEY))


def set_theme(theme_id):
    """Validate the identifier, persist it, and return the stored value.

    An unknown identifier falls back to the default instead of raising,
    and the fallback value is what gets persisted.
    """
    stored = normalize(theme_id)
    _config_set(CONFIG_KEY, stored)
    return stored
