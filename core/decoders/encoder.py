# -*- coding: utf-8 -*-
"""Quadrature encoder A/B/Z decoder."""
from ..events import event
from ..model import channel_bits
from ..registry import register

# ======================================================================
# 3. 正交编码器 A/B/Z（4 倍频计数，Z 相零点复位）
# ======================================================================
def decode_encoder(samples, rate, a_ch=0, b_ch=1, z_ch=2, ppr=None):
    """
    x4 计数：A/B 每个跳变沿计一次。A 超前 B 为正转。
    z_ch 给出时，Z 相上升沿把位置清零并输出 ZERO 事件（无 Z 相时传 z_ch=None）；
    ppr 给出每转脉冲数时，事件里附带转速 RPM（RPM=沿速/(4*ppr)*60）。
    事件抽样输出（前 30 沿 + 此后每 30 沿），末尾给汇总。
    """
    a = channel_bits(samples, a_ch)
    b = channel_bits(samples, b_ch)
    z = channel_bits(samples, z_ch) if z_ch is not None else None
    n = len(samples)
    if n == 0:
        return []            # 空数据直接返回，保证不崩溃
    dt = 1.0 / rate
    FWD = {(0, 0): (1, 0), (1, 0): (1, 1), (1, 1): (0, 1), (0, 1): (0, 0)}
    REV = {(0, 0): (0, 1), (0, 1): (1, 1), (1, 1): (1, 0), (1, 0): (0, 0)}
    events = []
    pos = 0
    edges_cnt = 0
    last_t = None
    speeds = []
    prev = (a[0], b[0])
    for i in range(1, n):
        if z is not None and z[i - 1] == 0 and z[i] == 1:
            pos = 0
            events.append(event(i * dt, z_ch, "ZERO", "Z相零点 位置复位=0"))
        cur = (a[i], b[i])
        if cur != prev:
            if FWD.get(prev) == cur:
                delta = 1
            elif REV.get(prev) == cur:
                delta = -1
            else:
                delta = 0            # 双相同时跳变（毛刺），忽略
            if delta:
                pos += delta
                edges_cnt += 1
                t_now = i * dt
                if last_t is not None and t_now > last_t:
                    speeds.append(1.0 / (t_now - last_t))
                last_t = t_now
                if edges_cnt <= 30 or edges_cnt % 30 == 0:
                    rpm = ""
                    if ppr and speeds:
                        rpm = (f" 转速="
                               f"{sum(speeds[-30:]) / len(speeds[-30:]) / (ppr * 4) * 60:.0f}RPM")
                    events.append(event(t_now, a_ch, "ENCODER",
                        f"第{edges_cnt}沿 {'正' if delta > 0 else '反'} "
                        f"位置={pos:+d}{rpm}"))
            prev = cur
    if edges_cnt:
        avg = sum(speeds) / len(speeds) if speeds else 0.0
        events.append(event((n - 1) * dt, a_ch, "ENCODER_SUM",
                            f"共{edges_cnt}沿 位置={pos:+d} 平均={avg:.1f}沿/s"))
    events.sort(key=lambda e: e["t"])
    return events

def make_encoder_test(rate):
    """A 超前 B 正转 25 圈周期（100 沿）→ Z 脉冲清零 → 反转 5 周期（20 沿）。"""
    n = int(0.06 * rate)
    a = [0] * n
    b = [0] * n
    z = [0] * n

    def put(arr, t0, t1, val):
        aa = max(0, int(round(t0 * rate)))
        bb = min(n, int(round(t1 * rate)))
        for i in range(aa, bb):
            arr[i] = val

    dur = 0.00025                      # 每个相位 250us
    t = 0.002
    FWD = [(1, 0), (1, 1), (0, 1), (0, 0)]     # A 超前 B
    REV = [(0, 1), (1, 1), (1, 0), (0, 0)]     # B 超前 A

    def cycle(seq):
        nonlocal t
        for (av, bv) in seq:
            put(a, t, t + dur, av)
            put(b, t, t + dur, bv)
            t += dur

    for _ in range(25):
        cycle(FWD)
    put(z, t - dur, t, 1)              # Z 相脉冲（零点复位）
    for _ in range(5):
        cycle(REV)
    return [(a[i]) | (b[i] << 1) | (z[i] << 2) for i in range(n)]

register("encoder", decode_encoder, make_encoder_test, "正交编码器A/B/Z")
