# -*- coding: utf-8 -*-
"""Infrared RC-5 remote decoder (Philips, 14-bit biphase frames)."""
from ..events import event
from ..model import channel_bits
from ..registry import register

# ======================================================================
# 4. Infrared RC-5 remote (Philips, 14-bit frames, biphase encoding)
# ======================================================================
def decode_rc5(samples, rate, ch=0):
    """
    RC-5: idle low; each bit is 1778us and must flip in the middle
    (biphase encoding): first half high + second half low = logic 1,
    first half low + second half high = logic 0.
    Frame = start 1,1 + toggle + 5-bit address + 6-bit command
    (MSB first).
    Try every candidate start and validate the 14-bit structure (the
    1/4 and 3/4 levels of each bit must differ); accept only frames
    whose first two bits are 1, to avoid half-bit false positives.
    """
    bits = channel_bits(samples, ch)
    n = len(bits)
    dt = 1.0 / rate
    events = []
    full = 1778e-6                      # 1.778 ms per bit
    rises = [i for i in range(1, n) if bits[i - 1] == 0 and bits[i] == 1]
    used = set()
    for s in rises:
        if s in used:
            continue
        frame = []
        ok = True
        for k in range(14):
            q1 = int(round(s + (k + 0.25) * full * rate))
            q3 = int(round(s + (k + 0.75) * full * rate))
            if q1 >= n or q3 >= n:
                ok = False
                break
            l1, l3 = bits[q1], bits[q3]
            if l1 == l3:                 # The bit midpoint must flip
                ok = False
                break
            frame.append(l1)             # First half high = 1, first half
                                         # low = 0
        if ok and frame[0] == 1 and frame[1] == 1:
            toggle = frame[2]
            addr = 0
            for b in frame[3:8]:
                addr = (addr << 1) | b
            cmd = 0
            for b in frame[8:14]:
                cmd = (cmd << 1) | b
            events.append(event(s * dt, ch, "RC5",
                                f"addr={addr} cmd={cmd} toggle={toggle}"))
            end_i = int(round(s + 14 * full * rate))
            for r in rises:              # Candidate starts inside this frame
                                         # are not re-tested
                if s < r < end_i:
                    used.add(r)
    events.sort(key=lambda e: e["t"])
    return events

def make_rc5_test(rate):
    """One RC-5 frame: start 1,1 + toggle 0 + address 0b00101 (5) +
command 0b100001 (33)."""
    half = 889e-6
    frame = [1, 1, 0] + [0, 0, 1, 0, 1] + [1, 0, 0, 0, 0, 1]
    n = int((0.010 + 14 * 2 * half + 0.010) * rate)
    bits = [0] * n

    def put(t0, t1, val):
        a = max(0, int(round(t0 * rate)))
        b = min(n, int(round(t1 * rate)))
        for i in range(a, b):
            bits[i] = val

    t = 0.010
    for bit in frame:
        put(t, t + half, bit)                    # First half = bit value
        put(t + half, t + 2 * half, 1 - bit)     # Second half inverted
                                                # (midpoint flip)
        t += 2 * half
    return bits[:]

register("rc5", decode_rc5, make_rc5_test, "IR RC-5")
