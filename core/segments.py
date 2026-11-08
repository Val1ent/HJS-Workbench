# -*- coding: utf-8 -*-
"""Edge detection, pulse segmentation, and test waveform building."""
from .model import set_channel


def edges_of(bits):
    """Return the list of level transition edges [(index, new_level), ...]
(including the initial level)."""
    out = []
    if not bits:
        return out
    out.append((0, bits[0]))
    for i in range(1, len(bits)):
        if bits[i] != bits[i - 1]:
            out.append((i, bits[i]))
    return out


def pulse_widths(bits, rate):
    """Split a single-channel sequence into constant-level segments:
[(start_index, level, width_seconds), ...]."""
    dt = 1.0 / rate
    segs = []
    start = 0
    for i in range(1, len(bits)):
        if bits[i] != bits[start]:
            segs.append((start, bits[start], (i - start) * dt))
            start = i
    segs.append((start, bits[start], (len(bits) - start) * dt))
    return segs


def build_wave(ch, pulses, rate, n, idle=1):
    """
    Generate an 8-channel test waveform (the other channels stay 0).
    pulses: [(start_seconds, level, duration_seconds), ...] in time
    order; idle is the idle level.
    """
    samples = [0] * n
    # Fill the idle level first
    for i in range(n):
        set_channel(samples, i, ch, idle)
    for (t0, lvl, dur) in pulses:
        a = int(round(t0 * rate))
        b = int(round((t0 + dur) * rate))
        for i in range(max(0, a), min(n, b)):
            set_channel(samples, i, ch, lvl)
    return samples
