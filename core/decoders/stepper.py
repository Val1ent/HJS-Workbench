# -*- coding: utf-8 -*-
"""Stepper motor STEP/DIR decoder."""
from ..events import event
from ..model import channel_bits
from ..registry import register


# ======================================================================
# 2. Stepper motor STEP/DIR (each STEP rising edge = one step, DIR
#    high = forward)
# ======================================================================
def decode_stepper(samples, rate, step_ch=0, dir_ch=1):
    """
    STEP rising edge = one step; DIR=1 forward (+1), DIR=0 reverse (-1).
    Reports per-step events (first 20 steps, then every 20th, to avoid
    flooding the screen) and an end summary (total steps / accumulated
    position / direction changes / average and peak speed).
    """
    step = channel_bits(samples, step_ch)
    dirn = channel_bits(samples, dir_ch)
    n = len(samples)
    dt = 1.0 / rate
    events = []
    pos = 0
    steps = 0
    flips = 0
    prev_dir = None
    last_t = None
    speeds = []
    for i in range(1, n):
        if step[i - 1] == 0 and step[i] == 1:
            d = 1 if dirn[i] else 0
            pos += 1 if d else -1
            steps += 1
            t_now = i * dt
            if prev_dir is not None and prev_dir != d:
                flips += 1
            prev_dir = d
            sp_txt = ""
            if last_t is not None and t_now > last_t:
                sp = 1.0 / (t_now - last_t)
                speeds.append(sp)
                sp_txt = f" speed={sp:.0f} steps/s"
            last_t = t_now
            if steps <= 20 or steps % 20 == 0:
                events.append(event(t_now, step_ch, "STEP",
                    f"step #{steps} dir={'FWD' if d else 'REV'} pos={pos:+d}{sp_txt}"))
    if steps:
        avg = sum(speeds) / len(speeds) if speeds else 0.0
        pk = max(speeds) if speeds else 0.0
        events.append(event((n - 1) * dt, step_ch, "STEP_SUM",
            f"total {steps} steps pos={pos:+d} dir flips={flips} "
            f"avg={avg:.0f} steps/s peak={pk:.0f} steps/s"))
    events.sort(key=lambda e: e["t"])
    return events

def make_stepper_test(rate):
    """30 steps forward + 10 steps reverse, 500us step interval (2 kHz), DIR=D1."""
    n = int(0.06 * rate)
    step = [0] * n
    dirn = [1] * n

    def put(arr, t0, t1, val):
        a = max(0, int(round(t0 * rate)))
        b = min(n, int(round(t1 * rate)))
        for i in range(a, b):
            arr[i] = val

    t = 0.005

    def burst(count, d, per=0.0005):
        nonlocal t
        put(dirn, t, t + count * per, d)
        for _ in range(count):
            put(step, t, t + 0.0002, 1)     # 200us high pulse
            t += per

    burst(30, 1)                            # 30 steps forward
    burst(10, 0)                            # 10 steps reverse
    return [(step[i]) | (dirn[i] << 1) for i in range(n)]

register("stepper", decode_stepper, make_stepper_test, "Stepper STEP/DIR")
