# -*- coding: utf-8 -*-
"""Edge detection, pulse segmentation, and test waveform building."""
from .model import set_channel


def edges_of(bits):
    """返回电平跳变沿列表：[(index, new_level), ...]（含初始电平）。"""
    out = []
    if not bits:
        return out
    out.append((0, bits[0]))
    for i in range(1, len(bits)):
        if bits[i] != bits[i - 1]:
            out.append((i, bits[i]))
    return out


def pulse_widths(bits, rate):
    """把单通道序列切成连续电平段：[(start_index, level, 宽度_秒), ...]。"""
    dt = 1.0 / rate
    segs = []
    start = 0
    for i in range(1, len(bits)):
        if bits[i] != bits[start]:
            segs.append((start, bits[start], (i - start) * dt))
            start = i
    segs.append((start, bits[start], (len(bits) - start) * dt))
    return segs


def build_wave(ch, pulses, rate, n, idle=1):
    """
    生成 8 通道测试波形（其余通道为 0）。
    pulses: [(起始秒, 电平, 时长秒), ...]，按时间顺序；空闲为 idle。
    """
    samples = [0] * n
    # 先铺空闲电平
    for i in range(n):
        set_channel(samples, i, ch, idle)
    for (t0, lvl, dur) in pulses:
        a = int(round(t0 * rate))
        b = int(round((t0 + dur) * rate))
        for i in range(max(0, a), min(n, b)):
            set_channel(samples, i, ch, lvl)
    return samples
