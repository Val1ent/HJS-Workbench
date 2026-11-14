# -*- coding: utf-8 -*-
"""Quadrature encoder A/B/Z decoder."""
from ..events import event
from ..model import channel_bits
from ..registry import register


# ======================================================================
# 3. Quadrature encoder A/B/Z (x4 counting, Z-phase zero reset)
# ======================================================================
def decode_encoder(samples, rate, a_ch=0, b_ch=1, z_ch=2, ppr=None):
    """
    x4 counting: every A/B edge counts once. A leading B = forward.
    When z_ch is given, a Z rising edge resets the position to zero and
    emits a ZERO event (pass z_ch=None when there is no Z phase);
    when ppr gives the pulses per revolution, events also carry the
    speed in RPM (RPM = edge_rate / (4 * ppr) * 60).
    Events are sampled (first 30 edges + every 30th after that), with a
    summary at the end.
    """
    a = channel_bits(samples, a_ch)
    b = channel_bits(samples, b_ch)
    z = channel_bits(samples, z_ch) if z_ch is not None else None
    n = len(samples)
    if n == 0:
        return []            # Return immediately on empty data to stay safe
    dt = 1.0 / rate
    FWD = {(0, 0): (1, 0), (1, 0): (1, 1), (1, 1): (0, 1), (0, 1): (0, 0)}
    REV = {(0, 0): (0, 1), (0, 1): (1, 1), (1, 1): (1, 0), (1, 0): (0, 0)}
    events = []
    pos = 0
    edges_cnt = 0
    last_t = None
    speeds = []
    prev = (a[0], b[0])
    for i in range(1, n):
        if z is not None and z[i - 1] == 0 and z[i] == 1:
            pos = 0
            events.append(event(i * dt, z_ch, "ZERO", "Z phase zero: position reset to 0"))
        cur = (a[i], b[i])
        if cur != prev:
            if FWD.get(prev) == cur:
                delta = 1
            elif REV.get(prev) == cur:
                delta = -1
            else:
                delta = 0            # Both phases changed at once (glitch),
                                     # ignore
            if delta:
                pos += delta
                edges_cnt += 1
                t_now = i * dt
                if last_t is not None and t_now > last_t:
                    speeds.append(1.0 / (t_now - last_t))
                last_t = t_now
                if edges_cnt <= 30 or edges_cnt % 30 == 0:
                    rpm = ""
                    if ppr and speeds:
                        rpm = (f" rpm="
                               f"{sum(speeds[-30:]) / len(speeds[-30:]) / (ppr * 4) * 60:.0f}RPM")
                    events.append(event(t_now, a_ch, "ENCODER",
                        f"edge #{edges_cnt} {'FWD' if delta > 0 else 'REV'} "
                        f"pos={pos:+d}{rpm}"))
            prev = cur
    if edges_cnt:
        avg = sum(speeds) / len(speeds) if speeds else 0.0
        events.append(event((n - 1) * dt, a_ch, "ENCODER_SUM",
                            f"total {edges_cnt} edges pos={pos:+d} avg={avg:.1f} edges/s"))
    events.sort(key=lambda e: e["t"])
    return events

def make_encoder_test(rate):
    """A leading B forward 25 cycles (100 edges) -> Z pulse resets to zero ->
reverse 5 cycles (20 edges)."""
    n = int(0.06 * rate)
    a = [0] * n
    b = [0] * n
    z = [0] * n

    def put(arr, t0, t1, val):
        aa = max(0, int(round(t0 * rate)))
        bb = min(n, int(round(t1 * rate)))
        for i in range(aa, bb):
            arr[i] = val

    dur = 0.00025                      # Each phase 250us
    t = 0.002
    FWD = [(1, 0), (1, 1), (0, 1), (0, 0)]     # A leads B
    REV = [(0, 1), (1, 1), (1, 0), (0, 0)]     # B leads A

    def cycle(seq):
        nonlocal t
        for (av, bv) in seq:
            put(a, t, t + dur, av)
            put(b, t, t + dur, bv)
            t += dur

    for _ in range(25):
        cycle(FWD)
    put(z, t - dur, t, 1)              # Z-phase pulse (zero reset)
    for _ in range(5):
        cycle(REV)
    return [(a[i]) | (b[i] << 1) | (z[i] << 2) for i in range(n)]

register("encoder", decode_encoder, make_encoder_test, "Quadrature encoder A/B/Z")
