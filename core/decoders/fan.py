# -*- coding: utf-8 -*-
"""4-wire fan speed decoder (TACH falling-edge intervals -> RPM)."""
from ..events import event
from ..model import channel_bits
from ..registry import register

# ======================================================================
# 6. 4 线风扇转速（TACH 每圈 2 个脉冲，下降沿间隔 → RPM）
# ======================================================================
def decode_fan(samples, rate, tach_ch=0, pulses_per_rev=2):
    """
    TACH 每转输出 pulses_per_rev（默认 2）个脉冲；下降沿间隔 = 半圈时间。
    RPM = 60 / (间隔秒 * 每转脉冲数)。每攒满 5 个间隔输出一次滑动平均，
    末尾输出整体平均/最低/最高。
    """
    tach = channel_bits(samples, tach_ch)
    n = len(samples)
    dt = 1.0 / rate
    falls = [i for i in range(1, n) if tach[i - 1] == 1 and tach[i] == 0]
    events = []
    win = []
    for k in range(len(falls) - 1):
        per = (falls[k + 1] - falls[k]) * dt
        if not (0.0001 <= per <= 1.0):      # 忽略异常间隔
            continue
        win.append(per)
        if len(win) > 5:
            win.pop(0)
        if len(win) == 5:
            rpms = [60.0 / (p * pulses_per_rev) for p in win]
            events.append(event(falls[k] * dt, tach_ch, "FAN",
                                f"转速≈{sum(rpms) / len(rpms):.0f}RPM"))
    if win:
        rpms = [60.0 / (p * pulses_per_rev) for p in win]
        events.append(event((n - 1) * dt, tach_ch, "FAN_SUM",
            f"平均={sum(rpms) / len(rpms):.0f}RPM "
            f"最低={min(rpms):.0f} 最高={max(rpms):.0f}"))
    events.sort(key=lambda e: e["t"])
    return events

def make_fan_test(rate):
    """3000RPM 风扇：2 脉冲/圈 → 100 脉冲/s → 脉冲周期 10ms，共 20 个脉冲。"""
    n = int(0.25 * rate)
    tach = [0] * n

    def put(arr, t0, t1, val):
        a = max(0, int(round(t0 * rate)))
        b = min(n, int(round(t1 * rate)))
        for i in range(a, b):
            arr[i] = val

    t = 0.010
    period = 0.010                      # 10ms = 3000RPM×2脉冲/圈
    for _ in range(20):
        put(tach, t, t + period / 2, 1)  # 50% 占空比
        t += period
    return tach[:]

register("fan", decode_fan, make_fan_test, "风扇转速TACH")
