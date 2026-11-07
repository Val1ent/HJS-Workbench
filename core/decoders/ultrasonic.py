# -*- coding: utf-8 -*-
"""HC-SR04 ultrasonic ranging decoder (TRIG + ECHO -> distance cm)."""
from ..events import event
from ..model import channel_bits
from ..registry import register

# ======================================================================
# 5. HC-SR04 超声波测距（TRIG 触发，ECHO 高电平时间 → 距离）
# ======================================================================
def decode_ultrasonic(samples, rate, trig_ch=0, echo_ch=1):
    """
    TRIG 上升沿 = 一次测量开始；随后 ECHO 高电平时间 = 回波时间。
    距离 cm = 回波秒 * 340m/s / 2 * 100。量程 100us~50ms（约 1.7cm~8.5m）。
    """
    trig = channel_bits(samples, trig_ch)
    echo = channel_bits(samples, echo_ch)
    n = len(samples)
    dt = 1.0 / rate
    events = []
    i = 0
    while i < n - 1:
        if trig[i] == 0 and trig[i + 1] == 1:
            tr = i + 1
            events.append(event(tr * dt, trig_ch, "TRIG", "触发脉冲"))
            er = None
            j = tr
            while j < n - 1:                       # 找 ECHO 上升沿
                if echo[j] == 0 and echo[j + 1] == 1:
                    er = j + 1
                    break
                j += 1
            if er is not None:
                ef = n
                j = er
                while j < n - 1:                   # 找 ECHO 下降沿
                    if echo[j] == 1 and echo[j + 1] == 0:
                        ef = j + 1
                        break
                    j += 1
                dur = (ef - er) * dt
                cm = dur * 340.0 / 2.0 * 100.0
                if 0.0001 <= dur <= 0.05:
                    events.append(event(er * dt, echo_ch, "DISTANCE",
                                        f"回波={dur * 1e6:.0f}us 距离≈{cm:.1f}cm"))
                else:
                    events.append(event(er * dt, echo_ch, "DIST_ERR",
                                        f"回波={dur * 1e6:.0f}us 超出量程"))
                i = er
            else:
                i = tr
            continue
        i += 1
    events.sort(key=lambda e: e["t"])
    return events

def make_ultrasonic_test(rate):
    """两次测量：回波 1.0ms→≈17.0cm；回波 1.5ms→≈25.5cm（声速 340m/s）。"""
    n = int(0.05 * rate)
    trig = [0] * n
    echo = [0] * n

    def put(arr, t0, t1, val):
        a = max(0, int(round(t0 * rate)))
        b = min(n, int(round(t1 * rate)))
        for i in range(a, b):
            arr[i] = val

    put(trig, 0.003, 0.0031, 1)
    put(echo, 0.004, 0.005, 1)          # 1.0ms 回波 → 17.0cm
    put(trig, 0.030, 0.0301, 1)
    put(echo, 0.031, 0.0325, 1)         # 1.5ms 回波 → 25.5cm
    return [(trig[i]) | (echo[i] << 1) for i in range(n)]

register("ultrasonic", decode_ultrasonic, make_ultrasonic_test, "超声测距HC-SR04")
