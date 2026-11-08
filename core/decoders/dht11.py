# -*- coding: utf-8 -*-
"""DHT11 temperature/humidity decoder (one data line, channel 0).

Real DHT11 timing: the host pulls the line low for at least 18 ms, the
sensor answers with an 80 us low / 80 us high response, and each of the
40 data bits starts with a 50 us low followed by a high level of about
26-27 us (bit 0) or 70 us (bit 1). Those real pulse widths are far below
the 200 us limit of a 10 kHz sampling device, so genuine high-speed DHT11
captures need a higher sample-rate device; this decoder only claims to
resolve pulses the capture rate can actually represent.

The self-test waveform keeps every pulse at 200 us or more: a 2 ms start
pulse, a 200 us / 200 us response, and data bits with a 200 us low and a
300 us (0) or 700 us (1) high, which the same decoder resolves.
"""
from ..events import event
from ..model import channel_bits
from ..registry import register
from ..segments import build_wave, pulse_widths


def _us(w):
    return w * 1_000_000.0


def decode_dht11(samples, rate, ch=0):
    bits = channel_bits(samples, ch)
    segs = pulse_widths(bits, rate)          # [(start, level, width_s), ...]
    dt = 1.0 / rate
    events = []
    i = 0
    n = len(segs)
    while i < n:
        start, lvl, w = segs[i]
        # Start: host pulls low >= 1 ms (real DHT11: >= 18 ms)
        if lvl == 0 and _us(w) >= 1000:
            t_start = start * dt
            events.append(event(t_start, ch, "DHT11_START",
                                "host start pulse"))
            # Host releases, sensor pulls the line back low (response)
            j = i + 1
            if j + 1 < n:
                _, lvl_a, w_a = segs[j]      # release high
                _, lvl_b, w_b = segs[j + 1]  # response low
                _, lvl_c, w_c = segs[j + 2]  # response high
                if (lvl_a == 1 and lvl_b == 0 and lvl_c == 1
                        and _us(w_b) <= 300 and _us(w_c) <= 300):
                    events.append(event(segs[j + 1][0] * dt, ch,
                                        "DHT11_RESPONSE",
                                        "sensor response pulse"))
                    bits40 = []
                    k = j + 3
                    while len(bits40) < 40 and k + 1 < n:
                        sl, ll, wl = segs[k]
                        sh, lh, wh = segs[k + 1]
                        if ll == 0 and lh == 1 and _us(wl) <= 300:
                            hu = _us(wh)
                            if hu <= 400:          # real ~26 us, test 300 us
                                bits40.append(0)
                            elif hu >= 400:        # real ~70 us, test 700 us
                                bits40.append(1)
                            else:
                                break
                            k += 2
                        else:
                            break
                    if len(bits40) == 40:
                        def take(off):
                            v = 0
                            for b in range(8):     # MSB first
                                v = (v << 1) | bits40[off + b]
                            return v
                        hum_i, hum_d = take(0), take(8)
                        tmp_i, tmp_d = take(16), take(24)
                        chk = take(32)
                        t = t_start
                        if chk == (hum_i + hum_d + tmp_i + tmp_d) & 0xFF:
                            events.append(event(t, ch, "DHT11",
                                f"humidity={hum_i}.{hum_d}% "
                                f"temperature={tmp_i}.{tmp_d}C"))
                        else:
                            events.append(event(t, ch, "DHT11_ERR",
                                f"checksum failed humidity={hum_i} "
                                f"temperature={tmp_i} checksum={chk}"))
                        i = k
                        continue
        i += 1
    events.sort(key=lambda e: e["t"])
    return events


def make_dht11_test(rate):
    """Self-test: humidity 45.0%, temperature 25.0C, checksum 70.

    All pulses are 200 us or longer so a 10 kHz capture resolves them.
    """
    n = int(0.12 * rate)
    pulses = []
    t = 0.002                                  # idle high
    pulses.append((t, 0, 0.002)); t += 0.002   # start pulse (real: 18 ms+)
    pulses.append((t, 1, 0.0002)); t += 0.0002  # host release
    pulses.append((t, 0, 0.0002)); t += 0.0002  # response low
    pulses.append((t, 1, 0.0002)); t += 0.0002  # response high
    # 40 data bits, MSB first: 45, 0, 25, 0, checksum 70
    data = [45, 0, 25, 0, 70]
    seq = [(v >> (7 - b)) & 1 for v in data for b in range(8)]
    for b in seq:
        pulses.append((t, 0, 0.0002)); t += 0.0002            # bit low
        pulses.append((t, 1, 0.0003 if b == 0 else 0.0007))   # data high
        t += (0.0003 if b == 0 else 0.0007)
    # End marker: a short low bounds the last data high so the idle
    # high level does not extend it.
    pulses.append((t, 0, 0.0002)); t += 0.0002
    return build_wave(0, pulses, rate, max(n, int(t * rate) + 10), idle=1)


register("dht11", decode_dht11, make_dht11_test, "DHT11 temperature/humidity")
