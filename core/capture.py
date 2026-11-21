# -*- coding: utf-8 -*-
"""Thin wrappers over the current device backend.

Port enumeration and serial acquisition delegate entirely to the
currently selected backend; no board parameters or board-specific
text live here. When the caller supplies a sample rate or a capture
mode, the value is validated through the backend and the matching
firmware command is sent before collecting; the rate returned with the
data is the rate that was actually applied, never a substituted value.

Pattern playback (``playback_pattern``) loads a level sequence into the
firmware pattern buffer, replays it on the real GPO pins, and reads the
real capture back over the same signal connection; it never fabricates
samples.
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


PATTERN_PLAYBACK_RATE = 10000

# Firmware capture block: the sampling DMA sends complete 1000-byte
# blocks (CAP_BLOCK_LEN in firmware/src/Common/dma_capture.c). When K
# lands in the middle of a block, up to one whole block of pre-K data
# arrives before the new waveform, so the default window margin must
# absorb one complete block on each side.
PATTERN_CAPTURE_BLOCK = 1000


def _poll_bytes(conn, need, timeout):
    """Poll non-blocking reads until ``need`` bytes arrive or the timeout.

    ``read_blocking`` repeatedly reconfigures the port timeout and has
    been shown to drop bytes on the pattern path, so this loop only uses
    ``read_available``; a partial read is returned when the deadline
    expires first and nothing is fabricated.
    """
    buf = bytearray()
    deadline = time.monotonic() + timeout
    while len(buf) < need and time.monotonic() < deadline:
        chunk = conn.read_available()
        if chunk:
            buf.extend(chunk[:need - len(buf)])
        else:
            time.sleep(0.005)
    return bytes(buf)


def playback_pattern(port, cells, margin=PATTERN_CAPTURE_BLOCK, timeout=20.0):
    """Load a level sequence, play it, and return the real capture.

    Every cell is masked to the six GPO bits (0x3F), the length is
    bounded to the firmware pattern buffer, and one long signal-baud
    connection carries the whole flow (load, flush, play, read, stop) so
    the capture starts before the waveform head is missed. ``K`` is
    written separately from the pattern bytes, and ``L`` is sent on the
    error path as well. The default margin equals one capture block
    (``PATTERN_CAPTURE_BLOCK``): even when ``K`` lands on the worst
    block boundary, where up to one whole block of pre-K data precedes
    the new waveform, the complete real waveform still falls inside the
    read window. Returns ``(rate, samples)`` where ``rate`` is always
    10000 and ``samples`` are the bytes actually read back from the
    real device; the list is shorter than ``need`` when the timeout
    expired first. The connection is closed in every case.
    """
    from .hal import pattern
    data = bytes(int(c) & 0x3F for c in cells)
    if len(data) < 1 or len(data) > pattern.PATTERN_MAX:
        raise ValueError(
            _("Pattern length must be between {min} and {max} cells."
              ).format(min=1, max=pattern.PATTERN_MAX))
    backend = current_backend()
    conn = backend.connect(port, baud=backend.capabilities.signal_baud)
    try:
        pattern.load_pattern(conn, data)
        conn.reset_input()
        pattern.play(conn)
        need = len(data) + 2 * margin
        captured = _poll_bytes(conn, need, timeout)
        pattern.stop(conn)
    except Exception:
        try:
            pattern.stop(conn)
        except Exception:
            pass
        conn.close()
        raise
    conn.close()
    return PATTERN_PLAYBACK_RATE, list(captured)


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
