# -*- coding: utf-8 -*-
"""UART text decoding (firmware frame: 1000 bps, 8N1, LSB first, 10 ticks/bit)."""

TICKS_PER_BIT = 10


def uart_decode(bits):
    """Software UART decode: return the decoded string."""
    out = []
    n = len(bits)
    i = 1
    while i < n:
        # Start bit: falling edge 1->0
        if bits[i-1] == 1 and bits[i] == 0:
            start = i
            mid = start + TICKS_PER_BIT // 2
            # The start-bit midpoint must be 0
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


def scan_frames(bits, ticks=TICKS_PER_BIT):
    """Scan all successfully decoded UART frames; return [(start index, char)].

    ``ticks`` is the number of samples per bit (default 10 = the firmware
    1000 bps frame); other slow baud rates pass their own value. The
    default call keeps the exact original behavior.
    """
    frames = []
    n = len(bits)
    half = max(1, ticks // 2)
    i = 1
    while i < n:
        if bits[i - 1] == 1 and bits[i] == 0:
            start = i
            mid = start + half
            if mid < n and bits[mid] == 0:
                byte = 0
                ok = True
                for bit in range(8):
                    pos = start + half + ticks * (bit + 1)
                    if pos >= n:
                        ok = False; break
                    if bits[pos] == 1:
                        byte |= (1 << bit)
                stop = start + half + ticks * 9
                if ok and stop < n and bits[stop] == 1:
                    frames.append((start, chr(byte)))
                i = start + ticks * 9
            else:
                i += 1
        else:
            i += 1
    return frames


def best_packet(bits):
    """Find the longest continuous run of frames; return
(wave segment, string, frame list)."""
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
