# -*- coding: utf-8 -*-
"""Thin wrappers over the current device backend.

Port enumeration and serial acquisition delegate entirely to the
currently selected backend; no board parameters or board-specific
text live here. When the caller supplies a sample rate or a capture
mode, the value is validated through the backend and the matching
firmware command is sent before collecting; the rate returned with the
data is the rate that was actually applied, never a substituted value.
"""
import time

from .hal import current_backend
from .hal.burst import download_burst
from .i18n import _


def list_serial_ports():
    """Return the list of available serial ports [(device name, description), ...]."""
    return current_backend().list_ports()


def _require_command(conn, name, backend_name):
    """Return the connection's command method ``name`` or raise.

    An explicit request must never be silently ignored, so a backend
    without the matching firmware control raises a clear error.
    """
    method = getattr(conn, name, None)
    if method is None:
        raise ValueError(
            _("The {name} backend does not support the {command} command."
              ).format(name=backend_name, command=name))
    return method


def _apply_rate(conn, backend, rate):
    """Validate ``rate`` and send the ``R<rate>LF`` command."""
    backend.validate_config(sample_rate=rate)
    _require_command(conn, "set_sample_rate", backend.display_name)(rate)


def _apply_mode(conn, backend, mode):
    """Validate ``mode`` and send the matching ``M`` command."""
    backend.validate_config(mode=mode)
    _require_command(conn, "set_mode", backend.display_name)(mode)


def acquire_serial(port, n_points, timeout=8.0, sample_rate=None, mode=None):
    """Acquire exactly n_points bytes in one shot from the given serial port.

    Opens the port through the current backend (asserting its control
    lines, waiting, and flushing the input buffer exactly as the backend
    declares), then polls non-blocking until n_points bytes have been
    received or the timeout expires; the port is closed when finished
    (including on error). When the timeout expires before enough bytes
    arrive, the backend raises its troubleshooting text.

    ``sample_rate`` selects a rate from the backend's supported rates:
    it is validated first, then the ``R<rate>LF`` command is sent before
    collecting. ``mode`` selects a capture mode (``realtime``/``burst``):
    it is validated first, then the matching ``M`` command is sent.
    With neither argument the current behaviour is unchanged and the
    backend default rate is returned. The return value is always the
    rate actually applied together with the samples.
    """
    backend = current_backend()
    if sample_rate is not None:
        backend.validate_config(sample_rate=sample_rate)
    if mode is not None:
        backend.validate_config(mode=mode)
    conn = backend.connect(port)
    try:
        if sample_rate is not None:
            _apply_rate(conn, backend, sample_rate)
        if mode is not None:
            _apply_mode(conn, backend, mode)
        samples = conn.acquire(n_points, timeout)
    except Exception:
        conn.close()
        raise
    applied_rate = (backend.capabilities.sample_rate if sample_rate is None
                    else sample_rate)
    return applied_rate, samples


def acquire_burst(port, sample_rate=None, timeout=10.0, wait_time=None):
    """Record and upload one full burst; return ``(rate, samples)``.

    Drives the burst flow over the current backend: select the burst
    mode and the sample rate, start the recording, wait for the buffer
    to fill (``wait_time`` seconds; when omitted it is derived from the
    declared burst capacity and the applied rate), then download the
    upload with the burst helper and return the header rate with the
    samples. On any failure the burst is cancelled and a clear error is
    raised; the connection is closed in every case.
    """
    backend = current_backend()
    caps = backend.capabilities
    if caps.burst_capacity <= 0:
        raise ValueError(
            _("The {name} backend does not support burst capture."
              ).format(name=caps.display_name))
    rate = caps.sample_rate if sample_rate is None else sample_rate
    backend.validate_config(sample_rate=rate, mode="burst")
    conn = backend.connect(port)
    try:
        _apply_rate(conn, backend, rate)
        _apply_mode(conn, backend, "burst")
        _require_command(conn, "start_burst", caps.display_name)()
        if wait_time is None:
            wait_time = caps.burst_capacity / float(rate) + 0.25
        time.sleep(wait_time)
        result = download_burst(conn, timeout)
    except Exception:
        try:
            cancel = getattr(conn, "cancel_burst", None)
            if cancel is not None:
                cancel()
        except Exception:
            pass
        conn.close()
        raise
    conn.close()
    return result
