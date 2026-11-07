# -*- coding: utf-8 -*-
"""Slow SPI decoder (SCK/MOSI/MISO/CS, CPOL/CPHA, MSB first)."""
from ..events import event
from ..model import channel_bits
from ..registry import register

# ======================================================================
# 1. 慢速 SPI（演示：SCK=1kHz，CPOL=0/CPHA=0，MSB 先发）
# ======================================================================
def decode_spi(samples, rate, sck_ch=2, mosi_ch=3, miso_ch=4, cs_ch=5,
               cpol=0, cpha=0):
    """
    在 CS 有效(低)期间，按采样沿取 MOSI/MISO 各 8 位为一字节（MSB 先发）。
    采样沿规则：CPOL=0 前导沿=上升、CPOL=1 前导沿=下降；
               CPHA=0 在前导沿采样、CPHA=1 在后沿采样。
    """
    sck = channel_bits(samples, sck_ch)
    mosi = channel_bits(samples, mosi_ch)
    miso = channel_bits(samples, miso_ch)
    cs = channel_bits(samples, cs_ch)
    n = len(samples)
    dt = 1.0 / rate
    events = []
    sample_rising = (cpol == cpha)     # CPOL==CPHA 时采样沿为上升沿
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
            events.append(event(i * dt, cs_ch, "CS_LOW", "片选拉低，传输开始"))
        elif cs[i] == 1 and active:
            active = False
            events.append(event(i * dt, cs_ch, "CS_HIGH", "片选拉高，传输结束"))
        elif active and i in sample_idx:
            if not bits_m:
                t_byte = i * dt
            bits_m.append(mosi[i])
            bits_s.append(miso[i])
            if len(bits_m) == 8:
                vm = vs = 0
                for b in bits_m:                 # MSB 先发
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
    """慢速 SPI：CS 拉低 → MOSI 0x3C,0xA5 / MISO 0x11,0x22 → CS 拉高。"""
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

    T = 0.001                       # 1kHz 时钟
    half = 0.0005
    t = 0.003
    put(cs, t, t + 0.0165, 0)       # CS 低 16 个时钟 + 余量

    def send(m, s):
        nonlocal t
        for k in range(8):
            bm = (m >> (7 - k)) & 1
            bs = (s >> (7 - k)) & 1
            put(sck, t, t + half, 0)          # SCK 低半周期
            put(mosi, t, t + T, bm)           # 数据在 SCK 低时建立
            put(miso, t, t + T, bs)
            put(sck, t + half, t + T, 1)      # SCK 高半周期（采样沿）
            t += T

    send(0x3C, 0x11)
    send(0xA5, 0x22)
    # 合并：SCK=D2 MOSI=D3 MISO=D4 CS=D5
    return [(sck[i] << 2) | (mosi[i] << 3) | (miso[i] << 4) | (cs[i] << 5)
            for i in range(n)]

register("spi", decode_spi, make_spi_test, "慢速SPI")
