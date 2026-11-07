# -*- coding: utf-8 -*-
"""Slow I2C decoder (SCL=D1, SDA=D0)."""
from ..events import event
from ..model import channel_bits
from ..registry import register

# ======================================================================
# 慢速 I2C（SCL=D1，SDA=D0；空闲 SCL=1、SDA=1；MSB 先发，9 位一组）
# ======================================================================
def decode_i2c(samples, rate, scl_ch=1, sda_ch=0):
    """
    慢速 I2C 解码（10kHz 采样适合 SCL<=1kHz）：
      START/STOP：SCL 为高时 SDA 跳变（1->0 起始，0->1 停止）；
      数据：在 SCL 上升沿采样 SDA，每 9 位一组（8 数据 MSB 先 + ACK）；
      第一组 = 7 位从机地址 + R/W（0=写 W，1=读 R），ACK 位 0=ACK、1=NACK。
    """
    scl = channel_bits(samples, scl_ch)
    sda = channel_bits(samples, sda_ch)
    n = len(samples)
    dt = 1.0 / rate
    marks = []                                   # (索引, 类型, SDA采样值)
    for i in range(1, n):                        # 总线条件：SCL 高时 SDA 跳变
        if sda[i] != sda[i - 1] and scl[i] == 1:
            marks.append((i, "STOP" if sda[i] == 1 else "START", None))
    for i in range(1, n):                        # 数据采样点：SCL 上升沿
        if scl[i - 1] == 0 and scl[i] == 1:
            marks.append((i, "SCLK", sda[i]))
    marks.sort(key=lambda m: (m[0], m[1] != "SCLK"))   # 同采样点先处理总线条件

    events = []
    in_trans = False
    bits = []
    t_byte = 0.0
    first_byte = True
    for idx, kind, val in marks:
        if kind == "START":
            in_trans = True
            bits = []
            first_byte = True
            events.append(event(idx * dt, sda_ch, "START", "起始条件"))
        elif kind == "STOP":
            if in_trans:
                events.append(event(idx * dt, sda_ch, "STOP", "停止条件"))
            in_trans = False
            bits = []
        elif in_trans:
            if not bits:
                t_byte = idx * dt                  # 本字节首 bit 时刻
            bits.append(val)
            if len(bits) == 9:
                val8 = 0
                for b in bits[:8]:                 # MSB 先发
                    val8 = (val8 << 1) | b
                ack = "ACK" if bits[8] == 0 else "NACK"
                if first_byte:
                    addr = val8 >> 1               # 高 7 位为从机地址
                    rw = "R" if (val8 & 1) else "W"
                    events.append(event(t_byte, sda_ch, "ADDR",
                                        f"0x{addr:02X} {rw} {ack}"))
                    first_byte = False
                else:
                    events.append(event(t_byte, sda_ch, "DATA",
                                        f"0x{val8:02X} {ack}"))
                bits = []
    events.sort(key=lambda e: e["t"])
    return events

def make_i2c_test(rate):
    """
    慢速 I2C 写传输：START → 地址 0x48+W（=0x90，ACK）→ 数据 0x55（ACK）→ STOP。
    SCL 周期 1000us（1kHz，10kHz 采样下高/低半周期各 5 个采样点）。
    SDA 用 D0（sda_ch=0），SCL 用 D1（scl_ch=1），按位或合并互不覆盖。
    """
    n = int(0.05 * rate)            # 50ms
    scl = [1] * n                   # 空闲 SCL=1
    sda = [1] * n                   # 空闲 SDA=1
    T = 0.001                       # 1000us 时钟周期
    half = 0.0005

    def put(arr, t0, t1, val):
        a = max(0, int(round(t0 * rate)))
        b = min(n, int(round(t1 * rate)))
        for i in range(a, b):
            arr[i] = val

    def send_byte(value, ack=0):
        nonlocal t
        data = [(value >> (7 - b)) & 1 for b in range(8)]
        for b in data:
            put(scl, t, t + half, 0)        # SCL 低半周期
            put(sda, t, t + T, b)           # SDA 在 SCL 低时建立
            put(scl, t + half, t + T, 1)    # SCL 高半周期（采样点）
            t += T
        put(scl, t, t + half, 0)            # 第 9 个时钟：ACK 位
        put(sda, t, t + T, ack)
        put(scl, t + half, t + T, 1)
        t += T

    t = 0.002
    put(sda, t, t + 0.0004, 0)              # START：SCL 高时 SDA 高->低
    t += 0.0004
    send_byte(0x90)                         # 地址 0x48 + W(0)
    send_byte(0x55)                         # 数据 0x55
    put(sda, t, t + 0.0004, 1)              # STOP：SCL 高时 SDA 低->高

    # 合并两通道：SDA=D0，SCL=D1
    return [(scl[i] << 1) | sda[i] for i in range(n)]

register("i2c", decode_i2c, make_i2c_test, "慢速I2C")
