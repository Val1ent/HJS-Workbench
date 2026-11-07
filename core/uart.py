# -*- coding: utf-8 -*-
"""UART text decoding (firmware frame: 1000 bps, 8N1, LSB first, 10 ticks/bit)."""

TICKS_PER_BIT = 10


def uart_decode(bits):
    """软件 UART 解码：返回解出的字符串"""
    out = []
    n = len(bits)
    i = 1
    while i < n:
        # 起始位：下降沿 1->0
        if bits[i-1] == 1 and bits[i] == 0:
            start = i
            mid = start + TICKS_PER_BIT // 2
            # 起始位中点应为 0
            if mid < n and bits[mid] == 0:
                byte = 0
                ok = True
                for bit in range(8):
                    pos = start + TICKS_PER_BIT//2 + TICKS_PER_BIT*(bit+1)
                    if pos >= n:
                        ok = False; break
                    if bits[pos] == 1:
                        byte |= (1 << bit)
                stop = start + TICKS_PER_BIT//2 + TICKS_PER_BIT*9
                if ok and stop < n and bits[stop] == 1:
                    out.append(chr(byte))
            i = start + TICKS_PER_BIT * 9
        else:
            i += 1
    return ''.join(out)


def scan_frames(bits):
    """扫描所有成功解码的 UART 帧，返回 [(起始位置, 字符)]"""
    frames = []
    n = len(bits)
    i = 1
    while i < n:
        if bits[i - 1] == 1 and bits[i] == 0:
            start = i
            mid = start + TICKS_PER_BIT // 2
            if mid < n and bits[mid] == 0:
                byte = 0
                ok = True
                for bit in range(8):
                    pos = start + TICKS_PER_BIT // 2 + TICKS_PER_BIT * (bit + 1)
                    if pos >= n:
                        ok = False; break
                    if bits[pos] == 1:
                        byte |= (1 << bit)
                stop = start + TICKS_PER_BIT // 2 + TICKS_PER_BIT * 9
                if ok and stop < n and bits[stop] == 1:
                    frames.append((start, chr(byte)))
                i = start + TICKS_PER_BIT * 9
            else:
                i += 1
        else:
            i += 1
    return frames


def best_packet(bits):
    """找出帧最多的连续报文，返回 (波形段, 字符串, 帧列表)"""
    frames = scan_frames(bits)
    if len(frames) < 2:
        return None
    groups = []
    cur = [frames[0]]
    for f in frames[1:]:
        if f[0] - cur[-1][0] <= TICKS_PER_BIT * 13:
            cur.append(f)
        else:
            groups.append(cur)
            cur = [f]
    groups.append(cur)
    g = max(groups, key=lambda x: len(x))
    if len(g) < 2:
        return None
    s0 = g[0][0]
    s1 = g[-1][0] + TICKS_PER_BIT * 10
    return bits[s0:s1], ''.join(c for _, c in g), g
