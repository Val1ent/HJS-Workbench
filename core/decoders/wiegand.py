# -*- coding: utf-8 -*-
"""Wiegand access-control decoder (DATA0=D0, DATA1=D1).

Wiegand cards transmit negative (active-low) pulses on DATA0 (bit 0) and
DATA1 (bit 1) with an inter-pulse gap of 1 ms or more and a long gap
after the frame. Real readers usually pulse 20-100 us, which is below
the 200 us limit of a 10 kHz capture, so genuine fast hardware needs a
higher sample-rate device; the self-test uses 300 us pulses with 1.5 ms
gaps, which the decoder resolves.

26-bit frames: even parity bit, 8-bit facility code, 16-bit card number,
odd parity bit. 34-bit frames (16-bit facility, 16-bit card) are also
recognized. The decoder emits every bit plus the assembled frame with
the facility and card number.
"""
from ..events import event
from ..model import channel_bits
from ..registry import register

FRAME_GAP_US = 5000.0  # gap that ends a frame


def decode_wiegand(samples, rate, d0_ch=0, d1_ch=1):
    d0 = channel_bits(samples, d0_ch)
    d1 = channel_bits(samples, d1_ch)
    n = len(samples)
    dt = 1.0 / rate
    # Negative pulses: falling edges on D0 -> bit 0, on D1 -> bit 1
    pulses = []
    for i in range(1, n):
        if d0[i - 1] == 1 and d0[i] == 0:
            pulses.append((i, 0))
        elif d1[i - 1] == 1 and d1[i] == 0:
            pulses.append((i, 1))
    events = []
    frame = []
    t_first = 0.0
    for idx, bit in pulses:
        t = idx * dt
        if frame and (t - (frame[-1][0] * dt)) > FRAME_GAP_US / 1e6:
            events.extend(_finish_frame(frame, t_first, dt, d0_ch))
            frame = []
        if not frame:
            t_first = t
        frame.append((idx, bit))
        events.append(event(t, d0_ch if bit == 0 else d1_ch,
                            "WIEGAND_BIT", f"bit={bit}"))
    if frame:
        events.extend(_finish_frame(frame, t_first, dt, d0_ch))
    events.sort(key=lambda e: e["t"])
    return events


def _finish_frame(frame, t_first, dt, ch):
    """Assemble a 26- or 34-bit frame; return its events."""
    bits = [b for _, b in frame]
    out = []
    if len(bits) in (26, 34):
        if len(bits) == 26:
            p1_ok = bits[0] == (sum(bits[1:13]) % 2)
            p2_ok = bits[25] == (1 - sum(bits[13:25]) % 2)
            fac = _bits_val(bits[1:9])
            card = _bits_val(bits[9:25])
            nbits = 26
        else:
            p1_ok = bits[0] == (sum(bits[1:17]) % 2)
            p2_ok = bits[33] == (1 - sum(bits[17:33]) % 2)
            fac = _bits_val(bits[1:17])
            card = _bits_val(bits[17:33])
            nbits = 34
        stream = "".join(str(b) for b in bits)
        if p1_ok and p2_ok:
            out.append(event(t_first, ch, "WIEGAND_FRAME",
                f"{nbits}-bit facility={fac} card={card} parity OK "
                f"bits={stream}"))
        else:
            out.append(event(t_first, ch, "WIEGAND_PARITY_ERR",
                f"{nbits}-bit facility={fac} card={card} parity failed "
                f"bits={stream}"))
    else:
        stream = "".join(str(b) for b in bits)
        out.append(event(t_first, ch, "WIEGAND_FRAME",
                         f"{len(bits)}-bit bits={stream}"))
    return out


def _bits_val(bits):
    v = 0
    for b in bits:                      # MSB first
        v = (v << 1) | b
    return v


def make_wiegand_test(rate):
    """Self-test: 26-bit frame, facility 101, card 12345, both parities valid.

    Bits: 0 | 01100101 | 0011000000111001 | 1. Pulse width 300 us,
    inter-pulse gap 1.5 ms.
    """
    from ..model import set_channel
    frame_bits = [0] + [(101 >> (7 - b)) & 1 for b in range(8)] \
        + [(12345 >> (15 - b)) & 1 for b in range(16)] + [1]
    n = max(int(0.30 * rate), int((0.002 + 26 * 0.0015) * rate) + 10)
    samples = [0] * n
    for i in range(n):                  # both lines idle high
        set_channel(samples, i, 0, 1)
        set_channel(samples, i, 1, 1)
    for k, bit in enumerate(frame_bits):
        t0 = 0.002 + k * 0.0015
        a = int(round(t0 * rate))
        b = int(round((t0 + 0.0003) * rate))
        ch = 0 if bit == 0 else 1
        for i in range(max(0, a), min(n, b)):
            set_channel(samples, i, ch, 0)      # negative pulse
    return samples


register("wiegand", decode_wiegand, make_wiegand_test, "Wiegand 26/34-bit")
