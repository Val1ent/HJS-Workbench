# -*- coding: utf-8 -*-
"""Sony SIRC infrared decoder (one line, channel 0, active high).

SIRC (12-bit version): idle low, a 2.4 ms start pulse, then 12 bits where
a 1.2 ms high is a 1 and a 0.6 ms high is a 0, each separated by a 0.6 ms
low gap. The bits are LSB first: 5 device bits then 7 command bits.

Real infrared receivers output these widths directly at the receiver pin,
so a 10 kHz capture resolves them; the self-test uses the standard widths
(shortest pulse 600 us). 15- and 20-bit variants exist; the decoder reads
any length and reports the device/command split when the bit count is 12,
15, or 20.
"""
from ..events import event
from ..model import channel_bits
from ..registry import register
from ..segments import build_wave, pulse_widths


def _us(w):
    return w * 1_000_000.0


def decode_sirc(samples, rate, ch=0):
    bits = channel_bits(samples, ch)
    segs = pulse_widths(bits, rate)
    dt = 1.0 / rate
    events = []
    i = 0
    n = len(segs)
    while i < n:
        start, lvl, w = segs[i]
        if lvl == 1 and 1800 <= _us(w) <= 3200:     # start pulse
            t0 = start * dt
            events.append(event(t0, ch, "SIRC_START",
                                "start pulse"))
            data = []
            j = i + 1
            # The start pulse is followed by a ~0.6 ms space before the
            # first data burst.
            if j < n and segs[j][1] == 0 and _us(segs[j][2]) <= 1000:
                j += 1
            while j < n:
                sh, lh, wh = segs[j]                # bit high
                if lh != 1:
                    break
                hu = _us(wh)
                if 800 <= hu <= 1600:
                    data.append(1)
                elif 400 <= hu < 800:
                    data.append(0)
                else:
                    break
                # A following gap keeps the frame going; a long low
                # (or the end of the capture) ends it.
                if j + 1 < n and segs[j + 1][1] == 0 \
                        and _us(segs[j + 1][2]) <= 1000:
                    j += 2
                else:
                    j += 1
                    break
            if data:
                if len(data) in (12, 15, 20):
                    dev = 0
                    for b in range(5):              # LSB first
                        if data[b]:
                            dev |= (1 << b)
                    cmd = 0
                    for b in range(len(data) - 5):
                        if data[5 + b]:
                            cmd |= (1 << b)
                    events.append(event(t0, ch, "SIRC",
                                        f"dev={dev} cmd={cmd} "
                                        f"({len(data)} bits)"))
                else:
                    stream = "".join(str(b) for b in data)
                    events.append(event(t0, ch, "SIRC",
                                        f"bits={stream} ({len(data)} bits)"))
            i = j
            continue
        i += 1
    events.sort(key=lambda e: e["t"])
    return events


def make_sirc_test(rate):
    """Self-test: SIRC 12-bit, device 1, command 22 (0b0010110), LSB first."""
    n = int(0.10 * rate)
    pulses = []
    t = 0.002                                   # idle low
    pulses.append((t, 1, 0.0024)); t += 0.0024  # start pulse
    pulses.append((t, 0, 0.0006)); t += 0.0006  # gap after the start pulse
    dev, cmd = 1, 22
    seq = [(dev >> b) & 1 for b in range(5)] \
        + [(cmd >> b) & 1 for b in range(7)]
    for b in seq:
        pulses.append((t, 1, 0.0012 if b else 0.0006))
        t += (0.0012 if b else 0.0006)
        pulses.append((t, 0, 0.0006))           # gap
        t += 0.0006
    return build_wave(0, pulses, rate, max(n, int(t * rate) + 10), idle=0)


register("sirc", decode_sirc, make_sirc_test, "Sony SIRC IR remote")
