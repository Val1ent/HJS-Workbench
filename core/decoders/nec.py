# -*- coding: utf-8 -*-
"""NEC infrared remote decoder."""
from ..events import event
from ..model import channel_bits
from ..registry import register
from ..segments import build_wave, pulse_widths

# ======================================================================
# 红外遥控 NEC（低电平有效）
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
        # 引导/重复码都以 7~11ms 低电平开头
        if lvl == 0 and _us(w) >= 7000 and _us(w) <= 11000:
            lead_t = start * dt
            if i + 1 < n:
                _, lvl2, w2 = segs[i + 1]
                us2 = _us(w2)
                if lvl2 == 1 and 3500 <= us2 <= 5500:
                    # ---- 引导码，读 32 位 ----
                    events.append(event(lead_t, ch, "LEADER", "NEC引导码"))
                    bits32 = []
                    j = i + 2
                    # 每位 = 低(560us) + 高(数据)
                    while len(bits32) < 32 and j + 1 < n:
                        sl, ll, wl = segs[j]      # 低段
                        sh, lh, wh = segs[j + 1]  # 高段
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
                            for b in range(8):       # LSB 先发
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
                                f"地址=0x{addr:02X} 命令=0x{cmd:02X}"))
                        else:
                            events.append(event(t, ch, "NEC_ERR",
                                f"校验失败 addr=0x{addr:02X}/0x{addr_n:02X} "
                                f"cmd=0x{cmd:02X}/0x{cmd_n:02X}"))
                        i = j
                        continue
                elif lvl2 == 1 and 1800 <= us2 <= 2800:
                    # ---- 重复码 ----
                    events.append(event(start * dt, ch, "REPEAT",
                                        "NEC重复码"))
                    i += 2
                    continue
        i += 1
    events.sort(key=lambda e: e["t"])
    return events

def make_nec_test(rate):
    n = int(0.09 * rate)        # 90ms
    pulses = []
    t = 0.010                   # 10ms 空闲
    # 引导码
    pulses.append((t, 0, 0.009)); t += 0.009
    pulses.append((t, 1, 0.0045)); t += 0.0045
    # 地址 0x00（8 个 0）、地址反码 0xFF（8 个 1）
    seq = []
    seq += [0] * 8                       # 地址 0x00
    seq += [1] * 8                       # 地址反码 0xFF
    # 命令 0x45 = 0b01000101，LSB 先发
    cmd = 0x45
    cmd_bits = [(cmd >> b) & 1 for b in range(8)]
    seq += cmd_bits
    seq += [(~((cmd >> b) & 1)) & 1 for b in range(8)]
    for b in seq:
        pulses.append((t, 0, 0.000560)); t += 0.000560
        pulses.append((t, 1, 0.000560 if b == 0 else 0.001690))
        t += (0.000560 if b == 0 else 0.001690)
    # 结束低脉冲
    pulses.append((t, 0, 0.000560)); t += 0.000560
    # 重复码（再隔约 10ms）
    t += 0.010
    pulses.append((t, 0, 0.009)); t += 0.009
    pulses.append((t, 1, 0.00225)); t += 0.00225
    pulses.append((t, 0, 0.000560)); t += 0.000560
    return build_wave(0, pulses, rate, max(n, int(t * rate) + 10), idle=1)

register("nec", decode_nec, make_nec_test, "红外遥控NEC")
