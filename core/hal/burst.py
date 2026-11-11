# -*- coding: utf-8 -*-
"""Burst upload receiver: read one recorded burst over an open connection.

After the ``T`` command the firmware sends one ASCII header line
``BURST,<length>,<rate>LF`` followed by exactly ``<length>`` raw recorded
bytes, split into chunks of at most 1000 bytes. This module downloads
that upload: it requests the transfer, locates the header line inside
the incoming byte stream (residual realtime bytes before the marker are
discarded), parses the exact byte count and rate, then reads exactly
that many raw bytes through blocking reads. No fixed chunk size is
assumed, short reads are never padded, and no byte of the body is ever
lost or discarded: body bytes that arrive together with the header line
are carried over into the sample buffer.
"""
import time

from ..i18n import _

_READ_TIMEOUT = 0.5


def download_burst(conn, timeout=10.0):
    """Request and receive a full burst upload; return ``(rate, samples)``.

    Steps: request the upload, locate and parse the ASCII header line
    ``BURST,<length>,<rate>`` inside the incoming byte stream (bytes
    before the marker are residual realtime data and are discarded),
    then read exactly ``length`` raw body bytes through blocking reads
    until satisfied or ``timeout`` expires, and return the parsed rate
    with the samples as a list of ints. A malformed header raises
    ``ValueError``; a timeout raises a readable error reporting the
    received versus expected byte count.
    """
    deadline = time.monotonic() + timeout
    conn.request_burst_upload()
    buf = bytearray()
    marker_pos = -1
    lf_pos = -1
    while (marker_pos < 0 or lf_pos < 0) and time.monotonic() < deadline:
        chunk = conn.read_blocking(4096, _READ_TIMEOUT)
        if not chunk:
            continue
        buf.extend(chunk)
        if marker_pos < 0:
            marker_pos = buf.find(b"BURST,")
        if marker_pos >= 0 and lf_pos < 0:
            lf_pos = buf.find(b"\n", marker_pos)
    if marker_pos < 0 or lf_pos < 0:
        raise RuntimeError(
            _("Burst upload timed out waiting for the BURST header line: "
              "received {got} bytes so far.").format(got=len(buf)))
    text = buf[marker_pos:lf_pos].decode("ascii", "replace").strip()
    if not text.startswith("BURST,"):
        raise ValueError(
            _("Malformed burst header from the device: {header!r}"
              ).format(header=text))
    parts = text.split(",")
    if len(parts) != 3:
        raise ValueError(
            _("Malformed burst header from the device: {header!r}"
              ).format(header=text))
    try:
        length = int(parts[1])
        rate = int(parts[2])
    except ValueError:
        raise ValueError(
            _("Malformed burst header from the device: {header!r}"
              ).format(header=text)) from None
    if length <= 0 or rate <= 0:
        raise ValueError(
            _("Malformed burst header from the device: {header!r}"
              ).format(header=text))
    data = bytearray(buf[lf_pos + 1:])
    while len(data) < length and time.monotonic() < deadline:
        chunk = conn.read_blocking(
            min(4096, length - len(data)), _READ_TIMEOUT)
        if chunk:
            data.extend(chunk)
    if len(data) < length:
        raise RuntimeError(
            _("Burst upload timed out: received {got} of {expected} bytes."
              ).format(got=len(data), expected=length))
    return rate, list(data)
