# -*- coding: utf-8 -*-
"""Single-channel measurement: frequency, period, pulse widths, duty, jitter."""

SAMPLE_RATE = 10000
DT          = 1.0 / SAMPLE_RATE


def measure(bits):
    """对单通道 0/1 序列测量，返回指标 dict，信号不足返回 None"""
    rising, falling = [], []
    for i in range(1, len(bits)):
        if bits[i-1] == 0 and bits[i] == 1: rising.append(i)
        if bits[i-1] == 1 and bits[i] == 0: falling.append(i)
    if len(rising) < 2:
        return None
    periods = [rising[i+1] - rising[i] for i in range(len(rising)-1)]
    per_avg = sum(periods) / len(periods)
    per_min = min(periods) * DT
    per_max = max(periods) * DT
    period_s = per_avg * DT
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
    high_s = (sum(highs) / len(highs)) * DT
    low_s  = period_s - high_s
    duty   = high_s / period_s * 100.0
    return {"freq": freq, "period": period_s, "high": high_s, "low": low_s,
            "duty": duty, "pmin": per_min, "pmax": per_max, "cycles": len(periods)}
