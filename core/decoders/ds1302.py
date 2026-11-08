# -*- coding: utf-8 -*-
"""DS1302 real-time clock decoder (CE=D0, SCLK=D1, IO=D2).

A transfer begins when CE goes high. Every byte is 8 bits LSB first on IO,
sampled on the rising edge of SCLK: first a command byte (bit 0 = R/W,
bits 1-6 = register address, bit 7 = 1), then one data byte (BCD for the
time registers). Reads and writes are distinguished by the R/W bit.

Real DS1302 parts tolerate clock rates up to 2 MHz, far beyond a 10 kHz
capture, so genuine fast hardware needs a higher sample-rate device; the
self-test uses a 2.5 kHz SCLK (400 us per bit). It writes 45 seconds,
30 minutes, and 13 hours (24-hour mode), reads the three registers back,
and the decoder emits the register events plus the assembled time.
"""
from ..events import event
from ..model import channel_bits
from ..registry import register

REG_NAMES = {
    0x00: "seconds", 0x01: "minutes", 0x02: "hours", 0x03: "date",
    0x04: "month", 0x05: "day", 0x06: "year", 0x07: "write-protect",
}


def _bcd(v, mask=0xFF):
    return (v & 0x0F) + ((v >> 4) & 0x07) * 10 if (v & mask) else 0


def decode_ds1302(samples, rate, ce_ch=0, sclk_ch=1, io_ch=2):
    ce = channel_bits(samples, ce_ch)
    sclk = channel_bits(samples, sclk_ch)
    io = channel_bits(samples, io_ch)
    n = len(samples)
    dt = 1.0 / rate
    events = []
    active = False
    bits_acc = []
    cmd = None
    t_byte = 0.0
    time_regs = {}
    for i in range(1, n):
        if ce[i - 1] == 0 and ce[i] == 1:
            active = True
            bits_acc = []
            cmd = None
            events.append(event(i * dt, ce_ch, "CE_HIGH",
                                "transfer start"))
            continue
        if ce[i - 1] == 1 and ce[i] == 0:
            active = False
            bits_acc = []
            cmd = None
            events.append(event(i * dt, ce_ch, "CE_LOW",
                                "transfer end"))
            continue
        if not active:
            continue
        if sclk[i - 1] == 0 and sclk[i] == 1:    # rising edge: sample IO
            if not bits_acc:
                t_byte = i * dt
            bits_acc.append(io[i])
            if len(bits_acc) == 8:
                v = 0
                for b in range(8):               # LSB first
                    if bits_acc[b]:
                        v |= (1 << b)
                bits_acc = []
                if cmd is None:
                    cmd = v
                    rw = "read" if (v & 1) else "write"
                    reg = (v >> 1) & 0x3F
                    events.append(event(t_byte, io_ch, "DS1302_CMD",
                                        f"{rw} reg=0x{reg:02X}"))
                else:
                    reg = (cmd >> 1) & 0x3F
                    rw = "R" if (cmd & 1) else "W"
                    name = REG_NAMES.get(reg, f"reg=0x{reg:02X}")
                    kind = "DS1302_READ" if (cmd & 1) else "DS1302_WRITE"
                    events.append(event(t_byte, io_ch, kind,
                                        f"{name} value=0x{v:02X}"))
                    if reg in (0x00, 0x01, 0x02):
                        time_regs[reg] = v
                    cmd = None
                    if 0x00 in time_regs and 0x01 in time_regs \
                            and 0x02 in time_regs:
                        h = _bcd(time_regs[0x02], 0x7F)
                        m = _bcd(time_regs[0x01])
                        s = _bcd(time_regs[0x00])
                        events.append(event(t_byte, io_ch, "TIME",
                                            f"time={h:02d}:{m:02d}:{s:02d}"))
                        time_regs = {}
    events.sort(key=lambda e: e["t"])
    return events


def make_ds1302_test(rate):
    """Self-test: write 45 s / 30 m / 13 h, then read them back.

    SCLK period 400 us, CE high 200 us before the first clock and 300 us
    after the last one.
    """
    n = int(0.40 * rate)
    ce = [0] * n
    sclk = [0] * n
    io = [0] * n

    def put(arr, t0, t1, val):
        a = max(0, int(round(t0 * rate)))
        b = min(n, int(round(t1 * rate)))
        for i in range(a, b):
            arr[i] = val

    t = 0.001
    T = 0.0004                       # 400 us per bit
    half = 0.0002

    def transfer(cmds, data):
        nonlocal t
        t_begin = t
        t += 0.0002                             # CE high before the clocks
        for cmd, dat in zip(cmds, data):
            seq = [(cmd >> b) & 1 for b in range(8)] \
                + [(dat >> b) & 1 for b in range(8)]
            for b in seq:
                put(io, t, t + T, b)            # IO set before the rising edge
                put(sclk, t, t + half, 0)
                put(sclk, t + half, t + T, 1)
                t += T
        put(ce, t_begin, t + 0.0002, 1)         # CE high across the transfer
        t += 0.0005                             # CE low gap

    # Write: seconds 45, minutes 30, hours 13 (24-hour mode)
    transfer([0x80, 0x82, 0x84], [0x45, 0x30, 0x13])
    # Read back the same three registers
    transfer([0x81, 0x83, 0x85], [0x45, 0x30, 0x13])
    return [(ce[i] << 0) | (sclk[i] << 1) | (io[i] << 2) for i in range(n)]


register("ds1302", decode_ds1302, make_ds1302_test, "DS1302 RTC")
