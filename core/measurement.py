# -*- coding: utf-8 -*-
"""Single-channel measurement: frequency, period, pulse widths, duty, jitter."""

from .hal import current_backend


def measure(bits, rate=None):
    """Measure a single-channel 0/1 sequence; return a metrics dict, or None
when the signal is insufficient.

``rate`` is the sample rate in Hz; when omitted, the current device
backend's sample rate is used.
"""
    if rate is None:
        rate = current_backend().capabilities.sample_rate
    dt = 1.0 / rate
    rising, falling = [], []
    for i in range(1, len(bits)):
        if bits[i-1] == 0 and bits[i] == 1: rising.append(i)
        if bits[i-1] == 1 and bits[i] == 0: falling.append(i)
    if len(rising) < 2:
        return None
    periods = [rising[i+1] - rising[i] for i in range(len(rising)-1)]
    per_avg = sum(periods) / len(periods)
    per_min = min(periods) * dt
    per_max = max(periods) * dt
    period_s = per_avg * dt
    freq = 1.0 / period_s

    highs = []
    fi = 0
    for r in rising:
        while fi < len(falling) and falling[fi] <= r:
            fi += 1
        if fi < len(falling):
            highs.append(falling[fi] - r)
    if not highs:
        return None
    high_s = (sum(highs) / len(highs)) * dt
    low_s  = period_s - high_s
    duty   = high_s / period_s * 100.0
    return {"freq": freq, "period": period_s, "high": high_s, "low": low_s,
            "duty": duty, "pmin": per_min, "pmax": per_max, "cycles": len(periods)}
