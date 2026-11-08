# -*- coding: utf-8 -*-
"""Cross-platform terminal helpers shared by every CLI flow."""
import os

import core
from core.hal import BackendConnectionError, current_backend
from core.i18n import _


def clear_screen():
    """Clear the screen: cls on Windows, clear elsewhere."""
    os.system("cls" if os.name == "nt" else "clear")


def open_serial(port, baud=None):
    """Open the current backend's device connection on the given port.

    The backend prepares the connection (asserting its control lines,
    waiting, flushing the input buffer) and returns the DeviceConnection.
    ``baud`` defaults to the backend's data baud; pass a backend-declared
    rate (for example its signal baud) when a flow needs it.
    """
    backend = current_backend()
    if baud is None:
        return backend.connect(port)
    return backend.connect(port, baud=baud)


def read_int(prompt, default=None):
    """Read an integer: Enter returns default, invalid input returns None
(no ValueError)."""
    raw = input(prompt).strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return None


def choose_port():
    """List serial ports and let the user pick one; Enter rescans, q returns
None, other invalid input re-prompts."""
    while True:
        ports = core.list_serial_ports()
        if not ports:
            print(_("No serial ports found, check the USB connection"))
        print(_("===== Detected serial ports ====="))
        for i, p in enumerate(ports):
            print(f"  [{i}]  {p[0]}   {p[1]}")
        sel = input(_("Choose the data port number (Enter rescans, q quits): ")).strip()
        if sel.lower() == "q":
            return None
        if sel == "":
            continue
        try:
            return ports[int(sel)][0]
        except (ValueError, IndexError):
            print(_("Invalid number"))


def choose_decoder():
    """List decoder names and descriptions from DECKS and return the chosen
name; q returns None."""
    while True:
        names = list(core.DECKS.keys())
        print(_("===== Available protocol decoders ====="))
        for i, n in enumerate(names):
            print(f"  [{i}]  {n:<10} {core.DECKS[n]['desc']}")
        sel = input(_("Choose decoder number: ")).strip()
        if sel.lower() == "q":
            return None
        try:
            return names[int(sel)]
        except (ValueError, IndexError):
            print(_("Invalid number"))


def pause():
    """Wait for Enter before returning to the menu."""
    input(_("\nPress Enter to return to the menu..."))
