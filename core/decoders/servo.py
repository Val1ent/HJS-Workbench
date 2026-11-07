# -*- coding: utf-8 -*-
"""Servo PWM / PPM decoder."""
from ..events import event
from ..model import channel_bits
from ..registry import register
from ..segments import build_wave, edges_of

# ======================================================================
# 舵机 PWM / PPM（同一条线：20ms 周期单舵机 PWM 或 多通道 PPM 帧）
# ======================================================================
def decode_servo(samples, rate, ch=0):
    """
    识别两类信号：
      A. 标准舵机 PWM：周期 18~22ms、脉宽 500~2500us，
         角度 = (脉宽us - 1000) / 1000 * 180，结果钳制在 0~180。
      B. PPM 多通道帧：帧内相邻上升沿间隔 = 通道值（500~4000us），
         帧间隔（同步）> 4000us；一帧 >= 4 个通道才输出 PPM。
    """
    bits = channel_bits(samples, ch)
    n = len(bits)
    dt = 1.0 / rate
    edges = edges_of(bits)
    # 只取真实跳变沿（去掉 edges_of 附带的初始电平点）
    rising = [i for (i, lvl) in edges if lvl == 1 and i > 0]
    falling = [i for (i, lvl) in edges if lvl == 0 and i > 0]
    events = []

    # ---- A. 标准舵机 PWM：上升沿到下一个上升沿 = 一个完整周期 ----
    for i in range(len(rising) - 1):
        a, b = rising[i], rising[i + 1]
        per_us = (b - a) * 1e6 / rate
        if 18000.0 <= per_us <= 22000.0:            # 18~22ms 合法周期
            pw_us = None
            for f in falling:                        # 周期内的下降沿 = 脉宽
                if a < f < b:
                    pw_us = (f - a) * 1e6 / rate
                    break
            if pw_us is not None and 500.0 <= pw_us <= 2500.0:
                ang = (pw_us - 1000.0) / 1000.0 * 180.0
                if ang < 0.0:
                    ang = 0.0
                elif ang > 180.0:
                    ang = 180.0
                events.append(event(a * dt, ch, "SERVO",
                                    f"脉宽={pw_us:.0f}us 角度={ang:.1f}°"))

    # ---- B. PPM：相邻上升沿 500~4000us 为通道值，>4000us 为帧同步 ----
    frame = []          # 当前帧内的上升沿索引

    def flush_ppm():
        gaps = []
        for k in range(len(frame) - 1):
            g_us = (frame[k + 1] - frame[k]) * 1e6 / rate
            if 500.0 <= g_us <= 4000.0:
                gaps.append(g_us)
        if len(gaps) >= 4:
            vals = ",".join(f"{g:.0f}" for g in gaps)
            events.append(event(frame[0] * dt, ch, "PPM",
                                f"{len(gaps)}通道: [{vals}]"))

    for r in rising:
        if frame and (r - frame[-1]) * 1e6 / rate > 4000.0:
            flush_ppm()
            frame = []
        frame.append(r)
    flush_ppm()

    events.sort(key=lambda e: e["t"])
    return events

def make_servo_test(rate):
    """
    3 个 20ms 舵机周期：脉宽 1000/1500/2000us → 0°/90°/180°；
    第 4 个脉冲用于凑出第 3 个完整周期（上升沿到下一个上升沿）。
    """
    n = int(0.09 * rate)            # 90ms
    pulses = [
        (0.005, 1, 0.0010),         # 1000us → 0°
        (0.025, 1, 0.0015),         # 1500us → 90°
        (0.045, 1, 0.0020),         # 2000us → 180°
        (0.065, 1, 0.0020),         # 补第 4 个上升沿，凑出第 3 个完整周期
    ]
    return build_wave(0, pulses, rate, n, idle=0)

register("servo", decode_servo, make_servo_test, "舵机PWM/PPM")
