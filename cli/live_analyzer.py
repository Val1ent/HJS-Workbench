# -*- coding: utf-8 -*-
"""Streaming analyzer screen: ASCII D0 waveform, UART decode, measurement, CSV."""
import csv
import os
import time
from collections import deque

import core
from . import console

SAMPLE_RATE   = 10000
DT            = 1.0 / SAMPLE_RATE
WINDOW        = 5000
TICKS_PER_BIT = 10
WAVE_LEN      = 100


def run():
    """独立分析终端：实时读串口，周期刷新波形 + 串口参数 + UART 解码 + 测量 + CSV。"""
    port = console.choose_port()
    if port is None:
        return
    ser = console.open_serial(port)

    csv_path = os.path.join(os.getcwd(), "analyzer_log.csv")
    csv_file = open(csv_path, "w", newline="", encoding="utf-8-sig")
    writer = csv.writer(csv_file)
    writer.writerow(["时间戳", "波特率bps", "字符周期ms", "报文长度", "解码内容"])

    raw = deque(maxlen=WINDOW)
    last_show = 0
    rows = 0
    print(f"\n已连接 {port}，独立分析中 ...（Ctrl+C 退出）\n")

    try:
        while True:
            n = ser.in_waiting
            if n:
                raw.extend(ser.read(n))
            else:
                time.sleep(0.01)

            if time.time() - last_show >= 0.5 and len(raw) >= 100:
                last_show = time.time()
                bits = [(b >> 0) & 1 for b in raw]
                pkt = core.best_packet(bits)
                if pkt:
                    seg, decoded, g = pkt
                    wave = ''.join('█' if x else '_' for x in seg[:WAVE_LEN])
                    gaps = [g[i + 1][0] - g[i][0] for i in range(len(g) - 1)]
                    char_period = (sum(gaps) / len(gaps)) * DT if gaps else 0.0
                    baud = SAMPLE_RATE / TICKS_PER_BIT
                    nchar = len(g)
                else:
                    seg = None; decoded = ""
                    wave = ''.join('█' if x else '_' for x in bits[-WAVE_LEN:])
                    char_period = 0.0; baud = 0.0; nchar = 0

                console.clear_screen()
                print("===== 独立分析终端（不依赖 PulseView）=====")
                print(f"采样率: {SAMPLE_RATE} Hz   窗口: {len(raw)} 点\n")

                print("-- 终端波形 D0 (报文开头100点=10ms) --")
                print("  高=█  低=_")
                print("  " + wave + "\n")

                print("-- 串口参数测量 --")
                if nchar:
                    print(f"  波特率 {baud:.0f} bps | 字符周期 {char_period*1000:.3f} ms | "
                          f"报文长度 {nchar} 字符 | 帧格式 8N1")
                else:
                    print("  本窗口未识别到完整报文")

                print("\n-- 自主 UART 解码 --")
                print("  接收到: " + (repr(decoded) if decoded else "(本窗口未解码出完整帧)"))

                print("\n-- D0 实时测量 --")
                m = core.measure(bits)
                if m:
                    print(f"  频率 {m['freq']:.1f} Hz | 周期 {m['period']*1000:.3f} ms | "
                          f"占空比 {m['duty']:.1f}%")
                else:
                    print("  信号不足")

                # 写 CSV
                if nchar:
                    writer.writerow([f"{time.time():.1f}", f"{baud:.0f}",
                        f"{char_period*1000:.3f}", f"{nchar}", decoded])
                    csv_file.flush()
                    rows += 1
                print(f"\n-- 数据记录 --  已写入 {rows} 行 -> {csv_path}")
    except KeyboardInterrupt:
        pass
    finally:
        csv_file.close()
        ser.close()
        print("\n已退出，CSV 已保存:", csv_path)
