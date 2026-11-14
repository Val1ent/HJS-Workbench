# -*- coding: utf-8 -*-
"""Slow I2C decoder (SCL=D1, SDA=D0)."""
from ..events import event
from ..model import channel_bits
from ..registry import register


# ======================================================================
# Slow I2C (SCL=D1, SDA=D0; idle SCL=1, SDA=1; MSB first, 9 bits per
# group)
# ======================================================================
def decode_i2c(samples, rate, scl_ch=1, sda_ch=0):
    """
    Slow I2C decode (10 kHz sampling suits SCL <= 1 kHz):
      START/STOP: SDA transitions while SCL is high (1->0 start,
      0->1 stop);
      Data: sample SDA on SCL rising edges, in groups of 9 bits
      (8 data bits MSB first + ACK);
      First group = 7-bit slave address + R/W (0=write W, 1=read R),
      ACK bit 0=ACK, 1=NACK.
    """
    scl = channel_bits(samples, scl_ch)
    sda = channel_bits(samples, sda_ch)
    n = len(samples)
    dt = 1.0 / rate
    marks = []                                   # (index, kind, SDA sample value)
    for i in range(1, n):                        # Bus conditions: SDA
                                                # transitions while SCL is high
        if sda[i] != sda[i - 1] and scl[i] == 1:
            marks.append((i, "STOP" if sda[i] == 1 else "START", None))
    for i in range(1, n):                        # Data sampling points: SCL
                                                # rising edges
        if scl[i - 1] == 0 and scl[i] == 1:
            marks.append((i, "SCLK", sda[i]))
    marks.sort(key=lambda m: (m[0], m[1] != "SCLK"))   # At the same sample
                                                       # point, handle the bus
                                                       # condition first

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
            events.append(event(idx * dt, sda_ch, "START", "start condition"))
        elif kind == "STOP":
            if in_trans:
                events.append(event(idx * dt, sda_ch, "STOP", "stop condition"))
            in_trans = False
            bits = []
        elif in_trans:
            if not bits:
                t_byte = idx * dt                  # Time of the first bit of
                                                  # this byte
            bits.append(val)
            if len(bits) == 9:
                val8 = 0
                for b in bits[:8]:                 # MSB first
                    val8 = (val8 << 1) | b
                ack = "ACK" if bits[8] == 0 else "NACK"
                if first_byte:
                    addr = val8 >> 1               # Upper 7 bits = slave
                                                  # address
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
    Slow I2C write transaction: START -> address 0x48+W (=0x90, ACK) ->
    data 0x55 (ACK) -> STOP.
    SCL period 1000us (1 kHz; with 10 kHz sampling each half period is
    5 sample points). SDA uses D0 (sda_ch=0), SCL uses D1 (scl_ch=1);
    the bitwise OR merge keeps the two channels from overwriting each
    other.
    """
    n = int(0.05 * rate)            # 50ms
    scl = [1] * n                   # Idle SCL=1
    sda = [1] * n                   # Idle SDA=1
    T = 0.001                       # 1000us clock period
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
            put(scl, t, t + half, 0)        # SCL low half period
            put(sda, t, t + T, b)           # SDA set up while SCL is low
            put(scl, t + half, t + T, 1)    # SCL high half period (sampling
                                            # point)
            t += T
        put(scl, t, t + half, 0)            # 9th clock: ACK bit
        put(sda, t, t + T, ack)
        put(scl, t + half, t + T, 1)
        t += T

    t = 0.002
    put(sda, t, t + 0.0004, 0)              # START: SDA high->low while SCL
                                            # is high
    t += 0.0004
    send_byte(0x90)                         # Address 0x48 + W(0)
    send_byte(0x55)                         # Data 0x55
    put(sda, t, t + 0.0004, 1)              # STOP: SDA low->high while SCL
                                            # is high

    # Merge the two channels: SDA=D0, SCL=D1
    return [(scl[i] << 1) | sda[i] for i in range(n)]

register("i2c", decode_i2c, make_i2c_test, "Slow I2C")
