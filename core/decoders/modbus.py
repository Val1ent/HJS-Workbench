# -*- coding: utf-8 -*-
"""Modbus RTU decoder over RS-485 (half-duplex UART, channel 0).

Modbus RTU normally runs at 1200-115200 bps with a 3.5-character idle gap
between frames; real installations at the upper end of that range need a
higher sample-rate device. The self-test uses 1000 bps so the standard
10-tick UART framing resolves every bit cleanly (1 ms per bit).

A frame is slave address, function code, data, and a 16-bit CRC
(polynomial 0xA001, low byte first). The decoder reuses the shared UART
scan with the baud-derived tick count, splits frames on the idle gap, and
emits address, function code, register data, and the CRC result.
"""
from ..events import event
from ..model import channel_bits
from ..registry import register
from ..segments import build_wave
from ..uart import scan_frames

FUNC_NAMES = {
    1: "read coils",
    2: "read discrete inputs",
    3: "read holding registers",
    4: "read input registers",
    5: "write single coil",
    6: "write single register",
    15: "write multiple coils",
    16: "write multiple registers",
}


def _crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc >> 1) ^ 0xA001) if (crc & 1) else (crc >> 1)
    return crc


def decode_modbus(samples, rate, ch=0, baud=1000):
    ticks = max(2, int(round(rate / baud)))
    bits = channel_bits(samples, ch)
    frames = scan_frames(bits, ticks)
    if len(frames) < 4:
        return []
    dt = 1.0 / rate
    # Split frames on the 3.5-character idle gap between the end of one
    # character (start + 10 ticks) and the start of the next one.
    packets = []
    cur = [frames[0]]
    for f in frames[1:]:
        gap = f[0] - (cur[-1][0] + ticks * 10)
        if gap <= ticks * 4:
            cur.append(f)
        else:
            packets.append(cur)
            cur = [f]
    packets.append(cur)
    events = []
    for p in packets:
        if len(p) < 4:
            continue
        t0 = p[0][0] * dt
        raw = [ord(c) for _, c in p]
        crc_calc = _crc16(raw[:-2])
        crc_recv = raw[-2] | (raw[-1] << 8)
        ok = crc_calc == crc_recv
        addr = raw[0]
        func = raw[1]
        fname = FUNC_NAMES.get(func, f"func=0x{func:02X}")
        if func in (1, 2, 3, 4) and len(raw) >= 8:
            start = (raw[2] << 8) | raw[3]
            qty = (raw[4] << 8) | raw[5]
            data_txt = f"start={start} qty={qty}"
        elif func in (5, 6) and len(raw) >= 8:
            reg = (raw[2] << 8) | raw[3]
            val = (raw[4] << 8) | raw[5]
            data_txt = f"reg={reg} value={val}"
        else:
            data_txt = "data=" + " ".join(f"{b:02X}" for b in raw[2:-2])
        typ = "MODBUS" if ok else "MODBUS_CRC_ERR"
        events.append(event(t0, ch, typ,
            f"addr={addr} {fname} {data_txt} "
            f"CRC {'OK' if ok else 'BAD (calc=0x%04X)' % crc_calc}"))
    events.sort(key=lambda e: e["t"])
    return events


def make_modbus_test(rate):
    """Self-test: read holding registers 0-1 from slave 1, CRC 0x0BC4.

    Frame bytes: 01 03 00 00 00 02 C4 0B at 1000 bps (1 ms per bit, 8N1,
    LSB first), idle gaps of 5 ms around the frame.
    """
    n = int(0.30 * rate)
    pulses = []
    t = 0.004                                   # idle high
    bit_time = 0.001                            # 1000 bps

    def uart_byte(v):
        nonlocal t
        bits = [0]                              # start bit
        for b in range(8):                      # LSB first
            bits.append((v >> b) & 1)
        bits.append(1)                          # stop bit
        for b in bits:
            pulses.append((t, b, bit_time))
            t += bit_time

    frame = [0x01, 0x03, 0x00, 0x00, 0x00, 0x02, 0xC4, 0x0B]
    for v in frame:
        uart_byte(v)
    t += 0.005
    return build_wave(0, pulses, rate, max(n, int(t * rate) + 10), idle=1)


register("modbus", decode_modbus, make_modbus_test, "Modbus RTU")
