# -*- coding: utf-8 -*-
"""Sample-rate and capture-mode selection flows for the CLI settings
submenu.

Every listed option comes strictly from the current backend's declared
capabilities, the current effective value is shown from
``core.session``, and a chosen value is validated by
``core.session.save_sample_rate`` / ``save_capture_mode`` before it is
written. An invalid entry re-prompts; a saved choice is confirmed with
a translated message; the restore flow removes both saved keys and
prints the resulting effective values. This module never imports Qt.
"""
import core
from core.files import format_rate
from core.i18n import _


def choose_rate():
    """List the supported rates, show the current effective rate, read a
    choice, and save it."""
    caps = core.current_backend().capabilities
    print(_("===== Sample rate ====="))
    while True:
        current = core.session.effective_sample_rate()
        print(_("Current sample rate: {rate} Hz").format(rate=current))
        for index, rate in enumerate(caps.supported_rates):
            print("  [{}] {}".format(index, format_rate(rate)))
        sel = input(_("Choose sample rate number (Enter keeps the current rate, q quits): ")).strip()
        if sel.lower() == "q" or sel == "":
            return
        try:
            rate = caps.supported_rates[int(sel)]
        except (ValueError, IndexError):
            print(_("Invalid choice"))
            continue
        try:
            core.session.save_sample_rate(rate)
        except ValueError as exc:
            print(exc)
            continue
        print(_("Sample rate saved: {rate} Hz").format(rate=rate))
        return


def choose_mode():
    """List the supported modes, show the current effective mode, read a
    choice, and save it."""
    caps = core.current_backend().capabilities
    print(_("===== Capture mode ====="))
    while True:
        current = core.session.effective_capture_mode()
        print(_("Current capture mode: {mode}").format(
            mode=core.session.mode_label(current)))
        for index, mode in enumerate(caps.supported_modes):
            print("  [{}] {}".format(index, core.session.mode_label(mode)))
        sel = input(_("Choose capture mode number (Enter keeps the current mode, q quits): ")).strip()
        if sel.lower() == "q" or sel == "":
            return
        try:
            mode = caps.supported_modes[int(sel)]
        except (ValueError, IndexError):
            print(_("Invalid choice"))
            continue
        try:
            core.session.save_capture_mode(mode)
        except ValueError as exc:
            print(exc)
            continue
        print(_("Capture mode saved: {mode}").format(
            mode=core.session.mode_label(mode)))
        return


def restore_defaults():
    """Remove the saved rate and mode keys and print the resulting
    effective values."""
    core.session.reset_to_defaults()
    rate = core.session.effective_sample_rate()
    mode = core.session.effective_capture_mode()
    print(_("Defaults restored: sample rate {rate} Hz, capture mode {mode}."
            ).format(rate=rate, mode=core.session.mode_label(mode)))
