# -*- coding: utf-8 -*-
"""
统一协议分析流程（对应 proto_view.py）：
  1) 实时串口：从底部 USB-FS 口采集，实时解码（与真实/自测信号配合）
  2) 离线演示：用各解码器自带的测试波形演示，无需任何硬件
"""
import time
from collections import deque

import core
from core.registry import print_events
from . import console

SAMPLE_RATE = 10000
WINDOW = 3000


def offline_demo(name):
    print(f"\n===== 离线演示：{name}（自带测试波形，无需硬件）=====")
    samples = core.DECKS[name]["make"](SAMPLE_RATE)
    events = core.DECKS[name]["decode"](samples, SAMPLE_RATE)
    print_events(events)
    print(f"\n（共 {len(samples)} 个采样点，{len(events)} 个事件）")


def live_mode(name):
    port = console.choose_port()
    if port is None:
        return
    ser = console.open_serial(port)

    raw = deque(maxlen=WINDOW)
    shown = set()           # 已打印事件去重
    last = 0
    print(f"\n已连接 {port}，实时解码【{name}】中 ...（Ctrl+C 退出）\n")
    try:
        while True:
            n = ser.in_waiting
            if n:
                raw.extend(ser.read(n))
            else:
                time.sleep(0.01)
            if time.time() - last >= 0.5 and len(raw) >= 50:
                last = time.time()
                samples = list(raw)
                events = core.DECKS[name]["decode"](samples, SAMPLE_RATE)
                for e in events:
                    key = (e["type"], e["text"], int(e["t"] * 10))
                    if key not in shown:
                        shown.add(key)
                        print(f"  {e['t']*1000:9.3f} ms  D{e['ch']}  "
                              f"{e['type']:<10} {e['text']}")
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        print("\n已退出。")


def run():
    if not core.DECKS:
        print("没有已登记的解码器，请确认 core 包中的解码器模块已加载。")
        return
    print("===== 口袋数字调试助手 · 统一协议分析 =====")
    print("  [1] 实时串口解码（需硬件）")
    print("  [2] 离线演示（自带测试波形，无需硬件）")
    mode = input("选择模式: ").strip()
    name = console.choose_decoder()
    if name is None:
        return
    if mode == "1":
        live_mode(name)
    else:
        offline_demo(name)
