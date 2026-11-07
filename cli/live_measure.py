# -*- coding: utf-8 -*-
"""Streaming measurement screen: per-channel freq/duty, D0 details, edge counts."""
import time
from collections import deque

import core
from . import console

SAMPLE_RATE = 10000
DT          = 1.0 / SAMPLE_RATE
WINDOW      = 3000
NCH         = 8


def run():
    """三合一实时测量：多通道频率/占空比 + D0 详细指标 + 边沿触发计数。"""
    port = console.choose_port()
    if port is None:
        return
    ser = console.open_serial(port)

    raw = deque(maxlen=WINDOW)          # 原始字节（8通道）
    rise_cnt = [0] * NCH                # 边沿触发累计
    fall_cnt = [0] * NCH
    prev = None
    last_show = 0
    print(f"\n已连接 {port}，实时测量中 ...（Ctrl+C 退出）\n")

    try:
        while True:
            n = ser.in_waiting
            if n:
                chunk = ser.read(n)
                for b in chunk:
                    # 边沿触发：与上一字节逐通道比较
                    if prev is not None:
                        for ch in range(NCH):
                            p = (prev >> ch) & 1
                            c = (b >> ch) & 1
                            if p == 0 and c == 1: rise_cnt[ch] += 1
                            if p == 1 and c == 0: fall_cnt[ch] += 1
                    prev = b
                    raw.append(b)
            else:
                time.sleep(0.01)

            if time.time() - last_show >= 0.5 and len(raw) >= 100:
                last_show = time.time()
                console.clear_screen()
                print("===== 数字调试助手 · 三合一实时测量 =====")
                print(f"采样率: {SAMPLE_RATE} Hz   窗口: {len(raw)} 点\n")

                # 1) 多通道频率
                print("-- 多通道频率 --")
                results = []
                for ch in range(NCH):
                    bits = [(b >> ch) & 1 for b in raw]
                    results.append(core.measure(bits))
                    if results[ch]:
                        print(f"  D{ch}: {results[ch]['freq']:8.1f} Hz   占空比 {results[ch]['duty']:5.1f}%")
                    else:
                        print(f"  D{ch}:       --  (无周期信号)")

                # 2) 主通道 D0 详细测量
                m = results[0]
                print("\n-- D0 详细测量 --")
                if m:
                    print(f"  频率      : {m['freq']:.1f} Hz")
                    print(f"  周期      : {m['period']*1000:.3f} ms  "
                          f"(min {m['pmin']*1000:.3f} / max {m['pmax']*1000:.3f})")
                    print(f"  高电平脉宽: {m['high']*1000:.3f} ms")
                    print(f"  低电平脉宽: {m['low']*1000:.3f} ms")
                    print(f"  占空比    : {m['duty']:.1f} %   ({m['cycles']} 周期平均)")
                else:
                    print("  信号不足")

                # 3) 边沿触发计数
                print("\n-- 边沿触发累计 --")
                print("  通道   上升沿   下降沿")
                for ch in range(NCH):
                    print(f"   D{ch}   {rise_cnt[ch]:6d}   {fall_cnt[ch]:6d}")
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        print("\n已退出")
