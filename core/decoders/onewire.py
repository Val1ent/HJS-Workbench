# -*- coding: utf-8 -*-
"""1-Wire DS18B20 temperature decoder (one DQ line, channel 0).

Real DS18B20 timing: the reset pulse is 480 us or more low, the presence
pulse is 60-240 us low, and write/read slots are 60-120 us. Real hardware
running at full speed needs a higher sample-rate device; this decoder
resolves the slow slots the capture rate can actually represent.

The self-test transaction keeps every slot at 200 us or more: reset 600 us
low, presence 200 us low, write slots 200 us (bit 1) / 300 us (bit 0),
and read slots with a 200 us sampling low. The transaction is a ROM skip
(0xCC), convert T (0x44), a second reset, ROM skip, and a read scratchpad
(0xBE) returning the 9-byte scratchpad with CRC, from which the decoder
emits the temperature.
"""
from ..events import event
from ..model import channel_bits
from ..registry import register
from ..segments import build_wave, pulse_widths


def _us(w):
    return w * 1_000_000.0


def _crc8(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc >> 1) ^ 0x8C) if (crc & 1) else (crc >> 1)
    return crc


def decode_onewire(samples, rate, ch=0):
    bits = channel_bits(samples, ch)
    segs = pulse_widths(bits, rate)          # [(start, level, width_s), ...]
    dt = 1.0 / rate
    events = []
    i = 0
    n = len(segs)
    while i < n:
        start, lvl, w = segs[i]
        if lvl == 0 and _us(w) >= 500:       # reset pulse
            events.append(event(start * dt, ch, "RESET", "reset pulse"))
            j = i + 1
            # Presence: short release, then a low pulse < 500 us
            if j + 1 < n and segs[j][1] == 1 and _us(segs[j][2]) <= 300 \
                    and segs[j + 1][1] == 0 and _us(segs[j + 1][2]) < 500:
                events.append(event(segs[j + 1][0] * dt, ch, "PRESENCE",
                                    "device present"))
                j += 2
            # Command bytes (write slots) until the next reset; after the
            # 0xBE read-scratchpad command the slots become read slots.
            in_read = False
            byte_no = 0
            bits_acc = []
            t_byte = 0.0
            read_bytes = []

            def complete_byte(v):
                """Bookkeeping for one finished byte (both slot kinds)."""
                nonlocal in_read, byte_no
                if in_read:
                    read_bytes.append(v)
                    events.append(event(t_byte, ch, "DATA", f"0x{v:02X}"))
                    if len(read_bytes) == 9:
                        events.append(
                            event(t_byte, ch, "SCRATCHPAD",
                                  "scratchpad=" + " ".join(
                                      f"{x:02X}" for x in read_bytes)))
                        crc = _crc8(read_bytes[:8])
                        if crc == read_bytes[8]:
                            raw = read_bytes[0] | (read_bytes[1] << 8)
                            temp = raw / 16.0
                            events.append(
                                event(t_byte, ch, "TEMP",
                                      f"temp={temp:.1f}C CRC OK"))
                        else:
                            events.append(
                                event(t_byte, ch, "TEMP_ERR",
                                      f"CRC failed: got "
                                      f"{read_bytes[8]:02X} want "
                                      f"{crc:02X}"))
                        read_bytes[:] = []
                else:
                    byte_no += 1
                    if byte_no == 1:
                        label = "ROM" if v == 0xCC else "CMD"
                        events.append(event(t_byte, ch, label,
                                            f"0x{v:02X}"))
                    else:
                        events.append(event(t_byte, ch, "CMD",
                                            f"0x{v:02X}"))
                    if v == 0xBE:
                        in_read = True
                        byte_no = 0

            while j < n and not (segs[j][1] == 0 and _us(segs[j][2]) >= 500):
                s2, l2, w2 = segs[j]
                if l2 == 0:
                    if in_read and _us(w2) <= 300:
                        # Read slot: 200-300 us sampling low; the segment
                        # right after the low carries the bit (line
                        # released = 1, held low = 0).
                        if not bits_acc:
                            t_byte = s2 * dt
                        j += 1
                        if j < n and segs[j][1] == 1:
                            bits_acc.append(1)
                        else:
                            bits_acc.append(0)
                        j += 1               # consume the after-low segment
                        if len(bits_acc) == 8:
                            v = 0
                            for b in range(8):      # LSB first
                                if bits_acc[b]:
                                    v |= (1 << b)
                            bits_acc = []
                            complete_byte(v)
                        continue
                    # Write slot: 200 us low = 1, 300 us low = 0
                    if not bits_acc:
                        t_byte = s2 * dt
                    bits_acc.append(0 if _us(w2) >= 250 else 1)
                    if len(bits_acc) == 8:
                        v = 0
                        for b in range(8):              # LSB first
                            if bits_acc[b]:
                                v |= (1 << b)
                        bits_acc = []
                        complete_byte(v)
                j += 1
            i = j
            continue
        i += 1
    events.sort(key=lambda e: e["t"])
    return events


def make_onewire_test(rate):
    """Self-test DS18B20: skip ROM, convert, then read the scratchpad.

    Scratchpad: 0x90 0x01 (25.0C), TH=0x4B, TL=0x46, config=0x7F,
    0xFF 0xFF 0xFF, CRC=0x57. Every slot is 200 us or longer.
    """
    n = int(0.50 * rate)
    pulses = []
    t = 0.001

    def reset():
        nonlocal t
        pulses.append((t, 0, 0.0006)); t += 0.0006   # reset
        pulses.append((t, 1, 0.0002)); t += 0.0002   # release
        pulses.append((t, 0, 0.0002)); t += 0.0002   # presence
        pulses.append((t, 1, 0.0003)); t += 0.0003   # recovery

    def write_byte(v):
        nonlocal t
        for b in range(8):                          # LSB first
            bit = (v >> b) & 1
            if bit:
                pulses.append((t, 0, 0.0002)); t += 0.0002   # write 1
                pulses.append((t, 1, 0.0004)); t += 0.0004
            else:
                pulses.append((t, 0, 0.0003)); t += 0.0003   # write 0
                pulses.append((t, 1, 0.0003)); t += 0.0003

    def read_byte(v):
        nonlocal t
        for b in range(8):                          # LSB first
            bit = (v >> b) & 1
            pulses.append((t, 0, 0.0002)); t += 0.0002   # master sampling low
            if bit:
                pulses.append((t, 1, 0.0005)); t += 0.0005
            else:
                pulses.append((t, 0, 0.0002)); t += 0.0002   # device holds low
                pulses.append((t, 1, 0.0004)); t += 0.0004

    reset()
    write_byte(0xCC)                                # skip ROM
    write_byte(0x44)                                # convert T
    pulses.append((t, 1, 0.0010)); t += 0.0010      # conversion gap
    reset()
    write_byte(0xCC)                                # skip ROM
    write_byte(0xBE)                                # read scratchpad
    sp = [0x90, 0x01, 0x4B, 0x46, 0x7F, 0xFF, 0xFF, 0xFF, 0x57]
    for v in sp:
        read_byte(v)
    return build_wave(0, pulses, rate, max(n, int(t * rate) + 10), idle=1)


register("onewire", decode_onewire, make_onewire_test, "1-Wire DS18B20")
