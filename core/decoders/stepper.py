# -*- coding: utf-8 -*-
"""Stepper motor STEP/DIR decoder."""
from ..events import event
from ..model import channel_bits
from ..registry import register

# ======================================================================
# 2. 步进电机 STEP/DIR（STEP 上升沿走一步，DIR 高=正转）
# ======================================================================
def decode_stepper(samples, rate, step_ch=0, dir_ch=1):
    """
    STEP 上升沿 = 一步；DIR=1 正转（+1），DIR=0 反转（-1）。
    输出逐步事件（前 20 步 + 此后每 20 步抽样，避免实时刷屏）与
    收尾汇总（总步数/累计位置/换向次数/平均与峰值速度）。
    """
    step = channel_bits(samples, step_ch)
    dirn = channel_bits(samples, dir_ch)
    n = len(samples)
    dt = 1.0 / rate
    events = []
    pos = 0
    steps = 0
    flips = 0
    prev_dir = None
    last_t = None
    speeds = []
    for i in range(1, n):
        if step[i - 1] == 0 and step[i] == 1:
            d = 1 if dirn[i] else 0
            pos += 1 if d else -1
            steps += 1
            t_now = i * dt
            if prev_dir is not None and prev_dir != d:
                flips += 1
            prev_dir = d
            sp_txt = ""
            if last_t is not None and t_now > last_t:
                sp = 1.0 / (t_now - last_t)
                speeds.append(sp)
                sp_txt = f" 速度={sp:.0f}步/s"
            last_t = t_now
            if steps <= 20 or steps % 20 == 0:
                events.append(event(t_now, step_ch, "STEP",
                    f"第{steps}步 方向={'正' if d else '反'} 累计={pos:+d}{sp_txt}"))
    if steps:
        avg = sum(speeds) / len(speeds) if speeds else 0.0
        pk = max(speeds) if speeds else 0.0
        events.append(event((n - 1) * dt, step_ch, "STEP_SUM",
            f"共{steps}步 累计={pos:+d} 换向{flips}次 "
            f"均速={avg:.0f}步/s 峰值={pk:.0f}步/s"))
    events.sort(key=lambda e: e["t"])
    return events

def make_stepper_test(rate):
    """30 步正转 + 10 步反转，步间隔 500us（2kHz 步进），DIR=D1。"""
    n = int(0.06 * rate)
    step = [0] * n
    dirn = [1] * n

    def put(arr, t0, t1, val):
        a = max(0, int(round(t0 * rate)))
        b = min(n, int(round(t1 * rate)))
        for i in range(a, b):
            arr[i] = val

    t = 0.005

    def burst(count, d, per=0.0005):
        nonlocal t
        put(dirn, t, t + count * per, d)
        for _ in range(count):
            put(step, t, t + 0.0002, 1)     # 200us 高脉冲
            t += per

    burst(30, 1)                            # 正转 30 步
    burst(10, 0)                            # 反转 10 步
    return [(step[i]) | (dirn[i] << 1) for i in range(n)]

register("stepper", decode_stepper, make_stepper_test, "步进电机STEP/DIR")
