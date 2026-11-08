# -*- coding: utf-8 -*-
"""NMEA 0183 GPS sentence decoder (UART text, channel 0).

NMEA 0183 sentences are UART text at 4800 bps (or slower) that start
with "$", end with "*" plus a two-digit hex checksum (the XOR of every
character between "$" and "*"), and are followed by CR/LF. The decoder
reuses the shared UART scan with the baud-derived tick count, extracts
the "$...*XX" sentences, and emits the sentence text with its checksum
result.

The self-test sends a $GPGGA and a $GPRMC sentence at 4800 bps (8N1,
LSB first); both carry valid checksums.
"""
import re

from ..events import event
from ..model import channel_bits
from ..registry import register
from ..segments import build_wave
from ..uart import scan_frames

_SENTENCE_RE = re.compile(r"\$([^*\r\n]*)\*([0-9A-Fa-f]{2})")


def decode_nmea(samples, rate, ch=0, baud=4800):
    ticks = max(2, int(round(rate / baud)))
    bits = channel_bits(samples, ch)
    frames = scan_frames(bits, ticks)
    if not frames:
        return []
    dt = 1.0 / rate
    # Map every character to its start sample so sentence times are exact
    starts = {}
    text = []
    for start, c in frames:
        starts[len(text)] = start
        text.append(c)
    full = "".join(text)
    events = []
    for m in _SENTENCE_RE.finditer(full):
        body = m.group(1)
        cs = m.group(2)
        calc = 0
        for c in body:
            calc ^= ord(c)
        ok = calc == int(cs, 16)
        t0 = starts[m.start()] * dt
        typ = "NMEA" if ok else "NMEA_ERR"
        events.append(event(
            t0, ch, typ,
            f"${body}*{cs} checksum "
            f"{'OK' if ok else 'BAD (calc=%02X)' % calc}"))
    events.sort(key=lambda e: e["t"])
    return events


def make_nmea_test(rate):
    """Self-test: two valid sentences at 4800 bps (8N1, LSB first).

    $GPGGA,120000.000,3113.1234,N,12127.5678,E,1,08,0.9,45.5,M,0.0,M,,*55
    $GPRMC,120000.000,A,3113.1234,N,12127.5678,E,0.00,0.00,081126,,*03
    """
    sentences = [
        "$GPGGA,120000.000,3113.1234,N,12127.5678,E,1,08,0.9,45.5,M,0.0,M,,"
        "*55\r\n",
        "$GPRMC,120000.000,A,3113.1234,N,12127.5678,E,0.00,0.00,081126,,"
        "*03\r\n",
    ]
    bit_time = 1.0 / 4800.0
    pulses = []
    t = 0.004                                   # idle high
    for sentence in sentences:
        for c in sentence:
            byte = ord(c)
            bits = [0]                          # start bit
            for b in range(8):                  # LSB first
                bits.append((byte >> b) & 1)
            bits.append(1)                      # stop bit
            for b in bits:
                pulses.append((t, b, bit_time))
                t += bit_time
        t += 0.002                              # sentence gap
    n = max(int(0.80 * rate), int(t * rate) + 10)
    return build_wave(0, pulses, rate, n, idle=1)


register("nmea", decode_nmea, make_nmea_test, "NMEA 0183 GPS")
