# -*- coding: utf-8 -*-
"""4-wire fan speed decoder (TACH falling-edge intervals -> RPM)."""
from ..events import event
from ..model import channel_bits
from ..registry import register

# ======================================================================
# 6. 4-wire fan speed (TACH 2 pulses per revolution, falling-edge
#    interval -> RPM)
# ======================================================================
def decode_fan(samples, rate, tach_ch=0, pulses_per_rev=2):
    """
    TACH outputs pulses_per_rev (default 2) pulses per revolution; the
    falling-edge interval = half a revolution.
    RPM = 60 / (interval_s * pulses per rev). A moving average is
    reported every 5 intervals, and an overall average/min/max summary
    at the end.
    """
    tach = channel_bits(samples, tach_ch)
    n = len(samples)
    dt = 1.0 / rate
    falls = [i for i in range(1, n) if tach[i - 1] == 1 and tach[i] == 0]
    events = []
    win = []
    for k in range(len(falls) - 1):
        per = (falls[k + 1] - falls[k]) * dt
        if not (0.0001 <= per <= 1.0):      # Skip implausible intervals
            continue
        win.append(per)
        if len(win) > 5:
            win.pop(0)
        if len(win) == 5:
            rpms = [60.0 / (p * pulses_per_rev) for p in win]
            events.append(event(falls[k] * dt, tach_ch, "FAN",
                                f"speed={sum(rpms) / len(rpms):.0f}RPM"))
    if win:
        rpms = [60.0 / (p * pulses_per_rev) for p in win]
        events.append(event((n - 1) * dt, tach_ch, "FAN_SUM",
            f"avg={sum(rpms) / len(rpms):.0f}RPM "
            f"min={min(rpms):.0f} max={max(rpms):.0f}"))
    events.sort(key=lambda e: e["t"])
    return events

def make_fan_test(rate):
    """3000 RPM fan: 2 pulses/rev -> 100 pulses/s -> 10 ms pulse period,
20 pulses total."""
    n = int(0.25 * rate)
    tach = [0] * n

    def put(arr, t0, t1, val):
        a = max(0, int(round(t0 * rate)))
        b = min(n, int(round(t1 * rate)))
        for i in range(a, b):
            arr[i] = val

    t = 0.010
    period = 0.010                      # 10 ms = 3000 RPM x 2 pulses/rev
    for _ in range(20):
        put(tach, t, t + period / 2, 1)  # 50% duty cycle
        t += period
    return tach[:]

register("fan", decode_fan, make_fan_test, "Fan TACH speed")
