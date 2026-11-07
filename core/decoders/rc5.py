# -*- coding: utf-8 -*-
"""Infrared RC-5 remote decoder (Philips, 14-bit biphase frames)."""
from ..events import event
from ..model import channel_bits
from ..registry import register

# ======================================================================
# 4. 红外遥控 RC-5（飞利浦，14 位帧，双相编码）
# ======================================================================
def decode_rc5(samples, rate, ch=0):
    """
    RC-5：空闲低；每位 1778us，位中点必有跳变（双相编码）：
      前半高+后半低 = 逻辑 1，前半低+后半高 = 逻辑 0。
    帧 = 起始 1,1 + 翻转位 + 5 位地址 + 6 位命令（MSB 先发）。
    逐候选起点做 14 位结构校验（每位的 1/4 与 3/4 处电平必须相反），
    只接受前两位为 1 的帧，避免半位错位误报。
    """
    bits = channel_bits(samples, ch)
    n = len(bits)
    dt = 1.0 / rate
    events = []
    full = 1778e-6                      # 每位 1.778ms
    rises = [i for i in range(1, n) if bits[i - 1] == 0 and bits[i] == 1]
    used = set()
    for s in rises:
        if s in used:
            continue
        frame = []
        ok = True
        for k in range(14):
            q1 = int(round(s + (k + 0.25) * full * rate))
            q3 = int(round(s + (k + 0.75) * full * rate))
            if q1 >= n or q3 >= n:
                ok = False
                break
            l1, l3 = bits[q1], bits[q3]
            if l1 == l3:                 # 位中点必须有跳变
                ok = False
                break
            frame.append(l1)             # 前半高=1，前半低=0
        if ok and frame[0] == 1 and frame[1] == 1:
            toggle = frame[2]
            addr = 0
            for b in frame[3:8]:
                addr = (addr << 1) | b
            cmd = 0
            for b in frame[8:14]:
                cmd = (cmd << 1) | b
            events.append(event(s * dt, ch, "RC5",
                                f"地址={addr} 命令={cmd} 翻转位={toggle}"))
            end_i = int(round(s + 14 * full * rate))
            for r in rises:              # 帧内候选点不再重复检测
                if s < r < end_i:
                    used.add(r)
    events.sort(key=lambda e: e["t"])
    return events

def make_rc5_test(rate):
    """一帧 RC-5：起始 1,1 + 翻转 0 + 地址 0b00101(5) + 命令 0b100001(33)。"""
    half = 889e-6
    frame = [1, 1, 0] + [0, 0, 1, 0, 1] + [1, 0, 0, 0, 0, 1]
    n = int((0.010 + 14 * 2 * half + 0.010) * rate)
    bits = [0] * n

    def put(t0, t1, val):
        a = max(0, int(round(t0 * rate)))
        b = min(n, int(round(t1 * rate)))
        for i in range(a, b):
            bits[i] = val

    t = 0.010
    for bit in frame:
        put(t, t + half, bit)                    # 前半 = 位值
        put(t + half, t + 2 * half, 1 - bit)     # 后半反相（位中点跳变）
        t += 2 * half
    return bits[:]

register("rc5", decode_rc5, make_rc5_test, "红外RC-5")
