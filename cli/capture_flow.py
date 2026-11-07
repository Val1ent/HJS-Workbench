# -*- coding: utf-8 -*-
"""One-shot serial capture and save flow (capture3.py behavior)."""
import os
import time
from collections import Counter

import serial

import core
from . import console

POINTS = 3000


def run():
    """采集流程：选口 -> 单次采集 POINTS 点 -> 保存 .sr 文件；q 返回主菜单。"""
    while True:
        port = console.choose_port()
        if port is None:
            return
        print("2 秒后开始采集，请确认 A15 已接到 D0 ...")
        time.sleep(2)
        print(f"正在从 {port} 采集 {POINTS} 点 ...")
        t0 = time.time()
        try:
            _rate, data = core.acquire_serial(port, POINTS)
        except serial.SerialException as e:
            print("打开串口失败(关掉串口助手再试):", e)
            continue
        except Exception as e:
            print("数据不足。", e)
            print("- 若一直 in_waiting=0：设备没往这口发，确认选的是 USB-FS 口、A15->D0 接好、串口助手已关闭；")
            print("- 可拔插底部 USB 线、按 RESET 后重选端口再试。")
        else:
            print(f"共收到 {len(data)} 字节，用时 {time.time()-t0:.1f}s")
            top = Counter(data).most_common(5)
            print("最常见字节:", [(hex(k), v) for k, v in top])
            fn = os.path.join(os.getcwd(), f"capture_{int(time.time())}.sr")
            core.write_sr(fn, data)
            print("已生成:", fn)
        if input("\n回车再采一屏，q 退出: ").strip().lower() == "q":
            return
