# -*- coding: utf-8 -*-
"""Manchester decoder (one line, channel 0).

Convention: IEEE 802.3, where a high-to-low transition in the middle of a
bit cell is a 1 and a low-to-high transition is a 0; the mid-bit
transition carries the clock. The line idles high, so a transmission
starts with the mid-bit transition of the first 1 bit.

The self-test sends a 0x55 preamble followed by the text "Hi" (0x48
0x69, LSB first) with a 200 us half-bit (400 us per bit), which a 10 kHz
capture resolves. Faster links need a higher sample-rate device.
"""
from ..events import event
from ..model import channel_bits
from ..registry import register
from ..segments import build_wave


def decode_manchester(samples, rate, ch=0):
    bits = channel_bits(samples, ch)
    n = len(bits)
    dt = 1.0 / rate
    events = []
    # Transition points. With the mid-bit-transition convention the level
    # at a bit boundary always matches the start level of the next bit,
    # so a mid-bit transition occurs every bit time; equal consecutive
    # bits additionally produce a boundary transition exactly halfway
    # between two mid-bit transitions.
    trans = [i for i in range(1, n) if bits[i - 1] != bits[i]]
    if not trans:
        return events
    gaps = [trans[k + 1] - trans[k] for k in range(len(trans) - 1)]
    if not gaps:
        return events
    min_gap = min(gaps)
    if min_gap < 2:
        return events
    # Half-bit candidates (a capture with purely alternating bits shows
    # only full-bit gaps); pick the one that decodes the most bits.
    candidates = sorted({min_gap, 2 * min_gap})
    if min_gap % 2 == 0:
        candidates.insert(0, min_gap // 2)
    # The capture may start with a spurious head transition (an extra
    # level blip before the real signal), so anchor the decode at every
    # candidate start transition and keep the combination that yields the
    # most complete bytes.
    best = None
    for start in range(min(6, len(trans))):
        for half in candidates:
            if half < 2:
                continue
            data = _walk(bits, trans, half, start)
            score = (len(data) // 8, len(data),
                     1 if len(data) % 8 == 0 else 0)
            if best is None or score > best[0]:
                best = (score, start, half, data)
    if best is None or not best[3]:
        return events
    start, half, data = best[1], best[2], best[3]
    t_first = trans[start] * dt
    for k2, b in enumerate(data):
        events.append(event((trans[start] + 2 * k2 * half) * dt, ch, "MAN",
                            f"{b}"))
    # Group into bytes, LSB first
    byte_bits = []
    for b in data:
        byte_bits.append(b)
        if len(byte_bits) == 8:
            v = 0
            for bi, bb in enumerate(byte_bits):
                if bb:
                    v |= (1 << bi)
            txt = repr(chr(v) if 32 <= v <= 126 else "?")
            events.append(event(t_first, ch, "MAN_BYTE",
                                f"0x{v:02X} {txt}"))
            byte_bits = []
    if byte_bits:
        v = 0
        for bi, bb in enumerate(byte_bits):
            if bb:
                v |= (1 << bi)
        events.append(event(t_first, ch, "MAN_BYTE",
                            f"0x{v:02X} (partial)"))
    events.sort(key=lambda e: e["t"])
    return events


def _walk(bits, trans, half, start=0):
    """Decode the bit stream for one half-bit candidate anchored at
    ``trans[start]``."""
    data = []
    first = trans[start]
    ti = start
    expected = first
    while ti < len(trans):
        t = trans[ti]
        if abs(t - expected) <= half // 2:
            # Mid-bit transition: falling (new level 0) = 1,
            # rising (new level 1) = 0.
            data.append(1 if bits[t] == 0 else 0)
            expected += 2 * half
            ti += 1
        elif t < expected + half + half // 2:
            ti += 1                        # boundary transition, skip
        else:
            break                          # line went idle
    return data


def make_manchester_test(rate):
    """Self-test: 0x55 preamble + "Hi" (0x48 0x69), IEEE 802.3, idle high.

    Half-bit = 200 us, so every bit cell is 400 us.
    """
    n = int(0.30 * rate)
    pulses = []
    t = 0.001                                   # idle high
    hb = 0.0002                                 # half-bit
    text = [0x55, 0x48, 0x69]
    seq = [(v >> b) & 1 for v in text for b in range(8)]   # LSB first
    for b in seq:
        if b == 1:
            pulses.append((t, 1, hb)); t += hb      # high half
            pulses.append((t, 0, hb)); t += hb      # low half (falling mid)
        else:
            pulses.append((t, 0, hb)); t += hb      # low half
            pulses.append((t, 1, hb)); t += hb      # high half (rising mid)
    return build_wave(0, pulses, rate, max(n, int(t * rate) + 10), idle=1)


register("manchester", decode_manchester, make_manchester_test,
         "Manchester (IEEE 802.3)")
