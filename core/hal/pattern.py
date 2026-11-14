# -*- coding: utf-8 -*-
"""Pattern playback loader for the CH32 board.

Sends a level sequence to the firmware pattern buffer over the command
channel. The firmware drives real GPO pins and the real capture path reads
the pins back; this module never returns sample data.
"""
import time

PATTERN_MAX = 8000
_CHUNK = 64


def load_pattern(conn, samples):
    """Store a level byte sequence in the firmware pattern buffer.

    The connection is kept open by the caller so the same connection can
    read the capture stream immediately after playback starts.
    """
    data = bytes(samples)
    if len(data) < 1 or len(data) > PATTERN_MAX:
        raise ValueError("pattern length must be 1..%d cells" % PATTERN_MAX)

    conn.write(b"W" + str(len(data)).encode("ascii") + b"\n")
    time.sleep(0.05)

    off = 0
    while off < len(data):
        chunk = data[off:off + _CHUNK]
        conn.write(chunk)
        off += len(chunk)
        time.sleep(0.005)

    time.sleep(0.1)
    return len(data)


def play(conn):
    """Start firmware playback of the loaded pattern."""
    conn.write(b"K")


def stop(conn):
    """Force every GPO low."""
    conn.write(b"L")
