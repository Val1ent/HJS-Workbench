# -*- coding: utf-8 -*-
"""SWD debug-port decoder (SWDIO=D0, SWCLK=D1).

Serial Wire Debug: the host drives SWDIO while SWCLK toggles; every bit is
sampled on the rising edge of SWCLK. A transaction is an 8-bit request
(start=1, APnDP, RnW, A[2:3], parity, stop=0, park=1, LSB first), one
turnaround clock, a 3-bit ACK (0b001 OK, 0b010 WAIT, 0b100 FAULT), and
32 LSB-first data bits plus an even parity bit. A line reset is at least
50 clock cycles with SWDIO high.

Real SWD runs at 1 MHz and up, far beyond a 10 kHz capture, so genuine
high-speed debug traffic needs a higher sample-rate device; this decoder
resolves the slow clock the capture can actually represent. The self-test
uses a 2.5 kHz SWCLK (400 us per bit), a 52-cycle line reset, one DP
register write (0x12345678) and one DP register read (0x87654321), both
with valid parity and ACK=OK.
"""
from ..events import event
from ..model import channel_bits
from ..registry import register


def _even_parity(bits):
    return sum(bits) % 2


def _bit_list(value, count, lsb_first=True):
    if lsb_first:
        return [(value >> b) & 1 for b in range(count)]
    return [(value >> (count - 1 - b)) & 1 for b in range(count)]


def decode_swd(samples, rate, swdio_ch=0, swclk_ch=1):
    swdio = channel_bits(samples, swdio_ch)
    swclk = channel_bits(samples, swclk_ch)
    n = len(samples)
    dt = 1.0 / rate
    # Rising edges of SWCLK: bit sampling points
    rises = [i for i in range(1, n) if swclk[i - 1] == 0 and swclk[i] == 1]
    events = []
    r = 0
    m = len(rises)
    while r < m:
        # Try to match an 8-bit request starting at this clock:
        # bit0 start=1, bit6 stop=0, bit7 park=1, bit5 = even parity
        # over bits 1-4 (APnDP, RnW, A2, A3). A request must be
        # preceded by at least two idle high clocks so data bits that
        # accidentally look like a request are not matched.
        if r >= 2 and r + 8 <= m and swdio[rises[r]] == 1 \
                and swdio[rises[r - 1]] == 1 and swdio[rises[r - 2]] == 1 \
                and swdio[rises[r + 6]] == 0 and swdio[rises[r + 7]] == 1:
            req = [swdio[rises[r + k]] for k in range(8)]
            if req[5] == _even_parity(req[1:5]):
                t_req = rises[r] * dt
                apndp = req[1]
                rnw = req[2]
                addr = (req[3] | (req[4] << 1)) << 2
                r += 8
                r += 1                      # turnaround clock
                if r + 3 <= m:
                    ack = 0
                    for k in range(3):      # LSB first
                        if swdio[rises[r + k]]:
                            ack |= (1 << k)
                    r += 3
                    if ack == 1:            # OK
                        if r + 33 <= m:
                            data_bits = [swdio[rises[r + k]]
                                         for k in range(32)]
                            par = swdio[rises[r + 32]]
                            data = 0
                            for b in range(32):     # LSB first
                                if data_bits[b]:
                                    data |= (1 << b)
                            if par == _even_parity(data_bits):
                                par_txt = "parity OK"
                            else:
                                par_txt = "parity ERR"
                            kind = "SWD_READ" if rnw else "SWD_WRITE"
                            bus = "AP" if apndp else "DP"
                            events.append(event(
                                t_req, swdio_ch, kind,
                                f"{bus} addr=0x{addr:X} data=0x{data:08X} "
                                f"{par_txt} ACK=OK"))
                            r += 33
                        continue
                    # WAIT or FAULT: no data phase
                    ack_txt = {2: "WAIT", 4: "FAULT"}.get(ack, f"0x{ack:X}")
                    events.append(event(t_req, swdio_ch, "SWD_ACK",
                                        f"ACK={ack_txt}"))
                    continue
        # No request here: consume a high run (idle or line reset)
        if swdio[rises[r]] == 1:
            run_start = r
            while r < m and swdio[rises[r]] == 1:
                r += 1
            run_len = r - run_start
            if run_len >= 50:
                events.append(event(rises[run_start] * dt, swdio_ch,
                                    "SWD_RESET",
                                    f"line reset ({run_len} high clocks)"))
            # The last cycle of a multi-cycle run can be the start bit of
            # a request; step back one cycle so the loop re-examines it.
            # A one-cycle run has no such ambiguity and must not repeat.
            if r - run_start >= 2:
                r -= 1
            continue
        r += 1
    events.sort(key=lambda e: e["t"])
    return events


def make_swd_test(rate):
    """Self-test: line reset, one DP write and one DP read with OK ACKs."""
    n = int(0.30 * rate)
    swdio = [0] * n
    swclk = [0] * n
    T = 0.0004                       # 400 us clock period (2.5 kHz)
    half = 0.0002
    t = 0.001

    def put(arr, t0, t1, val):
        a = max(0, int(round(t0 * rate)))
        b = min(n, int(round(t1 * rate)))
        for i in range(a, b):
            arr[i] = val

    def cycle(io):
        nonlocal t
        put(swclk, t, t + half, 0)
        put(swdio, t, t + T, io)
        put(swclk, t + half, t + T, 1)
        t += T

    def send_bits(bits):
        for b in bits:
            cycle(b)

    # Line reset: 52 high clock cycles (plus 2 idle cycles around it)
    for _ in range(2):
        cycle(1)
    for _ in range(52):
        cycle(1)
    for _ in range(2):
        cycle(1)
    # DP write 0x12345678 to addr 0x0: req 1 0 0 0 0 0 0 1, ACK OK
    send_bits([1, 0, 0, 0, 0, 0, 0, 1])
    cycle(1)                          # turnaround
    send_bits([1, 0, 0])              # ACK = OK (LSB first)
    data = 0x12345678
    bits = _bit_list(data, 32)
    send_bits(bits)
    cycle(_even_parity(bits))
    for _ in range(2):
        cycle(1)                      # idle
    # DP read 0x87654321 from addr 0x0: req 1 0 1 0 0 1 0 1, ACK OK
    send_bits([1, 0, 1, 0, 0, 1, 0, 1])
    cycle(1)                          # turnaround
    send_bits([1, 0, 0])              # ACK = OK (LSB first)
    data = 0x87654321
    bits = _bit_list(data, 32)
    send_bits(bits)
    cycle(_even_parity(bits))
    for _ in range(2):
        cycle(1)
    return [(swclk[i] << 1) | swdio[i] for i in range(n)]


register("swd", decode_swd, make_swd_test, "SWD debug port")
