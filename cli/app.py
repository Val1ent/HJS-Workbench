# -*- coding: utf-8 -*-
"""Main menu loop and navigation for the unified CLI."""
from core import updates
from core.config import get as config_get, set as config_set
from core.i18n import SUPPORTED_LANGUAGES, _, get_language, set_language

from . import console  # noqa: F401  (helpers are used by every sub-flow)
from . import capture_flow, device_flow, guide_flow, live_analyzer
from . import live_measure, offline_flow, protocol_flow, signal_flow
from .version import __version__


def menu_items():
    """Return the main menu lines in the active language."""
    return [
        _("1. Capture to file"),
        _("2. Live analyzer"),
        _("3. Live measurement"),
        _("4. Protocol decoder"),
        _("5. Signal generator"),
        _("6. Offline tools"),
        _("7. Language"),
        _("8. Device"),
        _("9. Quick start guide"),
        _("0. Quit"),
    ]


def show_menu():
    print("=" * 64)
    print(f"HJS-Workbench - Unified CLI v{__version__}")
    print("=" * 64)
    for line in menu_items():
        print(line)


def choose_language(prompt):
    """Show the native-name language list and return the chosen code or None.

    The list and its prompts use the native names from SUPPORTED_LANGUAGES
    and are not translated, so they work before any language is chosen.
    """
    print("=" * 40)
    for i, (code, name) in enumerate(SUPPORTED_LANGUAGES, 1):
        marker = "  <- current" if code == get_language() else ""
        print(f"  [{i}] {name}{marker}")
    raw = input(prompt).strip()
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(SUPPORTED_LANGUAGES):
            return SUPPORTED_LANGUAGES[idx][0]
    return None


def apply_language(code):
    """Save and apply the language choice."""
    config_set("language", code)
    set_language(code)


def first_run_language():
    """Apply the saved language, or ask once on the first run.

    The choice is saved so the picker does not appear on the next launch.
    """
    saved = config_get("language")
    if saved:
        set_language(saved)
        return
    code = None
    while code is None:
        code = choose_language("Select language: ")
        if code is None:
            print("Invalid choice")
    apply_language(code)


def change_language():
    """Menu entry: pick a language, save and apply it, return to the menu."""
    code = choose_language("Select language: ")
    if code is None:
        print(_("Invalid choice"))
        return
    apply_language(code)
    print(_("Language changed."))


def show_release_notes():
    """Print the translated notes once after an update, then mark them seen.

    A separator, the translated "What's new" heading with the version, and
    the translated note lines are printed; Enter continues into the normal
    menu. First runs and unchanged versions print nothing. The marker is
    written only after the notes have been shown.
    """
    notes = updates.pending_notes("cli", __version__)
    if not notes:
        return
    print("=" * 64)
    print(_("What's new"))
    print(_("Version {version}").format(version=__version__))
    for line in notes:
        print(_(line))
    input(_("Press Enter to continue"))
    updates.mark_seen("cli", __version__)


def main():
    """Main menu loop: every sub-flow returns here; only choice 0 exits."""
    first_run_language()
    show_release_notes()
    while True:
        show_menu()
        sel = input(_("Select: ")).strip()
        if sel == "1":
            capture_flow.run()
        elif sel == "2":
            live_analyzer.run()
        elif sel == "3":
            live_measure.run()
        elif sel == "4":
            protocol_flow.run()
        elif sel == "5":
            signal_flow.run()
        elif sel == "6":
            offline_flow.run()
        elif sel == "7":
            change_language()
        elif sel == "8":
            device_flow.run()
        elif sel == "9":
            guide_flow.run()
        elif sel == "0":
            print(_("Exited."))
            return
        else:
            print(_("Invalid choice"))
