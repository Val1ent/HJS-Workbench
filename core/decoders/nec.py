# -*- coding: utf-8 -*-
"""NEC infrared remote decoder."""
from ..events import event
from ..model import channel_bits
from ..registry import register
from ..segments import build_wave, pulse_widths

# ======================================================================
# Infrared remote NEC (active low)
# ======================================================================
def _us(w):
    return w * 1_000_000.0

def decode_nec(samples, rate, ch=0):
    bits = channel_bits(samples, ch)
    segs = pulse_widths(bits, rate)          # [(start, level, width_s), ...]
    dt = 1.0 / rate
    events = []
    i = 0
    n = len(segs)
    while i < n:
        start, lvl, w = segs[i]
        # Leader and repeat codes both start with a 7-11 ms low pulse
        if lvl == 0 and _us(w) >= 7000 and _us(w) <= 11000:
            lead_t = start * dt
            if i + 1 < n:
                _, lvl2, w2 = segs[i + 1]
                us2 = _us(w2)
                if lvl2 == 1 and 3500 <= us2 <= 5500:
                    # ---- Leader code, read 32 bits ----
                    events.append(event(lead_t, ch, "LEADER", "NEC leader"))
                    bits32 = []
                    j = i + 2
                    # Each bit = low (560us) + high (data)
                    while len(bits32) < 32 and j + 1 < n:
                        sl, ll, wl = segs[j]      # Low segment
                        sh, lh, wh = segs[j + 1]  # High segment
                        if ll == 0 and lh == 1 and 350 <= _us(wl) <= 800:
                            hu = _us(wh)
                            if 350 <= hu <= 800:
                                bits32.append(0)
                            elif 1300 <= hu <= 2000:
                                bits32.append(1)
                            else:
                                break
                            j += 2
                        else:
                            break
                    if len(bits32) == 32:
                        def take(off):
                            v = 0
                            for b in range(8):       # LSB first
                                if bits32[off + b]:
                                    v |= (1 << b)
                            return v
                        addr = take(0)
                        addr_n = take(8)
                        cmd = take(16)
                        cmd_n = take(24)
                        t = (start) * dt
                        if (addr ^ addr_n) == 0xFF and (cmd ^ cmd_n) == 0xFF:
                            events.append(event(t, ch, "NEC",
                                f"addr=0x{addr:02X} cmd=0x{cmd:02X}"))
                        else:
                            events.append(event(t, ch, "NEC_ERR",
                                f"checksum failed addr=0x{addr:02X}/0x{addr_n:02X} "
                                f"cmd=0x{cmd:02X}/0x{cmd_n:02X}"))
                        i = j
                        continue
                elif lvl2 == 1 and 1800 <= us2 <= 2800:
                    # ---- Repeat code ----
                    events.append(event(start * dt, ch, "REPEAT",
                                        "NEC repeat"))
                    i += 2
                    continue
        i += 1
    events.sort(key=lambda e: e["t"])
    return events

def make_nec_test(rate):
    n = int(0.09 * rate)        # 90ms
    pulses = []
    t = 0.010                   # 10 ms idle
    # Leader code
    pulses.append((t, 0, 0.009)); t += 0.009
    pulses.append((t, 1, 0.0045)); t += 0.0045
    # Address 0x00 (eight 0s), inverted address 0xFF (eight 1s)
    seq = []
    seq += [0] * 8                       # Address 0x00
    seq += [1] * 8                       # Inverted address 0xFF
    # Command 0x45 = 0b01000101, LSB first
    cmd = 0x45
    cmd_bits = [(cmd >> b) & 1 for b in range(8)]
    seq += cmd_bits
    seq += [(~((cmd >> b) & 1)) & 1 for b in range(8)]
    for b in seq:
        pulses.append((t, 0, 0.000560)); t += 0.000560
        pulses.append((t, 1, 0.000560 if b == 0 else 0.001690))
        t += (0.000560 if b == 0 else 0.001690)
    # Final low pulse
    pulses.append((t, 0, 0.000560)); t += 0.000560
    # Repeat code (after a ~10 ms gap)
    t += 0.010
    pulses.append((t, 0, 0.009)); t += 0.009
    pulses.append((t, 1, 0.00225)); t += 0.00225
    pulses.append((t, 0, 0.000560)); t += 0.000560
    return build_wave(0, pulses, rate, max(n, int(t * rate) + 10), idle=1)

register("nec", decode_nec, make_nec_test, "NEC IR remote")
