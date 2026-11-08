# -*- coding: utf-8 -*-
"""Device configuration entry: show the current backend's real
capabilities and select another registered backend.

Every displayed value (channel count, names, byte mode, sample rate)
comes strictly from the selected backend's declared capabilities; the
selectable options are the registered real backends, so no unsupported
combination can be chosen.
"""
import core
from core.i18n import _


def show_info(backend):
    """Print the current backend's declared capabilities."""
    caps = backend.capabilities
    print(_("===== Device configuration ====="))
    print(_("Current device: {name}").format(name=caps.display_name))
    print(_("  Channels: {count} ({names})").format(
        count=caps.channel_count, names=", ".join(caps.channel_names)))
    print(_("  Byte mode: {unit} byte(s) per sample").format(unit=caps.unit_size))
    print(_("  Sample rate: {rate} Hz").format(rate=caps.sample_rate))


def choose_backend():
    """List the registered backends and return the chosen one; Enter keeps
the current backend, q returns None."""
    current = core.current_backend()
    print(_("===== Available devices ====="))
    backends = core.list_backends()
    for i, backend in enumerate(backends):
        marker = "  <- current" if backend.id == current.id else ""
        print(f"  [{i}] {backend.display_name}{marker}")
    sel = input(_("Choose device number (Enter keeps the current device, q quits): ")).strip()
    if sel.lower() == "q":
        return None
    if sel == "":
        return current
    try:
        return backends[int(sel)]
    except (ValueError, IndexError):
        print(_("Invalid number"))
        return choose_backend()


def run():
    """Device menu entry: show the capabilities, allow selection, return."""
    show_info(core.current_backend())
    backend = choose_backend()
    if backend is None:
        return
    core.select_backend(backend.id)
    print(_("Device selected: {name}").format(name=backend.display_name))
