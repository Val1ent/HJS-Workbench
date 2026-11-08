# -*- coding: utf-8 -*-
"""Thin wrappers over the current device backend.

Port enumeration and one-shot serial acquisition delegate entirely to
the currently selected backend; no board parameters or board-specific
text live here. The sample rate returned with the data is the backend's
declared capability.
"""
from .hal import current_backend


def list_serial_ports():
    """Return the list of available serial ports [(device name, description), ...]."""
    return current_backend().list_ports()


def acquire_serial(port, n_points, timeout=8.0):
    """Acquire exactly n_points bytes in one shot from the given serial port.

    Opens the port through the current backend (asserting its control
    lines, waiting, and flushing the input buffer exactly as the backend
    declares), then polls non-blocking until n_points bytes have been
    received or the timeout expires; the port is closed when finished
    (including on error). When the timeout expires before enough bytes
    arrive, the backend raises its troubleshooting text.
    """
    backend = current_backend()
    conn = backend.connect(port)
    try:
        samples = conn.acquire(n_points, timeout)
    except Exception:
        conn.close()
        raise
    return backend.capabilities.sample_rate, samples
