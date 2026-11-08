# -*- coding: utf-8 -*-
"""HD44780 character-LCD decoder, 4-bit bus (RS=D0, E=D1, D4-D7=D2-D5).

The HD44780 latches the bus on the falling edge of E. In 4-bit mode every
byte arrives as two nibbles (high nibble first) on D4-D7 while RS selects
the register: RS=0 is a command, RS=1 is character data.

Real HD44780 boards are usually strobed in 1 us or less, far below the
200 us limit of a 10 kHz capture, so genuine fast hardware needs a higher
sample-rate device; the self-test keeps every E pulse at 300 us. The
self-test sends the classic init sequence (function set 0x28, display on
0x0C, entry mode 0x06, clear 0x01) and then the text "Hi", and the
decoder emits each command and the decoded characters.
"""
from ..events import event
from ..model import channel_bits
from ..registry import register

CMD_NAMES = {
    0x01: "clear display",
    0x02: "return home",
    0x04: "entry mode",
    0x06: "entry mode",
    0x08: "display off",
    0x0C: "display on",
    0x10: "cursor shift",
    0x20: "function set",
    0x28: "function set",
    0x80: "set DDRAM address",
}


def decode_hd44780(samples, rate, rs_ch=0, e_ch=1,
                   d4_ch=2, d5_ch=3, d6_ch=4, d7_ch=5):
    rs = channel_bits(samples, rs_ch)
    e = channel_bits(samples, e_ch)
    d4 = channel_bits(samples, d4_ch)
    d5 = channel_bits(samples, d5_ch)
    d6 = channel_bits(samples, d6_ch)
    d7 = channel_bits(samples, d7_ch)
    n = len(samples)
    dt = 1.0 / rate
    events = []
    nibble = None
    t_byte = 0.0
    for i in range(1, n):
        if e[i - 1] == 1 and e[i] == 0:      # falling edge of E: latch
            val = d4[i] | (d5[i] << 1) | (d6[i] << 2) | (d7[i] << 3)
            if nibble is None:
                nibble = val                 # high nibble first
                t_byte = i * dt
            else:
                byte = (nibble << 4) | val
                nibble = None
                if rs[i]:
                    txt = repr(chr(byte) if 32 <= byte <= 126 else "?")
                    events.append(event(t_byte, rs_ch, "CHAR",
                                        f"0x{byte:02X} {txt}"))
                else:
                    name = CMD_NAMES.get(byte, "")
                    txt = f"cmd=0x{byte:02X}"
                    if name:
                        txt += f" {name}"
                    events.append(event(t_byte, rs_ch, "CMD", txt))
    events.sort(key=lambda e: e["t"])
    return events


def make_hd44780_test(rate):
    """Self-test: init commands 0x28 0x0C 0x06 0x01, then the text "Hi".

    Every E pulse is 300 us high and 300 us low (4-bit mode, high nibble
    first, data latched on the falling edge).
    """
    n = int(0.30 * rate)
    rs = [0] * n
    e = [0] * n
    d4 = [0] * n
    d5 = [0] * n
    d6 = [0] * n
    d7 = [0] * n

    def put(arr, t0, t1, val):
        a = max(0, int(round(t0 * rate)))
        b = min(n, int(round(t1 * rate)))
        for i in range(a, b):
            arr[i] = val

    t = 0.002

    def send_byte(value, rs_val):
        nonlocal t
        for nib in ((value >> 4) & 0xF, value & 0xF):
            put(rs, t, t + 0.0010, rs_val)
            put(d4, t, t + 0.0010, (nib >> 0) & 1)
            put(d5, t, t + 0.0010, (nib >> 1) & 1)
            put(d6, t, t + 0.0010, (nib >> 2) & 1)
            put(d7, t, t + 0.0010, (nib >> 3) & 1)
            put(e, t, t + 0.0003, 1)        # E pulse high
            put(e, t + 0.0003, t + 0.0006, 0)
            t += 0.0010

    for cmd in (0x28, 0x0C, 0x06, 0x01):
        send_byte(cmd, 0)
    for c in "Hi":
        send_byte(ord(c), 1)
    return [(e[i] << 1) | rs[i] | (d4[i] << 2) | (d5[i] << 3)
            | (d6[i] << 4) | (d7[i] << 5) for i in range(n)]


register("hd44780", decode_hd44780, make_hd44780_test, "HD44780 4-bit LCD")
