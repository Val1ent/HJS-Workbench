# -*- coding: utf-8 -*-
"""Slow SPI decoder (SCK/MOSI/MISO/CS, CPOL/CPHA, MSB first)."""
from ..events import event
from ..model import channel_bits
from ..registry import register


# ======================================================================
# 1. Slow SPI (demo: SCK=1 kHz, CPOL=0/CPHA=0, MSB first)
# ======================================================================
def decode_spi(samples, rate, sck_ch=2, mosi_ch=3, miso_ch=4, cs_ch=5,
               cpol=0, cpha=0):
    """
    While CS is asserted (low), group MOSI/MISO bits into bytes of 8 on
    the sampling edges (MSB first).
    Sampling edge rule: CPOL=0 leading edge = rising, CPOL=1 leading
    edge = falling; CPHA=0 samples on the leading edge, CPHA=1 on the
    trailing edge.
    """
    sck = channel_bits(samples, sck_ch)
    mosi = channel_bits(samples, mosi_ch)
    miso = channel_bits(samples, miso_ch)
    cs = channel_bits(samples, cs_ch)
    n = len(samples)
    dt = 1.0 / rate
    events = []
    sample_rising = (cpol == cpha)     # With CPOL == CPHA the sampling
                                       # edge is the rising edge
    sample_idx = set()
    for i in range(1, n):
        if sample_rising and sck[i - 1] == 0 and sck[i] == 1:
            sample_idx.add(i)
        elif not sample_rising and sck[i - 1] == 1 and sck[i] == 0:
            sample_idx.add(i)

    active = False
    bits_m = []
    bits_s = []
    t_byte = 0.0
    for i in range(n):
        if cs[i] == 0 and not active:
            active = True
            bits_m = []
            bits_s = []
            events.append(event(i * dt, cs_ch, "CS_LOW", "CS low, transfer start"))
        elif cs[i] == 1 and active:
            active = False
            events.append(event(i * dt, cs_ch, "CS_HIGH", "CS high, transfer end"))
        elif active and i in sample_idx:
            if not bits_m:
                t_byte = i * dt
            bits_m.append(mosi[i])
            bits_s.append(miso[i])
            if len(bits_m) == 8:
                vm = vs = 0
                for b in bits_m:                 # MSB first
                    vm = (vm << 1) | b
                for b in bits_s:
                    vs = (vs << 1) | b
                events.append(event(t_byte, sck_ch, "SPI",
                                    f"MOSI=0x{vm:02X} MISO=0x{vs:02X}"))
                bits_m = []
                bits_s = []
    events.sort(key=lambda e: e["t"])
    return events

def make_spi_test(rate):
    """Slow SPI: CS low -> MOSI 0x3C,0xA5 / MISO 0x11,0x22 -> CS high."""
    n = int(0.06 * rate)
    sck = [1] * n
    mosi = [0] * n
    miso = [0] * n
    cs = [1] * n

    def put(arr, t0, t1, val):
        a = max(0, int(round(t0 * rate)))
        b = min(n, int(round(t1 * rate)))
        for i in range(a, b):
            arr[i] = val

    T = 0.001                       # 1 kHz clock
    half = 0.0005
    t = 0.003
    put(cs, t, t + 0.0165, 0)       # CS low for 16 clocks + margin

    def send(m, s):
        nonlocal t
        for k in range(8):
            bm = (m >> (7 - k)) & 1
            bs = (s >> (7 - k)) & 1
            put(sck, t, t + half, 0)          # SCK low half period
            put(mosi, t, t + T, bm)           # Data set up while SCK is low
            put(miso, t, t + T, bs)
            put(sck, t + half, t + T, 1)      # SCK high half period (sampling
                                              # edge)
            t += T

    send(0x3C, 0x11)
    send(0xA5, 0x22)
    # Merge: SCK=D2 MOSI=D3 MISO=D4 CS=D5
    return [(sck[i] << 2) | (mosi[i] << 3) | (miso[i] << 4) | (cs[i] << 5)
            for i in range(n)]

register("spi", decode_spi, make_spi_test, "Slow SPI")
