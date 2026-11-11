# -*- coding: utf-8 -*-
"""Saved sample-rate and capture-mode policy shared by the CLI and the GUI.

Both front-ends persist the chosen sample rate and capture mode through
the same keys in ``core.config``. This module is the single place that
reads those keys, validates them against the current backend's real
capabilities, and writes them back:

- ``effective_sample_rate`` and ``effective_capture_mode`` return the
  saved value only when the backend still supports it; unsupported or
  stale values fall back to the declared backend default and are never
  passed into a capture.
- ``save_sample_rate`` and ``save_capture_mode`` validate first and
  write nothing when the value is outside the backend capabilities.
- ``reset_to_defaults`` removes both keys so the backend defaults
  apply again.

The module never imports the serial library and never opens a device;
it only reads the backend's declared capabilities.
"""
from . import config
from .hal import current_backend
from .i18n import _

SAMPLE_RATE_KEY = "sample_rate"
CAPTURE_MODE_KEY = "capture_mode"

_MODE_LABELS = {"realtime": "Realtime", "burst": "Burst"}


def mode_label(mode):
    """Return the translated display label for a capture mode id.

    The known ids map to msgids translated through the active catalog;
    any other id is backend data and is returned unchanged.
    """
    return _(_MODE_LABELS.get(mode, str(mode)))


def effective_sample_rate():
    """Return the effective sample rate in Hz.

    The saved "sample_rate" is returned only when it is one of the
    current backend's supported rates; otherwise the backend default
    rate applies.
    """
    caps = current_backend().capabilities
    saved = config.get(SAMPLE_RATE_KEY)
    if saved in caps.supported_rates:
        return saved
    return caps.sample_rate


def effective_capture_mode():
    """Return the effective capture mode id.

    The saved "capture_mode" is returned only when it is one of the
    current backend's supported modes; otherwise the backend default
    mode applies.
    """
    caps = current_backend().capabilities
    saved = config.get(CAPTURE_MODE_KEY)
    if saved in caps.supported_modes:
        return saved
    return caps.default_mode


def save_sample_rate(rate):
    """Persist ``rate`` under "sample_rate".

    A rate outside the current backend's supported rates raises
    ValueError and nothing is written.
    """
    caps = current_backend().capabilities
    if rate not in caps.supported_rates:
        raise ValueError(
            _("Unsupported sample rate {rate} Hz for the {name} backend; "
              "supported rates: {rates} Hz").format(
                rate=rate, name=caps.display_name,
                rates=", ".join(str(r) for r in caps.supported_rates)))
    config.set(SAMPLE_RATE_KEY, rate)


def save_capture_mode(mode):
    """Persist ``mode`` under "capture_mode".

    A mode outside the current backend's supported modes raises
    ValueError and nothing is written.
    """
    caps = current_backend().capabilities
    if mode not in caps.supported_modes:
        raise ValueError(
            _("Unsupported capture mode {mode} for the {name} backend; "
              "supported modes: {modes}").format(
                mode=mode, name=caps.display_name,
                modes=", ".join(str(m) for m in caps.supported_modes)))
    config.set(CAPTURE_MODE_KEY, mode)


def reset_to_defaults():
    """Remove the saved rate and mode keys so the backend defaults apply."""
    data = config.load()
    for key in (SAMPLE_RATE_KEY, CAPTURE_MODE_KEY):
        data.pop(key, None)
    config.save(data)
