# -*- coding: utf-8 -*-
"""Console encoding setup for the CLI.

The first-run language picker prints native names such as "Français". The
legacy Windows OEM code page (GBK on a Chinese system) cannot encode the
character in that name, so a plain print would crash before the user can
choose a language. On Windows the attached console is switched to the UTF-8
code page, and the standard streams are reconfigured to UTF-8 so every
supported language renders. Every step is defensive and never blocks
startup; the GUI has no console and does not use this module.
"""
import sys

UTF8_CODE_PAGE = 65001


def _reconfigure_stream(stream):
    """Point a standard stream at UTF-8 when the runtime allows it."""
    reconfigure = getattr(stream, "reconfigure", None)
    if stream is not None and callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def enable_utf8_console():
    """Make console output and input Unicode-safe.

    Safe to call on every platform and from a frozen executable. On a real
    Windows console the code page is changed first; when the streams are
    redirected to a pipe there is no console to change, but reconfiguring the
    streams still makes the emitted bytes UTF-8.
    """
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(UTF8_CODE_PAGE)
            kernel32.SetConsoleCP(UTF8_CODE_PAGE)
        except Exception:
            # The stream reconfiguration below still prevents an encoding crash.
            pass
    _reconfigure_stream(sys.stdout)
    _reconfigure_stream(sys.stderr)
    _reconfigure_stream(sys.stdin)
