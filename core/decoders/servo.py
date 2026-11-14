# -*- coding: utf-8 -*-
"""Servo PWM / PPM decoder."""
from ..events import event
from ..model import channel_bits
from ..registry import register
from ..segments import build_wave, edges_of


# ======================================================================
# Servo PWM / PPM (same wire: 20 ms single-servo PWM or multi-channel
# PPM frame)
# ======================================================================
def decode_servo(samples, rate, ch=0):
    """
    Recognizes two signal types:
      A. Standard servo PWM: period 18-22 ms, pulse width 500-2500 us,
         angle = (pulse_us - 1000) / 1000 * 180, clamped to 0-180.
      B. PPM multi-channel frame: gaps between adjacent rising edges
         inside a frame = channel values (500-4000 us); the frame gap
         (sync) > 4000 us; a frame is reported as PPM only when it has
         >= 4 channels.
    """
    bits = channel_bits(samples, ch)
    dt = 1.0 / rate
    edges = edges_of(bits)
    # Keep only real edges (drop the initial-level point added by edges_of)
    rising = [i for (i, lvl) in edges if lvl == 1 and i > 0]
    falling = [i for (i, lvl) in edges if lvl == 0 and i > 0]
    events = []

    # ---- A. Standard servo PWM: rising edge to the next rising edge = one
    #       full period ----
    for i in range(len(rising) - 1):
        a, b = rising[i], rising[i + 1]
        per_us = (b - a) * 1e6 / rate
        if 18000.0 <= per_us <= 22000.0:            # 18-22 ms valid period
            pw_us = None
            for f in falling:                        # Falling edge inside the
                                                    # period = pulse width
                if a < f < b:
                    pw_us = (f - a) * 1e6 / rate
                    break
            if pw_us is not None and 500.0 <= pw_us <= 2500.0:
                ang = (pw_us - 1000.0) / 1000.0 * 180.0
                if ang < 0.0:
                    ang = 0.0
                elif ang > 180.0:
                    ang = 180.0
                events.append(event(a * dt, ch, "SERVO",
                                    f"pulse={pw_us:.0f}us angle={ang:.1f} deg"))

    # ---- B. PPM: adjacent rising edges 500-4000 us apart = channel values,
    #       > 4000 us = frame sync ----
    frame = []          # Rising-edge indices inside the current frame

    def flush_ppm():
        gaps = []
        for k in range(len(frame) - 1):
            g_us = (frame[k + 1] - frame[k]) * 1e6 / rate
            if 500.0 <= g_us <= 4000.0:
                gaps.append(g_us)
        if len(gaps) >= 4:
            vals = ",".join(f"{g:.0f}" for g in gaps)
            events.append(event(frame[0] * dt, ch, "PPM",
                                f"{len(gaps)} ch: [{vals}]"))

    for r in rising:
        if frame and (r - frame[-1]) * 1e6 / rate > 4000.0:
            flush_ppm()
            frame = []
        frame.append(r)
    flush_ppm()

    events.sort(key=lambda e: e["t"])
    return events

def make_servo_test(rate):
    """
    3 servo periods of 20 ms: pulse widths 1000/1500/2000 us ->
    0/90/180 deg; the 4th pulse completes the 3rd full period
    (rising edge to the next rising edge).
    """
    n = int(0.09 * rate)            # 90ms
    pulses = [
        (0.005, 1, 0.0010),         # 1000us -> 0 deg
        (0.025, 1, 0.0015),         # 1500us -> 90 deg
        (0.045, 1, 0.0020),         # 2000us -> 180 deg
        (0.065, 1, 0.0020),         # 4th rising edge completes the 3rd full
                                    # period
    ]
    return build_wave(0, pulses, rate, n, idle=0)

register("servo", decode_servo, make_servo_test, "Servo PWM/PPM")
